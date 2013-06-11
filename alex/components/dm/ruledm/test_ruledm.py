import unittest

if __name__ == "__main__":
    import autopath
from alex.components.dm.ruledm.ruledm import RuleDM, DRuleDS
from alex.components.dm.ruledm.druledmpolicy import DRuleDMPolicy
from alex.components.slu.da import DialogueAct
#from alex.components.dm.ruledm.pruledm import PRuleDMPolicy, PRuleDM
from alex.utils.caminfodb import CamInfoDb
from alex.utils import script_path, DummyLogger


# disable unittest
def disabled(f):
    def _decorator():
        print f.__name__ + ' has been disabled'
    return _decorator


class TestRuleDS(unittest.TestCase):
    def get_dummy_ds(self):
        ds = DRuleDS(['slot1', 'slot2', 'slot3', 'slot4'])
        ds.update_user({'slot2': 2, 'slot3': 3, 'slot4': [1, 2, 3]})
        return ds

    def test_update_clear(self):
        ds = DRuleDS(['slot1', 'slot2', 'slot3', 'slot4'])
        ds.update_user({})
        ds.update_user({'slot1': 1})
        self.assertEqual(ds['slot1'], 1)

        ds.update_user({'slot2': 2, 'slot3': 3, 'slot4': [1, 2, 3]})
        for x in range(1, 4):
            self.assertEqual(ds['slot%d' % x], x)
        self.assertEqual(ds['slot4'], [1, 2, 3])

        ds.update_user({'slot4': [4, 5]})
        self.assertEqual(ds['slot4'], [1, 2, 3, 4, 5])

    def test_clear(self):
        ds = self.get_dummy_ds()
        ds.clear()
        for x in range(1, 5):
            self.assertEqual(ds['slot%d' % x], None)

    def test_reset_changes(self):
        ds = self.get_dummy_ds()
        self.assertNotEqual(ds.changed_slots, [])
        ds.new_turn()
        self.assertEqual(ds.changed_slots, [])

    def test_the_rest(self):
        ds = self.get_dummy_ds()
        self.assertEqual(ds.get('nonexistent', 9), 9)



class TestRuleDM(unittest.TestCase):
    def test_dialog(self):
        ontology_file = script_path(__file__, 'test_ruledm_data', 'ontology.cfg')
        db_file = script_path(__file__, 'test_ruledm_data', 'data.txt')

        class TRuleDMPolicy(DRuleDMPolicy):
            db_cls = CamInfoDb

        class TRuleDM(RuleDM):
            policy_cls = TRuleDMPolicy

        dm = TRuleDM(
            {'DM' :
             {'TRuleDM' :
              {
                  'ontology': ontology_file,
                  'db_cfg': db_file,
                  'provide_code': False,
                  'code_submit_url': None
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
        self.assertEquals(turn_2.has_dat("notunderstood"), True)

        dm.da_in([(1.0, DialogueAct("inform(price=cheap)"))])
        turn_3 = dm.da_out()
        self.assertEquals(turn_3.has_dat("nomatch"), True)

        dm.da_in([(1.0, DialogueAct("bye()"))])
        turn_bye = dm.da_out()
        self.assertEquals(turn_bye.has_dat("bye"), True)

"""
class TestPRuleDM(unittest.TestCase):
    def test_dialog(self):
        ontology_file = script_path(__file__, 'test_ruledm_data', 'ontology.cfg')
        db_file = script_path(__file__, 'test_ruledm_data', 'data.txt')

        class TRuleDMPolicy(PRuleDMPolicy):
            db_cls = CamInfoDb

        class TRuleDM(PRuleDM):
            policy_cls = TRuleDMPolicy

        dm = TRuleDM(
            {'DM' :
             {'TRuleDM' :
              {
                  'ontology': ontology_file,
                  'db_cfg': db_file,
                  'provide_code': False,
                  'code_submit_url': None
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
        self.assertEquals(turn_2.has_dat("notunderstood"), True)

        dm.da_in([(1.0, DialogueAct("inform(price=cheap)"))])
        turn_3 = dm.da_out()
        self.assertEquals(turn_3.has_dat("nomatch"), True)

        dm.da_in([(1.0, DialogueAct("bye()"))])
        turn_bye = dm.da_out()
        self.assertEquals(turn_bye.has_dat("bye"), True)

    def runTest( self ): # NOTE: required name
        self.failUnless( True is True )

"""

if __name__ == '__main__':
    unittest.main()
    #t = TestPRuleDM()
    #t.test_dialog()
