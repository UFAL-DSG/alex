#!/bin/bash
set -e

locdata=$1; shift
locdict=$1; shift


mkdir -p $locdict 

perl local/phonetic_transcription_dummy.pl $locdata/vocab-full.txt $locdict/dummy_transcription.txt

echo "--- Searching for OOV words ..."
gawk 'NR==FNR{words[$1]; next;} !($1 in words)' \
  $locdict/dummy_transcription.txt $locdata/vocab-full.txt | \
  egrep -v '<.?s>' > $locdict/vocab-oov.txt || echo "Good news no OOVs"

gawk 'NR==FNR{words[$1]; next;} ($1 in words)' \
  $locdata/vocab-full.txt $locdict/dummy_transcription.txt | \
  egrep -v '<.?s>' > $locdict/lexicon.txt

echo "# OOVs"
wc -l $locdict/vocab-oov.txt
echo "Size of lexicon"
wc -l $locdict/lexicon.txt
