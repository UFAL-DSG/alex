#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Matous Machacek, Lukas Zilka
#
# TODO:
#   1. Zjistovani detailu o vyhledanem spojeni
# X 2. Podpora alternativnich cest
#   3. Specifikace dopravniho prostredku
#   4. Specifikace dopoledne/odpoledne u casu + rikani casu v teto podobe
# X 5. Moznost rici stanici v kterekoli podobe
# X 6. Pridat implicitni potvrzovani v dialogovem manageru (napr. uzivatel: "Chci na malostranskou", System: "Dobre, na malostranskou. Odkat chcete jet?"
# X 7. Podpora oznamovani spojeni, kde jsou prestupy
#   8. Filtrace ASR chyb
#
import urllib
import datetime
import time
import json
from collections import namedtuple

import autopath

from alex.components.dm import DialogueManager
from alex.components.nlg.template import TemplateNLG
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActConfusionNetwork
from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork
from alex.applications.AlexOnTheBus.aotb_nlg import AOTBNLG

SlotChange = namedtuple('SlotChange', ['from_value', 'to_value', 'slot'])


class AOTBState(object):
    """Represents the state of dialogue in AOTB dialogue system."""
    from_stop = None
    to_stop = None
    time = None
    stop = None
    bye = False
    repeat = False
    help = False

    def __init__(self):
        self.slot_changes = []
        self.turn_number = 0
        self.directions = None
        self.alternatives = 0
        self.not_understood = False
        self.last_utterance = None

    def set(self, slot, value):
        print 'setting', slot, value
        if slot in ["from_stop", "to_stop", "time"]:
            self.slot_changes.append(SlotChange(from_value=getattr(self, slot),
                                                to_value=value,
                                                slot=slot))
        setattr(self, slot, value)

    def get(self, slot):
        return getattr(self, slot)


def _get_from_to_diff(cn):
    res = 0.0
    for prob, dai in cn:
        if dai.dat == "inform" and dai.name == "from_stop":
            res -= prob
        if dai.dat == "inform" and dai.name == "to_stop":
            res += prob
    return res


