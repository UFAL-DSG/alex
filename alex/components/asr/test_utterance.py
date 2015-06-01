#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

import __init__

if __name__ == "__main__":
    import autopath
from alex.components.asr.utterance import SENTENCE_START, SENTENCE_END, \
    Utterance, UtteranceNBList, UtteranceConfusionNetwork, \
    UtteranceConfusionNetworkFeatures


class TestUtterance(unittest.TestCase):
    """Tests correct working of the Utterance class."""

    def setUp(self):
        self.barbara = Utterance('b a r b a r a')
        self.ararat = Utterance('a r a r a t')

    def test_index(self):
        test_pairs = ((['b', 'a', 'r'], 0),
                      (['b', 'a', 'r', 'a'], 3),
                      (['a', 'r', 'a'], 4))
        for phrase, idx in test_pairs:
            self.assertEqual(self.barbara.index(phrase), idx)
        self.assertRaises(ValueError, self.barbara.index, ['r', 'a', 'b'])
        self.assertEqual(self.ararat.index(['a', 'r', 'a', 't']), 2)

    def test_ngram_iterator(self):
        # Normal use case.
        trigrams = [['b', 'a', 'r'],
                    ['a', 'r', 'b'],
                    ['r', 'b', 'a'],
                    ['b', 'a', 'r'],
                    ['a', 'r', 'a'],
                   ]
        trigrams_with_boundaries = [
                    [SENTENCE_START, 'b', 'a'],
                    ['b', 'a', 'r'],
                    ['a', 'r', 'b'],
                    ['r', 'b', 'a'],
                    ['b', 'a', 'r'],
                    ['a', 'r', 'a'],
                    ['r', 'a', SENTENCE_END],
                   ]
        act_trigrams = list(self.barbara.iter_ngrams(3))
        act_trigrams_with_boundaries = list(
            self.barbara.iter_ngrams(3, with_boundaries=True))
        self.assertItemsEqual(trigrams, act_trigrams)
        self.assertItemsEqual(trigrams_with_boundaries,
                         act_trigrams_with_boundaries)
        # Corner cases.
        self.assertItemsEqual(list(self.barbara.iter_ngrams(7)),
                              [['b', 'a', 'r', 'b', 'a', 'r', 'a']])
        self.assertItemsEqual(list(self.barbara.iter_ngrams(8)), [])
        self.assertItemsEqual(
            list(self.barbara.iter_ngrams(8, with_boundaries=True)),
            [[SENTENCE_START, 'b', 'a', 'r', 'b', 'a', 'r', 'a'],
             ['b', 'a', 'r', 'b', 'a', 'r', 'a', SENTENCE_END]])
        self.assertItemsEqual(
            list(self.barbara.iter_ngrams(9, with_boundaries=True)),
            [[SENTENCE_START, 'b', 'a', 'r', 'b', 'a', 'r', 'a',
              SENTENCE_END]])
        self.assertItemsEqual(
            list(self.barbara.iter_ngrams(10, with_boundaries=True)),
            [])


