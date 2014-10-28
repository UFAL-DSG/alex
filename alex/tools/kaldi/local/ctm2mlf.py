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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert alignments in ctm format to mlf format')
    parser.add_argument('ctm-ali', type=str, action='store',
                        help='Input alignments in ctm format. See Sclite.')
    parser.add_argument('mlf-ali', type=str, action='store',
                        help='Onput alignments in HTK mlf format.')
    args = parser.parse_args()
    print('TODO')
