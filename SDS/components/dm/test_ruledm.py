import unittest

if __name__ == "__main__":
    import autopath
from SDS.components.dm.ruledm import RuleDM, RuleDMPolicy, RuleDialogueState, CHANGES_SLOT, SLOT_REQ, SLOT_CONFIRM
from SDS.components.slu.da import DialogueAct
from SDS.utils.caminfodb import CamInfoDb
from SDS.utils import script_path, DummyLogger


class TestRuleDialogueState(unittest.TestCase):
    def get_dummy_ds(self):
        ds = RuleDialogueState(['slot1', 'slot2', 'slot3', 'slot4'])
        ds.update({'slot2': 2, 'slot3': 3, 'slot4': [1, 2, 3]})
        return ds

    def test_update_clear(self):
        ds = RuleDialogueState(['slot1', 'slot2', 'slot3', 'slot4'])
        ds.update({})
        ds.update({'slot1': 1})
        self.assertEqual(ds['slot1'], 1)

        ds.update({'slot2': 2, 'slot3': 3, 'slot4': [1, 2, 3]})
        for x in range(1, 4):
            self.assertEqual(ds['slot%d' % x], x)
        self.assertEqual(ds['slot4'], [1, 2, 3])

        ds.update({'slot4': [4, 5]})
        self.assertEqual(ds['slot4'], [1, 2, 3, 4, 5])

    def test_clear(self):
        ds = self.get_dummy_ds()
        ds.clear()
        for x in range(1, 5):
            self.assertEqual(ds['slot%d' % x], None)

    def test_reset_changes(self):
        ds = self.get_dummy_ds()
        self.assertNotEqual(ds[CHANGES_SLOT], [])
        ds.reset_changes()
        self.assertEqual(ds[CHANGES_SLOT], [])

    def test_copy(self):
        ds1 = RuleDialogueState(['slot1', 'slot2', 'slot3'])
        ds1.update({'slot1': 1, 'slot3': 9})

        ds2 = RuleDialogueState(['slot1', 'slot2', 'slot3'])
        ds2.update({'slot1': 2, 'slot2': 3})

        ds1.copy(ds2)
        self.assertEqual(ds1['slot1'], 2)
        self.assertEqual(ds1['slot2'], 3)
        self.assertNotEqual(ds1['slot3'], 9)

    def test_the_rest(self):
        ds = self.get_dummy_ds()
        self.assertNotEqual(RuleDialogueState.get_ch_name("test"), None)
        self.assertNotEqual(RuleDialogueState.get_rh_name("test"), None)
        self.assertEqual(ds.get('nonexistent', 9), 9)

        self.assertEqual(len(ds.keys(SLOT_CONFIRM)), 4)

        self.assertEqual(ds.reqkey_to_key(SLOT_REQ + "_test"), "test")
        self.assertEqual(ds.chkey_to_key(SLOT_CONFIRM + "_test"), "test")


class TestRuleDM(unittest.TestCase):
    def test_dialog(self):
        ontology_file = script_path(__file__, 'test_ruledm_data', 'ontology.cfg')
        db_file = script_path(__file__, 'test_ruledm_data', 'data.txt')

        class TRuleDMPolicy(RuleDMPolicy):
            db_cls = CamInfoDb

        class TRuleDM(RuleDM):
            policy_cls = TRuleDMPolicy

        dm = TRuleDM(
            {'DM' :
             {'TRuleDM' :
              {
                  'ontology': ontology_file,
                  'db_cfg': db_file,
               }
              }
             ,
            'Logging':
            {
                'system_logger': DummyLogger()
            }
            }
            )
        turn_init = dm.da_out()
        self.assertEquals(turn_init.has_dat("hello"), True)
        turn_init = dm.da_out()
        self.assertEquals(turn_init.has_dat("hello"), True)

        dm.da_in([(1.0, DialogueAct("inform(food=chinese)"))])
        turn_1 = dm.da_out()
        self.assertEquals(turn_1.has_dat("inform"), True)

        dm.da_in([(1.0, DialogueAct("asdf(fdsa=asdf)"))])
        turn_2 = dm.da_out()
        self.assertEquals(turn_2.has_dat("noentiendo"), True)

        dm.da_in([(1.0, DialogueAct("inform(price=cheap)"))])
        turn_3 = dm.da_out()
        self.assertEquals(turn_3.has_dat("nomatch"), True)

        dm.da_in([(1.0, DialogueAct("bye()"))])
        turn_bye = dm.da_out()
        self.assertEquals(turn_bye.has_dat("bye"), True)






if __name__ == '__main__':
    unittest.main()