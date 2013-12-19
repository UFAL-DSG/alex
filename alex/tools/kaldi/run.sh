#!/bin/bash
# Copyright Ondrej Platek Apache 2.0
# based on copyrighted 2012 Vassil Panayotov recipe
# at egs/voxforge/s5/run.sh(Apache 2.0)

renice 20 $$

# Load training parameters
. ./conf/train_conf.sh

. ./path.sh "$KALDI_ROOT"

# If you have cluster of machines running GridEngine you may want to
# change the train and decode commands in the file below
. ./cmd.sh

test_sets_ext=$test_sets
# If using zero grams for testing create
# additional lang_test_dir0 with 0 suffix
if [[ ! -z "$TEST_ZERO_GRAMS" ]] ; then
    for t in $test_sets ; do test_sets_ext="$test_sets_ext ${t}0" ; done
fi

# Copy the configuration files to exp directory.
# Write into the exp WARNINGs if reusing settings from another experiment!
local/save_check_conf.sh || exit 1;

# With save_check_conf.sh it ask about rewriting the data directory
if [ ! "$(ls -A data 2>/dev/null)" ]; then

  local/vystadial_data_split.sh --every_n $everyN ${DATA_ROOT} || exit 1

  # Prepare the lexicon, language model and various phone lists
  local/vystadial_create_LMs_dict.sh || exit 1

  # Prepare data/lang and data/local/lang directories read it IO param describtion
  utils/prepare_lang.sh data/local/dict 'OOV' data/local/lang data/lang || exit 1

  # Prepare G.fst
  local/vystadial_create_G.sh "$test_sets_ext" || exit 1
fi
# end of generating data directory


# With save_check_conf.sh it ask about rewriting the ${MFCC_DIR} directory
if [ ! "$(ls -A ${MFCC_DIR} 2>/dev/null)" ]; then
  # Creating MFCC features and storing at ${MFCC_DIR} (Could be large).
  for x in train $test_sets ; do
    steps/make_mfcc.sh --mfcc-config conf/mfcc.conf --cmd \
      "$train_cmd" --nj $njobs data/$x exp/make_mfcc/$x ${MFCC_DIR} || exit 1;
    # CMVN is turn off by default but the scripts require it
    steps/compute_cmvn_stats.sh data/$x exp/make_mfcc/$x ${MFCC_DIR} || exit 1;
    if [[ ! -z "$TEST_ZERO_GRAMS" ]] ; then
        cp data/$x/feats.scp data/${x}0/feats.scp
        cp data/$x/cmvn.scp data/${x}0/cmvn.scp
    fi
  done
fi

# Train monophone models
# If the monoTrainData is specified Train on data T; |T|==monoTrainData
if [ -z $monoTrainData ] ; then
    steps/train_mono.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" data/train data/lang exp/mono || exit 1;
else
    utils/subset_set_name.sh data/train $monoTrainData data/train.sub  || exit 1;
    steps/train_mono.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" data/train.sub data/lang exp/mono || exit 1;
fi

# Monophone decoding
for set_name in $test_sets_ext ; do
 utils/mkgraph.sh --mono data/lang_$set_name exp/mono exp/mono/graph_${set_name} || exit 1
 # note: steps/decode.sh calls the command line once for each test,
 # and afterwards averages the WERs into (in this case exp/mono/decode/)
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
   exp/mono/graph_${set_name} data/$set_name exp/mono/decode_$set_name
done

# Get alignments from monophone system.
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
  data/train data/lang exp/mono exp/mono_ali || exit 1;

# train tri1 [first triphone pass]
steps/train_deltas.sh --run-cmn $cmn --cmd "$train_cmd" \
  $pdf $gauss data/train data/lang exp/mono_ali exp/tri1 || exit 1;

# decode tri1
for set_name in $test_sets_ext ; do
 utils/mkgraph.sh data/lang_$set_name exp/tri1 exp/tri1/graph_${set_name} || exit 1;
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
   exp/tri1/graph_${set_name} data/$set_name exp/tri1/decode_$set_name
done

# draw-tree data/lang/phones.txt exp/tri1/tree | dot -Tsvg -Gsize=8,10.5  > graph.svg

#align tri1
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
  --use-graphs true data/train data/lang exp/tri1 exp/tri1_ali || exit 1;

# train tri2a [delta+delta-deltas]
steps/train_deltas.sh --run-cmn $cmn --cmd "$train_cmd" $pdf $gauss \
  data/train data/lang exp/tri1_ali exp/tri2a || exit 1;

# decode tri2a
for set_name in $test_sets_ext ; do
 utils/mkgraph.sh data/lang_$set_name exp/tri2a exp/tri2a/graph_${set_name}
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
  exp/tri2a/graph_${set_name} data/$set_name exp/tri2a/decode_$set_name
done

# train and decode tri2b [LDA+MLLT]
steps/train_lda_mllt.sh --run-cmn $cmn --cmd "$train_cmd" $pdf $gauss \
  data/train data/lang exp/tri1_ali exp/tri2b || exit 1;
for set_name in $test_sets_ext ; do
 utils/mkgraph.sh data/lang_$set_name exp/tri2b exp/tri2b/graph_${set_name}
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b/decode_$set_name
done

# Align all data with LDA+MLLT system (tri2b)
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
    --use-graphs true data/train data/lang exp/tri2b exp/tri2b_ali || exit 1;

# #  Do MMI on top of LDA+MLLT.
steps/make_denlats.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
   data/train data/lang exp/tri2b exp/tri2b_denlats || exit 1;
steps/train_mmi.sh --run-cmn $cmn data/train data/lang exp/tri2b_ali exp/tri2b_denlats exp/tri2b_mmi || exit 1;
for set_name in $test_sets_ext ; do
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mmi/decode_it4_$set_name
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mmi/decode_it3_$set_name
done

# Do the same with boosting. train_mmi_boost is a number e.g. 0.05
steps/train_mmi.sh --run-cmn $cmn --boost ${train_mmi_boost} data/train data/lang \
   exp/tri2b_ali exp/tri2b_denlats exp/tri2b_mmi_b${train_mmi_boost} || exit 1;
for set_name in $test_sets_ext ; do
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mmi_b${train_mmi_boost}/decode_it4_$set_name || exit 1;
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mmi_b${train_mmi_boost}/decode_it3_$set_name || exit 1;
done

# Do MPE.
steps/train_mpe.sh --run-cmn $cmn data/train data/lang exp/tri2b_ali exp/tri2b_denlats exp/tri2b_mpe || exit 1;
for set_name in $test_sets_ext ; do
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mpe/decode_it4_$set_name || exit 1;
 steps/decode.sh --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  exp/tri2b/graph_${set_name} data/$set_name exp/tri2b_mpe/decode_it3_$set_name || exit 1;
done


echo "Successfully trained and evaluated all the experiments"

if [ -f local/backup.sh ]; then
    local/backup.sh
fi
