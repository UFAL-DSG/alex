#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import numpy as np

from collections import defaultdict

from alex.utils.exception import UtteranceNBListException
from alex import utils


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
            if limit and count > limit:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split("=>")

            key = parts[0].strip()
            utt = parts[1].strip()

            utterances[key] = Utterance(utt)

    return utterances


class ASRHypothesis(object):
    """This is a base class for all forms of probabilistic ASR hypotheses
    representations."""
    pass


class Features(object):
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
        if other is None:
            return False

        if isinstance(other, Utterance):
            return self.utterance == other.utterance
        elif isinstance(other, basestring):
            return self.utterance == other.split()
        else:
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
        raise ValueError('Missing "{phrase}" in "{utt}"'.format(
                            phrase=phrase, utt=self.utterance))

    def replace(self, orig, replacement):
        try:
            orig_pos = self.index(orig)
        except ValueError:
            return

        self.utterance[orig_pos:orig_pos + len(orig)] = replacement

    def lower(self):
        """Transforms words of this utterance to lower case.

        BEWARE, this method is destructive. Instead of returning the lowercased
        version, it lowercases self (and returns None).

        """
        for word_idx in range(len(self.utterance)):
            self.utterance[word_idx] = self.utterance[word_idx].lower()


class UtteranceFeatures(Features):
    """Represents the vector of features for an utterance.

    The class also provides methods for manipulation of the feature vector,
    including extracting features from an utterance.

    Currently, only n-gram (including skip n-grams) features are implemented.

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
        self.type = type
        self.size = size
        self.features = defaultdict(float)

        if utterance is not None:
            self.parse(utterance)

    def __str__(self):
        return str(self.features)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, k):
        return self.features[k]

    def __contains__(self, k):
        return k in self.features

    def __iter__(self):
        for i in self.features:
            yield i

    def get_feature_vector(self, features_mapping):
        fv = np.zeros(len(features_mapping))
        for f in self.features:
            if f in features_mapping:
                fv[features_mapping[f]] = self.features[f]

        return fv

    def parse(self, utterance):
        """Extracts the features from `utterance'."""
        if utterance.isempty():
            self.features['__empty__'] += 1.0
        elif self.type == 'ngram':
            # Compute n-grams.
            # TODO: Consider the <sentence start> and <sentence end> tokens,
            # too. For longer n-grams, this can be generalised to <before
            # sentence> and <after sentence>.
            for length in xrange(1, self.size + 1):
                for start in xrange(len(utterance) - length + 1):
                    self.features[tuple(utterance[start:start + length])] \
                        += 1.0

            # Compute skip n-grams.
            new_features = defaultdict(float)
            for feat in self.features:
                if len(feat) == 3:
                    new_features[(feat[0], '*1', feat[2])] += 1.0
                elif len(feat) == 4:
                    new_features[(feat[0], '*2', feat[3])] += 1.0
            # Save the skip n-grams.
            for new_feat in new_features:
                self.features[new_feat] += new_features[new_feat]
        else:
            raise NotImplementedError(
                "Features can be extracted only from an empty utterance or "
                "for the `ngrams' feature type.")

        # FIXME: This is a debugging behaviour. Condition on DEBUG or `verbose'
        # etc. or raise it as an exception.
        if len(self.features) == 0:
            print utterance.utterance

        self.set = set(self.features.keys())

    def prune(self, remove_features):
        for f in self.set:
            if f in remove_features:
                self.set.remove(f)

                # DEBUG
                # If the feature is in the set of features, it should be in the
                # dictionary, too.
                assert f in self.features
                del self.features[f]


class UtteranceHyp(ASRHypothesis):
    """Provide an interface for 1-best hypothesis from the ASR component."""
    def __init__(self, prob=None, utterance=None):
        self.prob = prob
        self.utterance = utterance

    def __str__(self):
        return "%.3f %s" % (self.prob, self.utterance)

    def get_best_utterance(self):
        return self.utterance


class UtteranceNBList(ASRHypothesis):
    """Provides a convenient interface for processing N-best lists of
    recognised utterances.

    When updating the N-best list, one should do the following.

    1. add utterances or parse a confusion network
    2. merge
    3. normalise
    4. sort

    """
    def __init__(self):
        self.n_best = []

    def __str__(self):
        s = []
        for h in self.n_best:
            s.append("%.3f %s" % (h[0], h[1]))

        return '\n'.join(s)

    def __len__(self):
        return len(self.n_best)

    def __getitem__(self, i):
        return self.n_best[i]

    def __iter__(self):
        for i in self.n_best:
            yield i

    def get_best_utterance(self):
        """Returns the most probable utterance."""
        if self.n_best[0][1] == '__other__':
            return self.n_best[1][1]

        return self.n_best[0][1]

    def add(self, probability, utterance):
        self.n_best.append([probability, utterance])

    def merge(self):
        """Adds up probabilities for the same hypotheses.
        """
        new_n_best = []

        if len(self.n_best) <= 1:
            return
        else:
            new_n_best.append(self.n_best[0])

            for i in range(1, len(self.n_best)):
                for j in range(len(new_n_best)):
                    if new_n_best[j][1] == self.n_best[i][1]:
                        # merge, add the probabilities
                        new_n_best[j][0] += self.n_best[i][0]
                        break
                else:
                    new_n_best.append(self.n_best[i])

        self.n_best = new_n_best

    def scale(self):
        """The N-best list will be scaled to sum to one."""

        s = sum([p for p, da in self.n_best])

        for i in range(len(self.n_best)):
            # null act is already there, therefore just normalise
            self.n_best[i][0] /= s

    def normalise(self):
        suma = 0.0
        other_utt = -1
        for i in range(len(self.n_best)):
            suma += self.n_best[i][0]

            if self.n_best[i][1] == '__other__':
                if other_utt != -1:
                    raise UtteranceNBListException(
                        ('Utterance list includes multiple __other__ '
                         'utterances: {utts!s}').format(utts=self.n_best))
                other_utt = i

        if other_utt == -1:
            if suma > utils.one():
                raise UtteranceNBListException(
                    ('Sum of probabilities in the utterance list > 1.0: '
                     '{suma:8.6f}').format(suma=suma))
            prob_other = 1.0 - suma
            self.n_best.append([prob_other, Utterance('__other__')])
        else:
            for i in range(len(self.n_best)):
                # __other__ utterance is already there, therefore just
                # normalise
                self.n_best[i][0] /= suma

    def sort(self):
        self.n_best.sort(reverse=True)


class UtteranceNBListFeatures(Features):
    pass

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