class AOTBDM(DialogueManager):
    """Transport Directions DM"""

    ILLEGAL_VALUES = set(['[OTHER]'])

    def __init__(self, cfg):
        super(AOTBDM, self).__init__(cfg)

        self.cfg = cfg
        self.state = None  # wait for a new_dialogue to initialize it
        self.directions = GooglePIDDirectionsFinder()

        self.last_system_dialogue_act = None

    def new_dialogue(self):
        """Initialise the dialogue manager and makes it ready for a new dialogue conversation."""
        self.state = AOTBState()

    def _get_best_utterance(self, utterance):
        if utterance is not None:
            if isinstance(utterance, UtteranceNBList):
                utterance_1 = utterance.get_best()
            elif isinstance(utterance, UtteranceConfusionNetwork):
                utterance_1 = utterance.get_best_hyp()[1]
            elif not isinstance(utterance, Utterance):
                raise Exception("unknown utterance type: %s" % str(type(utterance)))
            else:
                utterance_1 = utterance

            self.state.last_utterance = utterance_1
        return utterance_1

    def da_in(self, da, utterance=None):
        """\
        Receives an input dialogue act or dialogue act list with
        probabilities or dialogue act confusion network.

        When the dialogue act is received, an update of the state is performed.
        """

        utterance = self._get_best_utterance(utterance)

        print "understood:"
        print unicode(da)
        print

        self.state.turn_number += 1

        from_dai = None
        to_dai = None
        time_dai = None

        cn_dict = da.make_dict()
        from_dai = cn_dict.get(('inform', 'from_stop', ))
        to_dai = cn_dict.get(('inform', 'to_stop', ))
        time_dai = cn_dict.get(('inform', 'time', ))
        bye_dai = cn_dict.get('bye')
        request_alternatives_dai = cn_dict.get('reqalts')
        repeat_dai = cn_dict.get('repeat')
        help_dai = cn_dict.get('help')

        self.state.not_understood = not any([from_dai, to_dai, time_dai, bye_dai, request_alternatives_dai, repeat_dai,  help_dai])

        if request_alternatives_dai is not None:
            self.state.alternatives += 1
            self.state.alternatives %= \
                len(self.state.directions) if self.state.directions is not None else 1

        if bye_dai is not None:
            self.state.bye = True

        if from_dai is not None:
            self.update_state(from_dai)

        if to_dai is not None:
            self.update_state(to_dai)

        if time_dai is not None:
            self.update_state(time_dai)

        if repeat_dai is not None:
            self.state.repeat = True

        if help_dai is not None:
            self.state.help = True

    def update_state(self, dai):
        """Copy values from the dai to the state. (i.e. "understand the dai")."""
        if dai.dat == 'inform':
            self.state.set(dai.name, dai.value)

    def say_directions(self):
        """Given the state say current directions."""
        route = self.state.directions.routes[self.state.alternatives]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []

        if len(self.state.directions) > 1:
            if self.state.alternatives == 0:
                res.append("inform(alternatives=%d)" % len(self.state.directions))
            res.append("inform(alternative=%d)" % (self.state.alternatives + 1))


        for step_ndx, step in enumerate(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                res.append(u"inform(vehicle=%s)" % step.vehicle)
                res.append(u"inform(line=%s)" % step.line_name)
                res.append(u"inform(go_at=%s)" % step.departure_time.strftime("%H:%M"))
                res.append(u"inform(enter_at=%s)" % step.departure_stop)
                res.append(u"inform(headsign=%s)" % step.headsign)
                res.append(u"inform(exit_at=%s)" % step.arrival_stop)
                res.append(u"inform(transfer='True')")

        res = res[:-1]

        if len(res) == 0:
            res.append(u'apology()')
            res.append(u"inform(from_stop='%s')" % self.state.from_stop)
            res.append(u"inform(to_stop='%s')" % self.state.to_stop)

#        print unicode(res)
#        print [type(x) for x in res]
        res_da = DialogueAct(u"&".join(res))

#        print unicode(res_da)

        return res_da

    def get_default_time(self):
        """Return default value for time."""
        return datetime.datetime.now().strftime("%H:%M")

    def da_out(self):
        """Produce output dialogue act."""

        if self.state.turn_number == 0:
            res = DialogueAct("hello()")
            return res
        if self.state.bye:
            self.state.bye = False
            res = DialogueAct("bye()")
            return res
        if self.state.help:
            self.state.help = False
            res = DialogueAct("help()")
            return res
        if self.state.repeat:
            self.state.repeat = False
            res = DialogueAct('irepeat()')
            return res
        elif self.state.not_understood:
            self.state.not_understood = False
            res = DialogueAct(u'notunderstood()')
            if self.state.from_stop is None:
                res.append(DialogueActItem("help", "from_stop"))
            elif self.state.to_stop is None:
                res.append(DialogueActItem("help", "to_stop"))

            return res
        else:
            req_das = []
            for slot in ['from_stop', 'to_stop']:
                if self.state.get(slot) is None:
                    req_das.append("request(%s)" % slot)

            iconf_das = []
            print self.state.slot_changes

            for slot_change in self.state.slot_changes:
                # FIXME: In the dialogue act standard, there are no iconfirm(s)
                # This must be properly defined and added into the documentation.
                iconf_das.append("iconfirm(%s=%s)" % (slot_change.slot, slot_change.to_value, ))
                if slot_change.slot in ["from_stop", "to_stop", "time"]:
                    self.state.alternatives = 0
            if len(iconf_das) > 0:
                iconf_da = DialogueAct("&".join(iconf_das))
            else:
                iconf_da = DialogueAct()

            self.state.slot_changes = []

            if len(req_das) > 0:
                req_da = DialogueAct("&".join(req_das))
                iconf_da.extend(req_da)
                return iconf_da
            else:
                time = self.state.time
                if time is None:
                    time = self.get_default_time()
                else:
                    time_parsed = datetime.datetime.strptime(time, "%H:%M")
                    new_hour = time_parsed.hour
                    if datetime.datetime.now().hour > time_parsed.hour:
                        new_hour = (new_hour + 12) % 24

                    time = "%d:%.2d" % (new_hour, time_parsed.minute)

                self.state.set('directions', self.directions.get_directions(
                    from_stop = self.state.from_stop,
                    to_stop = self.state.to_stop,
                    departure_time = time,
                ))

                directions_da = self.say_directions()

                iconf_da.extend(directions_da)
                return iconf_da


    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        pass


class Directions(object):
    pass


class Route(object):
    pass


class GoogleDirections(Directions):
    def __init__(self, input_json):
        self.routes = []
        for route in input_json['routes']:
            self.routes.append(GoogleRoute(route))

    def __len__(self):
        return len(self.routes)

class GoogleRoute(object):
    def __init__(self, input_json):
        self.legs = []
        for leg in input_json['legs']:
            self.legs.append(GoogleRouteLeg(leg))

class GoogleRouteLeg(object):
    def __init__(self, input_json):
        self.steps = []
        for step in input_json['steps']:
            self.steps.append(GoogleRouteLegStep(step))

class GoogleRouteLegStep(object):
    MODE_TRANSIT = "TRANSIT"
    MODE_WALKING = "WALKING"

    def __init__(self, input_json):
        self.travel_mode = input_json['travel_mode']
        if self.travel_mode == self.MODE_TRANSIT:
            self.departure_stop = input_json['transit_details']['departure_stop']['name']
            self.departure_time = \
                self.parsetime(input_json['transit_details']['departure_time']['text'])
            self.arrival_stop = input_json['transit_details']['arrival_stop']['name']
            self.headsign = input_json['transit_details']['headsign']
            self.vehicle = input_json['transit_details']['line']['vehicle']['type']
            self.line_name = input_json['transit_details']['line']['short_name']

    def parsetime(self, time_str):
        dt = datetime.datetime.strptime(time_str, "%H:%M%p")
        return dt


class DirectionsFinder(object):
    def get_directions(self, from_stop, to_stop, time):
        raise NotImplementedException()


class GooglePIDDirectionsFinder(DirectionsFinder):
    def __init__(self, *args, **kwargs):
        super(GooglePIDDirectionsFinder, self).__init__(*args, **kwargs)
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

    def get_directions(self, from_stop, to_stop, departure_time):
        departure = datetime.datetime.combine(
            datetime.datetime.now(),
            datetime.datetime.strptime(departure_time, "%H:%M").time()
        )

        departure_time = int(time.mktime(departure.timetuple()))

        data = {
            'origin': '%s, Praha' % from_stop.encode('utf8'),
            'destination': 'zastávka %s, Praha' % to_stop.encode('utf8'),
            'region': 'cz',
            'departure_time': departure_time,
            'sensor': 'false',
            'alternatives': 'true',
            'mode': 'transit',
        }

        page = urllib.urlopen(self.directions_url + '?' + urllib.urlencode(data))
        response = json.load(page)

        directions = GoogleDirections(response)
        return directions


def main():
    cfg = {
      'NLG': {
        'debug': True,
        'type': AOTBNLG,
        'Template' : {
            'model': 'nlg_templates.cfg'
        },
      },
    }
    nlg = TemplateNLG(cfg)
    da = DialogueAct(u'inform(vehicle="TRAM")&inform(line="16")&inform(go_at="4:16pm")&inform(enter_at="Štěpánská")&inform(headsign="Lehovec")&inform(exit_at="Náměstí Míru")')
    print da
    print nlg.generate(da)
    return

    #gpd = GooglePIDDirectionsFinder()
    #route = gpd.get_directions(u"vodičkova", u"hradčanská", "9:00").routes[0]
    #import ipdb; ipdb.set_trace()
    dm = AOTBDM({})
    dm.new_dialogue()
    print dm.da_out()
    #da = DialogueAct(u"inform(from_stop=vodičkova)&inform(to_stop=hradčanská)&inform(time=9:00)")
    da = DialogueAct(u"inform(from_stop=vodičkova)&inform(to_stop=hradčanská)")
    print dm.da_in(DialogueActConfusionNetwork.make_from_da(da))
    print dm.da_out()



if __name__ == '__main__':
    main()
