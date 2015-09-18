import unittest

from platform_info import CRWSPlatformInfo


class PlatformInfoTest(unittest.TestCase):
    def test_matching(self):
        x = CRWSPlatformInfo(None, None)
        self.assertTrue(x._matches('hr.kr.', 'hradec kralove'))
        self.assertTrue(x._matches('hr.kralove', 'hradec kralove'))
        self.assertTrue(x._matches('hr.kralove', 'hradec kr.'))
        self.assertTrue(x._matches('brno hl.n.', 'brno hlavni nadrazi'))
        self.assertFalse(x._matches('mostek', 'most'))
