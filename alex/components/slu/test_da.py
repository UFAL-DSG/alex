#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
import unittest

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, \
    DialogueActConfusionNetwork, merge_slu_nblists, merge_slu_confnets

class TestDA(unittest.TestCase):
    def test_swapping_merge_normalise(self):
        nblist1 = DialogueActNBList()
        nblist1.add(0.7, DialogueAct("hello()"))
        nblist1.add(0.2, DialogueAct("bye()"))
        nblist2 = deepcopy(nblist1)

        nblist1.merge().normalise()
        nblist2.normalise().merge()

        s = []
        s.append("")
        s.append("Using merge().normalise():")
        s.append(unicode(nblist1))
        s.append("")
        s.append("Using normalise().merge():")
        s.append(unicode(nblist2))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(nblist1, nblist2)

    def test_merge_slu_nblists_full_nbest_lists(self):
        # make sure the alex.components.slu.da.merge_slu_nblists merges nblists correctly

        nblist1 = DialogueActNBList()
        nblist1.add(0.7, DialogueAct("hello()"))
        nblist1.add(0.2, DialogueAct("bye()"))
        nblist1.merge().normalise()
        # nblist1.normalise()

        nblist2 = DialogueActNBList()
        nblist2.add(0.6, DialogueAct("hello()"))
        nblist2.add(0.3, DialogueAct("restart()"))
        nblist2.merge().normalise()
        # nblist2.normalise()

        nblists = [[0.7, nblist1], [0.3, nblist2]]

        merged_nblists = merge_slu_nblists(nblists)

        correct_merged_nblists = DialogueActNBList()
        correct_merged_nblists.add(0.7*0.7, DialogueAct("hello()"))
        correct_merged_nblists.add(0.7*0.2, DialogueAct("bye()"))
        correct_merged_nblists.add(0.7*0.1, DialogueAct("other()"))
        correct_merged_nblists.add(0.3*0.6, DialogueAct("hello()"))
        correct_merged_nblists.add(0.3*0.3, DialogueAct("restart()"))
        correct_merged_nblists.add(0.3*0.1, DialogueAct("other()"))
        correct_merged_nblists.merge().normalise()
        # correct_merged_nblists.normalise()

        s = []
        s.append("")
        s.append("Merged nblists:")
        s.append(unicode(merged_nblists))
        s.append("")
        s.append("Correct merged results:")
        s.append(unicode(correct_merged_nblists))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(unicode(merged_nblists), unicode(correct_merged_nblists))

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
        correct_merged_confnet.add_merge(0.7*0.7, DialogueActItem('hello'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.7*0.2, DialogueActItem('bye'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.3*0.6, DialogueActItem('hello'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.3*0.3, DialogueActItem('restart'),
                                         combine='add')

        s = []
        s.append("")
        s.append("Merged confnets:")
        s.append(unicode(merged_confnets))
        s.append("")
        s.append("Correct merged results:")
        s.append(unicode(correct_merged_confnet))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(unicode(merged_confnets), unicode(correct_merged_confnet))

if __name__ == '__main__':
    unittest.main()
