#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import __init__

if __name__ == "__main__":
    import autopath
from alex.components.asr.utterance import SENTENCE_START, SENTENCE_END, \
    Utterance, UtteranceNBList, UtteranceConfusionNetwork


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
        act_trigrams = [trigram for trigram in self.barbara.iter_ngrams(3)]
        act_trigrams_with_boundaries = [
            trigram for trigram in
            self.barbara.iter_ngrams(3, with_boundaries=True)]
        self.assertEqual(trigrams, act_trigrams)
        self.assertEqual(trigrams_with_boundaries,
                         act_trigrams_with_boundaries)
        # Corner cases.
        self.assertEqual([ngram for ngram in self.barbara.iter_ngrams(7)],
                         [['b', 'a', 'r', 'b', 'a', 'r', 'a']])
        self.assertEqual([ngram for ngram in self.barbara.iter_ngrams(8)],
                         [])
        self.assertEqual([ngram for ngram in
                          self.barbara.iter_ngrams(8, with_boundaries=True)],
                         [[SENTENCE_START, 'b', 'a', 'r', 'b', 'a', 'r', 'a'],
                          ['b', 'a', 'r', 'b', 'a', 'r', 'a', SENTENCE_END]])
        self.assertEqual([ngram for ngram in
                          self.barbara.iter_ngrams(9, with_boundaries=True)],
                         [[SENTENCE_START, 'b', 'a', 'r', 'b', 'a', 'r', 'a',
                           SENTENCE_END]])
        self.assertEqual([ngram for ngram in
                          self.barbara.iter_ngrams(10, with_boundaries=True)],
                         [])


class TestUtteranceConfusionNetework(unittest.TestCase):
    """ Test using
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
        correct_nblist.normalise()
        correct_nblist.sort()

        confnet = UtteranceConfusionNetwork()
        confnet.add([[A1, 'A1'], [A2, 'A2'], [A3, 'A3'],])
        confnet.add([[B1, 'B1'], [B2, 'B2'], [B3, 'B3'],])
        confnet.add([[C1, 'C1'], [C2, 'C2'], [C3, 'C3'],])
        confnet.merge()
        confnet.normalise()
        confnet.sort()

        gen_nblist = confnet.get_utterance_nblist(10)

        s = []
        s.append("")
        s.append("Confusion network:")
        s.append(str(confnet))
        s.append("")
        s.append("Generated nblist:")
        s.append(str(gen_nblist))
        s.append("")
        s.append("Correct nblist:")
        s.append(str(correct_nblist))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(str(gen_nblist), str(correct_nblist))


if __name__ == '__main__':
    unittest.main()
