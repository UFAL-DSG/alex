#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

"""This module collects classes representing the uncertainty about the actual
value of a base type instance.
"""

from __future__ import unicode_literals

from collections import namedtuple
from alex.ml.exceptions import NBListException
# from operator import mul


_HypWithEv = namedtuple('HypothesisWithEvidence', ['prob', 'fact', 'evidence'])


class Hypothesis(object):
    """This is the base class for all forms of probabilistic hypotheses
    representations.

    """
    @classmethod
    def from_fact(cls, fact):
        """\
        Constructs a deterministic hypothesis that asserts the given `fact'.
        """
        raise NotImplementedError("abstract method")


# TODO Make into a class template.
class NBList(Hypothesis):
    """This class represents the uncertainty using an n-best list.

    When updating an N-best list, one should do the following.

    1. add utterances or parse a confusion network
    2. merge and normalise, in either order

    """
    # NOTE the class invariant: self.n_best is always sorted from the most to
    # the least probable hypothesis.

    def __init__(self):
        self.n_best = []
        self.tolerance_over1 = 1e-2

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return '\n'.join('{p:.3f} {fact}'.format(p=prob, fact=unicode(fact))
                         for prob, fact in self.n_best)

    def __len__(self):
        return len(self.n_best)

    def __getitem__(self, i):
        return self.n_best[i]

    def __iter__(self):
        for hyp in self.n_best:
            yield hyp

    def __cmp__(self, other):
        return (self.n_best >= other.n_best) - (other.n_best >= self.n_best)

    @classmethod
    def from_fact(cls, fact):
        # Create a new object of our class.
        inst = cls()
        # Add the fact as the only hypothesis on the list.
        inst.add(1.0, fact)
        return inst

    def get_best(self):
        """Returns the most probable value of the object."""
        return self.n_best[0][1]

    def add(self, probability, fact):
        """\
        Finds the last hypothesis with a lower probability and inserts the
        new item before that one.  Optimised for adding objects from the
        highest probability ones to the lowest probability ones.

        """
        insert_idx = len(self.n_best)
        while insert_idx > 0:
            insert_idx -= 1
            if probability <= self.n_best[insert_idx][0]:
                insert_idx += 1
                break
        self.n_best.insert(insert_idx, [probability, fact])
        return self

    def merge(self):
        """Adds up probabilities for the same hypotheses. Returns self."""
        if len(self.n_best) <= 1:
            return
        else:
            new_n_best = self.n_best[:1]

            for cur_idx in xrange(1, len(self.n_best)):
                cur_hyp = self.n_best[cur_idx]
                for new_idx, new_hyp in enumerate(new_n_best):
                    if new_hyp[1] == cur_hyp[1]:
                        # Merge, add the probabilities.
                        new_hyp[0] += cur_hyp[0]
                        break
                else:
                    new_n_best.append(cur_hyp)

        self.n_best = sorted(new_n_best, reverse=True)
        return self

    def normalise(self):
        """Scales the list to sum to one."""
        tot = float(sum(p for p, fact in self.n_best))
        for hyp_idx in xrange(len(self.n_best)):
            self.n_best[hyp_idx][0] /= tot
        return self

    def add_other(self, other):
        """
        The N-best list is extended to include the ``other`` object to
        represent those object values that are not enumerated in the list.

        Returns self.

        """
        tot = 0.0
        other_idx = -1
        for hyp_idx in range(len(self.n_best)):
            tot += self.n_best[hyp_idx][0]

            if self.n_best[hyp_idx][1] == other:
                if other_idx != -1:
                    raise NBListException(
                        'N-best list includes multiple "other" objects: '
                        '{nb!s}'.format(nb=self.n_best))
                other_idx = hyp_idx

        # If `other' is absent,
        if other_idx == -1:
            if tot > 1.0:
                # Be tolerant.
                if tot <= 1. + self.tolerance_over1:
                    for hyp_idx in range(len(self.n_best)):
                        self.n_best[hyp_idx][0] /= tot
                    return self
                else:
                    raise NBListException(
                        'Sum of probabilities in n-best list > 1.0: '
                        '{s:8.6f}'.format(s=tot))
            # Append the `other' object.
            prob_other = 1.0 - tot
            self.n_best.append([prob_other, other])
        # If `other' was present,
        else:
            # Just normalise the probs.
            for hyp_idx in range(len(self.n_best)):
                self.n_best[hyp_idx][0] /= tot

        return self


