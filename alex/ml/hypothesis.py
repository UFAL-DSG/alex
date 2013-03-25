#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""This module collects classes representing the uncertainty about the actual
value of a base type instance.
"""

from alex.utils.exception import AlexException


class NBListException(AlexException):
    pass


class Hypothesis(object):
    """This is the base class for all forms of probabilistic hypotheses
    representations.

    """
    pass


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
        self.tolerance_over1 = 1e-5

    def __str__(self):
        return '\n'.join('{p:.3f} {obj}'.format(p=p, obj=obj)
                         for p, obj in self.n_best)

    def __len__(self):
        return len(self.n_best)

    def __getitem__(self, i):
        return self.n_best[i]

    def __iter__(self):
        for hyp in self.n_best:
            yield hyp

    def __cmp__(self, other):
        return (self.n_best >= other.n_best) - (other.n_best >= self.n_best)

    def get_best(self):
        """Returns the most probable value of the object."""
        return self.n_best[0][1]

    def add(self, probability, obj):
        """Finds the last hypothesis with a lower probability and inserts the
        new item before that one.  Optimised for adding objects from the
        highest probability ones to the lowest probability ones.

        """
        insert_idx = len(self.n_best)
        while insert_idx > 0:
            insert_idx -= 1
            if probability <= self.n_best[insert_idx][0]:
                insert_idx += 1
                break
        self.n_best.insert(insert_idx, [probability, obj])

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
        tot = float(sum(p for p, obj in self.n_best))
        for hyp_idx in xrange(len(self.n_best)):
            self.n_best[hyp_idx][0] /= tot
        return self

    def add_other(self, other):
        """The N-best list is extended to include the `other' object to
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
