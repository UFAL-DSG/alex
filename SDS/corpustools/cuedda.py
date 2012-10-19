#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections

import __init__

from SDS.utils.string import split_by_comma


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
            raise ValueError('FIXME: Ignore slots for which no values were found in the database.')

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

        if "good bye" in self.text and "bye()" not in s:
            s.append("bye()")
        if "goodbye" in self.text and "bye()" not in s:
            s.append("bye()")

        if "no thank" in self.text and "negate()" not in s:
            s.append('negate()')
        if "no good" in self.text and "negate()" not in s:
            s.append('negate()')
        if "no i " in self.text and "negate()" not in s:
            s.append('negate()')
        if "no i'm " in self.text and "negate()" not in s:
            s.append('negate()')

        if "hello" in self.text and "hello()" not in s:
            s.append("hello()")
        if " hi " in self.text and "hello()" not in s:
            s.append("hello()")
        if "hi " in self.text and "hello()" not in s:
            s.append("hello()")
        if " looking " in self.text and 'inform(task="find")' not in s:
            s.append('inform(task="find")')

        if "not" == self.text:
            s = ['negate()', ]
        if "it does not matter" == self.text:
            s = ['inform(="dontcare")', ]
        if "type of food" == self.text:
            s = ['request(food)', ]
        if "addenbrooke's" == self.text:
            s = ['request(name="addenbrookes")', ]

        s = '&'.join(sorted(s))

        if not s:
            print '# CUEDDialogueAct.get_ufal_da()'
            print '#'+'='*120
            print '#', self.text
            print '#', self.cuedDA
            print '#', 'null()'
            print '#'+'.'*120

        if not s:
            s = 'null()'

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
