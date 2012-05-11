#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import collections
import re

from SDS.utils.string import split_by_comma, split_by

"""
This program process CUED semantic annotations and converts them into UFAL semantic format.
A by product of the processing is a category database which contains a list of slots, their values, and
the alternative lexical representations. Currently the alternative value lexical representation are
trivially equal to the observed slot values.

This automatically generated category database must be manually checked and corrected for
errors observed in the data.

The database also contains a list of dialogue act types observed in the data.

It scans for all 'cued_data/*.sem' files and process them.


NOTE: This script can be used as a packege/library anytime someone needs to convert CUED dialogue acts into UFAL dialogue acts.

"""

idir = './cued_data'
odir = './data'

class CUEDSlot:
  def __init__(self, slot):
    self.slot = slot

    return

  def __str__(self):
    s = self.name
    if self.value:
      s += self.equal + '"' + self.value + '"'

    return s

  def parse(self):
    i = self.slot.find('!=')
    if i == -1:
      i = self.slot.find('=')
      if i == -1:
        self.name = self.slot
        self.equal = ''
        self.value = ''
        return
      else:
        self.equal = '='
    else:
      self.equal = '!='

    self.name = self.slot[:i]

    self.value = self.slot[i:]
    self.value = self.value.replace('!', '')
    self.value = self.value.replace('=', '')
    self.value = self.value.replace('"', '')

    if self.value == 'value':
      raise ValueError('FIX: Ignore slots for which no values were found in the database.')

    return


class CUEDDialogueAct:
  def __init__(self, text, da, database = None, dictionary = None):
    self.text = text
    self.cuedDA = da
    self.db = database

    return

  def __str__(self):
    s = self.dialogue_act_type
    try:
      s += '\n' + '\n'.join(self.slots)
    except:
      pass

    return s

  def get_slots_and_values(self):
    slots = collections.defaultdict(set)

    for slt in self.slots:
      slots[slt.name].add(slt.value)

    return slots

  def get_cued_da(self):
    s = self.dialogue_act_type
    s += '('
    try:
      s += ','.join([str(slt) for slt in self.slots])
    except:
      pass
    s += ')'
    return s

  def get_ufal_da(self):
    s = []

    if self.dialogue_act_type == 'inform':
      for slt in self.slots:
        if slt.equal == '=':
          s.append('inform('+str(slt)+')')
        else:
          s.append('deny('+slt.name+'="'+slt.value+'")')

    if self.dialogue_act_type == 'request':
      for slt in self.slots:
        if slt.value:
          if slt.equal == '=':
            s.append('inform('+str(slt)+')')
          else:
            s.append('deny('+slt.name+'="'+slt.value+'")')
        else:
          s.append('request('+slt.name+')')

    if self.dialogue_act_type == 'confirm':
      for slt in self.slots:
        if slt.name == 'name':
          s.append('inform('+str(slt)+')')
        else:
          s.append('confirm('+str(slt)+')')

    if self.dialogue_act_type == 'select':
      ss  = 'select('
      ss += str(self.slots[0])+','+str(self.slots[1])
      ss += ')'

      s.append(ss)

    if self.dialogue_act_type in ['silence','thankyou','ack','bye','hangup','repeat','help','restart','null']:
      s.append(self.dialogue_act_type+'()')

    if self.dialogue_act_type in ['hello', 'affirm', 'negate','reqalts', 'reqmore']:
      s.append(self.dialogue_act_type+'()')
      for slt in self.slots:
        if slt.equal == '=':
          s.append('inform('+str(slt)+')')
        else:
          s.append('deny('+slt.name+'="'+slt.value+'")')

    if self.dialogue_act_type == 'deny':
      i = 1
      for slt in self.slots:
        if i == 1:
          s.append('deny('+slt.name+'="'+slt.value+'")')
        else:
          if slt.equal == '=':
            s.append('inform('+str(slt)+')')
          else:
            s.append('deny('+slt.name+'="'+slt.value+'")')

        i += 1

    # normalise data
    if "thank you" in self.text and "thankyou()" not in s:
      s.append("thankyou()")
    if "thanks" in self.text and "thankyou()" not in s:
      s.append("thankyou()")
    if "thank" in self.text and "thankyou()" not in s:
      s.append("thankyou()")
    if "hello" in self.text and "hello()" not in s:
        s.append("hello()")
    if " hi " in self.text and "hello()" not in s:
      s.append("hello()")
    if "hi " in self.text and "hello()" not in s:
      s.append("hello()")
    if " looking " in self.text and 'inform(task="find")' not in s:
      s.append('inform(task="find")')

    s = '&'.join(sorted(s))

    if not s:
      print '#'+'='*120
      print '#', self.text
      print '#', self.cuedDA

    return s

  def parse(self):
    cuedDA = self.cuedDA

    numOfDAs = len(split_by_comma(cuedDA))
    if numOfDAs > 1:
      raise ValueError('Too many DAs in input text.')

    # get the dialogue act type
    i = cuedDA.index("(")
    dialogue_act_type = cuedDA[:i]

    slots = cuedDA[i:].lower()
    slots = slots.replace('(', '')
    slots = slots.replace(')', '')

    slts = []
    if slots == '':
      # no slots to process
      slots = []
    else:
      # split slots
      slots = split_by_comma(slots)
      for slt in slots:
        try:
          s = CUEDSlot(slt)
          s.parse()
          slts.append(s)
        except ValueError:
          # check for invalid slot items
          pass

    self.dialogue_act_type = dialogue_act_type
    self.slots = slts

    return

