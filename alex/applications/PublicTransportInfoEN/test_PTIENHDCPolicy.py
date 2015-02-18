from datetime import datetime, timedelta
from unittest import TestCase
from datetime import time as dttime
from alex.applications.PublicTransportInfoEN.directions import GoogleDirections, Travel

from alex.applications.PublicTransportInfoEN.hdc_policy import PTIENHDCPolicy
from alex.components.dm import Ontology
from alex.components.dm.dddstate import DeterministicDiscriminativeDialogueState
from alex.components.slu.da import DialogueAct
from alex.utils.config import Config, as_project_path


class TestPTIENHDCPolicy(TestCase):

    # ===== GATHERING CONNECTION INFORMATION =====
 # find a bus connection from Broadway Queens to seventh avenue and forty second street

    def test_gather_connection_info_from_street_to_stop(self):
        self.set_ds_connection_info(from_stop="Central Park")
        self.set_ds_street_connection_info(to_street="Wall St")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(1, len(req_da))
        self.assertEquals('Central Park', conn_info.from_stop)
        self.assertEquals('Wall St', conn_info.to_stop)

    def test_gather_connection_info_combined(self):
        self.set_ds_connection_info(to_city="Queens")
        self.set_ds_street_connection_info(to_street="42 St", to_street2="7 Ave", from_street="58 Dr")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(0, len(req_da))
        self.assertEquals('Queens', conn_info.to_city)
        self.assertEquals('42 St and 7 Ave', conn_info.to_stop)
        self.assertEquals('58 Dr', conn_info.from_stop)
        self.assertEquals('Queens', conn_info.from_city)

    def test_gather_connection_info_from_streets_to_stops2(self):
        self.set_ds_connection_info(to_city="New York", from_city="Baltimore")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(0, len(req_da))
        self.assertEquals('Baltimore', conn_info.from_city)
        self.assertEquals('New York', conn_info.to_city)

    def test_gather_connection_info_from_streets_to_stops(self):
        self.set_ds_street_connection_info(from_street="105 St", from_street2="5 Ave")
        self.set_ds_connection_info(to_stop="Central Park")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(0, len(req_da))
        self.assertEquals('105 St and 5 Ave', conn_info.from_stop)
        self.assertEquals('Central Park', conn_info.to_stop)
        self.assertEquals('New York', conn_info.to_city)

    def test_gather_connection_info_infer_from_borough(self):
        self.set_ds_street_connection_info(from_street="1 Ave", to_street="101 Ave", to_borough="Brooklyn")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(req_da))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals('Brooklyn', conn_info.from_city)
        self.assertEquals('1 Ave', conn_info.from_stop)
        self.assertEquals('Brooklyn', conn_info.to_city)
        self.assertEquals('101 Ave', conn_info.to_stop)

    def test_gather_connection_info_request_to_borough(self):
        self.set_ds_street_connection_info(from_street="1 Ave", to_street="101 St")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct('request(to_borough)'),str(req_da))
        self.assertEquals('New York', conn_info.from_city)
        self.assertEquals('1 Ave', conn_info.from_stop)
        self.assertEquals('New York', conn_info.to_city)
        self.assertEquals('101 St', conn_info.to_stop)

    # def test_gather_connection_info_street_infer_from_city(self):
    #     self.set_ds_street_connection_info(from_street="1 Av", to_borough="Bronx")
    #     req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
    #     self.assertEquals(DialogueAct('iconfirm(to_city="Baltimore")&iconfirm(from_city="New York")'), iconfirm_da)
    #     self.assertEquals(0, len(req_da))
    #     self.assertEquals('Bronx', conn_info.to_city)
    #     self.assertEquals('Bronx', conn_info.from_city)
    #     self.assertEquals('1 Av', conn_info.from_street)

    def test_gather_connection_info_street_infer_to_borough(self):
        self.set_ds_street_connection_info(to_street="1 Ct", from_borough="Manhattan")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct('request(from_stop)'),str(req_da))
        self.assertEquals('1 Ct', conn_info.to_stop)
        self.assertEquals('Brooklyn', conn_info.to_city)
        self.assertEquals('Manhattan', conn_info.from_city)

    def test_gather_connection_info_street_infer_from_to_borough(self):
        self.set_ds_street_connection_info(from_street="1 Ave", to_street="1 Ct")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(0, len(req_da))
        self.assertEquals('1 Ave', conn_info.from_stop)
        self.assertEquals('Brooklyn', conn_info.to_city)
        self.assertEquals('1 Ct', conn_info.to_stop)
        self.assertEquals('Brooklyn', conn_info.from_city)

    def test_gather_connection_info_request_from_street(self):
        self.set_ds_street_connection_info(to_street="1 Ct")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct('request(from_stop)'),str(req_da))
        self.assertEquals('1 Ct', conn_info.to_stop)

    def test_gather_connection_info_request_to_street(self):
        self.set_ds_street_connection_info(from_street="1 Ave")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct('request(to_stop)'), str(req_da))
        self.assertEquals('1 Ave', conn_info.from_stop)





    def test_gather_connection_info_infer_from_city(self):
        self.set_ds_connection_info(from_stop="City Hall", to_stop="Broadway", to_city="New York")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(req_da))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals('New York', conn_info.from_city)
        self.assertEquals('City Hall', conn_info.from_stop)
        self.assertEquals('New York', conn_info.to_city)
        self.assertEquals('Broadway', conn_info.to_stop)

    def test_gather_connection_info_request_to_city(self):
        self.set_ds_connection_info(from_stop="City Hall", to_stop="Broadway")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct('request(to_city)'),str(req_da))
        self.assertEquals('none', conn_info.from_city)
        self.assertEquals('City Hall', conn_info.from_stop)
        self.assertEquals('none', conn_info.to_city)
        self.assertEquals('Broadway', conn_info.to_stop)

    def test_gather_connection_info_infer_from_city_iconfirm(self):
        self.set_ds_connection_info(from_stop="Wall Street", to_city="Baltimore")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(req_da))
        self.assertEquals(DialogueAct('iconfirm(to_city="Baltimore")&iconfirm(from_city="New York")'), iconfirm_da)
        self.assertEquals('Baltimore', conn_info.to_city)
        self.assertEquals('New York', conn_info.from_city)
        self.assertEquals('Wall Street', conn_info.from_stop)

    def test_gather_connection_info_infer_to_city(self):
        self.set_ds_connection_info(to_stop="Central Park", from_city="Ohio")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(req_da))
        self.assertEquals(DialogueAct('iconfirm(to_city="New York")&iconfirm(from_city="Ohio")'), iconfirm_da)
        self.assertEquals('Central Park', conn_info.to_stop)
        self.assertEquals('New York', conn_info.to_city)
        self.assertEquals('Ohio', conn_info.from_city)

    def test_gather_connection_info_infer_from_to_city(self):
        self.set_ds_connection_info(to_stop="Central Park", from_stop="Wall Street")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(0, len(req_da))
        self.assertEquals('Central Park', conn_info.to_stop)
        self.assertEquals('New York', conn_info.to_city)
        self.assertEquals('Wall Street', conn_info.from_stop)
        self.assertEquals('New York', conn_info.from_city)
    
    def test_gather_connection_info_request_to_stop_from_empty(self):
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct("request(to_stop)"),str(req_da))

    def test_gather_connection_info_request_from_stop(self):
        self.set_ds_connection_info(to_stop="Central Park")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct("request(from_stop)"),str(req_da))
        self.assertEquals('Central Park', conn_info.to_stop)
        self.assertEquals('New York', conn_info.to_city)
        
    def test_gather_connection_info_request_to_stop(self):
        self.set_ds_connection_info(from_stop="Wall Street")
        req_da, iconfirm_da, conn_info = self.policy.gather_connection_info(self.ds, self.ds.get_accepted_slots(0.8))
        self.assertEquals(0, len(iconfirm_da))
        self.assertEquals(DialogueAct("request(to_stop)"),str(req_da))
        self.assertEquals('Wall Street', conn_info.from_stop)
        self.assertEquals('New York', conn_info.from_city)

        

    # ===== DEPARTURE TIMES =====

    def test_req_departure_time_rel_missed(self):
        self.set_ds_directions()
        self.ds.directions[0].legs[0].steps[1].departure_time = self.now - timedelta(minutes=1)

        dialogue_act = self.policy.req_departure_time_rel(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[0]))
        self.assertEquals('apology()', str(dialogue_act.dais[1]))
        self.assertEquals('inform(missed_connection="true")', str(dialogue_act.dais[2]))

    def test_req_departure_time_rel_now(self):
        self.set_ds_directions()
        self.ds.directions[0].legs[0].steps[1].departure_time = self.now

        dialogue_act = self.policy.req_departure_time_rel(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[0]))
        self.assertEquals('inform(from_stop="eighty sixth street")', str(dialogue_act.dais[1]))
        self.assertEquals('inform(departure_time_rel="now")', str(dialogue_act.dais[2]))

    def test_req_departure_time_rel_in_five_minutes(self):
        self.set_ds_directions()
        self.ds.directions[0].legs[0].steps[1].departure_time = self.now + timedelta(minutes=5)

        dialogue_act = self.policy.req_departure_time_rel(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[0]))
        self.assertEquals('inform(from_stop="eighty sixth street")', str(dialogue_act.dais[1]))
        self.assertEquals('inform(departure_time_rel="0:05")', str(dialogue_act.dais[2]))

    def test_req_departure_time_abs(self):
        self.set_ds_directions()
        dialogue_act = self.policy.req_departure_time(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(from_stop="eighty sixth street")', str(dialogue_act.dais[0]))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[1]))
        self.assertEquals('inform(departure_time="01:46:PM")', str(dialogue_act.dais[2]))
        
     # ===== ARRIVAL TIMES =====

    def test_req_arrival_time_rel_in_five_minutes(self):
        self.set_ds_directions()
        self.ds.directions[0].legs[0].steps[1].arrival_time = self.now + timedelta(minutes=5)

        dialogue_act = self.policy.req_arrival_time_rel(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(to_stop="wall street")', str(dialogue_act.dais[0]))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[1]))
        self.assertEquals('inform(arrival_time_rel="0:05")', str(dialogue_act.dais[2]))    

    def test_req_arrival_time_abs(self):
        self.set_ds_directions()
        dialogue_act = self.policy.req_arrival_time(self.ds)

        self.assertEquals(3, len(dialogue_act.dais))
        self.assertEquals('inform(to_stop="wall street")', str(dialogue_act.dais[0]))
        self.assertEquals('inform(vehicle="subway")', str(dialogue_act.dais[1]))
        self.assertEquals('inform(arrival_time="02:04:PM")', str(dialogue_act.dais[2]))

    # ===== TIME INTERPRETATION =====

    def test_interpret_time_string_now(self):
        time, _ = self.policy.interpret_time('now', 'none', 'none', 'none', 'none')
        self.assertEquals(time, self.now)

    def test_interpret_time_empty(self):
        time, _ = self.policy.interpret_time('none', 'none', 'none', 'none', 'none')
        self.assertEquals(time, self.now)

    def test_interpret_time_in_twenty_minutes(self):
        time, _ = self.policy.interpret_time('none', 'none', '0:20', 'none', 'none')
        true_time = self.now + timedelta(minutes=20)
        self.assertEquals(true_time, time)

    def test_interpret_time_tomorrow(self):
        time, _ = self.policy.interpret_time('none', 'none', 'none', 'tomorrow', 'none')
        true_time = self.now + timedelta(days=1)
        self.assertEquals(true_time, time)

    def test_interpret_time_tomorrow_at_eight_pm(self):
        time, _ = self.policy.interpret_time('8:00', 'pm', 'none', 'tomorrow', 'none')
        true_time = datetime.combine(self.now + timedelta(days=1), dttime(hour=20))
        self.assertEquals(true_time, time)

    def test_interpret_time_morning(self):
        time, _ = self.policy.interpret_time('none', 'morning', 'none', 'none', 'none')
        true_time = datetime.combine(self.now, dttime(hour=6))
        true_time += timedelta(days=1) if true_time < datetime.now() else timedelta(hours=0)
        self.assertEquals(true_time, time)

    # ===== SET UP AND CONSTANTS =====

    def set_ds_directions(self):
        travel = Travel(from_city='New York', from_stop='Wall street',
                       from_stop_geo=None, to_stop_geo=None,
                       to_city='New York', to_stop='Central park',
                       vehicle='none', max_transfers='none')
        self.ds.directions = GoogleDirections(input_json=self.get_directions_json(), travel=travel)
        self.ds['route_alternative'] = 0

    def set_ds_connection_info(self, to_stop='none', from_stop='none', to_city='none', from_city='none'):
        self.ds.slots['to_stop'].scale(0.0)
        self.ds.slots['to_stop'].add(to_stop, 1.0)
        self.ds.slots['from_stop'].scale(0.0)
        self.ds.slots['from_stop'].add(from_stop, 1.0)
        self.ds.slots['to_city'].scale(0.0)
        self.ds.slots['to_city'].add(to_city, 1.0)
        self.ds.slots['from_city'].scale(0.0)
        self.ds.slots['from_city'].add(from_city, 1.0)
        
    def set_ds_street_connection_info(self, to_street='none', to_street2='none', to_borough='none', from_street='none', from_street2='none', from_borough='none'):
        self.ds.slots['to_street'].scale(0.0)
        self.ds.slots['to_street'].add(to_street, 1.0)
        self.ds.slots['to_street2'].scale(0.0)
        self.ds.slots['to_street2'].add(to_street2, 1.0)
        self.ds.slots['to_borough'].scale(0.0)
        self.ds.slots['to_borough'].add(to_borough, 1.0)
        self.ds.slots['from_street'].scale(0.0)
        self.ds.slots['from_street'].add(from_street, 1.0)
        self.ds.slots['from_street2'].scale(0.0)
        self.ds.slots['from_street2'].add(from_street2, 1.0)
        self.ds.slots['from_borough'].scale(0.0)
        self.ds.slots['from_borough'].add(from_borough, 1.0)


    def get_clean_ds(self):
        ds =  DeterministicDiscriminativeDialogueState(self.cfg, self.ontology)
        # add time so it wont randomly (1/10) ask for departure_time
        ds.slots['time'].scale(0.0)
        ds.slots['time'].add('value', 1.0)
        return ds

    def setUp(self):

        self.cfg = Config.load_configs(log=False)
        self.cfg.update(self.get_config())
        self.ontology = Ontology(self.cfg['DM']['ontology'])
        self.policy = PTIENHDCPolicy(self.cfg, self.ontology)

        self.now = datetime.now()
        self.now -= timedelta(seconds=self.now.second, microseconds=self.now.microsecond)
        self.utcnow = datetime.utcnow()
        self.utcnow -= timedelta(seconds=self.utcnow.second, microseconds=self.utcnow.microsecond)

        self.ds = self.get_clean_ds()

    def get_config(self):
        return {
            'PublicTransportInfoEN': {
                'max_turns': 120,
              },
            'DM': {
    'debug': True,
    'type': 'basic',
    'epilogue': {
        # if set to None, no question is asked
        # 'final_question': u"I have one last question, have You obtained desired information?",
        'final_question': None,
        # if set to None, no code is given
        # if set to a valid url, a code is given and reported to the url as "url.format(code=code)"
        # 'final_code_url': None,
        'final_code_url': 'https://147.251.253.9/?q={code}&a=1',
        # time in seconds before valid dialogue can successfully end (to prevent from saying hello, good bye)
        'final_code_min_turn_count': 5,
        'final_code_text_min_turn_count_not_reached': u"I'm sorry, You haven't met the minimum question count limit.",
        # the message is generated as "final_code_text.format(code=code)"
        'final_code_text': u'Your code is {code} .',
        'final_code_text_repeat': u' I repeat, ',
        # initialise the seed of the code generation algorithm
        'code_seed': 1,
    },
    'basic': {
        'debug': True,
    },
    'ontology': as_project_path('applications/PublicTransportInfoEN/data/ontology.py'),
    'dialogue_state': {
        'type': DeterministicDiscriminativeDialogueState,
     },
    'DeterministicDiscriminativeDialogueState': {
        #'type' : 'MDP',
        'type' : 'UFAL_DSTC_1.0_approx',
    },
    'dialogue_policy': {
        'type': PTIENHDCPolicy,
        'PTIENHDCPolicy': {
            'accept_prob_ludait': 0.5,
            'accept_prob_being_requested': 0.8,
            'accept_prob_being_confirmed': 0.8,
            'accept_prob_being_selected': 0.8,
            'accept_prob_noninformed': 0.8,
            'accept_prob': 0.8,
            'confirm_prob':  0.4,
            'select_prob': 0.4,
            'min_change_prob': 0.1,
        }
    },
  },
        }

    def get_directions_json(self):
        return{
    'routes': [{
        'overview_polyline': {
            'points': 'yi|wFhlmbMTe@b@i@f@U`@GFg@Rm@P}@L{@Fe@J]T]ZMRWJUH[@c@Bg@Dm@Jq@T_AnBsBdC{HnCuIgGaE|A{ETs@N_@tc@vYhdArq@b_Axm@XXPb@Lh@rAjJH^N\\RVrr@td@zn@za@PHd@Hd@Dh@AdCUz@Av@B~O`Cv@Xl@d@f@n@t@nA\\^nMlKtGnEdMnJFFRLf@VnDbAj@XnLpJvY`WTNXHXD|DTh@Fb@N`@TdDpChBhBVZPb@Nf@~C|RHXXj@FHhDrCpPtMQ_A\\u@hAmBrCmFjAmC'
        },
        'warnings': ['Walking directions are in beta.    Use caution \u2013 This route may be missing sidewalks or pedestrian paths.'],
        'bounds': {
            'northeast': {
                'lat': 40.7825267,
                'lng': -73.955589
            },
            'southwest': {
                'lat': 40.7060081,
                'lng': -74.011862
            }
        },
        'waypoint_order': [],
        'summary': '',
        'copyrights': 'Map data \xa92015 Google',
        'legs': [{
            'distance': {
                'text': '6.8 mi',
                'value': 10887
            },
            'end_address': '58 Wall Street, New York, NY 10005, USA',
            'via_waypoint': [],
            'start_address': '1 West 86th Street, New York, NY 10024, USA',
            'arrival_time': {
                'text': '2:07pm',
                'time_zone': 'America/New_York',
                'value': 1422904073
            },
            'steps': [{
                'html_instructions': 'Walk to 86 St',
                'distance': {
                    'text': '0.7 mi',
                    'value': 1088
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.7825267,
                    'lng': -73.9656492
                },
                'polyline': {
                    'points': 'yi|wFhlmbMHQJSNURSPKTI`@GFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FUnBsBdC{H~BqHNc@_C}AgCcBxAsEBGFO@E@GHUN_@'
                },
                'duration': {
                    'text': '13 mins',
                    'value': 801
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b>',
                    'distance': {
                        'text': '299 ft',
                        'value': 91
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.7825267,
                        'lng': -73.9656492
                    },
                    'polyline': {
                        'points': 'yi|wFhlmbMHQJSNURSPKTI`@G'
                    },
                    'duration': {
                        'text': '1 min',
                        'value': 63
                    },
                    'end_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> toward <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 303
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    },
                    'polyline': {
                        'points': 'ue|wFzhmbMFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FU'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    }
                }, {
                    'html_instructions': 'Continue onto <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 396
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    },
                    'polyline': {
                        'points': '{~{wFdulbMnBsBdC{H~BqHNc@'
                    },
                    'duration': {
                        'text': '5 mins',
                        'value': 319
                    },
                    'end_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> onto <b>Park Ave</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 167
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    },
                    'polyline': {
                        'points': 'ur{wF~|kbM_C}AgCcB'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 123
                    },
                    'end_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    }
                }, {
                    'html_instructions': 'Turn <b>right</b> onto <b>E 86th St</b><div style="font-size:0.9em">Destination will be on the right</div>',
                    'distance': {
                        'text': '430 ft',
                        'value': 131
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-right',
                    'start_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    },
                    'polyline': {
                        'points': '}z{wF|vkbMxAsEBGFO@E@GHUN_@'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 94
                    },
                    'end_location': {
                        'lat': 40.779492,
                        'lng': -73.955589
                    }
                }],
                'end_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                }
            }, {
                'html_instructions': 'Subway towards Crown Hts - Utica Av',
                'distance': {
                    'text': '5.9 mi',
                    'value': 9506
                },
                'travel_mode': 'TRANSIT',
                'start_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                },
                'polyline': {
                    'points': 'yv{wFlmkbMtc@vYfa@~W`b@rXz`@tWx\\vTFDDDFDDDDFDDBFDHBFBHBHBH@HBJ@Jd@`Dh@tD@F@F@FBF@FBFBFBDBFBDDDDDBDDDDDl_@tVxQrL`SrMxZfSHDFBH@FBH@H@H@H@F?H@J?H?HAH?JAPCPCPCPANAPANANAN?L?L?N?L@L?J@lNtBPBNBNBLDLDLDLFJFJHJHHHJHHJFJHLDHDJDHFHDHDHFFFHDFFFFFFFDFFDHFvLvJtGnEdMnJBBBBDBBBBBD@BBDBB@DBB@D@B@DBB@xCx@@@B?@@B?@@B@@?@@B@@@B?@@@@B@B@B@@@@@@?@@@@B@@@@@@@B@@@@@BB|K`JxFbFpQtODBDBDBBBDBDBD@DBD@F@D@D@D?F@D?`DRJ@H?H@J?H@HBF@HBHBFDHBFDFDFDFF|ChCbBbBDDDFDDDFDDBFDHBFBHBFBHBHBJ@HBJvC`R@D@F@D@DBD@FBB@DBDBD@DBBBBBDBBhDrCpPtM'
                },
                'transit_details': {
                    'num_stops': 6,
                    'departure_stop': {
                        'location': {
                            'lat': 40.779492,
                            'lng': -73.955589
                        },
                        'name': '86 St'
                    },
                    'headsign': 'Crown Hts - Utica Av',
                    'arrival_time': {
                        'text': '2:04pm',
                        'time_zone': 'America/New_York',
                        'value': 1422903870
                    },
                    'arrival_stop': {
                        'location': {
                            'lat': 40.707557,
                            'lng': -74.011862
                        },
                        'name': 'Wall St'
                    },
                    'line': {
                        'name': 'Lexington Avenue Express',
                        'short_name': '4',
                        'color': '#00933c',
                        'agencies': [{
                            'url': 'http://www.mta.info/',
                            'phone': '1 718-330-1234',
                            'name': 'MTA New York City Transit'
                        }],
                        'url': 'http://web.mta.info/nyct/service/pdf/t4cur.pdf',
                        'vehicle': {
                            'type': 'SUBWAY',
                            'name': 'Subway',
                            'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/metro.png'
                        },
                        'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/us-ny-mta/4.png'
                    },
                    'departure_time': {
                        'text': '1:46pm',
                        'time_zone': 'America/New_York',
                        'value': 1422902790
                    }
                },
                'duration': {
                    'text': '18 mins',
                    'value': 1080
                },
                'end_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                }
            }, {
                'html_instructions': 'Walk to 58 Wall Street, New York, NY 10005, USA',
                'distance': {
                    'text': '0.2 mi',
                    'value': 293
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                },
                'polyline': {
                    'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                },
                'duration': {
                    'text': '3 mins',
                    'value': 202
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b> on <b>Wall St</b> toward <b>New St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 293
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.707557,
                        'lng': -74.011862
                    },
                    'polyline': {
                        'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.7060081,
                        'lng': -74.00881509999999
                    }
                }],
                'end_location': {
                    'lat': 40.7060081,
                    'lng': -74.00881509999999
                }
            }],
            'duration': {
                'text': '35 mins',
                'value': 2085
            },
            'end_location': {
                'lat': 40.7060081,
                'lng': -74.00881509999999
            },
            'start_location': {
                'lat': 40.7825267,
                'lng': -73.9656492
            },
            'departure_time': {
                'text': '1:33pm',
                'time_zone': 'America/New_York',
                'value': 1422901988
            }
        }]
    }, {
        'overview_polyline': {
            'points': 'yi|wFhlmbMTe@b@i@f@U`@GFg@Rm@P}@L{@Fe@J]T]ZMRWJUH[@c@Bg@Dm@Jq@T_AnBsBdC{HnCuIgGaE|A{ETs@N_@tc@vYhdArq@b_Axm@XXPb@Lh@rAjJH^N\\RVrr@td@zn@za@PHd@Hd@Dh@AdCUz@Av@B~O`Cv@Xl@d@f@n@t@nA\\^nMlKtGnEdMnJFFRLf@VnDbAj@XnLpJvY`WTNXHXD|DTh@Fb@N`@TdDpChBhBVZPb@Nf@~C|RHXXj@FHhDrCpPtMQ_A\\u@hAmBrCmFjAmC'
        },
        'warnings': ['Walking directions are in beta.    Use caution \u2013 This route may be missing sidewalks or pedestrian paths.'],
        'bounds': {
            'northeast': {
                'lat': 40.7825267,
                'lng': -73.955589
            },
            'southwest': {
                'lat': 40.7060081,
                'lng': -74.011862
            }
        },
        'waypoint_order': [],
        'summary': '',
        'copyrights': 'Map data \xa92015 Google',
        'legs': [{
            'distance': {
                'text': '6.8 mi',
                'value': 10887
            },
            'end_address': '58 Wall Street, New York, NY 10005, USA',
            'via_waypoint': [],
            'start_address': '1 West 86th Street, New York, NY 10024, USA',
            'arrival_time': {
                'text': '2:11pm',
                'time_zone': 'America/New_York',
                'value': 1422904313
            },
            'steps': [{
                'html_instructions': 'Walk to 86 St',
                'distance': {
                    'text': '0.7 mi',
                    'value': 1088
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.7825267,
                    'lng': -73.9656492
                },
                'polyline': {
                    'points': 'yi|wFhlmbMHQJSNURSPKTI`@GFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FUnBsBdC{H~BqHNc@_C}AgCcBxAsEBGFO@E@GHUN_@'
                },
                'duration': {
                    'text': '13 mins',
                    'value': 801
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b>',
                    'distance': {
                        'text': '299 ft',
                        'value': 91
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.7825267,
                        'lng': -73.9656492
                    },
                    'polyline': {
                        'points': 'yi|wFhlmbMHQJSNURSPKTI`@G'
                    },
                    'duration': {
                        'text': '1 min',
                        'value': 63
                    },
                    'end_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> toward <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 303
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    },
                    'polyline': {
                        'points': 'ue|wFzhmbMFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FU'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    }
                }, {
                    'html_instructions': 'Continue onto <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 396
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    },
                    'polyline': {
                        'points': '{~{wFdulbMnBsBdC{H~BqHNc@'
                    },
                    'duration': {
                        'text': '5 mins',
                        'value': 319
                    },
                    'end_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> onto <b>Park Ave</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 167
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    },
                    'polyline': {
                        'points': 'ur{wF~|kbM_C}AgCcB'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 123
                    },
                    'end_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    }
                }, {
                    'html_instructions': 'Turn <b>right</b> onto <b>E 86th St</b><div style="font-size:0.9em">Destination will be on the right</div>',
                    'distance': {
                        'text': '430 ft',
                        'value': 131
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-right',
                    'start_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    },
                    'polyline': {
                        'points': '}z{wF|vkbMxAsEBGFO@E@GHUN_@'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 94
                    },
                    'end_location': {
                        'lat': 40.779492,
                        'lng': -73.955589
                    }
                }],
                'end_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                }
            }, {
                'html_instructions': 'Subway towards Flatbush Av - Brooklyn College',
                'distance': {
                    'text': '5.9 mi',
                    'value': 9506
                },
                'travel_mode': 'TRANSIT',
                'start_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                },
                'polyline': {
                    'points': 'yv{wFlmkbMtc@vYfa@~W`b@rXz`@tWx\\vTFDDDFDDDDFDDBFDHBFBHBHBH@HBJ@Jd@`Dh@tD@F@F@FBF@FBFBFBDBFBDDDDDBDDDDDl_@tVxQrL`SrMxZfSHDFBH@FBH@H@H@H@F?H@J?H?HAH?JAPCPCPCPANAPANANAN?L?L?N?L@L?J@lNtBPBNBNBLDLDLDLFJFJHJHHHJHHJFJHLDHDJDHFHDHDHFFFHDFFFFFFFDFFDHFvLvJtGnEdMnJBBBBDBBBBBD@BBDBB@DBB@D@B@DBB@xCx@@@B?@@B?@@B@@?@@B@@@B?@@@@B@B@B@@@@@@?@@@@B@@@@@@@B@@@@@BB|K`JxFbFpQtODBDBDBBBDBDBD@DBD@F@D@D@D?F@D?`DRJ@H?H@J?H@HBF@HBHBFDHBFDFDFDFF|ChCbBbBDDDFDDDFDDBFDHBFBHBFBHBHBJ@HBJvC`R@D@F@D@DBD@FBB@DBDBD@DBBBBBDBBhDrCpPtM'
                },
                'transit_details': {
                    'num_stops': 6,
                    'departure_stop': {
                        'location': {
                            'lat': 40.779492,
                            'lng': -73.955589
                        },
                        'name': '86 St'
                    },
                    'headsign': 'Flatbush Av - Brooklyn College',
                    'arrival_time': {
                        'text': '2:08pm',
                        'time_zone': 'America/New_York',
                        'value': 1422904110
                    },
                    'arrival_stop': {
                        'location': {
                            'lat': 40.707557,
                            'lng': -74.011862
                        },
                        'name': 'Wall St'
                    },
                    'line': {
                        'name': 'Lexington Avenue Express',
                        'short_name': '5',
                        'color': '#00933c',
                        'agencies': [{
                            'url': 'http://www.mta.info/',
                            'phone': '1 718-330-1234',
                            'name': 'MTA New York City Transit'
                        }],
                        'url': 'http://web.mta.info/nyct/service/pdf/t5cur.pdf',
                        'vehicle': {
                            'type': 'SUBWAY',
                            'name': 'Subway',
                            'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/metro.png'
                        },
                        'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/us-ny-mta/5.png'
                    },
                    'departure_time': {
                        'text': '1:50pm',
                        'time_zone': 'America/New_York',
                        'value': 1422903030
                    }
                },
                'duration': {
                    'text': '18 mins',
                    'value': 1080
                },
                'end_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                }
            }, {
                'html_instructions': 'Walk to 58 Wall Street, New York, NY 10005, USA',
                'distance': {
                    'text': '0.2 mi',
                    'value': 293
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                },
                'polyline': {
                    'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                },
                'duration': {
                    'text': '3 mins',
                    'value': 202
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b> on <b>Wall St</b> toward <b>New St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 293
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.707557,
                        'lng': -74.011862
                    },
                    'polyline': {
                        'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.7060081,
                        'lng': -74.00881509999999
                    }
                }],
                'end_location': {
                    'lat': 40.7060081,
                    'lng': -74.00881509999999
                }
            }],
            'duration': {
                'text': '35 mins',
                'value': 2085
            },
            'end_location': {
                'lat': 40.7060081,
                'lng': -74.00881509999999
            },
            'start_location': {
                'lat': 40.7825267,
                'lng': -73.9656492
            },
            'departure_time': {
                'text': '1:37pm',
                'time_zone': 'America/New_York',
                'value': 1422902228
            }
        }]
    }, {
        'overview_polyline': {
            'points': 'yi|wFhlmbMTe@b@i@f@U`@GFg@Rm@P}@L{@Fe@J]T]ZMRWJUH[@c@Bg@Dm@Jq@T_AnBsBdC{HnCuIgGaE|A{ETs@N_@tc@vYhdArq@b_Axm@XXPb@Lh@rAjJH^N\\RVrr@td@zn@za@PHd@Hd@Dh@AdCUz@Av@B~O`Cv@Xl@d@f@n@t@nA\\^nMlKtGnEdMnJFFRLf@VnDbAj@XnLpJvY`WTNXHXD|DTh@Fb@N`@TdDpChBhBVZPb@Nf@~C|RHXXj@FHhDrCpPtMQ_A\\u@hAmBrCmFjAmC'
        },
        'warnings': ['Walking directions are in beta.    Use caution \u2013 This route may be missing sidewalks or pedestrian paths.'],
        'bounds': {
            'northeast': {
                'lat': 40.7825267,
                'lng': -73.955589
            },
            'southwest': {
                'lat': 40.7060081,
                'lng': -74.011862
            }
        },
        'waypoint_order': [],
        'summary': '',
        'copyrights': 'Map data \xa92015 Google',
        'legs': [{
            'distance': {
                'text': '6.8 mi',
                'value': 10887
            },
            'end_address': '58 Wall Street, New York, NY 10005, USA',
            'via_waypoint': [],
            'start_address': '1 West 86th Street, New York, NY 10024, USA',
            'arrival_time': {
                'text': '2:15pm',
                'time_zone': 'America/New_York',
                'value': 1422904553
            },
            'steps': [{
                'html_instructions': 'Walk to 86 St',
                'distance': {
                    'text': '0.7 mi',
                    'value': 1088
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.7825267,
                    'lng': -73.9656492
                },
                'polyline': {
                    'points': 'yi|wFhlmbMHQJSNURSPKTI`@GFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FUnBsBdC{H~BqHNc@_C}AgCcBxAsEBGFO@E@GHUN_@'
                },
                'duration': {
                    'text': '13 mins',
                    'value': 801
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b>',
                    'distance': {
                        'text': '299 ft',
                        'value': 91
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.7825267,
                        'lng': -73.9656492
                    },
                    'polyline': {
                        'points': 'yi|wFhlmbMHQJSNURSPKTI`@G'
                    },
                    'duration': {
                        'text': '1 min',
                        'value': 63
                    },
                    'end_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> toward <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 303
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7818661,
                        'lng': -73.96509809999999
                    },
                    'polyline': {
                        'points': 'ue|wFzhmbMFg@FSJYFUHg@Dc@FW@UDOBMFOT]ZMLODGDIDKDOBK@K?W@Q@U@SBYDSD]Li@FU'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    }
                }, {
                    'html_instructions': 'Continue onto <b>E 84th St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 396
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.78077830000001,
                        'lng': -73.9619483
                    },
                    'polyline': {
                        'points': '{~{wFdulbMnBsBdC{H~BqHNc@'
                    },
                    'duration': {
                        'text': '5 mins',
                        'value': 319
                    },
                    'end_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> onto <b>Park Ave</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 167
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7788333,
                        'lng': -73.9580794
                    },
                    'polyline': {
                        'points': 'ur{wF~|kbM_C}AgCcB'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 123
                    },
                    'end_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    }
                }, {
                    'html_instructions': 'Turn <b>right</b> onto <b>E 86th St</b><div style="font-size:0.9em">Destination will be on the right</div>',
                    'distance': {
                        'text': '430 ft',
                        'value': 131
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-right',
                    'start_location': {
                        'lat': 40.7801464,
                        'lng': -73.95711109999999
                    },
                    'polyline': {
                        'points': '}z{wF|vkbMxAsEBGFO@E@GHUN_@'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 94
                    },
                    'end_location': {
                        'lat': 40.779492,
                        'lng': -73.955589
                    }
                }],
                'end_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                }
            }, {
                'html_instructions': 'Subway towards Crown Hts - Utica Av',
                'distance': {
                    'text': '5.9 mi',
                    'value': 9506
                },
                'travel_mode': 'TRANSIT',
                'start_location': {
                    'lat': 40.779492,
                    'lng': -73.955589
                },
                'polyline': {
                    'points': 'yv{wFlmkbMtc@vYfa@~W`b@rXz`@tWx\\vTFDDDFDDDDFDDBFDHBFBHBHBH@HBJ@Jd@`Dh@tD@F@F@FBF@FBFBFBDBFBDDDDDBDDDDDl_@tVxQrL`SrMxZfSHDFBH@FBH@H@H@H@F?H@J?H?HAH?JAPCPCPCPANAPANANAN?L?L?N?L@L?J@lNtBPBNBNBLDLDLDLFJFJHJHHHJHHJFJHLDHDJDHFHDHDHFFFHDFFFFFFFDFFDHFvLvJtGnEdMnJBBBBDBBBBBD@BBDBB@DBB@D@B@DBB@xCx@@@B?@@B?@@B@@?@@B@@@B?@@@@B@B@B@@@@@@?@@@@B@@@@@@@B@@@@@BB|K`JxFbFpQtODBDBDBBBDBDBD@DBD@F@D@D@D?F@D?`DRJ@H?H@J?H@HBF@HBHBFDHBFDFDFDFF|ChCbBbBDDDFDDDFDDBFDHBFBHBFBHBHBJ@HBJvC`R@D@F@D@DBD@FBB@DBDBD@DBBBBBDBBhDrCpPtM'
                },
                'transit_details': {
                    'num_stops': 6,
                    'departure_stop': {
                        'location': {
                            'lat': 40.779492,
                            'lng': -73.955589
                        },
                        'name': '86 St'
                    },
                    'headsign': 'Crown Hts - Utica Av',
                    'arrival_time': {
                        'text': '2:12pm',
                        'time_zone': 'America/New_York',
                        'value': 1422904350
                    },
                    'arrival_stop': {
                        'location': {
                            'lat': 40.707557,
                            'lng': -74.011862
                        },
                        'name': 'Wall St'
                    },
                    'line': {
                        'name': 'Lexington Avenue Express',
                        'short_name': '4',
                        'color': '#00933c',
                        'agencies': [{
                            'url': 'http://www.mta.info/',
                            'phone': '1 718-330-1234',
                            'name': 'MTA New York City Transit'
                        }],
                        'url': 'http://web.mta.info/nyct/service/pdf/t4cur.pdf',
                        'vehicle': {
                            'type': 'SUBWAY',
                            'name': 'Subway',
                            'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/metro.png'
                        },
                        'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/us-ny-mta/4.png'
                    },
                    'departure_time': {
                        'text': '1:54pm',
                        'time_zone': 'America/New_York',
                        'value': 1422903270
                    }
                },
                'duration': {
                    'text': '18 mins',
                    'value': 1080
                },
                'end_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                }
            }, {
                'html_instructions': 'Walk to 58 Wall Street, New York, NY 10005, USA',
                'distance': {
                    'text': '0.2 mi',
                    'value': 293
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.707557,
                    'lng': -74.011862
                },
                'polyline': {
                    'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                },
                'duration': {
                    'text': '3 mins',
                    'value': 202
                },
                'steps': [{
                    'html_instructions': 'Head <b>southeast</b> on <b>Wall St</b> toward <b>New St</b>',
                    'distance': {
                        'text': '0.2 mi',
                        'value': 293
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.707557,
                        'lng': -74.011862
                    },
                    'polyline': {
                        'points': 'gumwFbmvbMQ_A\\u@hAmBrCmFjAmC'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 202
                    },
                    'end_location': {
                        'lat': 40.7060081,
                        'lng': -74.00881509999999
                    }
                }],
                'end_location': {
                    'lat': 40.7060081,
                    'lng': -74.00881509999999
                }
            }],
            'duration': {
                'text': '35 mins',
                'value': 2085
            },
            'end_location': {
                'lat': 40.7060081,
                'lng': -74.00881509999999
            },
            'start_location': {
                'lat': 40.7825267,
                'lng': -73.9656492
            },
            'departure_time': {
                'text': '1:41pm',
                'time_zone': 'America/New_York',
                'value': 1422902468
            }
        }]
    }, {
        'overview_polyline': {
            'points': 'yi|wFhlmbMKZIz@?nAKF@t@Cf@Gd@KZ]`@g@VYD_@@]I[n@e@r@[XGRALAV?v@[h@e@r@Yt@EX?`@qEwCg@a@f_Axm@`qAxz@xeCdaBdEpC^N\\J^D\\?^C^K\\Ob[wOZMx@Kv@Dv@XbLpHj@ZvIzDnAh@pObFjVjHl@Hn@@r@AbEK~IMx@Dv@Nv@X`c@h[b@X`@P`@F^C\\KZUZ_@xEmLP^vBtB`B~AlAxAxDfDpBdBrCmFjAmC'
        },
        'warnings': ['Walking directions are in beta.    Use caution \u2013 This route may be missing sidewalks or pedestrian paths.'],
        'bounds': {
            'northeast': {
                'lat': 40.785868,
                'lng': -73.9656492
            },
            'southwest': {
                'lat': 40.7060081,
                'lng': -74.01072309999999
            }
        },
        'waypoint_order': [],
        'summary': '',
        'copyrights': 'Map data \xa92015 Google',
        'legs': [{
            'distance': {
                'text': '6.7 mi',
                'value': 10741
            },
            'end_address': '58 Wall Street, New York, NY 10005, USA',
            'via_waypoint': [],
            'start_address': '1 West 86th Street, New York, NY 10024, USA',
            'arrival_time': {
                'text': '2:18pm',
                'time_zone': 'America/New_York',
                'value': 1422904725
            },
            'steps': [{
                'html_instructions': 'Walk to 86 St',
                'distance': {
                    'text': '0.4 mi',
                    'value': 622
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.7825267,
                    'lng': -73.9656492
                },
                'polyline': {
                    'points': 'yi|wFhlmbMCFGRE\\C\\?Z?r@?@KD@F?@@LA\\AVANGd@KZSVIHUNQFKBM@OBOAMAOGMVMV[d@IL[XGRAF?D?HAL?H?l@ORKTS^QROXIZEX?`@iCeBgAq@MKYU'
                },
                'duration': {
                    'text': '8 mins',
                    'value': 457
                },
                'steps': [{
                    'html_instructions': 'Head <b>northwest</b>',
                    'distance': {
                        'text': '243 ft',
                        'value': 74
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.7825267,
                        'lng': -73.9656492
                    },
                    'polyline': {
                        'points': 'yi|wFhlmbMCFGRE\\C\\?Z?r@?@'
                    },
                    'duration': {
                        'text': '1 min',
                        'value': 55
                    },
                    'end_location': {
                        'lat': 40.7826353,
                        'lng': -73.96649950000001
                    }
                }, {
                    'html_instructions': 'Turn <b>right</b> toward <b>Central Park West</b>',
                    'distance': {
                        'text': '26 ft',
                        'value': 8
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-right',
                    'start_location': {
                        'lat': 40.7826353,
                        'lng': -73.96649950000001
                    },
                    'polyline': {
                        'points': 'oj|wFrqmbMKD'
                    },
                    'duration': {
                        'text': '1 min',
                        'value': 6
                    },
                    'end_location': {
                        'lat': 40.7827013,
                        'lng': -73.9665271
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> toward <b>Central Park West</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 166
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7827013,
                        'lng': -73.9665271
                    },
                    'polyline': {
                        'points': '{j|wFxqmbM@F?@@LA\\AVANGd@KZSVIHUNQFKBM@OBOAMAOG'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 122
                    },
                    'end_location': {
                        'lat': 40.7835959,
                        'lng': -73.9676142
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> toward <b>Central Park West</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 232
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7835959,
                        'lng': -73.9676142
                    },
                    'polyline': {
                        'points': 'op|wFpxmbMMVMV[d@IL[XGRAF?D?HAL?H?l@ORKTS^QROXIZEX?`@'
                    },
                    'duration': {
                        'text': '3 mins',
                        'value': 163
                    },
                    'end_location': {
                        'lat': 40.7846217,
                        'lng': -73.9698525
                    }
                }, {
                    'html_instructions': 'Turn <b>right</b> onto <b>Central Park West</b><div style="font-size:0.9em">Destination will be on the right</div>',
                    'distance': {
                        'text': '466 ft',
                        'value': 142
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-right',
                    'start_location': {
                        'lat': 40.7846217,
                        'lng': -73.9698525
                    },
                    'polyline': {
                        'points': '{v|wFpfnbMiCeBgAq@MKYU'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 111
                    },
                    'end_location': {
                        'lat': 40.785868,
                        'lng': -73.968916
                    }
                }],
                'end_location': {
                    'lat': 40.785868,
                    'lng': -73.968916
                }
            }, {
                'html_instructions': 'Subway towards Euclid Av',
                'distance': {
                    'text': '5.9 mi',
                    'value': 9505
                },
                'travel_mode': 'TRANSIT',
                'start_location': {
                    'lat': 40.785868,
                    'lng': -73.968916
                },
                'polyline': {
                    'points': 'u~|wFv`nbMvZbSnc@tYpl@h`@tS~MdIjFrDbCd_@nVj^xUzf@`\\j^xUvDdCLJNFNFLDNDNBN@L?N?NANANENENELIrZoONGLGLENCLCLALAL?L@L@L@LBLDLFLF~DjCBBD@xE~CDBDBDBB@DBDBBBD@BBD@DBB@D@DBB@rHfDJDHDHDHBHDHBHBFDHBFBH@FBFBF@FBtMjEhU`HJBH@JBH@JBJ@J@J?J@J?J?L?J?L?JAzDKF?nIKNAL@L?N@L@L@LBLBLDLDLDLDLFJHLFpWhRtIlGPLPJPHNFPBNBN?NCNCLGLILKLOLOJSlEyK'
                },
                'transit_details': {
                    'num_stops': 13,
                    'departure_stop': {
                        'location': {
                            'lat': 40.785868,
                            'lng': -73.968916
                        },
                        'name': '86 St'
                    },
                    'headsign': 'Euclid Av',
                    'arrival_time': {
                        'text': '2:11pm',
                        'time_zone': 'America/New_York',
                        'value': 1422904290
                    },
                    'arrival_stop': {
                        'location': {
                            'lat': 40.710197,
                            'lng': -74.007691
                        },
                        'name': 'Fulton St'
                    },
                    'line': {
                        'name': '8 Avenue Local',
                        'short_name': 'C',
                        'color': '#2850ad',
                        'agencies': [{
                            'url': 'http://www.mta.info/',
                            'phone': '1 718-330-1234',
                            'name': 'MTA New York City Transit'
                        }],
                        'text_color': '#ffffff',
                        'url': 'http://web.mta.info/nyct/service/pdf/tccur.pdf',
                        'vehicle': {
                            'type': 'SUBWAY',
                            'name': 'Subway',
                            'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/metro.png'
                        },
                        'icon': '//maps.gstatic.com/mapfiles/transit/iw/6/us-ny-mta/C.png'
                    },
                    'departure_time': {
                        'text': '1:50pm',
                        'time_zone': 'America/New_York',
                        'value': 1422903000
                    }
                },
                'duration': {
                    'text': '22 mins',
                    'value': 1290
                },
                'end_location': {
                    'lat': 40.710197,
                    'lng': -74.007691
                }
            }, {
                'html_instructions': 'Walk to 58 Wall Street, New York, NY 10005, USA',
                'distance': {
                    'text': '0.4 mi',
                    'value': 614
                },
                'travel_mode': 'WALKING',
                'start_location': {
                    'lat': 40.710197,
                    'lng': -74.007691
                },
                'polyline': {
                    'points': 'wenwF`subMP^vBtB`B~AlAxA|AtAzApApBdBrCmFjAmC'
                },
                'duration': {
                    'text': '7 mins',
                    'value': 434
                },
                'steps': [{
                    'html_instructions': 'Head <b>southwest</b> on <b>Nassau St</b> toward <b>John St</b>',
                    'distance': {
                        'text': '0.3 mi',
                        'value': 410
                    },
                    'travel_mode': 'WALKING',
                    'start_location': {
                        'lat': 40.710197,
                        'lng': -74.007691
                    },
                    'polyline': {
                        'points': 'wenwF`subMP^vBtB`B~AlAxA|AtAzApApBdB'
                    },
                    'duration': {
                        'text': '5 mins',
                        'value': 293
                    },
                    'end_location': {
                        'lat': 40.7071295,
                        'lng': -74.01072309999999
                    }
                }, {
                    'html_instructions': 'Turn <b>left</b> onto <b>Wall St</b>',
                    'distance': {
                        'text': '0.1 mi',
                        'value': 204
                    },
                    'travel_mode': 'WALKING',
                    'maneuver': 'turn-left',
                    'start_location': {
                        'lat': 40.7071295,
                        'lng': -74.01072309999999
                    },
                    'polyline': {
                        'points': 'qrmwF~evbMrCmFjAmC'
                    },
                    'duration': {
                        'text': '2 mins',
                        'value': 141
                    },
                    'end_location': {
                        'lat': 40.7060081,
                        'lng': -74.00881509999999
                    }
                }],
                'end_location': {
                    'lat': 40.7060081,
                    'lng': -74.00881509999999
                }
            }],
            'duration': {
                'text': '36 mins',
                'value': 2184
            },
            'end_location': {
                'lat': 40.7060081,
                'lng': -74.00881509999999
            },
            'start_location': {
                'lat': 40.7825267,
                'lng': -73.9656492
            },
            'departure_time': {
                'text': '1:42pm',
                'time_zone': 'America/New_York',
                'value': 1422902541
            }
        }]
    }],
    'status': 'OK'
}