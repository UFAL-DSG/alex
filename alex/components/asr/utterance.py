#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import numpy as np

from collections import defaultdict

from alex import utils
from alex.ml.hypothesis import Hypothesis, NBList, NBListException
# TODO: The following import is a temporary workaround for moving classes
# originally defined here to that module.  Instead, refer to the new module's
# definitions everywhere where this module would have been used.
from alex.ml.features import *
from alex.utils.exception import UtteranceNBListException


SENTENCE_START = '<s>'
SENTENCE_END = '</s>'


def load_utterances(utt_fname, limit=None):
    """Loads a dictionary of utterances from a given file. The file is assumed
    to contain lines of the following form:

    [whitespace..]<key>[whitespace..]=>[whitespace..]<utterance>[whitespace..]

    Arguments:
        utt_fname -- path towards the file to read the utterances from
        limit -- limit on the number of utterances to read

    Returns a dictionary with utterances (instances of Utterance) as values.

    """
    with open(utt_fname) as utt_file:
        utterances = {}
        count = 0
        for line in utt_file:
            count += 1
            if limit is not None and count > limit:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split("=>")

            key = parts[0].strip()
            utt = parts[1].strip()

            utterances[key] = Utterance(utt)

    return utterances


class ASRHypothesis(Hypothesis):
    """This is a base class for all forms of probabilistic ASR hypotheses
    representations."""
    pass


class Utterance(object):
    # TODO: Since Utterance basically represents a (is-a) list, it should
    # inherit from the builtin `list', I reckon. This might be a bit tricky,
    # though, because of the way built-in types are constructed.

    def __init__(self, surface):
        self.utterance = surface.split()

    def __str__(self):
        return ' '.join(self.utterance)

    def __contains__(self, s):
        try:
            self.index(s)
        except ValueError:
            return False

        return True

    def __lt__(self, other):
        return self.utterance < other.utterance

    def __le__(self, other):
        return self.utterance <= other.utterance

    def __eq__(self, other):
        if isinstance(other, Utterance):
            return self.utterance == other.utterance
        elif isinstance(other, basestring):
            return self.utterance == other.split()
        return False

    def __ne__(self, other):
        return not self.__eq__(other.utterance)

    def __gt__(self, other):
        return self.utterance > other.utterance

    def __ge__(self, other):
        return self.utterance >= other.utterance

    def __len__(self):
        return len(self.utterance)

    def __getitem__(self, idx):
        return self.utterance[idx]

    def __iter__(self):
        for word in self.utterance:
            yield word

    def isempty(self):
        return len(self.utterance) == 0

    # TODO cache(1)
    def index(self, phrase):
        """Returns the word index of the start of first occurence of `phrase'
        within this utterance. If none is found, ValueError is raised.

        Arguments:
            phrase -- a list of words constituting the phrase sought

        """
        assert len(phrase) > 0
        # All through this method, we assume a short length of `phrase', with
        # little or none repeated word tokens.

        # Compute the maximal skip in case of incomplete match.
        initial = phrase[0]
        for word_count, word in enumerate(phrase[1:], start=1):
            if word == initial:
                max_skip = word_count
                break
        else:
            max_skip = len(phrase)

        # last index where the match can start
        last_idx = len(self.utterance) - len(phrase)
        # Iterate over the utterance.
        match_idx = 0
        while match_idx <= last_idx:
            # If the initial word matches,
            if self.utterance[match_idx] == initial:
                # Check the subsequent words too.
                for phrase_idx in xrange(1, len(phrase)):
                    if self.utterance[match_idx + phrase_idx] !=\
                            phrase[phrase_idx]:
                        break
                else:
                    # Match found.
                    return match_idx
                # If subsequent words do not match, skip them.
                match_idx += min(max_skip, phrase_idx)
            else:
                match_idx += 1
        # No match found.
        raise ValueError('Missing "{phrase}" in "{utt}"'
                         .format(phrase=phrase, utt=self.utterance))

    def replace(self, orig, replacement):
        # If `orig' does not occur in self, do nothing, return self.
        try:
            orig_pos = self.index(orig)
        except ValueError:
            return self

        # If `orig' does occur in self, construct a new utterance with `orig'
        # replaced by `replacement' and return that.
        ret = Utterance('')
        if not isinstance(replacement, list):
            replacement = list(replacement)
        ret.utterance = (self.utterance[:orig_pos] + replacement +
                         self.utterance[orig_pos + len(orig):])
        return ret

    def lower(self):
        """Transforms words of this utterance to lower case.

        BEWARE, this method is destructive, it lowercases self.

        """
        for word_idx in range(len(self.utterance)):
            self.utterance[word_idx] = self.utterance[word_idx].lower()
        return self

    def iter_with_boundaries(self):
        """Iterates the sequence [SENTENCE_START, word1, ..., wordlast,
        SENTENCE_END].

        """
        yield SENTENCE_START
        for word in self.utterance:
            yield word
        yield SENTENCE_END

    def iter_ngrams(self, n, with_boundaries=False):
        min_len = n - with_boundaries * 2
        # If the n-gram so-so fits into the utterance.
        if len(self.utterance) <= min_len:
            if len(self.utterance) == min_len:
                if with_boundaries:
                    yield [SENTENCE_START] + self.utterance + [SENTENCE_END]
                else:
                    yield self.utterance[:]
            return
        # Usual cases.
        if with_boundaries and len(self.utterance) > min_len:
            yield [SENTENCE_START] + self.utterance[:n - 1]
        for start_idx in xrange(len(self.utterance) - n + 1):
            yield self.utterance[start_idx:start_idx + n]
        if with_boundaries:
            yield self.utterance[-(n - 1):] + [SENTENCE_END]


