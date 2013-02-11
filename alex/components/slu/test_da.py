#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, \
    DialogueActConfusionNetwork, merge_slu_nblists, merge_slu_confnets

class TestDA(unittest.TestCase):
    def test_merge_slu_nblists_full_nbest_lists(self):
        # make sure the alex.components.slu.da.merge_slu_nblists merges nblists correctly

        nblist1 = DialogueActNBList()
        nblist1.add(0.7, DialogueAct("hello()"))
        nblist1.add(0.2, DialogueAct("bye()"))
        nblist1.merge()
        nblist1.normalise()
        nblist1.sort()

        nblist2 = DialogueActNBList()
        nblist2.add(0.6, DialogueAct("hello()"))
        nblist2.add(0.3, DialogueAct("restart()"))
        nblist2.merge()
        nblist2.normalise()
        nblist2.sort()

        nblists = [[0.7, nblist1], [0.3, nblist2]]

        merged_nblists = merge_slu_nblists(nblists)

        correct_merged_nblists = DialogueActNBList()
        correct_merged_nblists.add(0.7*0.7, DialogueAct("hello()"))
        correct_merged_nblists.add(0.7*0.2, DialogueAct("bye()"))
        correct_merged_nblists.add(0.7*0.1, DialogueAct("other()"))
        correct_merged_nblists.add(0.3*0.6, DialogueAct("hello()"))
        correct_merged_nblists.add(0.3*0.3, DialogueAct("restart()"))
        correct_merged_nblists.add(0.3*0.1, DialogueAct("other()"))
        correct_merged_nblists.merge()
        correct_merged_nblists.normalise()
        correct_merged_nblists.sort()

        s = []
        s.append("")
        s.append("Merged nblists:")
        s.append(str(merged_nblists))
        s.append("")
        s.append("Correct merged results:")
        s.append(str(correct_merged_nblists))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(str(merged_nblists), str(correct_merged_nblists))

    def test_merge_slu_confnets(self):
        confnet1 = DialogueActConfusionNetwork()
        confnet1.add(0.7, DialogueActItem('hello'))
        confnet1.add(0.2, DialogueActItem('bye'))

        confnet2 = DialogueActConfusionNetwork()
        confnet2.add(0.6, DialogueActItem('hello'))
        confnet2.add(0.3, DialogueActItem('restart'))

        confnets = [[0.7, confnet1], [0.3, confnet2]]

        merged_confnets = merge_slu_confnets(confnets)

        correct_merged_confnet = DialogueActConfusionNetwork()
        correct_merged_confnet.add_merge(0.7*0.7, DialogueActItem('hello'))
        correct_merged_confnet.add_merge(0.7*0.2, DialogueActItem('bye'))
        correct_merged_confnet.add_merge(0.3*0.6, DialogueActItem('hello'))
        correct_merged_confnet.add_merge(0.3*0.3, DialogueActItem('restart'))

        s = []
        s.append("")
        s.append("Merged confnets:")
        s.append(str(merged_confnets))
        s.append("")
        s.append("Correct merged results:")
        s.append(str(correct_merged_confnet))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(str(merged_confnets), str(correct_merged_confnet))

if __name__ == '__main__':
    unittest.main()
