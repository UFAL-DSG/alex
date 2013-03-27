#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class VocalizePrepos(Block):
    """\
    This block replaces the forms of prepositions 'k', 'v', 'z', 's'
    with their vocalized variants 'ke'/'ku', 've', 'ze', 'se' according
    to the following word.
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_atree(self, aroot):
        """\
        Find and vocalize prepositions according to their context.
        """
        anodes = aroot.get_descendants(ordered=True)
        for anode, anext in zip(anodes[:-1], anodes[1:]):
            if anode.morphcat_pos == 'R' and \
                    anode.lemma in {'k', 'v', 'z', 's'}:
                anode.form = self.vocalize(anode.lemma, anext.form.lower())

    def vocalize(self, prep, follow):
        """\
        Given a preposition lemma and the form of the word following it,
        return the appropriate form (base or vocalized).
        """
        if prep == 'k' and re.match('^(prospěch|příklad)', follow):
            return 'ku'
        if prep == 'k' and re.match('^(k|g|sp|sn|zv|zm|sc|zl|sl|sk|zp|zk|šk|' +
                                    'zd|zt|zb|zr|sv|mn|vš|vs|ct|sj|dv|zř|zh|' +
                                    'vč|šp|lá|šť|mř|zc|št|vk|sta|vzn|stu|' +
                                    'vzd|smí|stě|dnu|vzo|sti|sty|sro|dnů|' +
                                    'sdr|sbl|sbí|čty|zná)', follow):
            return 'ke'
        if prep == 'v' and re.match('^(v|f|st|sp|čt|sk|sv|kt|fr|fi|sl|sn|fu|' +
                                    'zl|fo|šv|zn|zp|šk|wa|ii|hř|dv|zd|sb|šp|' +
                                    'sh|št|zb|fa|fá|rw|zk|wi|tm|jm|we|fs|fy|' +
                                    'fó|žď|hv|gy|mz|žd|šl|gi|zh|sj|zt|žr|šr|' +
                                    'cv|sw|sro|sml|tří|tva|srá|obž|zví|psa|' +
                                    'smr|žlu|sca|zrů|sce|zvo|zme|mně$|mne$)',
                                    follow):
            return 've'
        if prep == 's' and re.match('^(s|z|kt|vz|vš|mn|šk|že|čt|šv|št|ps|vs|' +
                                    'šp|ži|cm|ža|ct|cv|dž|šl|še|bý|čle|jmě|' +
                                    'ple|šam|lst|prs|dvě|dře|7|17$|1\d\d\D?)',
                                    follow):
            return 'se'
        if prep == 'z' and re.match('^(s|z|kt|dn|šk|vs|šv|vš|št|šu|dř|mz|ži|' +
                                    'tm|kb|šp|pé|ša|kč|hv|nk|ši|rt|lh|ký|ža|' +
                                    'lv|šl|žď|žl|hry|vzd|tří|rom|jmě|šes|' +
                                    'mne|řet|hři|lan|žel|pan|wil|dou|thp|' +
                                    'pak|půt|cih|brá|hrd|mik|idy|psů|mst|' +
                                    'mag|vas|4|7|17|1\d\d\D?)', follow):
            return 'ze'
        return prep
