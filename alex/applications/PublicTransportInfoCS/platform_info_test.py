import autopath
import mox
import unittest
from nose.tools import ok_, eq_, istest, nottest

from alex.applications.PublicTransportInfoCS.directions import \
    CRWSDirectionsFinder
from alex.applications.thub import TextHub
from alex.components.asr.utterance import Utterance
from alex.components.dm.dddstate import DeterministicDiscriminativeDialogueState
from alex.components.slu.da import DialogueAct, DialogueActConfusionNetwork, \
    DialogueActItem
from alex.utils.config import Config, as_project_path
from alex.utils.mproc import SystemLogger
from alex.utils.sessionlogger import SessionLogger
from alex.components.dm.base import DialogueManager
from alex.applications.PublicTransportInfoCS.hdc_policy import PTICSHDCPolicy


def utter(dai_text):
    cn = DialogueActConfusionNetwork()
    cn.add(1.0, DialogueActItem(dai=dai_text))
    return cn


class TestPlatformInfo(unittest.TestCase):
    def test_prague_to_brno(self):
        m = mox.Mox()

        system_logger = SystemLogger("/tmp/xxx")


        session_logger = m.CreateMockAnything()
        session_logger.AnyMethod()

        cfg = Config("applications/PublicTransportInfoCS/private"
                          "/default.cfg", project_root=True)
        cfg.update(
            {
                'PublicTransportInfoCS': {
                    'max_turns': 120,
                },
                'DM': {
                    'basic': {
                        'debug': True,
                    },
                    'ontology': as_project_path('applications/PublicTransportInfoCS/data/ontology.py'),
                    'dialogue_state': {
                        'type': DeterministicDiscriminativeDialogueState,
                    },
                    'DeterministicDiscriminativeDialogueState': {
                        'type' : 'UFAL_DSTC_1.0_approx',
                    },
                    'dialogue_policy': {
                        'type': PTICSHDCPolicy,
                        'PTICSHDCPolicy': {
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
                    'directions': {
                        'type': CRWSDirectionsFinder,
                    }
                },
                'Logging': {
                    'system_logger': system_logger,
                    'session_logger': SessionLogger()
                },
                'CRWS': {
                    'max_connections_count': 1
                }
            })

        dm = DialogueManager(cfg)
        dm.new_dialogue()
        system_logger.debug(dm.da_out())
        dm.da_in(utter("inform(task=find_platform)"))
        system_logger.debug(dm.da_out())
        dm.da_in(utter("inform(from_city=Praha)"))
        system_logger.debug(dm.da_out())
        dm.da_in(utter("inform(train_name='Phoenix')"))
        system_logger.debug(dm.da_out())

        #dm.da_in(utter("inform(to_city=Olomouc)"))
        #system_logger.debug(dm.da_out())
        #dm.da_in(utter("inform(to_city=Cheb)"))
        #system_logger.debug(dm.da_out())
