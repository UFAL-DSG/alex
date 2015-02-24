#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014, Ondrej Platek, Ufal MFF UK <oplatek@ufal.mff.cuni.cz>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License. #
from __future__ import absolute_import, division, unicode_literals, print_function
import argparse
import codecs

def write_mlf_recording(wf, name, alignment, second_split=10000000):
    wf.write('"%s"\n' % name)
    for (start, length, phoneme) in alignment:
        start = start * second_split
        end = start + (length * second_split)
        wf.write('%d %d %s\n' % (start, end, phoneme))
    wf.write('.\n')


def ctm2mlf(ctmr, mlfw):
    mlfw.write("#!MLF!#\n")

    current_name, alignment = None, []
    for line in ctmr:
        split_line = line.strip().split(' ')
        assert(len(split_line) == 5)
        name, one, start, length, phoneme = split_line
        assert(one == '1')
        start, length = float(start), float(length)
        if name != current_name:
            if current_name is not None:
                write_mlf_recording(mlfw, current_name, alignment)
            current_name, alignment = name, []
        alignment.append((start, length, phoneme))
    if current_name is not None:
        write_mlf_recording(mlfw, current_name, alignment)

            



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='''Convert alignments in ctm format to mlf format.
        The assumption is that you used alex/tools/kaldi/local/get_train_ctm_phones.sh script
        for generating ctm file and you are generating mlf for estimating vad using
        alex/tools/vad/train_vad_nn_theano.py''')
    parser.add_argument('ctmali', type=str, action='store',
                        help='Input alignments in ctm format. See Sclite.')
    parser.add_argument('mlfali', type=str, action='store',
                        help='Onput alignments in HTK mlf format.')
    args = parser.parse_args()
    with codecs.open(args.ctmali, 'r', 'utf8') as ctmr:
        with codecs.open(args.mlfali, 'w', 'utf8') as mlfw:
            ctm2mlf(ctmr, mlfw)
