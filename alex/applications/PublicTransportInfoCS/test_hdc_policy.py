from unittest import TestCase

import alex.applications.PublicTransportInfoCS.hdc_policy as hdc_policy
from alex.utils.config import Config, as_project_path

import alex.applications.PublicTransportInfoCS.directions as directions
import alex.utils
from alex.components.dm.dddstate import DeterministicDiscriminativeDialogueState
from alex.components.slu.da import DialogueActConfusionNetwork, DialogueActItem
from alex.components.dm.ontology import Ontology

class TestPTICSHDCPolicy(TestCase):

    def setUp(self):
        super(TestPTICSHDCPolicy, self).setUp()

        self.cfg = self._get_cfg()
        self.ontology = Ontology(self.cfg['DM']['ontology'])

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
