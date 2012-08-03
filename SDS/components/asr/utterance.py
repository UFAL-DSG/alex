#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from collections import defaultdict

def load_utterances(file_name, limit = None):
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

class ASRHypotheses:
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
    if other == None:
      return False

    if isinstance(other, Utterance):
      return self.utterance == other.utterance
    elif isinstance(other, str):
      return self.utterance == Utterance(other)
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
        if self.utterance[i+j] != s[j]:
          raise IndexError
      except IndexError:
        raise ValueError('Missing %s in %s' % (str(s), str(self.utterance)))

    return i

  def replace(self, s, r):
    try:
      i = self.index(s)
    except ValueError:
      return

    self.utterance[i:i+len(s)] = r

class UtteranceFeatures(Features):
  def __init__(self, type = 'ngram', size = 3, utterance = None):
    self.type = type
    self.size = size
    self.features = defaultdict(float)

    if utterance != None:
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
      for k in range(1, self.size+1):
        for i in range(len(u)):
          if i+k > len(u):
            break

          self.features[tuple(u[i:i+k])] += 1.0

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

class UtteranceNBList(ASRHypotheses):
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
    if self.n_best[0][1] == '__other__':
      return self.n_best[1][1]

    return self.n_best[0][1]

  def parse_utterance_confusion_network(self, utterance_cn, n = 10, expand_upto_total_prob_mass = 0.9):
    """Parses the input utterance confusion network and generates N-best hypotheses.

    The result is a list of utterance hypotheses each with a with assigned probability.
    The list also include the utterance "__other__" for not having the correct utterance in the list.
    """
    self.n_best = []

    #TODO: expand the utterance confusion network

    self.merge()
    self.normalise()
    self.sort()

  def add(self, probability, utterance):
    self.n_best.append([probability, utterance])

  def merge(self):
    """Adds up probabilities for the same hypotheses.
    """
    new_n_best = []

    if len(self.n_best) <= 1:
      return
    else:
      new_n_best[0]  = self.n_best[0]

      for i in range(1, len(self.n_best)):
        for j in range(len(new_n_best)):
          if new_n_best[j][1] == self.n_best[i][1]:
            # merge, add the probabilities
            new_n_best[j][1][0] += self.n_best[i][0]
            break
        else:
          new_n_best.append(self.n_best[i])

    self.n_best = new_n_best

  def normalise(self):
    sum = 0.0
    other_utt = -1
    for i in range(len(self.n_best)):
      sum += self.n_best[i][0]

      if self.n_best[i][1] == '__other__':
        if other_utt != -1:
          raise UtteranceNBListException('Utterance list include multiple __other__ utterances: %s' %str(n_best))
        other_utt = i

    if other_utt == -1:
      if sum > 1.0:
        raise UtteranceNBListException('Sum of probabilities in the utterance list > 1.0: %8.6f' % sum)
      prob_other = 1.0-sum
      self.n_best.append([prob_other, '__other__'])
    else:
      for i in range(len(n_best)):
        # __other__ utterance is already there, therefore just normalize
        self.n_best[i][0] /= sum

  def sort(self):
    self.n_best.sort(reverse=True)

class UtteranceNBListFeatures(Features):
  pass
#TODO: You can implement UtteranceConfusionNetwork and UtteranceConfusionNetworkFeatures to
# serve the similar purpose for DAILogRegClassifier as Utterance and UtteranceFeatures
#
# - then the code will be more general

class UtteranceConfusionNetwork(ASRHypotheses):

  def __init__(self):
    self.cn = []
    pass

  def __str__(self):
    s = []
    for alts in self.cn:
      ss = []
      for w in alts:
        ss.append("(%.3f : %s) " % (w[0], w[1] if w[1] else '-'))
      s.append(' '.join(ss))

    return '\n'.join(s)

  def add(self, words):
    """Adds next word with its alternatives"""

    self.cn.append(words)

  def get_best_utterance(self):
    utterance = []
    for alts in self.cn:
      utterance.append(alts[0][1])

    return ' '.join(utterance)

  def get_best_hyp(self):
    utterance = []
    prob = 1.0
    for alts in self.cn:
      utterance.append(alts[0][1])
      prob *= alt[0][0]

    return (prob, Utterance(' '.join(utterance)))

  def merge(self):
    """Adds up probabilities for the same hypotheses.

    TODO: not implemented yet
    """
    pass

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
