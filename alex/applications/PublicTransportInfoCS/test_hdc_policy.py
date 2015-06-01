# encoding: utf8

from unittest import TestCase

import alex.applications.PublicTransportInfoCS.hdc_policy as hdc_policy
from alex.utils.config import Config, as_project_path

import alex.applications.PublicTransportInfoCS.directions as directions
import alex.utils
from alex.components.dm.dddstate import DeterministicDiscriminativeDialogueState
from alex.components.slu.da import DialogueActConfusionNetwork, DialogueActItem
from alex.components.dm.ontology import Ontology

import mox

class TestPTICSHDCPolicy(TestCase):

    def setUp(self):
        super(TestPTICSHDCPolicy, self).setUp()

        self.cfg = self._get_cfg()
        self.ontology = Ontology(self.cfg['DM']['ontology'])
        self.mox = mox.Mox()

    def _get_cfg(self):
        cfg = Config(config={
            'PublicTransportInfoCS': {
                'max_turns': 120,
            },
            'DM': {
                'directions': {
                    'type': directions.GoogleDirectionsFinder,

                },
                'dialogue_policy': {
                    'PTICSHDCPolicy': {
                        'accept_prob': 0.5,
                        'accept_prob_being_requested': 0.5,
                        'accept_prob_being_confirmed': 0.5,
                        'accept_prob_ludait': 0.5,
                        'accept_prob_noninformed': 0.5,
                        'confirm_prob': 0.5,
                        'select_prob': 0.5,
                        'min_change_prob': 0.5
                    }
                },
                'dialogue_state': {
                    'type': DeterministicDiscriminativeDialogueState,
                 },
                'DeterministicDiscriminativeDialogueState': {
                    'type': 'UFAL_DSTC_1.0_approx',
                },
                'ontology': as_project_path('applications/PublicTransportInfoCS/data/ontology.py'),
            },
            'Logging': {
                'system_logger': alex.utils.DummyLogger(),
                'session_logger': alex.utils.DummyLogger()
            },
            'weather': {
                'dictionary': as_project_path('applications/PublicTransportInfoCS/weather_cs.cfg'),
                'suffix': 'CZ',
                'units': 'celsius',
            }
        })
        return cfg

    def _build_policy(self):
        return hdc_policy.PTICSHDCPolicy(self.cfg, self.ontology)

    def test_get_platform_res_da(self):
        hdc_policy = self._build_policy()

        state = DeterministicDiscriminativeDialogueState(self.cfg, self.ontology)

        system_input = DialogueActConfusionNetwork()

        res = hdc_policy.get_da(state)

        user_input = DialogueActConfusionNetwork()
        user_input.add(1.0, DialogueActItem(dai='info(task=find_platform)'))
        user_input.add(1.0, DialogueActItem(dai='inform(from_stop=Praha)'))
        user_input.add(1.0, DialogueActItem(dai='inform(to_stop=Brno)'))

        state.update(user_input, system_input)
        res = hdc_policy.get_da(state)

        self.assert_('inform(not_supported)' in res)

    def test_switching_tasks(self):
        hdc_policy = self._build_policy()
        self.mox.StubOutWithMock(hdc_policy.weather, 'get_weather')
        self.mox.StubOutWithMock(hdc_policy, 'get_directions')

        hdc_policy.weather.get_weather(city=u'Praha',
                                       daily=False,
                                       lat=u'50.0755381',
                                       lon=u'14.4378005',
                                       time=None).AndReturn(None)
        hdc_policy.get_directions(mox.IgnoreArg(),
                                  check_conflict=True).AndReturn([DialogueActItem(dai="inform(time=10:00)")])

        self.mox.ReplayAll()

        state = DeterministicDiscriminativeDialogueState(self.cfg, self.ontology)

        system_input = DialogueActConfusionNetwork()

        res = hdc_policy.get_da(state)

        # User says she wants weather so the task should be weather.
        user_input = self._build_user_input("inform(task=weather)")
        state.update(user_input, system_input)
        res = hdc_policy.get_da(state)
        self.assertEqual(state['lta_task'].mpv(), 'weather')

        # User wants to find a connection so the task should be find_connection.
        user_input = self._build_user_input(u"inform(task=find_connection)",
                                            u"inform(to_stop=Malostranská)",
                                            u"inform(from_stop=Anděl)")
        state.update(user_input, system_input)
        res = hdc_policy.get_da(state)
        self.assertEqual(state['lta_task'].mpv(), 'find_connection')

        self.mox.VerifyAll()


    def _build_user_input(self, *args):
        user_input = DialogueActConfusionNetwork()
        for arg in args:
            user_input.add(1.0, DialogueActItem(dai=arg))

        return user_input
