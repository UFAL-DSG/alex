#!/bin/bash

# Copyright (c) 2013, Ondrej Platek, Ufal MFF UK <oplatek@ufal.mff.cuni.cz>
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

tgt=$1; shift

mkdir -p $tgt

for srcdir in "$@" ; do
    name=`basename $srcdir`
    tgtdir=$tgt/$name
    mkdir -p $tgtdir
    for f in final.mdl final.mat tree splice_opts ; do
        # Some of the files may not exists. E.g. final.mat only for LDA
        cp -f $srcdir/$f $tgtdir  2> /dev/null
    done

    for g in `ls -d $srcdir/graph*/` ; do
        gb=`basename $g`
        mkdir -p $tgtdir/$gb
        for f in words.txt HCLG.fst phones.txt phones/silence.csl ; do
            # Skipping some files some e.g. word_bounary.{int|txt}, ..
            cp -f $g/$f $tgtdir/$gb 2> /dev/null
        done
    done

done


