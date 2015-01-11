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
set -e

train_text=""
arpa_paths="build2"   
lm_names="$arpa_path"

. utils/parse_options.sh

if [ $# != 1 ]; then
   echo "usage: $0 <options> directory to store LMS"
   echo "--arpa-paths \"path1.arpa path2.arpa build2\"     default: $arpa_paths"  specify either path or build[0-4] to build LM note that
   echo "               Contains paths to arpa files or command to build n-gram model from transcriptions"
   echo "--train-text   Path to transcriptions"
   echo "--lm-names     The # of names should match # of arpa paths; the names should not contain underscore"
   exit 1;
fi

local_lm=$1; shift

declare -A lms
set -- $arpa_paths
for k in $lm_names ; do 
    lms[$k]=$1
    shift
done


mkdir -p $local_lm

echo "=== Preparing the LM ..."

function build_0gram {
    echo "=== Building zerogram $lm from ${transcr}. ..."
    transcr=$1; lm=$2
    cut -d' ' -f2- $transcr | tr ' ' '\n' | sort -u > $lm
    echo "<s>" >> $lm
    echo "</s>" >> $lm
    python -c """
import math
with open('$lm', 'r+') as f:
    lines = f.readlines()
    p = math.log10(1/float(len(lines)));
    lines = ['%f\\t%s'%(p,l) for l in lines]
    f.seek(0); f.write('\\n\\\\data\\\\\\nngram  1=       %d\\n\\n\\\\1-grams:\\n' % len(lines))
    f.write(''.join(lines) + '\\\\end\\\\')
"""
}

for name  in "${!lms[@]}" ; do
    if [[ ${name%[0-5]} ==  'build' ]] ; then
        if [ $name != ${lms[$name]} ] ; then
            echo -e "\nIf using the build command $name, specify path as the same value!\n"
            exit 1;
        fi
        # We will build the LM 'build[0-9].arpa
        lm_order=${name#build}
        echo "=== Building LM of order ${lm_order}..."
        cut -d' ' -f2- $train_text | sed -e 's:^:<s> :' -e 's:$: </s>:' | \
            sort -u > $local_lm/lm_train.txt
        echo "LM $name is build from text: $train_text"
        if [ $lm_order -eq 0 ] ; then
            build_0gram  $local_lm/lm_train.txt $local_lm/${name}
        else
            ngram-count -text $local_lm/lm_train.txt -order ${lm_order} \
                -wbdiscount -interpolate -lm $local_lm/${name}
        fi
    else
        if [[ ! -f ${lms[$name]} ]] ; then
            echo ${lms[$name]} is not path to arpa file!
            exit 1
        fi
        cp -f ${lms[$name]} $local_lm/$name
    fi
done
echo "*** LMs preparation finished!"

echo "=== Preparing the vocabulary ..."

if [ "$DICTIONARY" == "build" ]; then
  echo; echo "Building dictionary from train data"; echo
  cut -d' ' -f2- $train_text | tr ' ' '\n' > $local_lm/vocab-full-raw.txt
else
  echo; echo "Using predefined dictionary: ${DICTIONARY}"
  echo "Throwing away first 2 rows."; echo
  tail -n +3 $DICTIONARY | cut -f 1 > $local_lm/vocab-full-raw.txt
fi

echo '</s>' >> $local_lm/vocab-full-raw.txt
echo "Removing from vocabulary _NOISE_, and  all '_' words from vocab-full.txt"
cat $local_lm/vocab-full-raw.txt | grep -v '_' | \
  sort -u > $local_lm/vocab-full.txt
echo "*** Vocabulary preparation finished!"
