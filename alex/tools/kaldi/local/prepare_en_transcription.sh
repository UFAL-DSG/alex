#!/bin/bash

locdata=$1
locdict=$2


if [ ! -f common/cmudict.0.7a ]; then
  echo "--- Downloading CMU dictionary ..."
  svn export http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/cmudict.0.7a \
     common/cmudict.0.7a || exit 1;
fi

echo; echo "If common/cmudict.ext exists, add extra pronunciation to dictionary" ; echo
cat common/cmudict.0.7a common/cmudict.ext > $locdict/cmudict_ext.txt

echo "--- Striping stress and pronunciation variant markers from cmudict ..."
perl $locdict/cmudict/scripts/make_baseform.pl \
  $locdict/cmudict_ext /dev/stdout |\
  sed -e 's:^\([^\s(]\+\)([0-9]\+)\(\s\+\)\(.*\):\1\2\3:' > $locdict/cmudict-plain.txt

echo "--- Searching for OOV words ..."
gawk 'NR==FNR{words[$1]; next;} !($1 in words)' \
  $locdict/cmudict-plain.txt $locdata/vocab-full.txt |\
  egrep -v '<.?s>' > $locdict/vocab-oov.txt

gawk 'NR==FNR{words[$1]; next;} ($1 in words)' \
  $locdata/vocab-full.txt $locdict/cmudict-plain.txt |\
  egrep -v '<.?s>' > $locdict/lexicon.txt

wc -l $locdict/vocab-oov.txt
wc -l $locdict/lexicon.txt
