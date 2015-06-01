#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
import unittest
from unittest import TestCase
import math

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, \
    DialogueActConfusionNetwork, DialogueActConfusionNetworkException, merge_slu_nblists, merge_slu_confnets
from alex.ml.hypothesis import ConfusionNetworkException


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
        correct_merged_nblists.add(0.7 * 0.7, DialogueAct("hello()"))
        correct_merged_nblists.add(0.7 * 0.2, DialogueAct("bye()"))
        correct_merged_nblists.add(0.7 * 0.1, DialogueAct("other()"))
        correct_merged_nblists.add(0.3 * 0.6, DialogueAct("hello()"))
        correct_merged_nblists.add(0.3 * 0.3, DialogueAct("restart()"))
        correct_merged_nblists.add(0.3 * 0.1, DialogueAct("other()"))
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
        correct_merged_confnet.add_merge(0.7 * 0.7, DialogueActItem('hello'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.7 * 0.2, DialogueActItem('bye'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.3 * 0.6, DialogueActItem('hello'),
                                         combine='add')
        correct_merged_confnet.add_merge(0.3 * 0.3, DialogueActItem('restart'),
                                         combine='add')

        s = []
        s.append("")
        s.append("Merged confnets:")
        s.append(unicode(merged_confnets))
        s.append("")
        s.append("Correct merged results:")
        s.append(unicode(correct_merged_confnet))
        s.append("")

        self.assertEqual(unicode(merged_confnets), unicode(correct_merged_confnet))


class TestDialogueActConfusionNetwork(TestCase):
    def test_add_merge(self):
        dai = DialogueActItem(dai='inform(food=chinese)')
        dacn = DialogueActConfusionNetwork()
        dacn.add_merge(0.5, dai, combine='add')
        self.assertEqual(dacn._get_prob([0]), 0.5)

        dacn.add_merge(0.5, dai, combine='add')
        self.assertEqual(dacn._get_prob([0]), 1.0)

    def test_get_best_da(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.2, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.1, DialogueActItem(dai='inform(food=russian)'))

        da = dacn.get_best_da()
        self.assertEqual(len(da), 1)
        self.assertEqual(da.dais[0], DialogueActItem(dai='inform(food=czech)'))

        dacn = DialogueActConfusionNetwork()
        dacn.add(0.2, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.3, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=null)'))
        dacn.add(0.1, DialogueActItem(dai='inform(food=russian)'))

        da = dacn.get_best_nonnull_da()
        self.assertEqual(len(da), 1)
        self.assertEqual(da.dais[0], DialogueActItem(dai='inform(food=null)'))

    def test_get_best_nonnull_da(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.2, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.1, DialogueActItem(dai='inform(food=russian)'))

        da_nn = dacn.get_best_nonnull_da()
        self.assertEqual(len(da_nn), 1)
        self.assertEqual(da_nn.dais[0], DialogueActItem(dai='inform(food=czech)'))

        dacn = DialogueActConfusionNetwork()
        dacn.add(0.075, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='null()'))
        dacn.add(0.15, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.075, DialogueActItem(dai='inform(food=russian)'))

        da_nn = dacn.get_best_nonnull_da()
        self.assertEqual(len(da_nn), 1)

        self.assertEqual(da_nn.dais[0], DialogueActItem(dai='inform(food=czech)'))

    def test_get_best_da_hyp(self):
        # Test case when only one dai should be included in the hyp.
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.2, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.1, DialogueActItem(dai='inform(food=russian)'))

        best_hyp = dacn.get_best_da_hyp(use_log=False)
        self.assertAlmostEqual(best_hyp.prob, 0.8 * 0.7 * 0.9)
        self.assertEqual(len(best_hyp.da), 1)

        # Test case when 2 dais should be included in the hyp.
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.1, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=russian)'))

        best_hyp = dacn.get_best_da_hyp(use_log=False)
        self.assertAlmostEqual(best_hyp.prob, 0.9 * 0.7 * 0.9)
        self.assertEqual(len(best_hyp.da), 2)

        # Test the case with logarithms.
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.1, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=russian)'))

        best_hyp = dacn.get_best_da_hyp(use_log=True)
        self.assertAlmostEqual(best_hyp.prob, math.log(0.9 * 0.7 * 0.9))
        self.assertEqual(len(best_hyp.da), 2)

        # Test the case with manual thresholds.
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.1, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=russian)'))

        best_hyp = dacn.get_best_da_hyp(
            use_log=True, threshold=0.1, thresholds={
                DialogueActItem(dai='inform(food=chinese)'): 0.5,
                DialogueActItem(dai='inform(food=czech)'): 0.9,
                DialogueActItem(dai='inform(food=russian)'): 0.5
            })
        # Test food=czech should NOT be included.
        self.assertAlmostEqual(best_hyp.prob, math.log(0.9 * 0.3 * 0.9))
        self.assertEqual(len(best_hyp.da), 1)
        self.assertTrue(not DialogueActItem(dai='inform(food=czech)') in best_hyp.da)

        dacn = DialogueActConfusionNetwork()
        dacn.add(0.1, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=russian)'))

        best_hyp = dacn.get_best_da_hyp(
            use_log=True, threshold=0.1, thresholds={
                DialogueActItem(dai='inform(food=chinese)'): 0.5,
                DialogueActItem(dai='inform(food=czech)'): 0.5,
                DialogueActItem(dai='inform(food=russian)'): 0.5
            })
        # Test food=czech should be included.
        self.assertAlmostEqual(best_hyp.prob, math.log(0.9 * 0.7 * 0.9))
        self.assertEqual(len(best_hyp.da), 2)
        self.assertTrue(DialogueActItem(dai='inform(food=czech)') in best_hyp.da)

    def test_get_prob(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.2, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.7, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.1, DialogueActItem(dai='inform(food=russian)'))

        self.assertAlmostEqual(dacn._get_prob([0, 1, 1]), 0.2 * 0.3 * 0.9)
        self.assertAlmostEqual(dacn._get_prob([0, 0, 0]), 0.2 * 0.7 * 0.1)

    def test_get_da_nblist(self):
        # Simple case with one good hypothesis.
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.05, DialogueActItem(dai='inform(food=russian)'))

        nblist = dacn.get_da_nblist()
        best_da = nblist.get_best_da()
        expected_da = DialogueAct(da_str='inform(food=czech)')
        self.assertEqual(best_da, expected_da)

        # More good hypotheses
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=russian)'))

        nblist = dacn.get_da_nblist()
        best_da = nblist.get_best_da()
        expected_da = DialogueAct(da_str='inform(food=czech)&inform(food=russian)')
        self.assertEqual(best_da, expected_da)

    def test_prune(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.00005, DialogueActItem(dai='inform(food=russian)'))

        # Russian food should be pruned.
        self.assertEqual(len(dacn), 3)
        dacn.prune()
        self.assertEqual(len(dacn), 2)
        self.assertTrue(not DialogueActItem(dai='inform(food=russian)') in dacn)

    def test_normalise(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(1.9, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.00005, DialogueActItem(dai='inform(food=russian)'))
        self.assertRaises(ConfusionNetworkException, dacn.normalise)

    def test_sort(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(1.0, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.00005, DialogueActItem(dai='inform(food=russian)'))

        dacn.sort()

        cn = list(dacn)
        self.assertEqual(cn[0][1], DialogueActItem(dai='inform(food=czech)'))
        self.assertEqual(cn[1][1], DialogueActItem(dai='inform(food=chinese)'))
        self.assertEqual(cn[2][1], DialogueActItem(dai='inform(food=russian)'))

    def test_make_from_da(self):
        da = DialogueAct('inform(food=czech)&inform(area=north)')
        dacn = DialogueActConfusionNetwork.make_from_da(da)
        self.assertEqual(dacn.get_best_da(), da)

    def test_merge(self):
        dacn = DialogueActConfusionNetwork()
        dacn.add(0.05, DialogueActItem(dai='inform(food=chinese)'))
        dacn.add(0.9, DialogueActItem(dai='inform(food=czech)'))
        dacn.add(0.00005, DialogueActItem(dai='inform(food=russian)'))

        dacn.merge(dacn, combine='max')

        # Russian food should be pruned.
        dacn.sort().prune()
        self.assertTrue(not DialogueActItem(dai='inform(food=russian)') in dacn)


if __name__ == '__main__':
    unittest.main()