class TestUtteranceConfusionNetwork(unittest.TestCase):
    """Tests correct working of the UtteranceConfusionNetwork class.

    Test using
            $ python -m unittest test_utterance
    """

    def test_conversion_of_confnet_into_nblist(self):

        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.50, 0.35, 0.15
        C1, C2, C3 = 0.60, 0.30, 0.10

        correct_nblist = UtteranceNBList()
        correct_nblist.add(A1*B1*C1, Utterance("A1 B1 C1"))
        correct_nblist.add(A1*B2*C1, Utterance("A1 B2 C1"))
        correct_nblist.add(A1*B1*C2, Utterance("A1 B1 C2"))
        correct_nblist.add(A1*B2*C2, Utterance("A1 B2 C2"))
        correct_nblist.add(A1*B3*C1, Utterance("A1 B3 C1"))
        correct_nblist.add(A1*B1*C3, Utterance("A1 B1 C3"))
        correct_nblist.add(A1*B3*C2, Utterance("A1 B3 C2"))
        correct_nblist.add(A1*B2*C3, Utterance("A1 B2 C3"))
        correct_nblist.merge()
        correct_nblist.add_other()

        confnet = UtteranceConfusionNetwork()
        confnet.add([[A1, 'A1'], [A2, 'A2'], [A3, 'A3'],])
        confnet.add([[B1, 'B1'], [B2, 'B2'], [B3, 'B3'],])
        confnet.add([[C1, 'C1'], [C2, 'C2'], [C3, 'C3'],])
        confnet.merge().sort()

        gen_nblist = confnet.get_utterance_nblist(10)

        s = []
        s.append("")
        s.append("Confusion network:")
        s.append(unicode(confnet))
        s.append("")
        s.append("Generated nblist:")
        s.append(unicode(gen_nblist))
        s.append("")
        s.append("Correct nblist:")
        s.append(unicode(correct_nblist))
        s.append("")

        self.assertEqual(unicode(gen_nblist), unicode(correct_nblist))

    def test_repr_basic(self):
        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.50, 0.35, 0.15
        C1, C2, C3 = 0.60, 0.30, 0.10

        confnet = UtteranceConfusionNetwork()
        confnet.add([[A1, 'A ("1\\")'], [A2, 'A2'], [A3, 'A3'],])
        confnet.add([[B1, 'B1'], [B2, 'B2'], [B3, 'B3'],])
        confnet.add([[C1, 'C1'], [C2, 'C2'], [C3, 'C3'],])

        rep = repr(confnet)
        self.assertEqual(repr(eval(rep)), rep)

    def test_repr_w_long_links(self):
        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.70, 0.20, 0.10
        C1, C2, C3 = 0.80, 0.10, 0.10

        asr_confnet = UtteranceConfusionNetwork()
        asr_confnet.add([[A1, "want"], [A2, "has"], [A3, 'ehm']])
        asr_confnet.add([[B1, "Chinese"],  [B2, "English"], [B3, 'cheap']])
        asr_confnet.add([[C1, "restaurant"],  [C2, "pub"],   [C3, 'hotel']])
        asr_confnet.merge().sort()

        confnet = asr_confnet.replace(("has", ), ("is", ))
        rep = repr(confnet)
        self.assertEqual(repr(eval(rep)), rep)

        confnet = asr_confnet.replace(("has", ), tuple())
        rep = repr(confnet)
        self.assertEqual(repr(eval(rep)), rep)

        confnet = asr_confnet.replace(("has", ), ("should", "have", ))
        rep = repr(confnet)
        self.assertEqual(repr(eval(rep)), rep)

        confnet.add([(0.5, 'want'), (0.5, 'pub')])
        rep = repr(confnet)
        self.assertEqual(repr(eval(rep)), rep)

    def test_ngram_iterator(self):
        tolerance = 0.01

        # Create a simple confusion network.
        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.70, 0.20, 0.10
        C1, C2, C3 = 0.80, 0.10, 0.10

        asr_confnet = UtteranceConfusionNetwork()
        asr_confnet.add([[A1, "want"], [A2, "has"], [A3, 'ehm']])
        asr_confnet.add([[B1, "Chinese"],  [B2, "English"], [B3, 'cheap']])
        asr_confnet.add([[C1, "restaurant"],  [C2, "pub"],   [C3, 'hotel']])
        asr_confnet.merge().sort()
        # Normal use case.
        trigram_hyps = [
            (0.504, ['want', 'Chinese', 'restaurant']),
            (0.063, ['want', 'Chinese', 'pub']),
            (0.063, ['want', 'Chinese', 'hotel']),
            (0.14400000000000004, ['want', 'English', 'restaurant']),
            (0.018000000000000006, ['want', 'English', 'pub']),
            (0.018000000000000006, ['want', 'English', 'hotel']),
            (0.07200000000000002, ['want', 'cheap', 'restaurant']),
            (0.009000000000000003, ['want', 'cheap', 'pub']),
            (0.009000000000000003, ['want', 'cheap', 'hotel']),
            (0.027999999999999997, ['has', 'Chinese', 'restaurant']),
            (0.0034999999999999996, ['has', 'Chinese', 'pub']),
            (0.0034999999999999996, ['has', 'Chinese', 'hotel']),
            (0.008000000000000002, ['has', 'English', 'restaurant']),
            (0.0010000000000000002, ['has', 'English', 'pub']),
            (0.0010000000000000002, ['has', 'English', 'hotel']),
            (0.004000000000000001, ['has', 'cheap', 'restaurant']),
            (0.0005000000000000001, ['has', 'cheap', 'pub']),
            (0.0005000000000000001, ['has', 'cheap', 'hotel']),
            (0.027999999999999997, ['ehm', 'Chinese', 'restaurant']),
            (0.0034999999999999996, ['ehm', 'Chinese', 'pub']),
            (0.0034999999999999996, ['ehm', 'Chinese', 'hotel']),
            (0.008000000000000002, ['ehm', 'English', 'restaurant']),
            (0.0010000000000000002, ['ehm', 'English', 'pub']),
            (0.0010000000000000002, ['ehm', 'English', 'hotel']),
            (0.004000000000000001, ['ehm', 'cheap', 'restaurant']),
            (0.0005000000000000001, ['ehm', 'cheap', 'pub']),
            (0.0005000000000000001, ['ehm', 'cheap', 'hotel'])]
        trigram_hyps_with_boundaries = [
            (0.63, [SENTENCE_START, 'want', 'Chinese']),
            (0.18000000000000002, [SENTENCE_START, 'want', 'English']),
            (0.09000000000000001, [SENTENCE_START, 'want', 'cheap']),
            (0.034999999999999996, [SENTENCE_START, 'has', 'Chinese']),
            (0.010000000000000002, [SENTENCE_START, 'has', 'English']),
            (0.005000000000000001, [SENTENCE_START, 'has', 'cheap']),
            (0.034999999999999996, [SENTENCE_START, 'ehm', 'Chinese']),
            (0.010000000000000002, [SENTENCE_START, 'ehm', 'English']),
            (0.005000000000000001, [SENTENCE_START, 'ehm', 'cheap']),
            (0.504, ['want', 'Chinese', 'restaurant']),
            (0.063, ['want', 'Chinese', 'pub']),
            (0.063, ['want', 'Chinese', 'hotel']),
            (0.14400000000000004, ['want', 'English', 'restaurant']),
            (0.018000000000000006, ['want', 'English', 'pub']),
            (0.018000000000000006, ['want', 'English', 'hotel']),
            (0.07200000000000002, ['want', 'cheap', 'restaurant']),
            (0.009000000000000003, ['want', 'cheap', 'pub']),
            (0.009000000000000003, ['want', 'cheap', 'hotel']),
            (0.027999999999999997, ['has', 'Chinese', 'restaurant']),
            (0.0034999999999999996, ['has', 'Chinese', 'pub']),
            (0.0034999999999999996, ['has', 'Chinese', 'hotel']),
            (0.008000000000000002, ['has', 'English', 'restaurant']),
            (0.0010000000000000002, ['has', 'English', 'pub']),
            (0.0010000000000000002, ['has', 'English', 'hotel']),
            (0.004000000000000001, ['has', 'cheap', 'restaurant']),
            (0.0005000000000000001, ['has', 'cheap', 'pub']),
            (0.0005000000000000001, ['has', 'cheap', 'hotel']),
            (0.027999999999999997, ['ehm', 'Chinese', 'restaurant']),
            (0.0034999999999999996, ['ehm', 'Chinese', 'pub']),
            (0.0034999999999999996, ['ehm', 'Chinese', 'hotel']),
            (0.008000000000000002, ['ehm', 'English', 'restaurant']),
            (0.0010000000000000002, ['ehm', 'English', 'pub']),
            (0.0010000000000000002, ['ehm', 'English', 'hotel']),
            (0.004000000000000001, ['ehm', 'cheap', 'restaurant']),
            (0.0005000000000000001, ['ehm', 'cheap', 'pub']),
            (0.0005000000000000001, ['ehm', 'cheap', 'hotel']),
            (0.5599999999999999, ['Chinese', 'restaurant', SENTENCE_END]),
            (0.06999999999999999, ['Chinese', 'pub', SENTENCE_END]),
            (0.06999999999999999, ['Chinese', 'hotel', SENTENCE_END]),
            (0.16000000000000003, ['English', 'restaurant', SENTENCE_END]),
            (0.020000000000000004, ['English', 'pub', SENTENCE_END]),
            (0.020000000000000004, ['English', 'hotel', SENTENCE_END]),
            (0.08000000000000002, ['cheap', 'restaurant', SENTENCE_END]),
            (0.010000000000000002, ['cheap', 'pub', SENTENCE_END]),
            (0.010000000000000002, ['cheap', 'hotel', SENTENCE_END])]
        act_trigram_hyps = list(asr_confnet.iter_ngrams(3))
        act_trigram_hyps_with_boundaries = list(
            asr_confnet.iter_ngrams(3, with_boundaries=True))
        # Compare the actual answer to the expected one.
        for hyps, act_hyps in ((trigram_hyps, act_trigram_hyps),
                               (trigram_hyps_with_boundaries,
                                act_trigram_hyps_with_boundaries)):
            self.assertItemsEqual([hyp[1] for hyp in hyps],
                                  [ahyp[1] for ahyp in act_hyps])
            for hyp in hyps:
                corresponding = [act_hyp for act_hyp in act_hyps
                                 if act_hyp[1] == hyp[1]]
                self.assertTrue(len(corresponding) == 1)
                act_hyp = corresponding[0]
                self.assertTrue(act_hyp[0] * (1 - tolerance) <= hyp[0]
                                <= act_hyp[0] * (1 + tolerance))
        # Corner cases.
        self.assertItemsEqual(list(asr_confnet.iter_ngrams(4)), [])
        pentagram_hyps = [
            (0.504, [SENTENCE_START, 'want', 'Chinese', 'restaurant', SENTENCE_END]),
            (0.063, [SENTENCE_START, 'want', 'Chinese', 'pub', SENTENCE_END]),
            (0.063, [SENTENCE_START, 'want', 'Chinese', 'hotel', SENTENCE_END]),
            (0.14400000000000004, [SENTENCE_START, 'want', 'English', 'restaurant', SENTENCE_END]),
            (0.018000000000000006, [SENTENCE_START, 'want', 'English', 'pub', SENTENCE_END]),
            (0.018000000000000006, [SENTENCE_START, 'want', 'English', 'hotel', SENTENCE_END]),
            (0.07200000000000002, [SENTENCE_START, 'want', 'cheap', 'restaurant', SENTENCE_END]),
            (0.009000000000000003, [SENTENCE_START, 'want', 'cheap', 'pub', SENTENCE_END]),
            (0.009000000000000003, [SENTENCE_START, 'want', 'cheap', 'hotel', SENTENCE_END]),
            (0.027999999999999997, [SENTENCE_START, 'has', 'Chinese', 'restaurant', SENTENCE_END]),
            (0.0034999999999999996, [SENTENCE_START, 'has', 'Chinese', 'pub', SENTENCE_END]),
            (0.0034999999999999996, [SENTENCE_START, 'has', 'Chinese', 'hotel', SENTENCE_END]),
            (0.008000000000000002, [SENTENCE_START, 'has', 'English', 'restaurant', SENTENCE_END]),
            (0.0010000000000000002, [SENTENCE_START, 'has', 'English', 'pub', SENTENCE_END]),
            (0.0010000000000000002, [SENTENCE_START, 'has', 'English', 'hotel', SENTENCE_END]),
            (0.004000000000000001, [SENTENCE_START, 'has', 'cheap', 'restaurant', SENTENCE_END]),
            (0.0005000000000000001, [SENTENCE_START, 'has', 'cheap', 'pub', SENTENCE_END]),
            (0.0005000000000000001, [SENTENCE_START, 'has', 'cheap', 'hotel', SENTENCE_END]),
            (0.027999999999999997, [SENTENCE_START, 'ehm', 'Chinese', 'restaurant', SENTENCE_END]),
            (0.0034999999999999996, [SENTENCE_START, 'ehm', 'Chinese', 'pub', SENTENCE_END]),
            (0.0034999999999999996, [SENTENCE_START, 'ehm', 'Chinese', 'hotel', SENTENCE_END]),
            (0.008000000000000002, [SENTENCE_START, 'ehm', 'English', 'restaurant', SENTENCE_END]),
            (0.0010000000000000002, [SENTENCE_START, 'ehm', 'English', 'pub', SENTENCE_END]),
            (0.0010000000000000002, [SENTENCE_START, 'ehm', 'English', 'hotel', SENTENCE_END]),
            (0.004000000000000001, [SENTENCE_START, 'ehm', 'cheap', 'restaurant', SENTENCE_END]),
            (0.0005000000000000001, [SENTENCE_START, 'ehm', 'cheap', 'pub', SENTENCE_END]),
            (0.0005000000000000001, [SENTENCE_START, 'ehm', 'cheap', 'hotel', SENTENCE_END])]
        act_pentagram_hyps = list(asr_confnet.iter_ngrams(5, with_boundaries=True))
        self.assertItemsEqual([hyp[1] for hyp in pentagram_hyps],
                                [ahyp[1] for ahyp in act_pentagram_hyps])
        for hyp in pentagram_hyps:
            corresponding = [act_hyp for act_hyp in act_pentagram_hyps
                                if act_hyp[1] == hyp[1]]
            self.assertTrue(len(corresponding) == 1)
            act_hyp = corresponding[0]
            self.assertTrue(act_hyp[0] * (1 - tolerance) <= hyp[0]
                            <= act_hyp[0] * (1 + tolerance))
        self.assertFalse(list(asr_confnet.iter_ngrams(6, with_boundaries=True)))

    def test_replace(self):
        tolerance = 0.01

        # Create a simple confusion network.
        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.70, 0.20, 0.10
        C1, C2, C3 = 0.80, 0.10, 0.10

        asr_confnet = UtteranceConfusionNetwork()
        asr_confnet.add([[A1, "want"], [A2, "has"], [A3, 'ehm']])
        asr_confnet.add([[B1, "Chinese"],  [B2, "English"], [B3, 'cheap']])
        asr_confnet.add([[C1, "restaurant"],  [C2, "pub"],   [C3, 'hotel']])
        asr_confnet.merge().sort()

        replaced = asr_confnet.replace(("nothing", ), ("something", ))
        self.assertEqual(replaced, asr_confnet)

        replaced = asr_confnet.replace(("has", ), ("is", ))
        self.assertNotEqual(replaced, asr_confnet)
        self.assertEqual(list(replaced.cn[0][1]), [A2, "is"])

        replaced = asr_confnet.replace(("has", ), tuple())
        self.assertNotEqual(replaced, asr_confnet)
        self.assertAlmostEqual(sum(hyp[0] for hyp in asr_confnet.cn[0]), 1.)

        replaced = asr_confnet.replace(("has", ), ("should", "have", ))
        replaced.add([(0.5, 'want'), (0.5, 'pub')])
        unigrams = [['want'], ['ehm'], ['should'], ['have'], ['Chinese'],
                    ['English'], ['cheap'], ['restaurant'], ['pub'], ['hotel'],
                    ['want'], ['pub'], ]
        act_unigrams = list(hyp[1] for hyp in replaced.iter_ngrams(1))
        self.assertItemsEqual(unigrams, act_unigrams)
        bigrams = [
            ['want', 'Chinese'],
            ['want', 'English'],
            ['want', 'cheap'],
            ['ehm', 'Chinese'],
            ['ehm', 'English'],
            ['ehm', 'cheap'],
            ['should', 'have'],
            ['have', 'Chinese'],
            ['have', 'English'],
            ['have', 'cheap'],
            ['Chinese', 'restaurant'],
            ['Chinese', 'pub'],
            ['Chinese', 'hotel'],
            ['English', 'restaurant'],
            ['English', 'pub'],
            ['English', 'hotel'],
            ['cheap', 'restaurant'],
            ['cheap', 'pub'],
            ['cheap', 'hotel'],
            ['restaurant', 'want'],
            ['restaurant', 'pub'],
            ['pub', 'want'],
            ['pub', 'pub'],
            ['hotel', 'want'],
            ['hotel', 'pub'],
        ]
        act_bigrams = list(hyp[1] for hyp in replaced.iter_ngrams(2))
        self.assertItemsEqual(bigrams, act_bigrams)
        trigrams = [
            ['want', 'Chinese', 'restaurant'],
            ['want', 'Chinese', 'pub'],
            ['want', 'Chinese', 'hotel'],
            ['want', 'English', 'restaurant'],
            ['want', 'English', 'pub'],
            ['want', 'English', 'hotel'],
            ['want', 'cheap', 'restaurant'],
            ['want', 'cheap', 'pub'],
            ['want', 'cheap', 'hotel'],
            ['ehm', 'Chinese', 'restaurant'],
            ['ehm', 'Chinese', 'pub'],
            ['ehm', 'Chinese', 'hotel'],
            ['ehm', 'English', 'restaurant'],
            ['ehm', 'English', 'pub'],
            ['ehm', 'English', 'hotel'],
            ['ehm', 'cheap', 'restaurant'],
            ['ehm', 'cheap', 'pub'],
            ['ehm', 'cheap', 'hotel'],
            ['should', 'have', 'Chinese'],
            ['should', 'have', 'English'],
            ['should', 'have', 'cheap'],
            ['have', 'Chinese', 'restaurant'],
            ['have', 'Chinese', 'pub'],
            ['have', 'Chinese', 'hotel'],
            ['have', 'English', 'restaurant'],
            ['have', 'English', 'pub'],
            ['have', 'English', 'hotel'],
            ['have', 'cheap', 'restaurant'],
            ['have', 'cheap', 'pub'],
            ['have', 'cheap', 'hotel'],
            ['Chinese', 'restaurant', 'want'],
            ['Chinese', 'restaurant', 'pub'],
            ['Chinese', 'pub', 'want'],
            ['Chinese', 'pub', 'pub'],
            ['Chinese', 'hotel', 'want'],
            ['Chinese', 'hotel', 'pub'],
            ['English', 'restaurant', 'want'],
            ['English', 'restaurant', 'pub'],
            ['English', 'pub', 'want'],
            ['English', 'pub', 'pub'],
            ['English', 'hotel', 'want'],
            ['English', 'hotel', 'pub'],
            ['cheap', 'restaurant', 'want'],
            ['cheap', 'restaurant', 'pub'],
            ['cheap', 'pub', 'want'],
            ['cheap', 'pub', 'pub'],
            ['cheap', 'hotel', 'want'],
            ['cheap', 'hotel', 'pub'],
        ]
        act_trigrams = list(hyp[1] for hyp in replaced.iter_ngrams(3))
        self.assertItemsEqual(trigrams, act_trigrams)

        replaced2 = replaced.replace(('pub',), ('fast', 'food',))
        replaced2 = replaced2.replace(('want', 'English'), ('would', 'like', 'English'))
        bigrams = [
            ['<s>', 'ehm'],
            ['<s>', 'should'],
            ['<s>', 'would'],
            ['ehm', 'Chinese'],
            ['ehm', 'cheap'],
            ['should', 'have'],
            ['have', 'Chinese'],
            ['have', 'cheap'],
            ['would', 'like'],
            ['like', 'English'],
            ['English', 'restaurant'],
            ['English', 'hotel'],
            ['English', 'fast'],
            ['Chinese', 'restaurant'],
            ['Chinese', 'hotel'],
            ['Chinese', 'fast'],
            ['cheap', 'restaurant'],
            ['cheap', 'hotel'],
            ['cheap', 'fast'],
            ['restaurant', 'want'],
            ['restaurant', 'fast'],
            ['hotel', 'want'],
            ['hotel', 'fast'],
            ['fast', 'food'],
            ['food', 'want'],
            ['food', 'fast'],
            ['want', '</s>'],
            ['fast', 'food'],
            ['food', '</s>']
        ]
        act_bigrams = list(hyp[1] for hyp in replaced2.iter_ngrams(2, True))
        self.assertItemsEqual(bigrams, act_bigrams)

    def test_idx_zero(self):
        # Construct a confnet that will contain a long link starting at index
        # zero.
        cn_repr = ('UtteranceConfusionNetwork("[]|'
                   'LongLink\\\\(end=3\\\\, '
                   'orig_probs=\\\\[1.0\\\\, 0.995\\\\, 1.0\\\\]\\\\, '
                   'hyp=\\\\(0.995\\\\, \\\\(u\'pub food\'\\\\,\\\\)\\\\)'
                   '\\\\, normalise=True\\\\)'
                   ';(0.005:it)|;|;(0.989:a),(0.011:)|;(0.989:),(0.011:cheap)'
                   '|;(0.982:need),(0.018:)|;(0.998:),(0.002:in)'
                   '|;(0.99:),(0.01:a)|;(0.983:i),(0.017:)|")')
        cn = eval(cn_repr)
        self.assertEquals(repr(cn), cn_repr)

        # Substitute for that long link.
        # import ipdb; ipdb.set_trace()
        replaced = cn.phrase2category_label(('pub food', ), ('FOOD', ))
        rep_repr = ('UtteranceConfusionNetwork("[Index(is_long_link=True, '
                    'word_idx=0, alt_idx=1, link_widx=None)]|LongLink\\\\('
                    'end=3\\\\, orig_probs=\\\\[1.0\\\\, 0.995\\\\, 1.0\\\\]'
                    '\\\\, hyp=\\\\(0.995\\\\, \\\\(u\'pub food\'\\\\,\\\\)'
                    '\\\\)\\\\, normalise=True\\\\),LongLink\\\\(end=3\\\\, '
                    'orig_probs=\\\\[1.0\\\\, 0.995\\\\, 1.0\\\\]\\\\, hyp='
                    '\\\\(0.995\\\\, \\\\(u\'FOOD=pub food\'\\\\,\\\\)\\\\)'
                    '\\\\, normalise=False\\\\);(0.005:it)|;|;(0.989:a),'
                    '(0.011:)|;(0.989:),(0.011:cheap)|;(0.982:need),(0.018:)|;'
                    '(0.998:),(0.002:in)|;(0.99:),(0.01:a)|;(0.983:i),(0.017:)'
                    '|")')
        self.assertEquals(repr(replaced), rep_repr)
        # import pprint
        # pprint.pprint(replaced._cn)
        # pprint.pprint(replaced._long_links)


class TestUttCNFeats(unittest.TestCase):
    """Basic test for utterance confnet features."""

    def test_empty_features(self):
        empty_feats_items = [('__empty__', 1.0)]
        cn = UtteranceConfusionNetwork()
        feats = UtteranceConfusionNetworkFeatures(confnet=cn)
        self.assertEqual(feats.features.items(), empty_feats_items)
        cn.add([(.9, '')])
        feats = UtteranceConfusionNetworkFeatures(confnet=cn)
        self.assertEqual(feats.features.items(), empty_feats_items)
        cn.add([(1., '')])
        feats = UtteranceConfusionNetworkFeatures(confnet=cn)
        self.assertEqual(feats.features.items(), empty_feats_items)


if __name__ == '__main__':
    unittest.main()