# UNDER CONSTRUCTION
class ConfusionNetwork(Hypothesis):
    """\
    Confusion network.  In this representation, each fact breaks down into
    a sequence of elemntary acts.

    """
    def __init__(self):
        self.cn = list()

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return '\n'.join('{p:.30} {f}'.format(p=prob, f=fact)
                         for (prob, fact) in self.cn)

    def __len__(self):
        return len(self.cn)

    def __getitem__(self, i):
        return self.cn[i]

    def __contains__(self, fact):
        return self.get_marginal(fact) is not None

    def __iter__(self):
        for fact in self.cn:
            yield fact

    def add(self, probability, fact):
        """Append a fact to the confusion network."""
        self.cn.append([probability, fact])

    @classmethod
    def from_fact(cls, fact):
        """\
        Constructs a deterministic confusion network that asserts the given
        `fact'.  Note that `fact' has to be an iterable of elementary acts.

        """
        # Create a new object of our class.
        inst = cls()
        # Add the fact as the only hypothesis to the network.
        inst.cn.extend([1., efact] for efact in fact)
        return inst

#     def add_merge(self, probability, fact):
#         """Add the probability mass of the passed dialogue act item to an
#         existing dialogue act item or adds a new dialogue act item.
#
#         """
#
#         for i in range(len(self.cn)):
#             if fact == self.cn[i][1]:
#                 # I found a matching DAI
#                 self.cn[i][0] += probability
#                 return
#         # if not found you should add it
#         self.add(probability, fact)
#
#     def get_best_da(self):
#         """Return the best dialogue act (one with the highest probability)."""
#         da = DialogueAct()
#         for prob, fact in self.cn:
#             if prob > 0.5:
#                 da.append(fact)
#
#         if len(da) == 0:
#             da.append(DialogueActItem('null'))
#
#         return da
#
#     def get_best_nonnull_da(self):
#         """Return the best dialogue act (with the highest probability)."""
#
#         res = self.get_best_da()
#
#         if res[0].dat == "null":
#             da = DialogueAct()
#             for prob, fact in self.cn:
#                 if fact.name is not None and len(fact.name) > 0:
#                     da.append(fact)
#                     break
#
#             if len(da) == 0:
#                 da.append(DialogueActItem('null'))
#
#             res = da
#
#         return res
#
#     def get_best_da_hyp(self, use_log=False, threshold=.5):
#         """Return the best dialogue act hypothesis.
#
#         Arguments:
#             use_log: whether to express probabilities on the log-scale
#                      (otherwise, they vanish easily in a moderately long
#                      confnet)
#             threshold: threshold on probabilities -- items with probability
#                        exceeding the threshold will be present in the output
#                        (default: 0.5)
#
#         """
#         da = DialogueAct()
#         if use_log:
#             from math import log
#             logprob = 0.
#         else:
#             prob = 1.0
#         for edge_p, fact in self.cn:
#             if edge_p > threshold:
#                 da.append(fact)
#                 # multiply with probability of presence of a dialogue act
#                 if use_log:
#                     logprob += log(edge_p)
#                 else:
#                     prob *= edge_p
#             else:
#                 # multiply with probability of exclusion of the dialogue act
#                 if use_log:
#                     logprob += log(1. - edge_p)
#                 else:
#                     prob *= (1. - edge_p)
#
#         if len(da) == 0:
#             da.append(DialogueActItem('null'))
#
#         # (FIXME) DialogueActHyp still thinks it uses linear-scale
#         # probabilities.
#         return DialogueActHyp(logprob if use_log else prob, da)
#
#     def get_prob(self, hyp_index):
#         """Return a probability of the given hypothesis."""
#
#         prob = 1.0
#         for i, (p, fact) in zip(hyp_index, self.cn):
#             if i == 0:
#                 prob *= p
#             else:
#                 prob *= (1 - p)
#
#         return prob
#
#     def get_marginal(self, fact):
#         for prob, my_dai in self.cn:
#             if my_dai == fact:
#                 return prob
#         return None
#
#     def get_next_worse_candidates(self, hyp_index):
#         """Returns such hypotheses that will have lower probability. It assumes
#         that the confusion network is sorted.
#
#         """
#         worse_hyp = []
#
#         for i in range(len(hyp_index)):
#             wh = list(hyp_index)
#             wh[i] += 1
#             if wh[i] >= 2:
#                 # this generate inadmissible word hypothesis
#                 # because there are only two alternatives - the DAI and the
#                 # null() dialogue act
#                 continue
#
#             worse_hyp.append(tuple(wh))
#
#         return worse_hyp
#
#     def get_hyp_index_dialogue_act(self, hyp_index):
#         da = DialogueAct()
#         for i, (p, fact) in zip(hyp_index, self.cn):
#             if i == 0:
#                 da.append(fact)
#
#         if len(da) == 0:
#             da.append(DialogueActItem('null'))
#
#         return da
#
#     def get_da_nblist_naive(self, n=10, expand_upto_total_prob_mass=0.9):
#         """For each CN item creates a NB list item."""
#
#         res = []
#         for cn_item in self.cn:
#             nda = DialogueAct()
#             print type(cn_item)
#             print cn_item
#             nda.append(cn_item[1])
#
#             res += [(cn_item[0], nda)]
#
#         res.sort(reverse=True)
#         return res
#
#     def get_da_nblist(self, n=10, expand_upto_total_prob_mass=0.9):
#         """Parses the input dialogue act item confusion network and generates
#         N-best hypotheses.
#
#         The result is a list of dialogue act hypotheses each with a with
#         assigned probability.  The list also include a dialogue act for not
#         having the correct dialogue act in the list - other().
#
#         FIXME: I should stop the expansion when expand_upto_total_prob_mass is
#         reached.
#
#         """
#
#         # print "Confnet:"
#         # print self
#         # print
#
#         open_hyp = []
#         closed_hyp = {}
#
#         # create index for the best hypothesis
#         best_hyp = tuple([0] * len(self.cn))
#         best_prob = self.get_prob(best_hyp)
#         open_hyp.append((best_prob, best_hyp))
#
#         i = 0
#         while open_hyp and i < n:
#             i += 1
#
#             current_prob, current_hyp_index = open_hyp.pop(0)
#
#             if current_hyp_index not in closed_hyp:
#                 # process only those hypotheses which were not processed so far
#
#                 closed_hyp[current_hyp_index] = current_prob
#
#                 # print "current_prob, current_hyp_index:", current_prob,
#                 # current_hyp_index
#
#                 for hyp_index in \
#                         self.get_next_worse_candidates(current_hyp_index):
#                     prob = self.get_prob(hyp_index)
#                     open_hyp.append((prob, hyp_index))
#
#                 open_hyp.sort(reverse=True)
#
#         nblist = DialogueActNBList()
#         for idx in closed_hyp:
#             nblist.add(closed_hyp[idx], self.get_hyp_index_dialogue_act(idx))
#
#         # print nblist
#         # print
#
#         nblist.merge()
#         nblist.normalise()
#         nblist.sort()
#
#         # print nblist
#         # print
#
#         return nblist
#
#     def merge(self):
#         """Adds up probabilities for the same hypotheses.
#
#         This method has actually nothing to do. The alternatives for each
#         dialog act item (DAI) are just two: it is there, or it isn't. The data
#         model captures only the presence of DAI-s, and hence no other
#         hypothesis' probabilities need to be added.
#
#         XXX As yet, though, we know that different values for the same slot are
#         contradictory (and in general, the set of contradicting attr-value
#         pairs could be larger).  We should therefore consider them alternatives
#         to each other.
#
#         """
#         pass
#
#     def prune(self, prune_prob=0.01):
#         """Prune all low probability dialogue act items."""
#         pruned_cn = []
#         for prob, fact in self.cn:
#             if prob < prune_prob:
#                 # prune out
#                 continue
#
#             pruned_cn.append([prob, fact])
#
#         self.cn = pruned_cn
#
#     def normalise(self):
#         """Makes sure that all probabilities add up to one. They should
#         implicitly sum to one: p + (1-p) == 1.0
#
#         """
#
#         for p,  fact in self.cn:
#             if p >= 1.0:
#                 raise DialogueActConfusionNetworkException(
#                     ("The probability of the {fact!s} dialogue act item is " + \
#                      "larger than 1.0, namely {p:0.3f}").format(fact=fact, p=p))
#
#     def sort(self):
#         self.cn.sort(reverse=True)
#
#
# class TypedConfusionNetwork(Hypothesis):
#     """Typed confusion network."""
#     # Implemented using this structure for self.cn:
#     # [(type_1, [hyp1, hyp2, ...]),
#     #  (type_2, [hyp1, hyp2, ...]),
#     #  ...]
#     #  where hypn is a _HypWithEv.
#     # TODO Define a corresponding namedtuple for HypWithEvidence.
#     def __init__(self):
#         self.cn = list()
#
#     def __str__(self):
#         ret = ('  {t}=({alts})'.format(
#                t=type_,
#                alts=(' | '.join('{h.p:.3f}:{h.f} ({h.e})'.format(h=hwe)
#                      for hwe in alts))
#                for (type_, alts) in self.cn)
#         return '\n'.join(ret)
#
#     def __len__(self):
#         return sum(map(len, self.cn))
#
#     def __contains__(self, fact):
#         return any((fact in alts) for (type_, alts) in self.cn)
#
#     def _gen_null(self):
#         """A method to be overriden in inheriting classes."""
#         return list()
#
#     def _join_items(self, items):
#         """A method to be overriden in inheriting classes."""
#         return items
#
#     def add(self, probability, type_, fact, evidence=1.):
#         new_item = (probability, fact, evidence)
#         for my_type, alts in self.cn:
#             if my_type == type_:
#                 ins_idx = len(alts)
#                 for idx, alt in enumerate(alts):
#                     cur_prob, cur_fact, cur_ev = alts[idx]
#                     if cur_fact == fact:
#                         new_prob = ((cur_ev * cur_prob + evidence * prob)
#                                     / float(cur_ev + evidence))
#                         alts[idx][0] = new_prob
#                         alts[idx][2] += evidence
#                         return self
#                     if alt[0] <= probability:
#                         ins_idx = idx
#                 alts.insert(ins_idx, new_item)
#         else:
#             self.cn.append((type_, [new_item]))
#         return self
#
#     def get_best(self):
#         return self._join_items(
#             (type_, alts[0][1]) for (type_, alts) in self.cn
#              if alts[0][0] > .5)
#
#     def get_best_nonempty(self):
#         best = [(type_, alts[0][1]) for (type_, alts) in self.cn
#                 if alts[0][0] > .5]
#         if best:
#             return self._join_items(best)
#         else:
#             max_prob = max(alts[0][0] for (type_, alts) in self.cn)
#             max_hyps = [(type_, alts[0][1]) for (type_, alts) in self.cn
#                         if alts[0][0] == max_prob]
#             return self._join_items((max_hyps[0], ))
#
#     def get_best_hyp(self, use_log=True):
#         probs = [alts[0][0] for (type_, alts) in self.cn if alts[0][0] > .5]
#         items = [(type_, alts[0][1]) for (type_, alts) in self.cn
#                  if alts[0][0] > .5]
#         if use_log:
#             from math import log
#             prob = sum(map(log, probs))
#         else:
#             prob = reduce(mul, probs, 1.)
#         return (prob, self._join_items(items))
#
