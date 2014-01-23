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
        return u'\n'.join('{p:.3f} {fact}'.format(p=prob, fact=unicode(fact)) for prob, fact in self.n_best)

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
    a sequence of elementary acts.

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
