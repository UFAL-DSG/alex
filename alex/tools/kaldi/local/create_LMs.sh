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
local_lm=$1
lms=$2


mkdir -p $local_lm

echo "=== Preparing the LM ..."


function build_0gram {
    echo "=== Building zerogram $lm from ${transcr}. ..."
    transcr=$1; lm=$2
    cut -d' ' -f2- $transcr | tr ' ' '\n' | sort -u > $lm
    python -c """
import math
with open('$lm', 'r+') as f:
    lines = f.readlines()
    p = math.log10(1/float(len(lines)));
    lines = ['%f\\t%s'%(p,l) for l in lines]
    f.seek(0); f.write('\\n\\\\data\\\\\\nngram  1=       %d\\n\\n\\\\1-grams:\\n' % len(lines))
    f.write(''.join(lines) + '\\\\end\\\\')
"""
    exit 0
}

mkdir $local_lm
for lm in $lms ; do
    lm_base=`basename $lm`
    if [ ${lm_base%[0-6]} !=  'build' ] ; then
        cp $lm $local_lm
    else
        # We will build the LM 'build[0-9].arpa
        lm_order=${lm_base#build}
        cut -d' ' -f2- data/train/text | sed -e 's:^:<s> :' -e 's:$: </s>:' | \
            > $locdata/lm_train.txt

        echo "=== Building LM of order ${LM_ORDER}..."
        if [ $lm_order -eq 0 ] ; then
            build_0gram  $locdata/lm_train.txt $loca_lm/${lm_base}.arpa
        else
            ngram-count -text $locdata/lm_train.txt -order ${LM_ORDER} \
                -wbdiscount -interpolate -lm $local_lm/${lm_base}.arpa
        fi
    fi
done
echo "*** LMs preparation finished!"
