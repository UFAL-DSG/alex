#!/usr/bin/env python
# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

from __future__ import unicode_literals

from alex.components.slu.da import DialogueAct, DialogueActItem
from alex.components.slu.exceptions import CuedDialogueActError
from alex.corpustools.wavaskey import load_wavaskey
from alex.utils.text import split_by, split_by_comma


def load_das(das_fname, limit=None, encoding='UTF-8'):
    return load_wavaskey(das_fname, CUEDDialogueAct, limit, encoding)


class CUEDSlot(object):
    def __init__(self, slot_str):
        self.parse(slot_str)

    def __unicode__(self):
        equals_sign = '!=' if self.negated else ('=' if self.negated is False
                                                 else '')
        equals_val = ('{eq}"{val}"'.format(eq=equals_sign, val=self.value)
                      if self.value
                      else '')
        return self.name + equals_val

    def parse(self, slot_str):
        # Try to find the not-equals relation.
        eq_idx = slot_str.find('!=')
        if eq_idx == -1:
            # Try to find the equals relation.
            eq_idx = slot_str.find('=')
            if eq_idx == -1:
                # If no equality is included, value is empty.
                self.name = slot_str
                self.negated = None
                self.value = ''
                return
            else:
                self.negated = False
                eq_eidx = eq_idx + 1
        else:
            self.negated = True
            eq_eidx = eq_idx + 2

        self.name = slot_str[:eq_idx]
        self.value = slot_str[eq_eidx:].strip('"')

        if self.value == 'value':
            raise ValueError('FIXME: Ignore slots for which no values were '
                             'found in the database.')


class CUEDDialogueAct(DialogueAct):
    """CUED-style dialogue act"""

    def parse(self, da_str):
        # Get the dialogue act type.
        first_par_idx = da_str.index("(")
        self.dat = da_str[:first_par_idx]

        if len(split_by_comma(da_str)) != 1:
            raise ValueError('Too many (or none -- too few) DAs in CUED DA '
                             'representation.')

        slots_str = da_str[first_par_idx:].lower()[1:-1]
        if not slots_str:
            # no slots to process
            self._dais = list()
        else:
            # split slots_str
            slotstr_list = split_by(slots_str, splitter=',', quotes='"')

            slots = list()
            for slot_str in slotstr_list:
                try:
                    slots.append(CUEDSlot(slot_str))
                except ValueError:
                    # Skip slots we cannot parse.
                    pass

            if self.dat == 'inform':
                for slot in slots:
                    if slot.negated:
                        self._dais.append(DialogueActItem(
                            'deny', slot.name, slot.value))
                    else:
                        self._dais.append(DialogueActItem(
                            'inform', slot.name, slot.value))

            elif self.dat == 'request':
                for slot in slots:
                    if slot.value:
                        if slot.negated:
                            self._dais.append(DialogueActItem(
                                'deny', slot.name, slot.value))
                        else:
                            self._dais.append(DialogueActItem(
                                'inform', slot.name, slot.value))
                    else:
                        self._dais.append(DialogueActItem(
                            'request', slot.name, slot.value))

            elif self.dat == 'confirm':
                for slot in slots:
                    if slot.name == 'name':
                        self._dais.append(DialogueActItem(
                            'inform', slot.name, slot.value))
                    else:
                        self._dais.append(DialogueActItem(
                            'confirm', slot.name, slot.value))

            elif self.dat == 'select':
                # XXX We cannot represent DAIS with multiple slots as of now.
                # Therefore, the select DAT is split into two DAIs here.
                self._dais.append(DialogueActItem(
                    'select', slots[0].name, slots[0].value))
                self._dais.append(DialogueActItem(
                    'select', slots[1].name, slots[1].value))

            elif self.dat in ('silence', 'thankyou', 'ack', 'bye', 'hangup',
                              'repeat', 'help', 'restart', 'null'):
                self._dais.append(DialogueActItem(self.dat))

            elif self.dat in ('hello', 'affirm', 'negate', 'reqalts',
                              'reqmore'):
                self._dais.append(DialogueActItem(self.dat))
                for slot in self._dais:
                    if slot.negated:
                        self._dais.append(DialogueActItem(
                            'deny', slot.name, slot.value))
                    else:
                        self._dais.append(DialogueActItem(
                            'inform', slot.name, slot.value))

            elif self.dat == 'deny':
                self._dais.append(DialogueActItem(
                    'deny', slots[0].name, slots[0].value))
                for slot in slots[1:]:
                    if slot.negated:
                        self._dais.append(DialogueActItem(
                            'deny', slot.name, slot.value))
                    else:
                        self._dais.append(DialogueActItem(
                            'inform', slot.name, slot.value))

            else:
                raise CuedDialogueActError(
                    'Unknown CUED DA type "{dat}" when parsing "{da_str}".'
                    .format(dat=self.dat, da_str=da_str))

        self._dais_sorted = False