class UtteranceFeatures(Features):
    """Represents the vector of features for an utterance.

    The class also provides methods for manipulation of the feature vector,
    including extracting features from an utterance.

    Currently, only n-gram (including skip n-grams) features are implemented.

    Attributes:
        type: type of features ('ngram')
        size: size of features (an integer)
        features: mapping { feature : value of feature (# occs) }

    """
    def __init__(self, type='ngram', size=3, utterance=None):
        """Creates a vector of utterance features if `utterance' is provided.
        Otherwise, just saves the type and size of features requested.

        Keyword arguments:
            - type: the type of features as a string; currently only 'ngram' is
                implemented
            - size: maximum order of the (n-gram) features; for skip n-grams,
                this is the distance between the first and last word plus one
            - utterance: the utterance for which to extract the features;
                If utterance is None (the default), an all-zeroes vector is
                created.

                Otherwise, utterance must be an instance of Utterance.

        """
        # This initialises the self.features and self.set fields.
        super(UtteranceFeatures, self).__init__()

        self.type = type
        self.size = size

        if utterance is not None:
            self.parse(utterance)

    def parse(self, utterance):
        """Extracts the features from `utterance'."""
        if utterance.isempty():
            self.features['__empty__'] += 1.0
        elif self.type == 'ngram':
            # Compute shorter n-grams.
            for word in utterance:
                self.features[(word, )] += 1.
            if self.size >= 2:
                for ngram in utterance.iter_ngrams(2, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
            # Compute n-grams and skip n-grams for size 3.
            if self.size >= 3:
                for ngram in utterance.iter_ngrams(3, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
                    self.features[(ngram[0], '*1', ngram[2])] += 1.
            # Compute n-grams and skip n-grams for size 4.
            if self.size >= 4:
                for ngram in utterance.iter_ngrams(4, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
                    self.features[(ngram[0], '*2', ngram[3])] += 1.
            # Compute longer n-grams.
            for length in xrange(5, self.size + 1):
                for ngram in utterance.iter_ngrams(length,
                                                   with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
        else:
            raise NotImplementedError(
                "Features can be extracted only from an empty utterance or "
                "for the `ngrams' feature type.")

        # FIXME: This is a debugging behaviour. Condition on DEBUG or `verbose'
        # etc. or raise it as an exception.
        if len(self.features) == 0:
            print '(EE) Utterance with no features: "{utt}"'.format(
                utt=utterance.utterance)

        self.set = set(self.features.keys())


class UtteranceHyp(ASRHypothesis):
    """Provide an interface for 1-best hypothesis from the ASR component."""
    def __init__(self, prob=None, utterance=None):
        self.prob = prob
        self.utterance = utterance

    def __str__(self):
        return "%.3f %s" % (self.prob, self.utterance)

    def get_best_utterance(self):
        return self.utterance


class UtteranceNBList(ASRHypothesis, NBList):
    """Provides functionality of n-best lists for utterances.

    When updating the n-best list, one should do the following.

    1. add utterances or parse a confusion network
    2. merge and normalise, in either order

    Attributes:
        n_best: the list containing pairs [prob, utterance] sorted from the
                most probable to the least probable ones

    """
    def __init__(self):
        NBList.__init__(self)

    def get_best_utterance(self):
        """Returns the most probable utterance.

        DEPRECATED. Use get_best instead.

        """
        return self.get_best()

    def get_best(self):
        if self.n_best[0][1] == '__other__':
            return self.n_best[1][1]
        return self.n_best[0][1]

    # TODO Replace with NBList.normalise.
    def scale(self):
        """Scales the n-best list to sum to one."""
        return NBList.normalise(self)

    def normalise(self):
        """The N-best list is extended to include the "__other__" utterance to
        represent those utterance hypotheses which are not included in the
        N-best list.

        DEPRECATED. Use add_other instead.

        """
        return self.add_other()

    def add_other(self):
        try:
            return NBList.add_other(self, Utterance('__other__'))
        except NBListException as ex:
            # DEBUG
            import ipdb; ipdb.set_trace()
            raise UtteranceNBListException(ex)

    # XXX It is now a class invariant that the n-best list is sorted.
    def sort(self):
        """DEPRECATED, going to be removed."""
        return self
        # self.n_best.sort(reverse=True)


class UtteranceNBListFeatures(Features):
    # TODO Document.
    def __init__(self, type='ngram', size=3, utt_nblist=None):
        # This initialises the self.features and self.set fields.
        super(UtteranceNBListFeatures, self).__init__()

        self.type = type
        self.size = size

        if utt_nblist is not None:
            self.parse(utt_nblist)

    def parse(self, utt_nblist):
        """This should be called only once during the object's lifetime,
        preferrably from within the initialiser.
        """
        first_utt_feats = None
        for hyp_idx, hyp in enumerate(utt_nblist):
            prob, utt = hyp
            utt_feats = UtteranceFeatures(type=self.type,
                                          size=self.size,
                                          utterance=utt)
            if first_utt_feats is None:
                first_utt_feats = utt_feats
            for feat, feat_val in utt_feats.iteritems():
                # Include the first rank of features occurring in the n-best list.
                if (0, feat) not in self.features:
                    self.features[(0, feat)] = float(hyp_idx)
                # Include the weighted features of individual hypotheses.
                self.features[(1, feat)] += prob * feat_val
        # Add features of the top utterance
        if first_utt_feats is None:
            self.features[(2, None)] = 1.
        else:
            self.features[(2, 'prob')] = utt_nblist[0][0]
            for feat, feat_val in first_utt_feats.iteritems():
                self.features[(2, feat)] = feat_val

        # Keep self.set up to date. (Why is it needed, anyway?)
        self.set = set(self.features)

#TODO: You can implement UtteranceConfusionNetwork and
# UtteranceConfusionNetworkFeatures to serve the similar purpose for
# DAILogRegClassifier as Utterance and UtteranceFeatures
#
# - then the code will be more general


class UtteranceConfusionNetwork(ASRHypothesis):
    """Word confusion network"""

    def __init__(self):
        self.cn = []

    def __str__(self):
        s = []
        for alts in self.cn:
            ss = []
            for p, w in alts:
                ss.append("(%.3f : %s) " % (p, w if w else '-'))
            s.append(' '.join(ss))

        return '\n'.join(s)

    def __len__(self):
        return len(self.cn)

    def __getitem__(self, i):
        return self.cn[i]

    def __iter__(self):
        for i in self.cn:
            yield i

    def add(self, words):
        """Adds the next word with its alternatives"""

        self.cn.append(words)

    def get_best_utterance(self):
        utterance = []
        for alts in self.cn:
            utterance.append(alts[0][1])

        return ' '.join(utterance).strip()

    def get_best_hyp(self):
        utterance = []
        prob = 1.0
        for alts in self.cn:
            utterance.append(alts[0][1])
            prob *= alts[0][0]

        utterance = ' '.join(utterance).strip()
        return (prob, Utterance(utterance))

    def get_prob(self, hyp_index):
        """Return a probability of the given hypothesis."""

        prob = 1.0
        for i, alts in zip(hyp_index, self.cn):
            prob *= alts[i][0]

        return prob

    def get_next_worse_candidates(self, hyp_index):
        """Returns such hypotheses that will have lower probability. It assumes
        that the confusion network is sorted."""
        worse_hyp = []

        for i in range(len(hyp_index)):
            wh = list(hyp_index)
            wh[i] += 1
            if wh[i] >= len(self.cn[i]):
                # this generate inadmissible word hypothesis
                continue

            worse_hyp.append(tuple(wh))

        return worse_hyp

    def get_hyp_index_utterence(self, hyp_index):
        s = [alts[i][1] for i, alts in zip(hyp_index, self.cn)]

        return Utterance(' '.join(s))

    def get_utterance_nblist(self, n=10, expand_upto_total_prob_mass=0.9):
        """Parses the confusion network and generates N-best hypotheses.

        The result is a list of utterance hypotheses each with a with assigned
        probability.  The list also include the utterance "__other__" for not
        having the correct utterance in the list.
        """
        # print "Confnet:"
        # print self
        # print

        open_hyp = []
        closed_hyp = {}

        # create index for the best hypothesis
        best_hyp = tuple([0] * len(self.cn))
        best_prob = self.get_prob(best_hyp)
        open_hyp.append((best_prob, best_hyp))

        i = 0
        while open_hyp and i < n:
            i += 1

            current_prob, current_hyp_index = open_hyp.pop(0)

            if current_hyp_index not in closed_hyp:
                # process only those hypotheses which were not processed so far

                closed_hyp[current_hyp_index] = current_prob

                # print "current_prob, current_hyp_index:", current_prob,
                # current_hyp_index

                for hyp_index in self.get_next_worse_candidates(
                        current_hyp_index):
                    prob = self.get_prob(hyp_index)
                    open_hyp.append((prob, hyp_index))

                open_hyp.sort(reverse=True)

        nblist = UtteranceNBList()
        for idx in closed_hyp:
            nblist.add(closed_hyp[idx], self.get_hyp_index_utterence(idx))

        # print nblist
        # print

        nblist.merge()
        nblist.normalise()
        nblist.sort()

        # print nblist
        # print

        return nblist

    def merge(self):
        """Adds up probabilities for the same hypotheses.

        TODO: not implemented yet
        """
        pass

    def prune(self, prune_prob=0.001):
        pruned_cn = []
        for alts in self.cn:
            if not alts[0][1] and alts[0][0] > 1.0 - prune_prob:
                # prune out silences
                continue

            pruned_alts = []
            for p, w in alts:
                if p < prune_prob:
                    continue
                else:
                    pruned_alts.append([p, w])

            if pruned_alts[0][1] == "" and len(pruned_alts) == 1:
                # I pruned out all alternatives except for silence,
                # then skip this
                continue

            pruned_cn.append(alts)

        self.cn = pruned_cn

    def normalise(self):
        """Makes sure that all probabilities adds up to one."""
        for alts in self.cn:
            sum = 0.0
            for p, w in alts:
                sum += p

            for i in range(len(alts)):
                alts[i][0] /= sum

    def sort(self):
        """Sort the alternatives for each word according their probability."""

        for alts in self.cn:
            alts.sort(reverse=True)


class UtteranceConfusionNetworkFeatures(Features):
    pass
