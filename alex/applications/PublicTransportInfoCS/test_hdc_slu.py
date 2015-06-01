# encoding: utf8
from __future__ import unicode_literals
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

    def test_parse_meta(self):
        utterances_to_understand = [
            (u"ahoj", "hello()", ),
            (u"sbohem čau", "bye()", ),
            (u"jiné", "reqalts()", ),
            (u"začneme znovu", "restart()", ),
            (u"zopakuj", "repeat()", ),
            (u"promiň", "apology()", ),
            (u"co se zeptat", "help()", ),
            (u"haló", "canthearyou()", ),
            (u"nerozuměl jsem", "notunderstood()", ),
            (u"ano jo", "affirm()", ),
            (u"ne ano nechci", "negate()", ),
            (u"děkuji", "thankyou()", ),
            (u"dobře", "ack()", ),
            (u"chci jet", "inform(task=find_connection)", ),
            (u"jak bude", "inform(task=weather)", ),
            (u"nástupiště", "inform(task=find_platform)", ),
            (u"z jaké jede", "request(from_stop)", ),
            (u"kam to jede", "request(to_stop)", ),
            (u"kdy to jede", "request(departure_time)", ),
            (u"za jak dlouho", "request(departure_time_rel)", ),
            (u"kdy tam budem", "request(arrival_time)", ),
            (u"za jak dlouho tam přijedu", "request(arrival_time_rel)", ),
            (u"jak dlouho bude trvat cesta", "request(duration)", ),
            (u"kolik je hodin", "request(current_time)", ),
            (u"jak dlouho trvá přestup", "request(time_transfers)", ),
            (u"kolik přestupů", "request(num_transfers)", ),
            (u"nechci přestup bez jet přímo", "inform(num_transfers=0)", ),
            (u"jeden přestup", "inform(num_transfers=1)", ),
            (u"dva přestupy", "inform(num_transfers=2)", ),
            (u"tři přestupy", "inform(num_transfers=3)", ),
            (u"čtyři přestupy", "inform(num_transfers=4)", ),
            (u"libovolně přestupů", "inform(num_transfers=dontcare)", ),
            (u"jet přímo", "inform(num_transfers=0)", ),
            (u"alternativa libovolný", "inform(alternative=dontcare)", ),
            (u"alternativa první", "inform(alternative=1)", ),
            (u"alternativa druhá", "inform(alternative=2)", ),
            (u"alternativa třetí", "inform(alternative=3)", ),
            (u"alternativa čtvrtá", "inform(alternative=4)", ),
            (u"alternativa páté", "inform(alternative=5)", ),
            (u"předchozí spoj", "inform(alternative=prev)", ),
            (u"nechci předchozí spoj", "deny(alternative=prev)", ),
            (u"poslední spoj", "inform(alternative=last)", ),
            (u"nechci poslední spoj", "deny(alternative=last)", ),
            (u"další spoj", "inform(alternative=next)", ),
            (u"další", "inform(alternative=next)", ),
            (u"předchozí", "inform(alternative=prev)", ),
            (u"jako ve dne", "inform(ampm=pm)", ),
        ]

        for utt, res in utterances_to_understand:
            asr_hyp = UtteranceNBList()
            asr_hyp.add(0.79, Utterance(utt))

            cn = self.slu.parse(asr_hyp)

            self.assertIn(DialogueActItem(dai=res), cn)

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
