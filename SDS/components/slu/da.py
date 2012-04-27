#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

from SDS.utils.string import split_by
from SDS.utils.exception import DialogueActItemException, DialogueActNBListException

def load_das(file_name, limit = None):
  f = open(file_name)

  semantics = defaultdict(list)
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
    sem = l[1].strip()

    semantics[key] = DialogueAct(sem)
  f.close()

  return semantics

def save_das(file_name, das):
  f = open(file_name, 'w+')

  for u in sorted(das):
    f.write(u)
    f.write(" => ")
    f.write(str(das[u])+'\n')

  f.close()

class DialogueActItem:
  def __init__(self, dialogue_act_type = None, name = None, value = None):
    self.dat = dialogue_act_type
    self.name = name
    self.value = value

  def __str__(self):
    r = self.dat+'('

    if self.name:
      r += self.name

    if self.value:
      r += '="'+self.value+'"'

    r += ')'
    return r

  def __eq__(self, dai):
    if dai.dat:
      if dai.dat != self.dat:
        return False

    if dai.name:
      if dai.name != self.name:
        return False

    if dai.value:
      if dai.value != self.value:
        return False

    return True

  def parse(self, dai):
    """Parse the dialogue act item in text format into a structured form.
    """
    try:
      i = dai.index('(')
    except ValueError:
      raise DialogueActItemException("Parsing error in: %s. Missing opening parenthesis." % dai)

    self.dat = dai[:i]

    # remove the parentheses
    dai_sv = dai[i+1:len(dai)-1]
    if not dai_sv:
      # there is no slot name or value
      return

    r = split_by(dai_sv, '=', '', '', '"')
    if len(r) == 1:
      # there is only slot name
      self.name = r[0]
    elif len(r) == 2:
      # there is slot name and value
      self.name = r[0]
      self.value = r[1][1:-1]
    else:
      raise DialogueActItemException("Parsing error in: %s: %s" % (dai, str(r)))

class DialogueAct:
  def __init__(self, da = None):
    self.dais = []

    if da:
      self.parse(da)

  def __str__(self):
    dais = []

    for dai in self.dais:
      dais.append(str(dai))

    return '&'.join(dais)

  def __contains__(self, dai):
    if isinstance(dai, DialogueActItem):
      return dai in self.dais
    elif isinstance(dai, string):
      l = [str(dai) for dai in self.dais]
      return dai in l

  def __lt__(self, other):
    return self.dais < other.dais
  def __le__(self, other):
    return self.dais <= other.dais
  def __eq__(self, other):
    return self.dais == other.dais
  def __ne__(self, other):
    return self.dais != other.dais
  def __gt__(self, other):
    return self.dais > other.dais
  def __ge__(self, other):
    return self.dais >= other.dais

  def __len__(self):
    return len(self.dais)

  def __getitem__(self, i):
    return self.dais[i]

  def __iter__(self):
    for i in self.dais:
      yield i

  def parse(self, da):
    """Parse the dialogue act in text format into the structured form.
    """
    dais = sorted(split_by(da, '&', '(', ')', '"'))

    for dai in dais:
      dai_parsed = DialogueActItem()
      dai_parsed.parse(dai)
      self.dais.append(dai_parsed)

class DialogueActNBList:
  """Provides N-best lists for dialogue acts.

  When updating the N-best list, one should do the follwing.

  1. add utterances or parse a confusion network
  2. merge
  3. normalise
  4. sort
  """

  def __init__(self):
    self.n_best = []

  def __len__(self):
    return len(self.n_best)

  def __getitem__(self, i):
    return self.n_best[i]

  def __iter__(self):
    for i in self.n_best:
      yield i

  def parse_dai_confusion_network(self, dai_cn, n = 10, expand_upto_total_prob_mass = 0.9):
    """Parses the input dialogue act item confusion network and generates N-best hypotheses.

    The result is a list of dialogue act hypotheses each with a with assigned probability.
    The list also include a dialogue act for not having the correct dialogue act in the list, e.g. null()
    """
    self.n_best = []

    #FIXME: expand the DAI confusion network

    self.merge()
    self.normalize()
    self.sort()

  def add(self, probability, da):
    self.n_best.append([probability, da])

  def merge(self):
    new_n_best = []

    if len(self.n_best) <= 1:
      return
    else:
      new_n_best[0]  = self.n_best[0]

      for i in range(1, len(self.n_best)):
        for j in range(len(new_n_best)):
          if new_n_best[j][1] == n_best[i][1]:
            # merge, add the probabilities
            new_n_best[j][1][0] += n_best[i][0]
            break
        else:
          new_n_best.append(n_best[i])

    self.n_best = new_n_best

  def normalize(self):
    sum = 0.0
    null_da = -1
    for i in range(len(n_best)):
      sum += n_best[i][0]

      if n_best[i][1] == 'null()':
        if null_da != -1:
          raise DialogueActNBListException('Dialogue act list include multiple null() dialogue acts: %s' %str(n_best))
        null_da = i

    if null_da == -1:
      if sum > 1.0:
        raise DialogueActNBListException('Sum of probabilities in dialogue act list > 1.5: %8.6f' % sum)
      prob_null = 1.0-sum
      n_best.append([prob_null, DialogueAct('null()')])

    else:
      for i in range(len(n_best)):
        # null act is already there, therefore just normalize
        n_best[i][0] /= sum

  def sort(self):
    self.n_best.sort(reverse=True)

class DialogueActConfusionNetwork:
  def __init__(self):
    pass

  def normalize(self):
    pass

