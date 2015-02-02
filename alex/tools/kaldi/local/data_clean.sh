#!/bin/bash
# This script shows how you can do data-cleaning.

set -e

nj=8
train_cmd=run.pl
thresh=0.1
cleandir=""

. ./cmd.sh || exit 1;


. utils/parse_options.sh || exit 1;

if [ $# -ne 4 ] ; then
  echo "Usage: $0 <train-data-dir> <lang-dir> <exp-src-dir> <subset-train-tgt-dir>"
fi

train_data=$1
lang=$2
srcdir=$3
tgt_dir=$4
if [ -z $cleandir ] ; then
  cleandir=${src_dir}_cleaned
fi

nj=`cat $srcdir/num_jobs` || exit 1;

steps/cleanup/find_bad_utts.sh --nj $nj --cmd "$train_cmd" \
  $train_data $lang $srcdir $cleandir

cat $cleandir/all_info.txt | awk -v threshold=$thresh '{ errs=$2;ref=$3; if (errs <= threshold*ref) { print $1; } }' > $cleandir/uttlist
utils/subset_data_dir.sh --utt-list $cleandir/uttlist $train_data  $tgt_dir
