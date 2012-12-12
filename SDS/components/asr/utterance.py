#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from collections import defaultdict, deque

from SDS.utils.exception import UtteranceNBListException, UtteranceConfusionNetworkException
from SDS import utils

def load_utterances(file_name, limit=None):
    f = open(file_name)

    utterances = {}
    c = 0
    for l in f:
        c += 1
        if limit and c > limit:
            break

        l = l.strip()
        if not l:
            continue

        l = l.split("=>")

        key = l[0].strip()
        utt = l[1].strip()

        utterances[key] = Utterance(utt)
    f.close()

    return utterances


class ASRHypothesis:
    """This is a base class for all forms of probabilistic ASR hypotheses representations."""
    pass


class Features:
    pass


class Utterance:
    def __init__(self, utterance):
        self.utterance = utterance.split()

    def __str__(self):
        return ' '.join(self.utterance)

    def __contains__(self, s):
        try:
            i = self.index(s)
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
        elif isinstance(other, str):
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

    def __getitem__(self, i):
        return self.utterance[i]

    def __iter__(self):
        for i in self.utterance:
            yield i

    def isempty(self):
        if len(self.utterance) == 0:
            return True

        return False

    def index(self, s):
        f = s[0]

        i = self.utterance.index(f)

        for j in range(1, len(s)):
            try:
                if self.utterance[i + j] != s[j]:
                    raise IndexError
            except IndexError:
                raise ValueError(
                    'Missing %s in %s' % (str(s), str(self.utterance)))

        return i

    def replace(self, s, r):
        try:
            i = self.index(s)
        except ValueError:
            return

        self.utterance[i:i + len(s)] = r

    def lower(self):
        for i in range(len(self.utterance)):
            self.utterance[i] = self.utterance[i].lower()

class UtteranceFeatures(Features):
    def __init__(self, type='ngram', size=3, utterance=None):
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

    def parse(self, u):
        if self.type == 'ngram':
            for k in range(1, self.size + 1):
                for i in range(len(u)):
                    if i + k > len(u):
                        break

                    self.features[tuple(u[i:i + k])] += 1.0

        if u.isempty():
            self.features['__empty__'] += 1.0

        new_features = defaultdict(float)
        for f in self.features:
            if len(f) == 3:
                new_features[(f[0], '*1', f[2])] += 1.0
            if len(f) == 4:
                new_features[(f[0], '*2', f[3])] += 1.0

        for f in new_features:
            self.features[f] += new_features[f]

        if len(self.features) == 0:
            print u.utterance

        self.set = set(self.features.keys())

    def prune(self, remove_features):
        for f in list(self.set):
            if f in remove_features:
                self.set.discard(f)

                if f in self.features:
                    del self.features[f]


class UtteranceHyp(ASRHypothesis):
    """Provide an interface for 1-best hypothesis from the ASR component."""
    def __init__(self, prob = None, utterance = None):
        self.prob = prob
        self.utterance = utterance

    def __str__(self):
        return "%.3f %s" % (self.prob, self.utterance)

    def get_best_utterance(self):
        return self.utterance


class UtteranceNBList(ASRHypothesis):
    """Provides a convenient interface for processing N-best lists of recognised utterances.

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
        sum = 0.0
        other_utt = -1
        for i in range(len(self.n_best)):
            sum += self.n_best[i][0]

            if self.n_best[i][1] == '__other__':
                if other_utt != -1:
                    raise UtteranceNBListException('Utterance list include multiple __other__ utterances: %s' % str(self.n_best))
                other_utt = i

        if other_utt == -1:
            if sum > utils.one():
                raise UtteranceNBListException('Sum of probabilities in the utterance list > 1.0: %8.6f' % sum)
            prob_other = 1.0 - sum
            self.n_best.append([prob_other, Utterance('__other__')])
        else:
            for i in range(len(self.n_best)):
                # __other__ utterance is already there, therefore just normalise
                self.n_best[i][0] /= sum

    def sort(self):
        self.n_best.sort(reverse=True)


class UtteranceNBListFeatures(Features):
    pass
#TODO: You can implement UtteranceConfusionNetwork and UtteranceConfusionNetworkFeatures to
# serve the similar purpose for DAILogRegClassifier as Utterance and UtteranceFeatures
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
        """Returns such hypotheses that will have lower probability. It assumes that the confusion network is sorted."""
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

        The result is a list of utterance hypotheses each with a with assigned probability.
        The list also include the utterance "__other__" for not having the correct utterance in the list.
        """
#        print "Confnet:"
#        print self
#        print

        open_hyp = []
        closed_hyp = {}

        # create index for the best hypothesis
        best_hyp  = tuple([0]*len(self.cn))
        best_prob = self.get_prob(best_hyp)
        open_hyp.append((best_prob, best_hyp))

        i = 0
        while open_hyp and i < n:
            i += 1

            current_prob, current_hyp_index = open_hyp.pop(0)

            if current_hyp_index not in closed_hyp:
                # process only those hypotheses which were not processed so far

                closed_hyp[current_hyp_index] = current_prob

#                print "current_prob, current_hyp_index:", current_prob, current_hyp_index

                for hyp_index in self.get_next_worse_candidates(current_hyp_index):
                    prob = self.get_prob(hyp_index)
                    open_hyp.append((prob, hyp_index))

                open_hyp.sort(reverse=True)

        nblist = UtteranceNBList()
        for idx in closed_hyp:
            nblist.add(closed_hyp[idx], self.get_hyp_index_utterence(idx))

#        print nblist
#        print

        nblist.merge()
        nblist.normalise()
        nblist.sort()

#        print nblist
#        print

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
