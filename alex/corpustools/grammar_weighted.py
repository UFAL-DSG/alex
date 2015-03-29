#!/usr/bin/env python

from __future__ import absolute_import, unicode_literals

import codecs
import random


def as_terminal(rule):
    return T(rule) if isinstance(rule, basestring) else rule


def as_weight_tuple(rule, def_weight=1.0):
    return rule if isinstance(rule, tuple) else (rule, def_weight)


def clamp_01(number):
    return min(max(number, 0.0), 1.0)


def counter_weight(rules):
    explicit_weigh_rules = [r for r in rules if isinstance(r, tuple)]
    explicit_weights = [w for _, w in explicit_weigh_rules]
    if len(rules) - len(explicit_weigh_rules) > 0:
        return clamp_01(1.0 - sum(explicit_weights)) / (len(rules) - len(explicit_weigh_rules))
    else:
        return 1.0


class Rule(object):
    def __init__(self):
        pass


class Terminal(Rule):

    def __init__(self, string):
        super(Terminal, self).__init__()
        self.string = string

    def __str__(self):
        return self.string

    def sample(self):
        return self.string


class Option(Rule):

    def __init__(self, rule, prob = 0.5):
        super(Option, self).__init__()

        self.prob = prob
        self.option = as_terminal(rule)

    def __str__(self):
        return "%.3f %s" %(self.prob, str(self.option))

    def sample(self):
        if random.random() < self.prob:
            return self.option.sample()
        else:
            return ''


class Alternative(Rule):
    def __init__(self, *rules):
        super(Alternative, self).__init__()
        cw = counter_weight(rules)
        weighted_alts = [as_weight_tuple(r, cw) for r in rules]
        self.alternatives = [(as_terminal(t), w) for t, w in weighted_alts]
        self.weight_sum = sum(w for _, w in self.alternatives)

    def __str__(self):
        return str(["%.3f" % w for _, w in self.alternatives])

    def sample(self):
        r = random.uniform(0, self.weight_sum)
        cumsum = 0
        for a, w in self.alternatives:
          if cumsum + w > r:
             return a.sample()
          cumsum += w
        assert False


class UniformAlternative(Rule):
    def __init__(self, *rules):
        super(UniformAlternative, self).__init__()
        self.alternatives = [as_terminal(t) for t in rules]
        self.length = len(self.alternatives)

    def __str__(self):
        return str(self.length)

    def sample(self):
        return random.choice(self.alternatives).sample()

    def load(self, fn):
        """ Load alternative terminal strings from a file.

        :param fn: a file name
        """
        self.alternatives = []
        with codecs.open(fn, 'r', 'utf8') as f:
            for l in f:
                l = l.strip()
                if l:
                    self.alternatives.append(T(l))

        self.alternatives = list(set(self.alternatives))
        self.length = len(self.alternatives)
        return self


class Sequence(Rule):
    def __init__(self, *rules):
        super(Sequence, self).__init__()

        self.sequence = [as_terminal(a) for a in rules]

    def __str__(self):
        return str(len(self.sequence))

    def sample(self):
        if self.sequence:
            r = []
            for s in self.sequence:
                r.append(s.sample())

            return ' '.join(r)
        else:
            ''


class T(Terminal):
    pass


class O(Option):
    pass


class A(Alternative):
    pass

class UA(UniformAlternative):
    pass


class S(Sequence):
    pass


def remove_spaces(utterance):
    return utterance.replace('  ', ' ').replace('  ', ' ').strip().lower()


class GrammarGen(object):
    def __init__(self, root):
        self.root = root

    def sample(self, n):
        """Sampling of n sentences.
        """
        for i in xrange(n):
            yield remove_spaces(self.root.sample())

    def sample_uniq(self, n):
        """Unique sampling of n sentences.
        """
        seen = set()

        for s in self.sample(n*100):
            if len(seen) > n:
                return

            h = hash(s)
            if h not in seen:
                seen.add(h)
                yield s




