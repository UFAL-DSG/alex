# encoding: utf8
from unittest import TestCase

from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU
from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.components.asr.utterance import Utterance, UtteranceNBList
from alex.components.slu.base import CategoryLabelDatabase
from alex.components.slu.da import DialogueAct, DialogueActItem
from alex.utils.config import as_project_path


class TestPTICSHDCSLU(TestCase):
    def test_parse_with_mutliple_date_rel(self):
        asr_hyp = UtteranceNBList()
        asr_hyp.add(0.1, Utterance("CHTEL BYCH ZITRA ZITRA JET"))

        cn = self.slu.parse(asr_hyp)

        self.assert_(DialogueActItem(dai="inform(date_rel=tomorrow)") in cn)

    @classmethod
    def setUpClass(cls):
        cfg = {
            'SLU': {
                'debug': True,
                'type': PTICSHDCSLU,
                PTICSHDCSLU: {
                    'preprocessing_cls': PTICSSLUPreprocessing
                },
            },
        }
        slu_type = cfg['SLU']['type']
        cldb = CategoryLabelDatabase()
        class db:
            database = {
                "task": {
                    "find_connection": ["najít spojení", "najít spoj", "zjistit spojení",
                                        "zjistit spoj", "hledám spojení", 'spojení', 'spoj',
                                       ],
                    "find_platform": ["najít nástupiště", "zjistit nástupiště", ],
                    'weather': ['pocasi', ],
                },
                "number": {
                    "1": ["jednu"]
                },
                "time": {
                    "now": ["nyní", "teď", "teďka", "hned", "nejbližší", "v tuto chvíli", "co nejdřív"],
                    "18": ["osmnáct", "osmnact"]
                },
                "date_rel": {
                    "tomorrow": ["zítra", "zitra"],
                }
            }

        cldb.load(db_mod=db)
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        cls.slu = slu_type(preprocessing, cfg)