if __name__ == '__main__':
  verbose = False
  sem_files = glob.glob(os.path.join(idir,'*.sem'))

  slots = collections.defaultdict(set)
  ufal_da_list = collections.defaultdict(list)

  for fn in sem_files:
    print 'Processing file: ' + fn
    bnfn = os.path.basename(fn)

    f = open(fn, 'r')

    da_clustered = collections.defaultdict(set)
    for line in f:
      line = line.strip()

      if verbose:
        print '-'*120
        print 'Input:   ' + line

      text, cued_da = line.split('<=>')
      text = text.strip()
      cued_da = cued_da.strip()


      if verbose:
        print 'Text:    ' + text
        print 'DA:      ' + cued_da
        print

      da = CUEDDialogueAct(text,cued_da)
      da.parse()

      if verbose:
        print 'cued_da:  ' + da.get_cued_da()
        print 'ufal_da:  ' + da.get_ufal_da()

      ufal_da = da.get_ufal_da()

      if ufal_da:
        ufal_da_list[bnfn].append((da.text, da.get_ufal_da()))
        da_clustered[da.get_ufal_da()].add(da.text)

        slts = da.get_slots_and_values()
        for slt in slts:
          slots[slt].update(slts[slt])

    fo = open(os.path.join(odir, os.path.basename(fn).replace('.sem', '.grp')), 'w+')
    for key in sorted(da_clustered):
      fo.write(key)
      fo.write(' <=> ')
      fo.write(str(sorted(list(da_clustered[key])))+'\n')
    fo.close()

    dai_unique = set()
    for da in sorted(da_clustered):
      dais = split_by(da, '&', '(', ')', '"')
      for dai in dais:
        dai_unique.add(dai)

    fo = open(os.path.join(odir, os.path.basename(fn).replace('.sem', '.grp.dais')), 'w+')
    for dai in sorted(dai_unique):
      fo.write(dai)
      fo.write('\n')
    fo.close()


    da_reclustered = collections.defaultdict(set)
    for key in da_clustered:
      sem_reduced = re.sub(r'([a-z_0-9]+)(="[a-zA-Z0-9_\'! ]+")', r'\1', key)
      da_reclustered[sem_reduced].update(da_clustered[key])

    fo = open(os.path.join(odir, os.path.basename(fn).replace('.sem', '.grp.reduced')), 'w+')
    for key in sorted(da_reclustered):
      fo.write(key)
      fo.write(' <=> ')
      fo.write(str(sorted(list(da_reclustered[key])))+'\n')
    fo.close()

    dai_unique = set()
    for da in sorted(da_reclustered):
      dais = split_by(da, '&', '(', ')', '"')
      for dai in dais:
        dai_unique.add(dai)

    fo = open(os.path.join(odir, os.path.basename(fn).replace('.sem', '.grp.reduced.dais')), 'w+')
    for dai in sorted(dai_unique):
      fo.write(dai)
      fo.write('\n')
    fo.close()

  i = 0
  for fn in ufal_da_list:
    if 'asr' in fn:
      ext = '.asr'
    else:
      ext = '.trn'
    fo_trn = open(os.path.join(odir, fn.replace('.sem', '.trn')), 'w+')
    fo_sem = open(os.path.join(odir, fn), 'w+')

    for text, da in ufal_da_list[fn]:
      wav_name = ("%06d" % i) + '.wav'
      fo_trn.write(wav_name + ' => ' + text+'\n')
      fo_sem.write(wav_name + ' => ' + da+'\n')

      i += 1

    fo_trn.close()
    fo_sem.close()


  s = 'database = {'
  for slt in sorted(slots):
    if not slt:
      continue
    s += '\n'
    s += '  "'+slt+'": {'
    s += '\n'

    for vlu in sorted(slots[slt]):
      if not vlu:
        continue
      s += '    "'+vlu+'": [' + '"'+vlu+'",],'
      s += '\n'

    s += '  },'
    s += '\n'
  s += '}'
  s += '\n'

  fo = open(os.path.join(odir,'auto_database.py'), 'w+')
  fo.write(s)
  fo.close()

