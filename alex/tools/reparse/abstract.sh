#!/bin/bash
#
# Cut just abstracted versions of both utterances and DAs, as produced by
# reparse_cs.py and reparse_en.py
#

if [[ $# -ne 2 ]]; then
    echo "Usage: ./abstract.sh input.tsv output.tsv"
    exit 1
fi

perl -pe 's/[(_](noise|hum|breath|laugh|cough|unint|sil)[)_] *//gi;' $1 | cut -f 4,2 | sort -k 2,2 -k 1,1 | uniq -c | sed 's/^ *//;' | sed 's/ /\t/;' > $2
