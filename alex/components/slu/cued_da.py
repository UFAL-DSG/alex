#!/usr/bin/env python
# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

from __future__ import unicode_literals

from alex.components.slu.da import DialogueAct, DialogueActItem
from alex.corpustools.wavaskey import load_wavaskey
from alex.utils.text import split_by


def load_das(das_fname, limit=None, encoding='UTF-8'):
    return load_wavaskey(das_fname, CUEDDialogueAct, limit, encoding)


class CUEDDialogueAct(DialogueAct):
    def parse(self, da_str):
        if self._dais:
            del self._dais[:]

        assert da_str[-1] == ')'
        left_par_idx = da_str.index('(')
        dat = da_str[:left_par_idx]
        dai_strs = split_by(da_str[left_par_idx + 1:-1], splitter=',',
                            quotes='"')
        self._dais.extend(DialogueActItem(dai='{dat}({slotval})'.format(
            dat=dat, slotval=dai_str)) for dai_str in dai_strs)
        self._dais_sorted = False
