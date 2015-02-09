from unittest import TestCase

from alex.applications.PublicTransportInfoEN.hdc_slu import PTIENHDCSLU
from alex.applications.PublicTransportInfoEN.preprocessing import PTIENSLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.components.slu.base import CategoryLabelDatabase
from alex.utils.config import as_project_path


class TestPTIENHDCSLU(TestCase):

    # def test_parse_next_connection_time(self):
    #     utterance = Utterance("when is the next connection")
    #     utterance = Utterance("when is the next train leaving")
    #     cn = self.slu.parse_1_best({'utt': utterance})
    #     self.assertEquals('inform(from_street1="5 Ave")', str(cn[0][1]))
    #     self.assertEquals('inform(from_borough="Manhattan")', str(cn[1][1]))

    def test_parse_from_borough_from_street(self):
        utterance = Utterance("from fifth avenue manhattan")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="5 Ave")', str(cn[0][1]))
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[1][1]))

    def test_parse_to_city_to_stop(self):
        utterance = Utterance("to main station new york")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_stop="Main Station")', str(cn[0][1]))
        self.assertEquals('inform(to_city="New York")', str(cn[1][1]))

    def test_parse_form_street_to_stop(self):
        utterance = Utterance("i would like to go from cypress avenue to the lincoln center")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="Cypress Ave")', str(cn[0][1]))
        self.assertEquals('inform(to_stop="Lincoln Center")', str(cn[1][1]))

    def test_parse_from_to_city(self):
        utterance = Utterance("i want to go from New York to Baltimore")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_city="New York")', str(cn[0][1]))
        self.assertEquals('inform(to_city="Baltimore")', str(cn[1][1]))

    def test_parse_borough_int(self):
        utterance = Utterance("i am in queens at the moment")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(in_borough="Queens")', str(cn[0][1]))

    def test_parse_borough_from_to(self):
        utterance = Utterance("i want to go from manhattan to brooklyn")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[0][1]))
        self.assertEquals('inform(to_borough="Brooklyn")', str(cn[1][1]))

    def test_parse_borough_from(self):
        utterance = Utterance("i want to go from manhattan")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_borough="Manhattan")', str(cn[0][1]))

    def test_parse_borough_to(self):
        utterance = Utterance("i want to go to brooklyn")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_borough="Brooklyn")', str(cn[0][1]))

    def test_parse_street_at_streets(self):
        utterance = Utterance("i am at the corner of third street and beacon court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="Beacon Ct")', str(cn[1][1]))

    def test_parse_street_from_street_to_streets(self):
        utterance = Utterance("third street to beacon court at beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="3 St")', str(cn[0][1]))
        self.assertEquals('inform(to_street1="Beacon Ct")', str(cn[1][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[2][1]))

    def test_parse_street_from_streets_to_streets(self):
        utterance = Utterance("from third street and twenty third avenue to beacon court and beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="23 Ave")', str(cn[1][1]))
        self.assertEquals('inform(to_street1="Beacon Ct")', str(cn[2][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[3][1]))

    def test_parse_street_to_streets(self):
        utterance = Utterance("to beacon court and beamer court")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(to_street1="Beacon Ct")', str(cn[0][1]))
        self.assertEquals('inform(to_street2="Beamer Ct")', str(cn[1][1]))

    def test_parse_street_from_streets(self):
        utterance = Utterance("from third street and twenty third avenue")
        cn = self.slu.parse_1_best({'utt': utterance})
        self.assertEquals('inform(from_street1="3 St")', str(cn[0][1]))
        self.assertEquals('inform(from_street2="23 Ave")', str(cn[1][1]))

    @classmethod
    def setUpClass(cls):
        cfg = cls.get_cfg()
        slu_type = cfg['SLU']['type']
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        cls.slu = slu_type(preprocessing)

    @classmethod
    def get_cfg(cls):
        return {
            'SLU': {
                'debug': True,
                'type': PTIENHDCSLU,
                PTIENHDCSLU: {
                    'cldb_fname': as_project_path("applications/PublicTransportInfoEN/data/database.py"),
                    'preprocessing_cls': PTIENSLUPreprocessing,
                },
            },
        }
