#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random
import itertools
from datetime import timedelta
from datetime import datetime
from datetime import time as dttime
from collections import defaultdict
import re
import os

from alex.applications.PublicTransportInfoEN.site_preprocessing import expand_stop
from alex.components.dm import DialoguePolicy
from alex.components.dm.dddstate import D3DiscreteValue
from alex.components.nlg.tools.en import word_for_number
from alex.components.slu.da import DialogueAct, DialogueActItem
from .time_zone import GoogleTimeFinder
from .directions import GoogleDirectionsFinder, Travel
from alex.applications.utils.weather import OpenWeatherMapWeatherFinder, WeatherPoint

from alex.components.dm.gp_sarsa.gp_sarsa_episode import ApproximateEpisodicGPSarsa
from alex.utils.sample_distribution import sample_a_prob
import numpy as np

def randbool(n):
    """Randomly return True in 1 out of n cases.

    :param n: Inverted chance of returning True
    :rtype: Boolean
    """
    if random.randint(1, n) == 1:
        return True
    return False


class PTIENHDCPolicy(DialoguePolicy):
    """The handcrafted policy for the PTI-EN system."""

    def __init__(self, cfg, ontology):
        super(PTIENHDCPolicy, self).__init__(cfg, ontology)

        os.environ['TZ'] = ontology['default_values']['time_zone']
        directions_type = GoogleDirectionsFinder
        if 'directions' in cfg['DM'] and 'type' in cfg['DM']['directions']:
            directions_type = cfg['DM']['directions']['type']
        self.directions = directions_type(cfg=cfg)
        self.weather = OpenWeatherMapWeatherFinder(cfg=cfg)
        self.time = GoogleTimeFinder(cfg=cfg)
        self.infer_default_stops = directions_type == GoogleDirectionsFinder

        self.system_das = []
        self.last_system_dialogue_act = None

        self.debug = cfg['DM']['basic']['debug']
        self.session_logger = cfg['Logging']['session_logger']
        self.system_logger = cfg['Logging']['system_logger']
        self.policy_cfg = self.cfg['DM']['dialogue_policy']['PTIENHDCPolicy']
        self.accept_prob = self.policy_cfg['accept_prob']

        #initilizing the GP-Sarsa Optimiser
        self.gp_sarsa = ApproximateEpisodicGPSarsa(cfg['DM']['dialogue_policy'])
        self.turn_reward = -1
        self.success_reward = 20
        self.unsuccess_reward = 0
        self.gp_sarsa.new_episode()

    def reset_on_change(self, ds, changed_slots):
        """Reset slots which depends on changed slots.

        :param ds: dialogue state
        :param changed_slots: slots changed in the last turn
        """
        for ds_slot in ds:
            if ds_slot in changed_slots:
                # do not reset a slot which just changed
                continue

            for changed_slot in changed_slots:
                if self.ontology.reset_on_change(ds_slot, changed_slot):
                    if isinstance(ds[ds_slot], float):
                        ds[ds_slot] = 0.0
                    elif isinstance(ds[ds_slot], int):
                        ds[ds_slot] = 0
                    elif isinstance(ds[ds_slot], basestring):
                        ds[ds_slot] = "none"
                    else:
                        ds[ds_slot].reset()

                    self.system_logger.debug("Reset on change: {slot} because of {changed_slot}".format(slot=ds_slot,
                                                                                                        changed_slot=changed_slot))
                    break

    def filter_iconfirms(self, da):
        """Filter implicit confirms if the same information is uttered in an inform
        dialogue act item. Also filter implicit confirms for stop names equaling city names.
        Also check if the stop and city names are equal!

        :param da: unfiltered dialogue act
        :return: filtered dialogue act
        """
        new_da = DialogueAct()
        informs = []
        requests = []
        iconfirms = defaultdict(int)

        for dai in da:
            if dai.dat == 'inform':
                informs.append((dai.name, dai.value))
            elif dai.dat == 'request':#THANH: change to filetr also request
                requests.append(dai.name)#TODO also need to add equivalent slots, if not, implconfim(from_city)&request(from_stop) 
            elif dai.dat == 'iconfirm':
                iconfirms[(dai.name, dai.value)] += 1

        for dai in da:
            if dai.dat == 'iconfirm':
                if dai.name in requests:
                    continue
                # filter slots explicitly informed
                if (dai.name, dai.value) in informs:
                    continue
                # filter repeating iconfirms
                elif iconfirms[dai.name, dai.value] > 1:
                    iconfirms[dai.name, dai.value] -= 1
                    continue
                # filter mistakenly added iconfirms that have an unset/meaningless value
                elif dai.value is None or dai.value in ['none', '*']:
                    continue
                # filter stop names that are the same as city names
                elif dai.name.endswith('_stop'):
                    city_dai = dai.name[:-4] + 'city'
                    if (city_dai, dai.value) in informs or iconfirms[(city_dai, dai.value)]:
                        continue
                # filter state names that are the same as city names
                elif dai.name.endswith('_state'):
                    city_dai = dai.name[:-5] + 'city'
                    if (city_dai, dai.value) in informs or iconfirms[(city_dai, dai.value)]:
                        continue

            new_da.append(dai)

        return new_da

    def get_da(self, dialogue_state):
        """The main policy decisions are made here. For each action, some set of conditions must be met. These
         conditions depends on the action.

        :param dialogue_state: the belief state provided by the tracker
        :return: a dialogue act - the system action
        """

        ludait_prob, last_user_dai_type = dialogue_state["ludait"].mph()
        if ludait_prob < self.policy_cfg['accept_prob_ludait']:
            last_user_dai_type = 'none'

        # all slots being requested by the user
        slots_being_requested = dialogue_state.get_slots_being_requested(self.policy_cfg['accept_prob_being_requested'])
        # all slots being confirmed by the user
        slots_being_confirmed = dialogue_state.get_slots_being_confirmed(self.policy_cfg['accept_prob_being_confirmed'])
        # all slots supplied by the user but not implicitly confirmed
        noninformed_slots = dialogue_state.get_slots_being_noninformed(self.policy_cfg['accept_prob_noninformed'])
        # all slots deemed to be accepted
        accepted_slots = dialogue_state.get_accepted_slots(self.accept_prob)
        # all slots that should be confirmed
        slots_tobe_confirmed = dialogue_state.get_slots_tobe_confirmed(self.policy_cfg['confirm_prob'], self.accept_prob)
        #  filter out all the slots that are not defined by the ontology to be confirmed
        slots_tobe_confirmed = {k: v for k, v in slots_tobe_confirmed.items() if k in self.ontology.slots_system_confirms()}
        # all slots for which the policy can use ``select`` DAI
        slots_tobe_selected = dialogue_state.get_slots_tobe_selected(self.policy_cfg['select_prob'])
        #  filter out all the slots that are not defined by the ontology to be selected
        slots_tobe_selected = {k: v for k, v in slots_tobe_selected.items() if k in self.ontology.slots_system_selects()}
        # all slots changed by a user in the last turn
        changed_slots = dialogue_state.get_changed_slots(self.accept_prob)
        # did the state changed at all?
        has_state_changed = dialogue_state.has_state_changed(self.policy_cfg['min_change_prob'])

        if self.debug:
            s = []
            s.append('PTIENHDCPolicy - Slot stats')
            s.append("")
            s.append("ludait:                 %s" % unicode(last_user_dai_type))
            s.append("Slots being requested:  %s" % unicode(slots_being_requested))
            s.append("Slots being confirmed:  %s" % unicode(slots_being_confirmed))
            s.append("Non-informed slots:     %s" % unicode(noninformed_slots))
            s.append("")
            s.append("Accepted slots:         %s" % unicode(accepted_slots))
            s.append("Slots to be confirmed:  %s" % unicode(slots_tobe_confirmed))
            s.append("Slots to be selected:   %s" % unicode(slots_tobe_selected))
            s.append("Changed slots:          %s" % unicode(changed_slots))
            s.append("State changed?          %s" % unicode(has_state_changed))
            s = '\n'.join(s)

            self.system_logger.debug(s)

        # output DA
        res_da = None

        # reset all slots depending on changed slots
        self.reset_on_change(dialogue_state, changed_slots)

        # These facts are used in the dialog-controlling conditions that follow.
        # They are named so that the dialog-controlling code is more readable.o
        fact = {
            'max_turns_exceeded': dialogue_state.turn_number > self.cfg[
                'PublicTransportInfoEN']['max_turns'],
            'dialog_begins': len(self.system_das) == 0,
            'user_did_not_say_anything': last_user_dai_type == "silence",
            'user_said_bye': "lta_bye" in accepted_slots,
            'we_did_not_understand': last_user_dai_type == "null" or
                                     last_user_dai_type == "other",
            'user_wants_help': last_user_dai_type == "help",
            'user_thanked': last_user_dai_type == "thankyou",
            'user_wants_restart': last_user_dai_type == "restart",
            'user_wants_us_to_repeat': last_user_dai_type == "repeat",
            'there_is_something_to_be_selected': bool(slots_tobe_selected),
            'there_is_something_to_be_confirmed': bool(slots_tobe_confirmed),
            'user_wants_to_know_the_time': 'current_time' in
                                           slots_being_requested,
            #'user_wants_to_know_the_weather': dialogue_state[
            'user_wants_to_know_the_weather': dialogue_state[
                'task'].test('weather', self.accept_prob),
            'user_wants_to_find_the_platform': dialogue_state[
                'lta_task'].test('find_platform', self.accept_prob),
        }


        # topic-independent behavior
        if fact['max_turns_exceeded']:
            # Hang up if the talk has been too long
            res_da = DialogueAct('bye()&inform(toolong="true")')

        elif fact['dialog_begins']:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            res_da = DialogueAct("hello()")

        elif fact['user_did_not_say_anything']:
            # at this moment the silence and the explicit null act
            # are treated the same way: NLG("")
            silence_time = dialogue_state['silence_time']

            if silence_time > self.cfg['DM']['basic']['silence_timeout']:
                res_da = DialogueAct('inform(silence_timeout="true")')
            else:
                res_da = DialogueAct("silence()")
            dialogue_state["ludait"].reset()

        elif fact['user_said_bye']:
            # NLG("Na shledanou.")
            res_da = DialogueAct("bye()")
            dialogue_state["ludait"].reset()
            dialogue_state["lta_bye"].reset()

        elif fact['we_did_not_understand']:
            # NLG("Sorry, I did not understand. You can say...")
            res_da = DialogueAct("notunderstood()")
            if randbool(5):
                res_da.extend(self.get_limited_context_help(dialogue_state))
            dialogue_state["ludait"].reset()

        elif fact['user_wants_help']:
            # NLG("Help.") based on context
            res_da = self.get_help_res_da(dialogue_state, accepted_slots, has_state_changed)
            # res_da = DialogueAct("help()")
            dialogue_state["ludait"].reset()

        elif fact['user_thanked']:
            # NLG("Díky.")
            if not changed_slots:  # plain thank you, nothing else said
                dialogue_state.restart()
            res_da = DialogueAct('inform(cordiality="true")&hello()')
            dialogue_state["ludait"].reset()

        elif fact['user_wants_restart']:
            # NLG("Dobře, zančneme znovu. Jak Vám mohu pomoci?")
            dialogue_state.restart()
            res_da = DialogueAct("restart()&hello()")
            dialogue_state["ludait"].reset()

        elif fact['user_wants_us_to_repeat']:
            # NLG - use the last dialogue act
            res_da = DialogueAct("irepeat()")
            dialogue_state["ludait"].reset()

        elif fact['user_wants_to_know_the_time']==False and fact['user_wants_to_know_the_weather']==False:
            #THANH, ask system repeat itself when chosen uncorrect act
            res_da = None
            repeated_count = 0
            while res_da is None or res_da.has_dat('cant_apply'):
                if res_da is not None: print '---GP-Sarsa choose: something wrong, cant_apply'
                res_da = self.get_gp_res_da(dialogue_state, changed_slots, accepted_slots, last_user_dai_type, slots_being_requested, slots_being_confirmed, has_state_changed)
                repeated_count +=1
            if repeated_count >=1000:
                print 'Choo 1000 times could find a act'
                import sys
                sys.exit()

        elif fact['there_is_something_to_be_confirmed']:#TODO: THANH
            # implicitly confirm all changed slots
            res_da = self.get_iconfirm_info(changed_slots)
            # confirm all slots that are not certain
            res_da.extend(self.confirm_info(slots_tobe_confirmed))
            res_da = self.filter_iconfirms(res_da)

        elif fact['user_wants_to_know_the_time']:#TODO THANH
            # Respond to questions about current time
            # TODO: allow combining with other questions?
            res_da = self.get_current_time_res_da(dialogue_state, accepted_slots, has_state_changed)

        # topic-dependent
        elif fact['user_wants_to_know_the_weather']:#TODO THANH
            # implicitly confirm all changed slots
            res_da = self.get_iconfirm_info(changed_slots)

            # talk about weather
            w_da = self.get_weather_res_da(dialogue_state, last_user_dai_type, slots_being_requested, slots_being_confirmed,
                                           accepted_slots, changed_slots, has_state_changed)
            res_da.extend(w_da)
            res_da = self.filter_iconfirms(res_da)
        else:#TODO: THANH Public infor ofer
            # implicitly confirm all changed slots
            #todo: refactoring (place, area) - remove this hack - streets share stop slot so we don't have to generate more nlg templates
            changed_slots = self.fix_stop_street_slots(changed_slots)
            res_da = self.get_iconfirm_info(changed_slots)
            # talk about public transport
            t_da = self.get_connection_res_da(dialogue_state, last_user_dai_type, slots_being_requested, slots_being_confirmed,
                                              accepted_slots, changed_slots, has_state_changed)
            res_da.extend(t_da)
            res_da = self.filter_iconfirms(res_da)

        self.last_system_dialogue_act = res_da

        # record the system dialogue acts
        self.system_das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act

    def get_gp_res_da(self, dialogue_state, changed_slots, accepted_slots, last_user_dai_type, slots_being_requested, slots_being_confirmed, has_state_changed):
        #-----------------------------the GP-Sarsa take stage for the transport information
        print 'Going to GP-Sarsa'
        ds = dialogue_state
        #print '------------DS--------'
        #print ds
        #print '------------DS--------'
        belief_features = self._extract_features(dialogue_state)
        sys_da = self.gp_sarsa.get_act(belief_features, self.turn_reward)
        print 'GP-Sarsa: sys_da:', sys_da
        import pdb
        if sys_da=='request':
            ret_da, iconfirm_da, conn_info = self.gather_connection_info(ds, accepted_slots, belief_features)
            #pdb.set_trace()
        elif sys_da=='select':
            #changed_slots = dialogue_state.get_changed_slots(0.0)#0.0 is not realy matter in this case, since only ask from_stop and to_stop
            #slots_tobe_selected = self.get_slots_tobe_selected(ds, self.policy_cfg['select_prob'], 1.0)
            slots_tobe_selected = self.get_slots_tobe_selected(ds, self.policy_cfg['select_prob'], self.accept_prob)

            #slots_tobe_selected = {k: v for k, v in slots_tobe_selected.items() if k in self.ontology.slots_system_selects()}
            if 'task' in slots_tobe_selected.keys():
                slots_tobe_selected.pop('task')
            print "slot tobe selected", slots_tobe_selected.keys()
            ret_da = self.select_info(slots_tobe_selected)
            #pdb.set_trace()
        elif sys_da=='confirm':
            #change to build the confirm act
            #slots_tobe_confirmed = self.get_slots_tobe_confirmed(ds, self.policy_cfg['confirm_prob'], 1.0)
            slots_tobe_confirmed = self.get_slots_tobe_confirmed(ds, self.policy_cfg['confirm_prob'], self.accept_prob)
            slots_tobe_confirmed = {k: v for k, v in slots_tobe_confirmed.items() if k in self.ontology.slots_system_confirms()}
            print "slot tobe confirm", slots_tobe_confirmed.keys()
            ret_da = self.confirm_info(slots_tobe_confirmed)
            #pdb.set_trace()
        elif sys_da=='implconfirm':
            #changed_slots = self.fix_stop_street_slots(changed_slots)
            changed_slots = dialogue_state.get_changed_slots(0.0)#0.0 is not realy matter in this case, since only ask from_stop and to_stop
            ret_da = self.get_iconfirm_info(changed_slots)
            print '-*implconfirm acts:', ret_da
            #pdb.set_trace()
            req_da, iconfirm_da, conn_info = self.gather_connection_info(ds, accepted_slots, belief_features)
            ret_da.extend(req_da)
            ret_da = self.filter_iconfirms(ret_da)
            #TODO: Check sometims should be implconfirm, slots are available, but not implconfirm, only request???
            #print 'implconfirm acts after add request'
            #pdb.set_trace()
        elif sys_da=='offer':
            #=============thanh: changes for evaluating, must remove to run normally======
            if belief_features[2]==0 or belief_features[4]==0:
                ret_da = DialogueAct()
            else:
                '''---Real interaction with user
                changed_slots = self.fix_stop_street_slots(changed_slots)
                res_da = self.get_iconfirm_info(changed_slots)
                # talk about public transport
                t_da = self.get_connection_res_da(dialogue_state, last_user_dai_type, slots_being_requested, slots_being_confirmed,
                                              accepted_slots, changed_slots, has_state_changed)
                res_da.extend(t_da)
                ret_da = self.filter_iconfirms(res_da)
                '''#----intreact with simulator
                ret_da = self._thanh_offer_route(ds)
        else:
            raise NotImplementedError("Not implement handler for the GP-Sarsa [sys_da=%s]"%sys_da)
        #print 'GP_Sarsa final acts:', ret_da
        if len(ret_da)==0:
            print 'GP-Sarsa return empty act?????'
            ret_da = DialogueAct('cant_apply()')
        res_da = ret_da
        print '-*final_acts:', res_da

        return res_da

    def get_connection_res_da(self, ds, ludait, slots_being_requested, slots_being_confirmed,
                              accepted_slots, changed_slots, state_changed):
        """Handle the public transport connection dialogue topic.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        # output DA
        res_da = None
        if ludait == "reqalts":
            # NLG("There is nothing else in the database.")
            # NLG("The next connection is ...")
            res_da = self.get_an_alternative(ds)
            ds["ludait"].reset()
        elif "alternative" in accepted_slots:
            # Search for traffic direction and/or present the requested directions already found, take into account additional requests (dep_time etc.)
            res_da = self.get_requested_alternative(ds, slots_being_requested, accepted_slots)
            ds["alternative"].reset()

        elif slots_being_requested:
            # inform about all requested slots
            res_da = self.get_requested_info(slots_being_requested, ds, accepted_slots)

        elif slots_being_confirmed:
            # inform about all slots being confirmed by the user
            res_da = self.get_confirmed_info(slots_being_confirmed, ds, accepted_slots)

        else:
            # gather known information about the connection
            req_da, iconfirm_da, conn_info = self.gather_connection_info(ds, accepted_slots)
            if True or len(req_da) == 0:
                if True or state_changed:
                    # we know everything we need -> start searching
                    ds.conn_info = conn_info
                    res_da = iconfirm_da
                    res_da.extend(self.get_directions(ds, check_conflict=True))
                else:
                    res_da = self.backoff_action(ds)
            else:
                res_da = req_da

        return res_da

    def _thanh_offer_route(self, ds):
        slots=['from_stop', 'to_stop', 'from_city', 'to_city', 'from_street', 'to_street', 'departure_time', 'arrival_time', 'departure_time_rel', 'arrival_time_rel','vehicle', 'from_borough', 'to_borough']
        defaults = {'task': 'find_connection', 'departure_time':'now', 'arrival_time':'now', 'vehicle':'dontcare'} 
        ret_da = DialogueAct()
        ret_da.append(DialogueActItem('offer', 'task', 'find_connection'))
        for s in slots:
            value = 'none'
            #print 'choo values for ', s
            for v, p in ds[s].items():
                #print v, p
                if v=='none':
                    continue
                else:
                    value = v
                    break
            if value == 'none':
                if s in defaults.keys():
                    value = defaults[s]
                else:
                    continue
            ret_da.append(DialogueActItem('offer', s, value))
        #print 'To offer:', ret_da
        #import pdb
        #pdb.set_trace()
        return ret_da

    def get_weather_res_da(self, ds, ludait, slots_being_requested, slots_being_confirmed,
                           accepted_slots, changed_slots, state_changed):
        """Handle the dialogue about weather.

        :param ds: The current dialogue state
        :param slots_being_requested: The slots currently requested by the user
        :rtype: DialogueAct
        """
        # collect all necesary information
        req_da, ref_point = self.gather_weather_info(ds, accepted_slots)
        if len(req_da):
            return req_da

        # check if it is valid information
        apology_da = self.check_city_state_conflict(ref_point.in_city, ref_point.in_state)
        if apology_da is not None:
            return apology_da

        # obtain the weather if have not done so in previous turn
        if state_changed:
            res_da = self.get_weather(ds, ref_point)
        else:
            res_da = self.backoff_action(ds)
        return res_da

    def get_current_time_res_da(self, ds, accepted_slots, state_changed):
        """Generates a dialogue act informing about the current time.
        :rtype: DialogueAct
        """

        req_da, in_city, in_state, lon, lat = self.gather_time_info(ds, accepted_slots)

        if len(req_da):
            return req_da

        # check for valid input
        if in_city != 'none':
            apology_da = self.check_city_state_conflict(in_city, in_state)
            if apology_da is not None:
                return apology_da

        # if state_changed:
        res_da = self.get_current_time(in_city, in_state, lon, lat)
        # else:
        #     res_da = self.backoff_action(ds)
        return res_da

    def get_weather(self, ds, ref_point = None):
        """Retrieve weather information according to the current dialogue state.
        Infers state names based on city names and vice versa.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        # get dialogue state values
        time_abs = ds['time'].mpv()
        time_rel = ds['time_rel'].mpv()
        date_rel = ds['date_rel'].mpv()
        ampm = ds['ampm'].mpv()
        lta_time = ds['lta_time'].mpv()
        in_city = ref_point.in_city#ds['in_city'].mpv()
        in_state = ref_point.in_state#ds['in_state'].mpv()

        # return the result
        res_da = DialogueAct()

        # interpret time
        daily = (time_abs == 'none' and ampm == 'none' and date_rel != 'none' and lta_time != 'time_rel')
        # check if any time is set to distinguish current/prediction
        weather_ts = None
        if time_abs != 'none' or time_rel != 'none' or ampm != 'none' or date_rel != 'none':
            weather_ts, time_type = self.interpret_time(time_abs, ampm, time_rel, date_rel, lta_time)
        else:
            time_type = ""

        # request the weather
        weather = self.weather.get_weather(time=weather_ts, daily=daily, city=in_city, state=in_state)
        # check errorscale
        if weather is None:
            return DialogueAct('apology()&inform(in_city="%s")&inform(in_state="%s")' % (in_city, in_state))
        # time
        if weather_ts:
            if time_type == 'rel':
                res_da.append(DialogueActItem('inform', 'time_rel', time_rel))
            else:
                if time_abs != 'none' or ampm != 'none':
                    res_da.append(DialogueActItem('inform', 'time', weather_ts.strftime("%I:%M:%p"))) # is time right?
                if date_rel != 'none':
                    res_da.append(DialogueActItem('inform', 'date_rel', date_rel))
        else:
            res_da.append(DialogueActItem('inform', 'time_rel', 'now'))
        # temperature
        if not daily:
            res_da.append(DialogueActItem('inform', 'temperature', str(weather.temp)))
        else:
            res_da.append(DialogueActItem('inform', 'min_temperature', str(weather.min_temp)))
            res_da.append(DialogueActItem('inform', 'max_temperature', str(weather.max_temp)))
        # weather conditions
        res_da.append(DialogueActItem('inform', 'weather_condition', weather.condition))
        return res_da

    def get_current_time(self, in_city, in_state, longitude, latitude):

        place = in_city + "," + in_state if in_city != 'none' else in_state
        if longitude and latitude:
            cur_time, time_zone = self.time.get_time(place=place, lat=latitude, lon=longitude)
        else:
            cur_time, time_zone = self.time.get_time(place=place)
        if cur_time is None:
            default_time = datetime.now()
            default_state = self.ontology.get_default_value('in_state')
            d_time = default_time.strftime("%I:%M:%p")
            if in_state is not default_state:
                return DialogueAct('apology()&inform(in_state="%s")&inform(current_time=%s)&iconfirm(in_state=%s)' % (in_state, d_time, default_state))
            else:
                return DialogueAct('inform(current_time=%s)&iconfirm(in_state="%s")' % (d_time, default_state))


        res_da = DialogueAct()
        res_da.append(DialogueActItem('iconfirm', 'in_state', in_state))
        res_da.append(DialogueActItem('inform', 'current_time', cur_time.strftime("%I:%M:%p")))
        res_da.append(DialogueActItem('inform', 'time_zone',  time_zone))

        return res_da

    def backoff_action(self, ds):
        """Generate a random backoff dialogue act in case we don't know what to do.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        if randbool(10):
            return self.get_limited_context_help(ds)
        elif randbool(9):
            return DialogueAct('reqmore()')
        elif randbool(8):
            return DialogueAct('notunderstood()')
        elif randbool(3):
            return DialogueAct('irepeat()')
        return DialogueAct('silence()')

    def get_an_alternative(self, ds):
        """Return an alternative route, if there is one, or ask for
        origin stop if there has been no route searching so far.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        if 'route_alternative' not in ds:
            return DialogueAct('request(from_stop)')
        else:
            ds['route_alternative'] += 1
            ds['route_alternative'] %= len(ds.directions) if ds.directions is not None else 1
            return self.get_directions(ds)

    def get_requested_alternative(self, ds, slots_being_requested, accepted_slots):
        """Return the requested route (or inform about not finding one).

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        if not 'route_alternative' in ds:
            if slots_being_requested:  # just waste the requested slots for not to carry them to the next round
                self.get_requested_info(slots_being_requested, ds, accepted_slots)
            return DialogueAct('inform(stop_conflict="no_stops")')
        else:
            ds_alternative = ds["alternative"].mpv()
            type = ds_alternative
            if ds_alternative == "next":
                increment = 1
            elif ds_alternative == "prev":
                increment = -1
            elif ds_alternative in ['last', 'dontcare']:
                increment = 0
            else:
                increment = int(ds_alternative) - ds["route_alternative"] - 1
                type = "true"

            ds["route_alternative"] += increment
            try:
                if ds['route_alternative'] < 0:
                    raise Exception()
                ds.directions[ds['route_alternative']] # just for failing
            except:
                ds["route_alternative"] -= increment
                if slots_being_requested:  # just waste the requested slots for not to carry them to the next round
                    self.get_requested_info(slots_being_requested, ds, accepted_slots)
                return DialogueAct('inform(found_directions="no_%s")' % type)

            if slots_being_requested:
                res_da.append(DialogueActItem('inform', 'alternative', word_for_number(ds['route_alternative'] + 1, True)))
                res_da.extend(self.get_requested_info(slots_being_requested, ds, accepted_slots))
                ds["route_alternative"] -= increment
                return res_da

            res_da.extend(self.get_directions(ds, type))
            # ds["route_alternative"] -= increment
            return res_da

    def get_requested_info(self, requested_slots, ds, accepted_slots):
        """Return a DA containing information about all requested slots.

        :param ds: The current dialogue state
        :param requested_slots: A dictionary with keys for all requested \
                slots and the correct return values.
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in requested_slots:
            if ds['route_alternative'] in [0, 1, 2, 3]:
                if slot == 'from_stop':
                    res_da.extend(self.req_from_stop(ds))
                elif slot == 'to_stop':
                    res_da.extend(self.req_to_stop(ds))
                elif slot == 'departure_time':
                    res_da.extend(self.req_departure_time(ds))
                elif slot == 'departure_time_rel':
                    res_da.extend(self.req_departure_time_rel(ds))
                elif slot == 'arrival_time':
                    res_da.extend(self.req_arrival_time(ds))
                elif slot == 'arrival_time_rel':
                    res_da.extend(self.req_arrival_time_rel(ds))
                elif slot in 'duration':
                    res_da.extend(self.req_duration(ds))
                elif slot == "num_transfers":
                    res_da.extend(self.req_num_transfers(ds))
                elif slot == "time_transfers":
                    res_da.extend(self.req_time_transfers(ds))
                elif slot == "distance":
                    res_da.extend(self.req_distance(ds))
            else:
                if slot in ['from_stop', 'to_stop',
                            'departure_time', 'departure_time_rel',
                            'arrival_time', 'arrival_time_rel',
                            'duration', 'num_transfers', 'time_transfers', 'distance' ]:
                    dai = DialogueActItem("inform", "stops_conflict", "no_stops")
                    res_da.append(dai)

                    if 'from_stop' not in accepted_slots:
                        dai = DialogueActItem("help", "inform", "from_stop")
                        res_da.append(dai)
                    elif 'to_stop' not in accepted_slots:
                        dai = DialogueActItem("help", "inform", "to_stop")
                        res_da.append(dai)
                else:
                    dai = DialogueActItem("inform", slot, requested_slots[slot])
                    res_da.append(dai)
                    ds["rh_" + slot].reset()

            ds["rh_" + slot].reset()

        return res_da

    def get_confirmed_info(self, confirmed_slots, ds, accepted_slots):
        """Return a DA containing information about all slots being confirmed
        by the user (confirm/deny).

        Update the current dialogue state regarding the information provided.

        *WARNING* This confirms only against values in the dialogue state, however, it should (also in some cases)
        confirm against the results obtained from database, e.g. departure_time slot.

        :param ds: The current dialogue state
        :param confirmed_slots: A dictionary with keys for all slots \
                being confirmed, along with their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in confirmed_slots:
            if confirmed_slots[slot].mpv() == ds[slot].mpv():
                # it is as user expected
                res_da.append(DialogueActItem("affirm"))
                dai = DialogueActItem("inform", slot, ds[slot].mpv())
                res_da.append(dai)
            else:
                # it is something else than what user expected
                res_da.append(DialogueActItem("negate"))
                dai = DialogueActItem("deny", slot, ds["ch_" + slot].mpv())
                res_da.append(dai)

                if slot in accepted_slots:
                    dai = DialogueActItem("inform", slot, ds[slot].mpv())
                    res_da.append(dai)

            ds["ch_" + slot].reset()

        return res_da

    def confirm_info(self, tobe_confirmed_slots):
        """Return a DA containing confirming only one slot from the slot to be confirmed.
        Confirm the slot with the most probable value among all slots to be confirmed.

        :param tobe_confirmed_slots: A dictionary with keys for all slots \
                that should be confirmed, along with their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()
        #TODO change like select infor, only consider about values not None, change the code but not check????
        #for _, slot in sorted([(h.mpvp(), s)  for s, h in tobe_confirmed_slots.items()], reverse=False):#THANH: change to confirm slot lowest prob
        for _, slot in sorted([(h.topn(1)[0][1], s)  for s, h in tobe_confirmed_slots.items()], reverse=False):#THANH: change to confirm slot lowest prob
            #dai = DialogueActItem("confirm", slot, tobe_confirmed_slots[slot].mpv())
            #THANH
            dai = DialogueActItem("confirm", slot, tobe_confirmed_slots[slot].topn(1)[0][0])

            res_da.append(dai)
            #confirm explicitly only one slot at the time
            break
        return res_da

    def select_info(self, tobe_selected_slots):
        """Return a DA containing select act for two most probable values of only one slot
        from the slot to be used for select DAI.

        :param tobe_selected_slots: A dictionary with keys for all slots \
                which the two most probable values should be selected
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        #for slot in tobe_selected_slots:
        #for _, slot in sorted([(h.mpvp(), s)  for s, h in tobe_selected_slots.items()], reverse=False):#THANH: change to false select lowers prob
        for _, slot in sorted([(h.topn(1)[0][1], s)  for s, h in tobe_selected_slots.items()], reverse=False):#THANH: change to false select lowers prob
            #val1, val2 = tobe_selected_slots[slot].tmpvs()
            #THANH
            topn = tobe_selected_slots[slot].topn(2)
            (val1, _), (val2, _) = topn

            res_da.append(DialogueActItem("select", slot, val1))
            res_da.append(DialogueActItem("select", slot, val2))
            #select values only in one slot at the time
            break
        return res_da

    def get_iconfirm_info(self, changed_slots):
        """Return a DA containing all needed implicit confirms.

        Implicitly confirm all slots provided but not yet confirmed.

        This include also slots changed during the conversation.

        :param changed_slots: A dictionary with keys for all slots \
                that have not been implicitly confirmed, along with \
                their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        if changed_slots:
            iconf_da = DialogueAct()
            for slot in changed_slots:
                if 'system_iconfirms' in self.ontology['slot_attributes'][slot]:
                    dai = DialogueActItem("iconfirm", slot, changed_slots[slot].mpv())
                    iconf_da.append(dai)
            res_da.extend(iconf_da)
        return res_da

    def get_default_stop_for_city(self, city):
        """Return a `default' stop based on the city name (main bus/train station).

        :param city: city name (unicode)
        :rtype: unicode
        """
        stops = self.ontology.get_compatible_vals('city_stop', city)
        for cand_stop_name in [city, 'Hlavní nádraží', 'CAN, Husova']:
            if cand_stop_name in stops:
                return cand_stop_name
        for cand_stop_suffix in [' main station', ' city', ]:
            stop = city + cand_stop_suffix
            if stop in stops:
                return stop
        return None

    def get_accepted_mpv(self, ds, slot_name, accepted_slots):
        """Return a slot's 'mpv()' (most probable value) if the slot is accepted, and
        return 'none' otherwise.
        Also, convert a mpv of '*' to 'none' since we don't know how to interpret it.

        :param ds: Dialogue state
        :param slot_name: The name of the slot to query
        :param accepted_slots: The currently accepted slots of the dialogue state
        :rtype: string
        """
        val = 'none'
        if slot_name in accepted_slots:
            val = ds[slot_name].mpv()
            if val == '*':
                val = 'none'
        return val

    def gather_connection_info(self, ds, accepted_slots, belief_features=None):
        """Return a DA requesting further information needed to search
        for traffic directions and a dictionary containing the known information.
        Infers city names based on stop names and vice versa.

        If the request DA is empty, the search for directions may be commenced immediately.

        :param ds: The current dialogue state
        :rtype: DialogueAct, dict
        """
        req_da = DialogueAct()

        # retrieve the slot variables
        from_city_val = self.get_accepted_mpv(ds, 'from_city', accepted_slots)
        from_borough_val = self.get_accepted_mpv(ds, 'from_borough', accepted_slots)
        from_stop_val = self.get_accepted_mpv(ds, 'from_stop', accepted_slots)
        from_street_val = self.get_accepted_mpv(ds, 'from_street', accepted_slots)
        from_street2_val = self.get_accepted_mpv(ds, 'from_street2', accepted_slots)
        to_city_val = self.get_accepted_mpv(ds, 'to_city', accepted_slots)
        to_borough_val = self.get_accepted_mpv(ds, 'to_borough', accepted_slots)
        to_stop_val = self.get_accepted_mpv(ds, 'to_stop', accepted_slots)
        to_street_val = self.get_accepted_mpv(ds, 'to_street', accepted_slots)
        to_street2_val = self.get_accepted_mpv(ds, 'to_street2', accepted_slots)
        vehicle_val = self.get_accepted_mpv(ds, 'vehicle', accepted_slots)
        max_transfers_val = self.get_accepted_mpv(ds, 'num_transfers', accepted_slots)

        # retrieve the slot variables values except none
        #'''
        from_city_val = self.get_top1_value(ds, 'from_city')
        from_borough_val = self.get_top1_value(ds, 'from_borough')
        from_stop_val = self.get_top1_value(ds, 'from_stop')
        from_street_val = self.get_top1_value(ds, 'from_street')
        from_street2_val = self.get_top1_value(ds, 'from_street2')
        to_city_val = self.get_top1_value(ds, 'to_city')
        to_borough_val = self.get_top1_value(ds, 'to_borough')
        to_stop_val = self.get_top1_value(ds, 'to_stop')
        to_street_val = self.get_top1_value(ds, 'to_street')
        to_street2_val = self.get_top1_value(ds, 'to_street2')
        vehicle_val = self.get_top1_value(ds, 'vehicle')
        max_transfers_val = self.get_top1_value(ds, 'num_transfers')

        # infer cities based on stops
        from_cities, to_cities = None, None
        stop_city_inferred = False
        if from_stop_val != 'none' and from_city_val == 'none':
            from_cities = self.ontology.get_compatible_vals('stop_city', from_stop_val)
            if len(from_cities) == 1:
                from_city_val = from_cities.pop()
                stop_city_inferred = True
        if to_stop_val != 'none' and to_city_val == 'none':
            to_cities = self.ontology.get_compatible_vals('stop_city', to_stop_val)
            if len(to_cities) == 1:
                to_city_val = to_cities.pop()
                stop_city_inferred = True

        # infer cities based on stops
        from_boroughs, to_boroughs = None, None
        stop_borough_inferred = False
        if from_stop_val != 'none' and from_borough_val == 'none':
            from_boroughs = self.ontology.get_compatible_vals('stop_borough', from_stop_val)
            if len(from_boroughs) == 1:
                from_borough_val = from_boroughs.pop()
                stop_borough_inferred = True
        if to_stop_val != 'none' and to_borough_val == 'none':
            to_boroughs = self.ontology.get_compatible_vals('stop_borough', to_stop_val)
            if len(to_boroughs) == 1:
                to_borough_val = to_boroughs.pop()
                stop_borough_inferred = True

        # infer boroughs based on streets
        from_boroughs_st, to_boroughs_st = None, None
        street_borough_inferred = False
        if to_street_val != 'none' and to_borough_val == 'none':
            to_boroughs_st = self.ontology.get_compatible_vals('street_borough', to_street_val)
            if len(to_boroughs_st) == 1:
                to_borough_val = to_boroughs_st.pop()
                street_borough_inferred = True
        if from_street_val != 'none' and from_borough_val == 'none':
            from_boroughs_st = self.ontology.get_compatible_vals('street_borough', from_street_val)
            if len(from_boroughs_st) == 1:
                from_borough_val = from_boroughs_st.pop()
                street_borough_inferred = True


        # infer cities based on each other
        if from_stop_val != 'none' and from_city_val == 'none' and to_city_val in from_cities:
            from_city_val = to_city_val
        elif to_stop_val != 'none' and to_city_val == 'none' and from_city_val in to_cities:
            to_city_val = from_city_val

        # infer boroughs based on each other
        # from stops
        if from_stop_val != 'none' and from_borough_val == 'none' and to_borough_val in from_boroughs:
            from_borough_val = to_borough_val
        elif to_stop_val != 'none' and to_borough_val == 'none' and from_borough_val in to_boroughs:
            to_borough_val = from_borough_val
        # from streets
        if from_street_val != 'none' and from_borough_val == 'none' and to_borough_val in from_boroughs_st:
            from_borough_val = to_borough_val
        elif to_street_val != 'none' and to_borough_val == 'none' and from_borough_val in to_boroughs_st:
            to_borough_val = from_borough_val

        # try to infer cities from intersection
        if to_cities is not None and from_cities is not None and from_city_val == 'none' and to_city_val == 'none':
            intersect_c = [c for c in from_cities if c in to_cities]
            if len(intersect_c) == 1:
                from_city_val = intersect_c.pop()
                to_city_val = from_city_val
                stop_city_inferred = True

        # try infer boroughs from intersection
        if to_boroughs is not None and from_boroughs is not None and from_borough_val == 'none' and to_borough_val == 'none':
            intersect_b = [b for b in from_boroughs if b in to_boroughs]
            if len(intersect_b) == 1:
                from_borough_val = intersect_b.pop()
                to_borough_val = from_borough_val
                stop_borough_inferred = True
        if to_boroughs_st is not None and from_boroughs_st is not None and from_borough_val == 'none' and to_borough_val == 'none':
            intersect_bs = [b for b in from_boroughs_st if b in to_boroughs_st]
            if len(intersect_bs) == 1:
                from_borough_val = intersect_bs.pop()
                to_borough_val = from_borough_val
                street_borough_inferred = True

        # place can be specified by street or stop and area by city or borough or another street
        has_from_place = from_stop_val != 'none' or from_street_val != 'none' or from_city_val not in ['none', 'New York']
        has_from_area = from_borough_val !='none' or from_street2_val != 'none' or from_city_val != 'none'
        from_info_complete = has_from_place and has_from_area
                             
        has_to_place = to_stop_val != 'none' or to_street_val != 'none' or to_city_val not in ['none', 'New York']
        has_to_area = to_borough_val !='none' or to_street2_val != 'none' or to_city_val != 'none'

        # hack for from CITY to CITY and allowing New York as one of them
        if (has_to_area and has_from_area) and from_city_val != to_city_val:
            has_to_place = True
            has_from_place = True

        to_info_complete = has_to_place and has_to_area
        
        if not from_info_complete and not to_info_complete and \
                        'departure_time' not in accepted_slots and 'time' not in accepted_slots and randbool(10):
            req_da.extend(DialogueAct('request(departure_time)'))
        elif True and belief_features is not None:#THANH change to ask a slot without default values which has lowest probability
            #NOTE have to change indexes manually if the feature change
            from_id = 2
            to_id = 4
            certain_level = (belief_features[from_id]+belief_features[to_id])/2.0
            if belief_features[12]==0 or sample_a_prob(1-certain_level):#no thing about frm/stop place has been filled or it still uncertain
                if belief_features[from_id]<=belief_features[to_id]:
                    req_da.extend(DialogueAct('request(from_stop)'))
                else:
                    req_da.extend(DialogueAct('request(to_stop)'))
            else:
                infers = self.places_inferred(ds)
                if infers[0]==0:#ambiguity in from_city
                    req_da.extend(DialogueAct('request(from_city)'))
                elif infers[1]==0: #ambiguity in to_city
                    req_da.extend(DialogueAct('request(to_city)'))
                elif infers[2]==0: #ambiguity in from_borough
                    req_da.extend(DialogueAct('request(from_borough)'))
                elif infers[3]==0: #ambiguity in to_borough
                    req_da.extend(DialogueAct('request(to_borough)'))
                else:
                    if belief_features[from_id]<=belief_features[to_id]:
                        req_da.extend(DialogueAct('request(from_stop)'))
                    else:
                        req_da.extend(DialogueAct('request(to_stop)'))
        elif not has_to_place:
            #TODO: Always ask to_stop where user want to go from city to city???
            req_da.extend(DialogueAct('request(to_stop)'))
        elif not has_from_place:
            req_da.extend(DialogueAct('request(from_stop)'))
        elif not has_to_area:
            if to_city_val == 'none' and to_street_val == 'none':
                req_da.extend(DialogueAct('request(to_city)'))
            else:
                req_da.extend(DialogueAct('request(to_borough)'))
        elif not has_from_area:
            if from_city_val == 'none' and from_street_val == 'none':
                req_da.extend(DialogueAct('request(from_city)'))
            else:
                req_da.extend(DialogueAct('request(from_borough)'))
        elif has_from_area and has_to_area:
            if not has_from_place and to_city_val == 'New York':
                req_da.extend(DialogueAct('request(to_stop)'))
            if not has_to_place and from_city_val == 'New York':
                req_da.extend(DialogueAct('request(from_stop)'))

        # generate implicit confirms if we inferred cities and they are not the same for both stops
        default_city = self.ontology.get_default_value('city')  # don't iconfirm borrough if new york is the other city, because all boroughs are in new york
        iconfirm_da = DialogueAct()
        if len(req_da) == 0:
            if stop_city_inferred and from_city_val != to_city_val:
                if to_city_val != 'none':
                    # append iconfirm only if it is not new york and from area is not borough - all boroughs are in new york
                    if to_city_val != 'New York' or not has_from_area or from_city_val != 'none':
                        iconfirm_da.append(DialogueActItem('iconfirm', 'to_city', to_city_val))
                if from_city_val != 'none':
                    # append iconfirm only if it is not new york and to area is not borough - all boroughs are in new york
                    if from_city_val != 'New York' or not has_to_area or to_city_val != 'none':
                        iconfirm_da.append(DialogueActItem('iconfirm', 'from_city', from_city_val))
            if (stop_borough_inferred or street_borough_inferred) and from_borough_val != to_borough_val:
                if to_borough_val != 'none':
                    iconfirm_da.append(DialogueActItem('iconfirm', 'to_borough', to_borough_val))
                if from_borough_val != 'none':
                    iconfirm_da.append(DialogueActItem('iconfirm', 'from_borough', from_borough_val))

        # retrieve additional geo location data:
        # we only need geo locations for stops, str(city + stop) is more informative than geo location of a city!
        from_stop_geo = self.ontology['addinfo']['city'].get(from_city_val, {}).get(from_stop_val, None)
        if from_stop_geo:
            from_stop_geo = None if from_stop_geo['lat'].isalnum() or from_stop_geo['lon'].isalnum() else from_stop_geo
        to_stop_geo = self.ontology['addinfo']['city'].get(to_city_val, {}).get(to_stop_val, None)
        if to_stop_geo:
            to_stop_geo = None if to_stop_geo['lat'].isalnum() or to_stop_geo['lon'].isalnum() else to_stop_geo

        # express boroughs as cities if city values are not set
        if from_city_val == 'none':
            from_city_val = from_borough_val if from_borough_val else 'none'
        if to_city_val == 'none':
            to_city_val = to_borough_val if to_borough_val else 'none'

        from_streets = " and ".join([street for street in [from_street_val, from_street2_val] if street not in ['none', None]])
        to_streets = " and ".join([street for street in [to_street_val, to_street2_val] if street not in ['none', None]])

        if from_stop_val == 'none':
            from_stop_val = from_streets if from_streets else 'none'
            if from_city_val == 'none':
                from_city_val = self.ontology.get_default_value('in_city')
        if to_stop_val == 'none':
            to_stop_val = to_streets if to_streets else 'none'
            if to_city_val == 'none':
                to_city_val = self.ontology.get_default_value('in_city')

        # todo - this would be sufficient: from_place, from_area, from_geo, to_place, to_area, to_geo, vehicle

        return req_da, iconfirm_da, Travel(from_city=from_city_val, from_stop=from_stop_val,
                                           from_stop_geo=from_stop_geo, to_stop_geo=to_stop_geo,
                                           to_city=to_city_val, to_stop=to_stop_val,
                                           vehicle=vehicle_val, max_transfers=max_transfers_val)

    def gather_weather_info(self, ds, accepted_slots):
        """Handles in_city and in_state to be properly filled. If needed, a Request DA is formed for missing slots to be filled.

        Returns Reqest DA and WeatherPoint - information about the place
        If the request DA is empty, the search for weather may be commenced immediately.

        :param ds: The current dialogue state,
        """

        req_da = DialogueAct()

        # retrieve the slot variables
        in_state_val = ds['in_state'].mpv() if 'in_state' in accepted_slots else 'none'
        in_city_val = ds['in_city'].mpv() if 'in_city' in accepted_slots else 'none'
        in_borough_val = ds['in_city'].mpv() if 'in_borough' in accepted_slots else 'none'

        if in_city_val != 'none' and in_state_val == 'none':
            in_states = self.ontology.get_compatible_vals('city_state', in_city_val)
            if not in_states or not len(in_states):
                print "WARNING: there is no state compatible with this city: " + in_city_val
            elif len(in_states) == 1:
                in_state_val = in_states.pop()

        if in_city_val == 'none' and in_state_val == 'none':
            if in_borough_val != 'none':
                in_city_val = in_borough_val
            else:
                in_city_val = self.ontology.get_default_value('in_city')
            in_state_val = self.ontology.get_default_value('in_state')

        if in_state_val == 'none':
            req_da.extend(DialogueAct("request(in_state)"))
        elif in_city_val == 'none':
            req_da.extend(DialogueAct("request(in_city)"))

        return req_da, WeatherPoint(in_city_val, in_state_val)

    def gather_time_info(self, ds, accepted_slots):
        """Handles if in_city specified it handles properly filled in_state slot. If needed, a Request DA is formed for missing in_state slot.

        Returns Reqest DA and in_state
        If the request DA is empty, the search for current_time may be commenced immediately.

        :param ds: The current dialogue state,
        """
        req_da = DialogueAct()

        in_state_val = ds['in_state'].mpv() if 'in_state' in accepted_slots else 'none'
        in_city_val = ds['in_city'].mpv() if 'in_city' in accepted_slots else 'none'

        if in_city_val != 'none' and in_state_val == 'none':
            in_states = self.ontology.get_compatible_vals('city_state', in_city_val)
            if not in_states or not len(in_states):
                print "WARNING: there is no state compatible with this city: " + in_city_val
            elif len(in_states) == 1:
                in_state_val = in_states.pop()

        if in_city_val == 'none' and in_state_val == 'none':
            in_state_val = self.ontology.get_default_value('in_state')
            in_city_val = self.ontology.get_default_value('in_city')

        if in_state_val == 'none':
            req_da = DialogueAct("request(in_state)")  # we don't know which state to choose

        lon = None
        lat = None
        if in_city_val != 'none' and in_state_val != 'none' and in_state_val in self.ontology['addinfo']['state']:
            cities = self.ontology['addinfo']['state'][in_state_val]
            if cities and in_city_val in cities:
                lat = cities[in_city_val]['lat']
                lon = cities[in_city_val]['lon']

        return req_da, in_city_val, in_state_val, lon, lat


    def req_from_stop(self, ds):
        """Generates a dialogue act informing about the origin stop of the last
        recommended connection.

        TODO: this gives too much of information. Maybe it would be worth to split this into more dialogue acts
          and let user ask for all individual pieces of information. The good thing would be that it would lead
          to longer dialogues.

        :rtype : DialogueAct
        """
        route = ds.directions[ds['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                da.append(DialogueActItem('inform', 'line', step.line_name))
                da.append(DialogueActItem('inform', 'headsign', step.headsign))
                break
        return da

    def req_to_stop(self, ds):
        """Return a DA informing about the destination stop of the last
        recommended connection.
        """
        route = ds.directions[ds['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                break
        return da

    def req_departure_time(self, dialogue_state):
        """Generates a dialogue act informing about the departure time from the origin stop of the last
        recommended connection.

        :rtype : DialogueAct
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                da.append(DialogueActItem('inform', 'departure_time', step.departure_time.strftime("%I:%M:%p")))
                break
        return da

    def req_departure_time_rel(self, dialogue_state):
        """Return a DA informing the user about the relative time until the
        last recommended connection departs.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                # construct relative time from now to departure
                now = datetime.now()
                now -= timedelta(seconds=now.second, microseconds=now.microsecond)  # floor to minute start
                departure_time_rel = step.departure_time - now

                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))

                # the connection was missed
                if departure_time_rel.days < 0:
                    da.append(DialogueActItem('apology'))
                    da.append(DialogueActItem('inform', 'missed_connection', 'true'))
                # the connection is right now
                elif departure_time_rel.days == 0 and departure_time_rel.seconds == 0:
                    da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                    da.append(DialogueActItem('inform', 'departure_time_rel', 'now'))
                # future connections
                else:
                    da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                    departure_time_rel_hrs, departure_time_rel_mins = divmod(departure_time_rel.seconds / 60, 60)
                    if departure_time_rel.days > 0:
                        departure_time_rel_hrs += 24 * departure_time_rel.days
                    da.append(DialogueActItem('inform', 'departure_time_rel',
                                              '%d:%02d' % (departure_time_rel_hrs, departure_time_rel_mins)))
                break
        return da

    def req_arrival_time(self, dialogue_state):
        """Return a DA informing about the arrival time the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                da.append(DialogueActItem('inform', 'arrival_time', step.arrival_time.strftime("%I:%M:%p")))
                break
        return da

    def req_arrival_time_rel(self, dialogue_state):
        """Return a DA informing about the relative arrival time the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                # construct relative time from now to arrival
                now = datetime.now()
                now -= timedelta(seconds=now.second, microseconds=now.microsecond)  # floor to minute start

                arrival_time_rel = step.arrival_time - now
                arrival_time_rel_hrs, arrival_time_rel_mins = divmod(arrival_time_rel.seconds / 60, 60)
                if arrival_time_rel.days > 0:
                    arrival_time_rel_hrs += 24 * arrival_time_rel.days
                da.append(DialogueActItem('inform', 'arrival_time_rel',
                                          '%d:%02d' % (arrival_time_rel_hrs, arrival_time_rel_mins)))
                break
        return da

    def req_duration(self, dialogue_state):
        """Return a DA informing about journey time to the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                departure_time = step.departure_time
                break
        else:
            departure_time = datetime.fromtimestamp(0)

        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                arrival_time = step.arrival_time
                break
        else:  # return time for walking (otherwise there would be mode_transit)
            arrival_time = datetime.fromtimestamp(leg.steps[0].duration)

        duration = (arrival_time - departure_time).seconds / 60
        duration_hrs, duration_mins = divmod(duration, 60)
        if duration_hrs == 0 and duration_mins == 0:
            duration_mins = 1
        da.append(DialogueActItem('inform', 'duration', '%d:%02d' % (duration_hrs, duration_mins)))
        return da

    def req_distance(self, dialogue_state):
        """Return a DA informing the user about the distance and number of stops in the last recommended connection."""
        def meters_to_miles(meters):
            return meters * 0.000621371
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]

        res_da = DialogueAct('inform(distance="%0.1f")' % meters_to_miles(leg.distance))

        steps = [(step.num_stops, step.departure_stop, step.vehicle, step.line_name) for step in leg.steps if step.travel_mode == step.MODE_TRANSIT]
        for stop_count, from_stop, vehice, line in steps:
            res_da.append(DialogueActItem('inform', 'num_stops', stop_count))
            res_da.append(DialogueActItem('inform', 'from_stop', from_stop))
            res_da.append(DialogueActItem('inform', 'vehicle', vehice))
            res_da.append(DialogueActItem('inform', 'line', line))
        return res_da

    def req_num_transfers(self, dialogue_state):
        """Return a DA informing the user about the number of transfers in the
        last recommended connection.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        n = sum([1 for step in leg.steps if step.travel_mode == step.MODE_TRANSIT]) - 1
        da = DialogueAct('inform(num_transfers="%d")' % n)
        return da

    def req_time_transfers(self, dialogue_state):
        """Return a DA informing the user about transfer places and time needed for the trasfer in the
        last recommended connection.
        """
        route = dialogue_state.directions[dialogue_state['route_alternative']]
        leg = route.legs[0]
        # get only transit with some means of transport
        transits = [step for step in route.legs[0].steps if step.travel_mode == step.MODE_TRANSIT ]

        # get_time counts difference between two datetime objects, returns a string h:min
        get_time = lambda f,t: '%d:%02d' % divmod(((t - f).seconds / 60), 60)
        # calculate time needed as "departure_time from next stop minus arrival time to the stop"
        n =  [ (arrive_at.arrival_stop, get_time( arrive_at.arrival_time, depart_from.departure_time))
                 for arrive_at, depart_from in itertools.izip(transits,transits[1:])]
        names = [ 'inform(time_transfers_stop="%s")&inform(time_transfers_limit="%s")' % tuple_n for tuple_n in n ]

        da = DialogueAct("&".join(names)) if len(names) > 0 else DialogueAct('inform(num_transfers="0")')
        return da

    def check_directions_conflict(self, wp):
        """Check for conflicts in the given waypoints. Return an apology() DA if the origin and
        the destination are the same, or if a city is not compatible with the corresponding stop.

        :param wp: wayponts of the user's connection query
        :rtype: DialogueAct
        :return: apology dialogue act in case of conflict, or None
        """
        # TODO: This is artificially added because streets now share stop slot and we don't need to check street compatibility
        if wp.to_stop not in self.ontology.ontology[u'slots'][u'stop'] or wp.from_stop not in self.ontology.ontology[u'slots'][u'stop']:
            return None
        # TODO: This is artificially added because boroughs now share city slot and we don't need to check borough compatibility
        if wp.to_city in self.ontology.ontology[u'slots'][u'borough'] or wp.from_city in self.ontology.ontology[u'slots'][u'borough']:
            return None
        # origin and destination are the same
        if (wp.from_city == wp.to_city) and (wp.from_stop in [wp.to_stop, None]):
            apology_da = DialogueAct('apology()&inform(stops_conflict="thesame")')
            apology_da.extend(DialogueAct(wp.get_minimal_info()))
            return apology_da
        # origin stop incompatible with origin city
        elif not self.ontology.is_compatible('city_stop', wp.from_city, wp.from_stop):
            apology_da = DialogueAct('apology()&inform(stops_conflict="incompatible")')
            apology_da.extend(DialogueAct('inform(from_city="%s")&inform(from_stop="%s")' %
                                          (wp.from_city, wp.from_stop)))
            return apology_da
        # destination stop incompatible with destination city
        elif not self.ontology.is_compatible('city_stop', wp.to_city, wp.to_stop):
            apology_da = DialogueAct('apology()&inform(stops_conflict="incompatible")')
            apology_da.extend(DialogueAct('inform(to_city="%s")&inform(to_stop="%s")' %
                                          (wp.to_city, wp.to_stop)))
            return apology_da
        return None

    def check_city_state_conflict(self, in_city, in_state):
        """Check for conflicts in the given city and state. Return an apology() DA if the state and city is incompatible.

        :param in_city: city slot value
        :param in_state: state slot value
        :rtype: DialogueAct
        :return: apology dialogue act in case of conflict, or None
        """

        if not self.ontology.is_compatible('city_state', in_city, in_state):
            apology_da = DialogueAct('apology()&inform(cities_conflict="incompatible")')
            apology_da.extend(DialogueAct('inform(in_city="%s")&inform(in_state="%s")' % (in_city, in_state)))
            return apology_da
        return None

    def get_directions(self, ds, route_type='true', check_conflict=False):
        """Retrieve Google directions, save them to dialogue state and return
        corresponding DAs.

        Responsible for the interpretation of AM/PM time expressions.

        :param ds: The current dialogue state
        :param route_type: a label for the found route (to be passed on to \
                :func:`say_directions`)
        :param check_conflict: If true, will check if the origin and \
                destination stops are different and issue a warning DA if not.
        :rtype: DialogueAct
        """
        conn_info = ds.conn_info
        # check for route conflicts
        if check_conflict:
            apology_da = self.check_directions_conflict(conn_info)
            if apology_da is not None:
                if 'route_alternative' in ds:
                    ds.directions = None
                    del ds['route_alternative']
                return apology_da

        # get dialogue state values
        departure_time = ds['departure_time'].mpv()
        departure_time_rel = ds['departure_time_rel'].mpv()
        arrival_time = ds['arrival_time'].mpv()
        arrival_time_rel = ds['arrival_time_rel'].mpv()
        date_rel = ds['date_rel'].mpv()
        ampm = ds['ampm'].mpv()
        time = ds['time'].mpv()
        time_rel = ds['time_rel'].mpv()

        # interpret departure and arrival time
        departure_ts, arrival_ts = None, None
        if arrival_time != 'none' or arrival_time_rel != 'none':
            arrival_ts, _ = self.interpret_time(arrival_time, ampm, arrival_time_rel, date_rel, ds['lta_arrival_time'].mpv())
        else:
            lta_departure_time = ds['lta_departure_time'].mpv()
            lta_time = ds['lta_time'].mpv()
            lta_time = lta_departure_time if lta_departure_time != 'none' else lta_time
            time_abs = departure_time if departure_time != 'none' else time
            time_rel = departure_time_rel if departure_time_rel != 'none' else time_rel
            departure_ts, _ = self.interpret_time(time_abs, ampm, time_rel, date_rel, lta_time)

        # retrieve transit directions
        ds.directions = self.directions.get_directions(conn_info, departure_time=departure_ts, arrival_time=arrival_ts)
        return self.process_directions_for_output(ds, route_type)

    ORIGIN = 'ORIGIN'
    DESTIN = 'FINAL_DEST'

    def process_directions_for_output(self, dialogue_state, route_type):
        """Return DAs for the directions in the current dialogue state.
        If the directions are not valid (nothing found), delete their object from the
        dialogue state and return apology DAs.

        :param dialogue_state: the current dialogue state
        :param route_type: the route type requested by the user ("last", "next" etc.)
        :rtype: DialogueAct
        """
        if not isinstance(dialogue_state['route_alternative'], int):
            dialogue_state['route_alternative'] = 0

        try:
            # get the alternative we want to say now
            route = dialogue_state.directions[dialogue_state['route_alternative']]
            # only 1 leg should be present in case we have no waypoints
            steps = route.legs[0].steps
        except IndexError:
            # this will lead to apology that no route has been found
            steps = []
            #dialogue_state.directions = None
            del dialogue_state['route_alternative']

        res = []

        # introduction
        if len(dialogue_state.directions) > 1:
            res.append('inform(found_directions="%s")' % route_type)
            if route_type != "last":
                res.append("inform(alternative=%s)" % word_for_number(dialogue_state['route_alternative'] + 1, True))

        # route description
        prev_arrive_stop = self.ORIGIN  # remember previous arrival stop
        for step_ndx, step in enumerate(steps):

            # find out what will be the next departure stop (needed later)
            next_leave_stop = self.DESTIN
            if step_ndx < len(steps) - 2 and steps[step_ndx + 1].travel_mode == step.MODE_WALKING:
                next_leave_stop = steps[step_ndx + 2].departure_stop
            elif step_ndx < len(steps) - 1 and steps[step_ndx + 1].travel_mode == step.MODE_TRANSIT:
                next_leave_stop = steps[step_ndx + 1].departure_stop

            # walking
            if step.travel_mode == step.MODE_WALKING:
                # walking to stops with different names
                # todo: delete those after merging hdc slu with origin master
                directions_to_stop = expand_stop(dialogue_state.directions.to_stop)
                directions_from_stop = expand_stop(dialogue_state.directions.from_stop)
                if (next_leave_stop == self.DESTIN and prev_arrive_stop != directions_to_stop) or \
                    (prev_arrive_stop == self.ORIGIN and next_leave_stop != directions_from_stop) or \
                    (next_leave_stop != self.DESTIN and prev_arrive_stop != self.ORIGIN and next_leave_stop != prev_arrive_stop):
                    # walking destination: next departure stop
                    res.append("inform(walk_to=%s)" % next_leave_stop)
                    #res.append("inform(duration=0:%02d)" % (step.duration / 60))
            # public transport
            elif step.travel_mode == step.MODE_TRANSIT:
                res.append("inform(vehicle=%s)" % step.vehicle)
                res.append("inform(line=%s)" % step.line_name)
                res.append("inform(departure_time=%s)" % step.departure_time.strftime("%I:%M:%p"))
                # only mention departure if it differs from previous arrival
                if step.departure_stop != prev_arrive_stop:
                    res.append("inform(enter_at=%s)" % step.departure_stop)
                res.append("inform(headsign=%s)" % step.headsign)
                res.append("inform(exit_at=%s)" % step.arrival_stop)
                # only mention transfer if there is one
                if next_leave_stop != self.DESTIN:
                    res.append("inform(transfer='true')")
                prev_arrive_stop = step.arrival_stop

        # no route found: apologize
        if len(res) == 0:
            res.append('apology()')
            res.append(dialogue_state.directions.get_minimal_info())

        res_da = DialogueAct("&".join(res))

        return res_da

    DEFAULT_AMPM_TIMES = {'morning': "06:00",
                          'am': "10:00",
                          'pm': "15:00",
                          'evening': "18:00",
                          'night': "00:00"}

    def interpret_time(self, time_abs, time_ampm, time_rel, date_rel, lta_time):
        """Interpret time, given current dialogue state most probable values for
        relative and absolute time and date, plus the corresponding last-talked-about value.

        :return: the inferred time value + flag indicating the inferred time type ('abs' or 'rel')
        :rtype: tuple(datetime, string)
        """
        now = datetime.now()
        now -= timedelta(seconds=now.second, microseconds=now.microsecond)  # floor to minute start

        # use only last-talked-about time (of any type -- departure/arrival)
        if (time_abs != 'none' or date_rel != 'none') and time_rel != 'none':
            if lta_time.endswith('time_rel'):
                time_abs = 'none'
                date_rel = 'none'
            elif lta_time.endswith('time') or lta_time == 'date_rel':
                time_rel = 'none'

        # remove bogus values (i.e. "now") from time_abs
        if not re.match('^[0-2]?[0-9]:[0-5][0-9]$', time_abs):
            time_abs = 'none'

        # relative time
        if (time_abs == 'none' and time_ampm == 'none' and date_rel == 'none') or time_rel != 'none':
            time_type = 'rel'
            time_abs = now
            if time_rel not in ['none', 'now']:
                trel_parse = datetime.strptime(time_rel, "%H:%M")
                time_abs += timedelta(hours=trel_parse.hour, minutes=trel_parse.minute)
        # absolute time (with relative date)
        else:
            time_type = 'abs'
            if time_abs == 'none':
                if time_ampm != 'none':
                    time_abs = self.DEFAULT_AMPM_TIMES[time_ampm]
                elif date_rel != 'none':
                    time_abs = "%02d:%02d" % (now.hour, now.minute)
            time_parsed = datetime.combine(now, datetime.strptime(time_abs, "%H:%M").time())
            time_hour = time_parsed.hour
            now_hour = now.hour
            # handle 12hr time
            if time_hour >= 1 and time_hour <= 12:
                # interpret AM/PM
                if time_ampm != 'none':
                    # 'pm' ~ 12pm till 11:59pm
                    if time_ampm == 'pm' and time_hour < 12:
                        time_hour += 12
                    # 'am'/'morning' ~ 12am till 11:59am
                    elif time_ampm in ['am', 'morning'] and time_hour == 12:
                        time_hour = 0
                    # 'evening' ~ 4pm till 3:59am
                    elif time_ampm == 'evening' and time_hour >= 4:
                        time_hour = (time_hour + 12) % 24
                    # 'night' ~ 6pm till 5:59am
                    elif time_ampm == 'night' and time_hour >= 6:
                        time_hour = (time_hour + 12) % 24
                # 12hr time + no AM/PM  set + today or no date set: default to next 12hrs
                elif date_rel in ['none', 'today'] and now_hour > time_hour and now_hour < time_hour + 12:
                    time_hour = (time_hour + 12) % 24
            time_abs = datetime.combine(now, dttime(time_hour, time_parsed.minute))
            # relative date
            if date_rel == 'tomorrow':
                time_abs += timedelta(days=1)
            elif date_rel == 'day_after_tomorrow':
                time_abs += timedelta(days=2)
            elif time_abs < now:
                time_abs += timedelta(days=1)

        return time_abs, time_type

    def get_limited_context_help(self, dialogue_state):
        res_da = DialogueAct()

        # if we do not understand the input then provide the context sensitive help
        if not 'route_alternative' in dialogue_state:
            # before something is offered
            if randbool(10):
                res_da.append(DialogueActItem("help", "task", "weather"))
            elif randbool(10):
                res_da.append(DialogueActItem("help", "request", "current_time"))
            elif randbool(10):
                res_da.append(DialogueActItem("help", "inform", "hangup"))
            elif randbool(9):
                res_da.append(DialogueActItem("help", "request", "help"))
            elif randbool(8):
                res_da.append(DialogueActItem("help", "inform", "departure_time"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "repeat"))
            elif not dialogue_state['from_stop'].test("none", self.accept_prob, neg_val=True):
                res_da.append(DialogueActItem("help", "inform", "from_stop"))
            elif not dialogue_state['to_stop'].test("none", self.accept_prob, neg_val=True):
                res_da.append(DialogueActItem("help", "inform", "to_stop"))
            else:
                res_da.append(DialogueActItem("silence"))
        else:
            # we already offered a connection
            if randbool(4):
                res_da.append(DialogueActItem("help", "inform", "alternative_last"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "inform", "alternative_next"))
            elif randbool(6):
                res_da.append(DialogueActItem("help", "inform", "alternative_prev"))
            elif randbool(5):
                res_da.append(DialogueActItem("help", "inform", "alternative_abs"))
            elif randbool(4):
                res_da.append(DialogueActItem("help", "request", "from_stop"))
            elif randbool(3):
                res_da.append(DialogueActItem("help", "request", "to_stop"))
            elif randbool(2):
                res_da.append(DialogueActItem("help", "request", "num_transfers"))
            else:
                res_da.append(DialogueActItem("silence"))

        return res_da

    def get_help_res_da(self, ds, accepted_slots, state_changed):
        topics_alternatives = ['inform="alternative_abs"', 'inform="alternative_prev"', 'inform="alternative_next"',
                               'inform="alternative_last"', ]
        topics_stops = ['inform="from_stop"', 'inform="to_stop"', 'request="from_stop"', 'request="to_stop"',
                        'request="num_transfers"', 'inform="num_transfers"',]
        topics_time = ['inform="departure_time"', 'request="current_time"', ]
        topics_general = ['', 'repeat', 'inform="hangup"', ]
        topics_weather = ['task="weather"', ]
        topics_connection = topics_alternatives + topics_stops + topics_time

        task = ds['task'].mpv() if 'task' in accepted_slots else ''

        if task == "weather":
            topics = topics_weather
        elif task == 'find_connection':
            topics = topics_connection
        else:
            topics = topics_general
        rand_theme = topics[random.randint(0, len(topics) - 1)]
        return DialogueAct("help(%s)" % rand_theme)


    def fix_stop_street_slots(self, changed_slots):
        from_list_stop = ['from_street', 'from_street2', 'from_stop', 'from_street']
        from_list_city = ['from_borough', 'from_city']
        to_list_city = ['to_borough', 'to_city']
        to_list_stop = ['to_street', 'to_street2', 'to_stop', 'to_street']

        from_stop_value = ' and '.join([changed_slots.pop(slot).mpv() for slot in from_list_stop if slot in changed_slots])
        to_stop_value = ' and '.join([changed_slots.pop(slot).mpv() for slot in to_list_stop if slot in changed_slots])
        from_city_value = ' and '.join([changed_slots.pop(slot).mpv() for slot in from_list_city if slot in changed_slots])
        to_city_value = ' and '.join([changed_slots.pop(slot).mpv() for slot in to_list_city if slot in changed_slots])

        if from_stop_value:
            changed_slots['from_stop'] = D3DiscreteValue({from_stop_value: 1.0, 'none': 0.0})
        if from_city_value:
            changed_slots['from_city'] = D3DiscreteValue({from_city_value: 1.0, 'none': 0.0})
        if to_stop_value:
            changed_slots['to_stop'] = D3DiscreteValue({to_stop_value: 1.0, 'none': 0.0})
        if to_city_value:
            changed_slots['to_city'] = D3DiscreteValue({to_city_value: 1.0, 'none': 0.0})

        return changed_slots

#=============================THANH: methods for embe GP-Sarsa================================
    def end_dialogue(self, user_satisfied=False):
        if user_satisfied:
            self.gp_sarsa.end_episode(self.success_reward)
        else:
            self.gp_sarsa.end_episode(self.unsuccess_reward)
        self.gp_sarsa.save()

    def _get_indicators(self, ds, features):
        #TODO: HERE , call get slot to be select, confirm two times
        return self.places_inferred(ds)#only indicator about infer city, street...
        indicators = [0, 0, 0]
        if features[2]>0 and features[4]>0:#offer is applicable
            indicators[0] = 1

        slots_tobe_selected = self.get_slots_tobe_selected(ds, self.policy_cfg['select_prob'], self.accept_prob)
        #slots_tobe_selected = {k: v for k, v in slots_tobe_selected.items() if k in self.ontology.slots_system_selects()}
        if 'task' in slots_tobe_selected.keys():
            slots_tobe_selected.pop('task')
        #print "FBuild: slot tobe selected", slots_tobe_selected.keys()
        if len(slots_tobe_selected)>0:#select is appliable
            indicators[1] = 1
 
        slots_tobe_confirmed = self.get_slots_tobe_confirmed(ds, self.policy_cfg['confirm_prob'], self.accept_prob)
        slots_tobe_confirmed = {k: v for k, v in slots_tobe_confirmed.items() if k in self.ontology.slots_system_confirms()}
        #print "FBuild: slot tobe confirm", slots_tobe_confirmed.keys()
        if len(slots_tobe_confirmed)>0:#confirm is appliable
            indicators[2] = 1

        #------check there is ambiguity about from/to street/stop
        if indicators[0]==1:
            infers = self.places_inferred(ds)
            if sum(infers)<4:
                indicators[0]=0
            #indicators.extend(infers) 

        return indicators

    def _extract_features(self, ds):
        #TODO: HERE, attache new feature by combine (fromStop/FromStreet and 2 number features for each from_borough, from_city (good for bot infer only one value and in the case user say also two value from hypothesis
        #TODO: what we get from palces_inferred???
        '''Features including only probabilities of top two hypothesis.'''
        print '------Extract features form belief state:'
        slots=['task', ('from_stop', 'from_street', 'from_city'), ('to_stop', 'to_street', 'to_city'), ('departure_time', 'departure_time_rel'), ('arrival_time', 'arrival_time_rel'),'vehicle',]
        defaults = ['task', 'departure_time', 'departure_time_rel', 'arrival_time', 'arrival_time_rel', 'vehicle']
        #slot_feature(D=5): {top first; the second  probability of not-none value; has default value, number of time system requested about the slot; cofirmed}
        features = []
        for s in slots:
            eq_slots = s
            if not isinstance(s, tuple):
                eq_slots = [s]
            fslot= None
            for eq_s in eq_slots:
                d1 = d2 = 0#top two not-none probabilities
                if eq_s in ds:
                    #print eq_s, ":", ds[eq_s].items()
                    for v, p in ds[eq_s].items():
                        if v != 'none':
                            if d1==0:
                                d1 = p
                            else:
                                d2 = p
                                break
                '''
                d3 = 0#has defatult value
                if eq_s in defaults:
                    d3 = 1
                d4 = 0#number of times system asked about the slot
                d5 = 0#the value has cofirnmed
                fkey = 'f' + eq_s#the fkey must be f_slotname
                if fkey in ds.slots.keys():
                    if 'requested' in ds.slots[fkey].keys():
                        d4 = ds.slots[fkey]['requested']
                    if 'confirmed' in ds.slots[fkey].keys():
                        d5 = ds.slots[fkey]['confirmed']
                '''
                if fslot is None or d1>fslot[0]:
                    #fslot = [d1, d2, d3, d4, d5]
                    fslot = [d1, d2]

            print '[%s]\t\t:'%eq_slots[0][0:5],
            for f in fslot:
                print '%.3f'%f,
            print ''
            features.extend(fslot)
        #------indicators features
        indicators = self._get_indicators(ds, features)
        print '[%s]\t\t:'%'indis',
        for v in indicators:
            print '%.3f'%v,
        print ''     
        features.extend(indicators)
        return np.array(features)

    def _extract_features1(self, ds):
        '''Features including, probabilities of top 2 hypothesis, 1 has default value, 1 #requested, 1#confirmed'''
        slots=['task', 'from_stop', 'to_stop', 'from_city', 'to_city', 'from_street', 'to_street', 'departure_time', 'arrival_time', 'departure_time_rel', 'arrival_time_rel','vehicle',]
        defaults = ['task', 'departure_time', 'departure_time_rel', 'arrival_time', 'arrival_time_rel', 'vehicle']
        #slot_feature(D=5): {top first; the second  probability of not-none value; has default value, number of time system requested about the slot; cofirmed}
        features = []
        for s in slots:
            d1 = d2 = 0#top two not-none probabilities
            if s in ds:
                for v, p in ds[s].items():
                    if v != 'none':
                        if d1==0:
                            d1 = p
                        else:
                            d2 = p
                            break
            d3 = 0#has defatult value
            if s in defaults:
                d3 = 1
            d4 = 0#number of times system asked about the slot
            d5 = 0#the value has cofirnmed
            fkey = 'f' + s
            if fkey in ds.slots.keys():
                if 'requested' in ds.slots[fkey].keys():
                    d4 = ds.slots[fkey]['requested']
                if 'confirmed' in ds.slots[fkey].keys():
                    d5 = ds.slots[fkey]['confirmed']
            fslot = [d1, d2, d3, d4, d5]
            print 'Feature for %s'%s, fslot
            features.extend(fslot)
        return np.array(features)

    def _extract_features_2(self, ds):
        '''Features including, probabilities of top 2 hypothesis, 1 has default value, 1 #requested, 1#confirmed.
            Combining equivalent slots to one feature. e.g. from_city, from_stop etc becom from_x
        '''
        print '------Extract features form belief state:'
        slots=['task', ('from_stop', 'from_street', 'from_city'), ('to_stop', 'to_street', 'to_city'), ('departure_time', 'departure_time_rel'), ('arrival_time', 'arrival_time_rel'),'vehicle',]
        defaults = ['task', 'departure_time', 'departure_time_rel', 'arrival_time', 'arrival_time_rel', 'vehicle']
        #slot_feature(D=5): {top first; the second  probability of not-none value; has default value, number of time system requested about the slot; cofirmed}
        features = []
        for s in slots:
            eq_slots = s
            if not isinstance(s, tuple):
                eq_slots = [s]
            fslot= None
            for eq_s in eq_slots:
                d1 = d2 = 0#top two not-none probabilities
                if eq_s in ds:
                    #print eq_s, ":", ds[eq_s].items()
                    for v, p in ds[eq_s].items():
                        if v != 'none':
                            if d1==0:
                                d1 = p
                            else:
                                d2 = p
                                break
                d3 = 0#has defatult value
                if eq_s in defaults:
                    d3 = 1
                d4 = 0#number of times system asked about the slot
                d5 = 0#the value has cofirnmed
                fkey = 'f' + eq_s#the fkey must be f_slotname
                if fkey in ds.slots.keys():
                    if 'requested' in ds.slots[fkey].keys():
                        d4 = ds.slots[fkey]['requested']
                    if 'confirmed' in ds.slots[fkey].keys():
                        d5 = ds.slots[fkey]['confirmed']
                if fslot is None or d1>fslot[0]:
                    fslot = [d1, d2, d3, d4, d5]
                    
            print '[%s]\t\t:'%eq_slots[0][0:5],
            for f in fslot:
                print '%.3f'%f,
            print ''
            features.extend(fslot)
        return np.array(features)

#============THANH=====redefine some routines to build suibalt actions
    def get_slots_tobe_confirmed(self, ds, min_prob, max_prob):
        """Returns all slots which have a probability of a non "none" value larger then some threshold and still not so
        large to be considered as accepted.
        """
        tobe_confirmed_slots = {}

        for slot in ds.slots:
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait", 'lta_'] if slot.startswith(x)]):
                continue
            if not isinstance(ds.slots[slot], D3DiscreteValue):
                continue

            #prob, value = self.slots[slot].mph()
            topn = ds.slots[slot].topn(1)
            if len(topn)<1:
                continue
            (value, prob) = topn[0]
            
            if value not in ['none', 'system-informed', None] and min_prob <= prob and prob < max_prob:
                tobe_confirmed_slots[slot] = ds.slots[slot]

        return tobe_confirmed_slots

    def get_slots_tobe_selected(self, ds, min_prob, max_prob=0.8):
        """Thanh Returns all slots which have a probability of the two most probable non "none" value larger then some threshold.
        """
        tobe_selected_slots = {}

        for slot in ds.slots:
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait", 'lta_'] if slot.startswith(x)]):
                continue
            if not isinstance(ds.slots[slot], D3DiscreteValue):
                continue

            #(prob1, value1), (prob2, value2) = self.slots[slot].tmphs()
            topn = ds.slots[slot].topn(2)
            if len(topn)<2:
                continue
            (value1, prob1), (value2, prob2) = topn

            if value1 not in ['none', 'system-informed', None] and prob1 >= min_prob and prob1<max_prob and \
                value2 not in ['none', 'system-informed', None] and prob2 >= min_prob and prob2<max_prob:
                tobe_selected_slots[slot] = ds.slots[slot]

        return tobe_selected_slots

    def get_top1_value(self, ds, slot):
        if slot not in ds:
            return u'none'
        lst = ds[slot].topn(1)
        if len(lst) == 0:
            return u'none'
        else:
            return lst[0][0]

    def places_inferred(self, ds):
        infers = [0, 0, 0, 0]#from_city, to_city, from_borough, to_borough

        # retrieve the slot variables
        from_city_val = self.get_top1_value(ds, 'from_city')
        from_borough_val = self.get_top1_value(ds, 'from_borough')
        from_stop_val = self.get_top1_value(ds, 'from_stop')
        from_street_val = self.get_top1_value(ds, 'from_street')
        from_street2_val = self.get_top1_value(ds, 'from_street2')
        to_city_val = self.get_top1_value(ds, 'to_city')
        to_borough_val = self.get_top1_value(ds, 'to_borough')
        to_stop_val = self.get_top1_value(ds, 'to_stop')
        to_street_val = self.get_top1_value(ds, 'to_street')
        to_street2_val = self.get_top1_value(ds, 'to_street2')
        vehicle_val = self.get_top1_value(ds, 'vehicle')
        max_transfers_val = self.get_top1_value(ds, 'num_transfers')
        #default New York
        #from_city_val = 'New York'
        #to_city_val = 'New York'

        if from_city_val!='none':
            infers[0] = 1
        if to_city_val!='none':
            infers[1] = 1
        if from_borough_val!='none':
            infers[2] = 1
        if to_borough_val!='none':
            infers[3]=1

        # infer cities based on stops
        from_cities, to_cities = None, None
        if infers[0]==0:
            from_cities = self.ontology.get_compatible_vals('stop_city', from_stop_val)
            if len(from_cities) <= 1:
                infers[0] = 1 
                
        if infers[1]==0:
            to_cities = self.ontology.get_compatible_vals('stop_city', to_stop_val)
            if len(to_cities)<=1:
                infers[1] = 1

        # infer cities based on street
        from_cities_st, to_cities_st = None, None
        if infers[0]==0:
            from_cities_st = self.ontology.get_compatible_vals('street_city', from_street_val)
            if len(from_cities_st)<=1:
                infers[0]=1

        if infers[1]==0:
            to_cities_st = self.ontology.get_compatible_vals('street_city', to_stop_val)
            if len(to_cities_st)<=1:
                infers[1]=1

        # infer borough based on stops
        from_boroughs, to_boroughs = None, None
        if infers[2]==0:
            from_boroughs = self.ontology.get_compatible_vals('stop_borough', from_stop_val)
            if len(from_boroughs)<=1:
                infers[2] = 1

        if infers[3]==0:
            to_boroughs = self.ontology.get_compatible_vals('stop_borough', to_stop_val)
            if len(to_boroughs)<=1:
                infers[3]=1

        # infer boroughs based on streets
        from_boroughs_st, to_boroughs_st = None, None
        if infers[2]==0:
            from_boroughs_st = self.ontology.get_compatible_vals('street_borough', from_street_val)
            if len(from_boroughs_st)<=1:
                infers[2]=1
        if infers[3]==0:
            to_boroughs_st = self.ontology.get_compatible_vals('street_borough', to_street_val)
            if len(to_boroughs_st)<=1:
                infers[3]=1

        return infers
