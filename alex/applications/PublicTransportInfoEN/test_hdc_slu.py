from unittest import TestCase

from alex.applications.PublicTransportInfoEN.hdc_slu import PTIENHDCSLU
from alex.applications.PublicTransportInfoEN.preprocessing import PTIENSLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.components.slu.base import CategoryLabelDatabase
from alex.utils.config import as_project_path


class TestPTIENHDCSLU(TestCase):

    def test_seventeen_fourteen_o_clock(self):
        utterance = Utterance("fourteen o'clock")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="14:00")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_seventeen_zero_five(self):
        utterance = Utterance("at seventeen zero five")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="17:05")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_seventeen(self):
        utterance = Utterance("at seventeen zero zero")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="17:00")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_ten_p_m(self):
        utterance = Utterance("ten p.m.")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="10:00")', str(cn[0][1]))
        self.assertEquals('inform(ampm="pm")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_ten_o_clock(self):
        utterance = Utterance("at ten o'clock in the afternoon")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="10:00")', str(cn[0][1]))
        self.assertEquals('inform(ampm="pm")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_hour_and_a_half(self):
        utterance = Utterance("hour and a half")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="1:30")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_two_hours_and_a_quarter(self):
        utterance = Utterance("two hours and a quarter")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="2:15")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_quarter_to_eleven(self):
        utterance = Utterance("quarter to eleven")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="10:45")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_in_a_minute(self):
        utterance = Utterance("in a minute")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="0:01")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_in_an_hour(self):
        utterance = Utterance("in an hour")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="1:00")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_three_twenty_five(self):
        utterance = Utterance("three hours twenty five minutes")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="3:25")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_in_two_hours(self):
        utterance = Utterance("in two minutes")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time_rel="0:02")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_two_hours(self):
        utterance = Utterance("two hours")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="2:00")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_two_and_a_half(self):
        utterance = Utterance("two and a half hours")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="2:30")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_two_hours_and_a_half(self):
        utterance = Utterance("two hours and a half")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="2:30")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_half_an_hour(self):
        utterance = Utterance("half an hour")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(time="0:30")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    # directions

    def test_parse_from_street_street_to_street(self):
        utterance = Utterance("i want to go from 7th avenue and 42nd street to broadway")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="7 Ave")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="42 St")', str(cn[1][1]))
        self.assertEquals('inform(to_street="Broadway")', str(cn[2][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[3][1]))
        self.assertEquals(4, len(cn))

    def test_parse_to_city_to_stop2(self):
        utterance = Utterance("to central park in new york")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_stop="Central Park")', str(cn[0][1]))
        self.assertEquals('inform(to_city="New York")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_to_borough_to_street(self):
        utterance = Utterance("TO BROADWAY IN BRONX")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_street="Broadway")', str(cn[0][1]))
        self.assertEquals('inform(to_borough="Bronx")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_next_connection_time(self):
        utterance = Utterance("what time does that leave again")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('request(departure_time)', str(cn[0][1]))
        self.assertEquals('inform(alternative="last")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_from_borough_from_street(self):
        utterance = Utterance("from fifth avenue manhattan")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="5 Ave")', str(cn[0][1]))
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_to_city_to_stop(self):
        utterance = Utterance("to main station new york")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_stop="Main Station")', str(cn[0][1]))
        self.assertEquals('inform(to_city="New York")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_form_street_to_stop(self):
        utterance = Utterance("i would like to go from cypress avenue to the lincoln center")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="Cypress Ave")', str(cn[0][1]))
        self.assertEquals('inform(to_stop="Lincoln Center")', str(cn[1][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[2][1]))
        self.assertEquals(3, len(cn))

    def test_parse_from_to_city(self):
        utterance = Utterance("i want to go from New York to Baltimore")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_city="New York")', str(cn[0][1]))
        self.assertEquals('inform(to_city="Baltimore")', str(cn[1][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[2][1]))
        self.assertEquals(3, len(cn))

    def test_parse_borough_int(self):
        utterance = Utterance("i am in queens at the moment")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(in_borough="Queens")', str(cn[0][1]))
        self.assertEquals(1, len(cn))

    def test_parse_borough_from_to(self):
        utterance = Utterance("i want to go from manhattan to brooklyn")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[0][1]))
        self.assertEquals('inform(to_borough="Brooklyn")', str(cn[1][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[2][1]))
        self.assertEquals(3, len(cn))

    def test_parse_borough_from(self):
        utterance = Utterance("i want to go from manhattan")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[0][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_borough_to(self):
        utterance = Utterance("i want to go to brooklyn")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_borough="Brooklyn")', str(cn[0][1]))
        self.assertEquals('inform(task="find_connection")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_street_at_streets(self):
        utterance = Utterance("i am at the corner of third street and beacon court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="Beacon Ct")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_street_from_street_to_streets(self):
        utterance = Utterance("third street to beacon court at beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="3 St")', str(cn[0][1]))
        self.assertEquals('inform(to_street="Beacon Ct")', str(cn[1][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[2][1]))
        self.assertEquals(3, len(cn))

    def test_parse_street_from_streets_to_streets(self):
        utterance = Utterance("from third street and twenty third avenue to beacon court and beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="23 Ave")', str(cn[1][1]))
        self.assertEquals('inform(to_street="Beacon Ct")', str(cn[2][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[3][1]))
        self.assertEquals(4, len(cn))

    def test_parse_street_to_streets(self):
        utterance = Utterance("to beacon court and beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_street="Beacon Ct")', str(cn[0][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    def test_parse_street_from_streets(self):
        utterance = Utterance("from third street and twenty third avenue")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="23 Ave")', str(cn[1][1]))
        self.assertEquals(2, len(cn))

    @classmethod
    def setUpClass(cls):
        cfg = cls.get_cfg()
        slu_type = cfg['SLU']['type']
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        cls.slu = slu_type(preprocessing, cfg)

    @classmethod
    def get_cfg(cls):
        return {
            'SLU': {
                'debug': True,
                'type': PTIENHDCSLU,
                PTIENHDCSLU: {
                    'cldb_fname': as_project_path("applications/PublicTransportInfoEN/data/database.py"),
                    'preprocessing_cls': PTIENSLUPreprocessing,
                    'utt2da': as_project_path("applications/PublicTransportInfoEN/data/utt2da_dict.txt"),
                },
            },
        }
