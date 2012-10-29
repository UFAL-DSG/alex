#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import __init__

from SDS.components.slu.da import DialogueAct, DialogueActNBList, merge_slu_nblists

class TestSLUDA(unittest.TestCase):
    def test_merge_slu_nblists_full_nbest_lists(self):
        # make sure the SDS.components.slu.da.merge_slu_nblists merges nblists correctly

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
        correct_merged_nblists.add(0.7*0.1, DialogueAct("null()"))
        correct_merged_nblists.add(0.3*0.6, DialogueAct("hello()"))
        correct_merged_nblists.add(0.3*0.3, DialogueAct("restart()"))
        correct_merged_nblists.add(0.3*0.1, DialogueAct("null()"))
        correct_merged_nblists.merge()
        correct_merged_nblists.normalise()
        correct_merged_nblists.sort()
                        
        print "Merged nblists:"
        print str(merged_nblists)
        print 
        print "Correct merged results:"
        print str(correct_merged_nblists)
        print
        
        self.assertEqual(str(merged_nblists), str(correct_merged_nblists))

if __name__ == '__main__':
    unittest.main()
