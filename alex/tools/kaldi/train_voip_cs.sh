#!/bin/bash
# Copyright Ondrej Platek Apache 2.0
renice 20 $$

# Load training parameters
. .env_voip_cs.sh

. ./path.sh "$KALDI_ROOT"

# If you have cluster of machines running GridEngine you may want to
# change the train and decode commands in the file below
. ./cmd.sh

#######################################################################
#       Preparing acoustic features, LMs and helper files             #
#######################################################################

# Decoding is done for each pair (TEST_SET x LMs)
test_sets_ext=""
for s in $test_sets ; do
    for lm in $LMs ; do
        test_sets_ext="$s_$lm"
    done
done

# Copy the configuration files to $EXP directory.
# Write into the $EXP WARNINGs if reusing settings from another experiment!
local/save_check.sh $WORK/local $WORK/mfcc|| exit 1;

local/data_split.sh --every_n $everyN $DATA_ROOT $WORK/local || exit 1

local/create_LMs.sh $WORK/local/lm $LMs || exit 1

local/prepare_cs_transcription.sh $WORK/local $WORK/local/dict || exit 1

# Prepare the lexicon and various phone lists
local/create_dict.sh $WORK/local $DICTIONARY $WORK/local/dict || exit 1

# Prepare WORK/lang and WORK/local/lang directories read it IO param describtion
# OOV words are mapped to _SIL_
utils/prepare_lang.sh WORK/local/dict '_SIL_' WORK/local/lang WORK/lang || exit 1

# Prepare G.fst
local/create_G.sh "$test_sets_ext" || exit 1

# Create MFCC features and storing them (Could be large).
for x in train $TEST_SETS ; do
    steps/make_mfcc.sh --mfcc-config conf/mfcc.conf --cmd \
      "$train_cmd" --nj $njobs $WORK/local/$s $EXP/make_mfcc/$s $WORK/mfcc || exit 1;
    # CMVN stats are always computed but not always used in decoding
    steps/compute_cmvn_stats.sh $WORK/local/$s $EXP/make_mfcc/$s $WORK/mfcc || exit 1;
    # Distribute the links to MFCC feats to all LM variations.
    for lm in $LMs; do
        cp $WORK/$s/feats.scp $WORK/$s_$lm/feats.scp
        cp $WORK/$s/cmvn.scp $WORK/$s_$lm/cmvn.scp
    done
done

#######################################################################
#                      Training Acoustic Models                       #
#######################################################################

# Train monophone models on full data -> may be wastefull (can be done on subset)
steps/train_mono.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" $WORK/train $WORK/lang $EXP/mono || exit 1;

# Get alignments from monophone system.
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
  $WORK/train $WORK/lang $EXP/mono $EXP/mono_ali || exit 1;

# train tri1 [first triphone pass]
steps/train_deltas.sh --run-cmn $cmn --cmd "$train_cmd" \
  $pdf $gauss $WORK/train $WORK/lang $EXP/mono_ali $EXP/tri1 || exit 1;

# draw-tree $WORK/lang/phones.txt $EXP/tri1/tree | dot -Tsvg -Gsize=8,10.5  > graph.svg

#align tri1
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
  --use-graphs true $WORK/train $WORK/lang $EXP/tri1 $EXP/tri1_ali || exit 1;

# train tri2a [delta+delta-deltas]
steps/train_deltas.sh --run-cmn $cmn --cmd "$train_cmd" $pdf $gauss \
  $WORK/train $WORK/lang $EXP/tri1_ali $EXP/tri2a || exit 1;

# Train tri2b [LDA+MLLT]
steps/train_lda_mllt.sh --run-cmn $cmn --cmd "$train_cmd" $pdf $gauss \
  $WORK/train $WORK/lang $EXP/tri1_ali $EXP/tri2b || exit 1;

# Align all data with LDA+MLLT system (tri2b)
steps/align_si.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
    --use-graphs true $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_ali || exit 1;

# Do MMI on top of LDA+MLLT.
steps/make_denlats.sh --run-cmn $cmn --nj $njobs --cmd "$train_cmd" \
   $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_denlats || exit 1;
steps/train_mmi.sh --run-cmn $cmn $WORK/train $WORK/lang $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mmi || exit 1;

# Do the same with boosting. train_mmi_boost is a number e.g. 0.05
steps/train_mmi.sh --run-cmn $cmn --boost ${train_mmi_boost} $WORK/train $WORK/lang \
   $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mmi_b${train_mmi_boost} || exit 1;
# Train MPE.
steps/train_mpe.sh --run-cmn $cmn $WORK/train $WORK/lang $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mpe || exit 1;

#######################################################################
#                              Decoding                               #
#######################################################################
# Monophone decoding
for set_name in $test_sets_ext ; do
 utils/mkgraph.sh --mono $WORK/lang_$set_name $EXP/mono $EXP/mono/graph_${set_name} || exit 1
 # note: steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
 # calls the command line once for each test,
 # and afterwards averages the WERs into (in this case $EXP/mono/decode/)
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
   $EXP/mono/graph_${set_name} $WORK/$set_name $EXP/mono/decode_$set_name
# Decode tri1
 utils/mkgraph.sh $WORK/lang_$set_name $EXP/tri1 $EXP/tri1/graph_${set_name} || exit 1;
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
   $EXP/tri1/graph_${set_name} $WORK/$set_name $EXP/tri1/decode_$set_name
# Decode tri2a
 utils/mkgraph.sh $WORK/lang_$set_name $EXP/tri2a $EXP/tri2a/graph_${set_name}
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2a/graph_${set_name} $WORK/$set_name $EXP/tri2a/decode_$set_name
# Decode tri2b [LDA+MLLT]
 utils/mkgraph.sh $WORK/lang_$set_name $EXP/tri2b $EXP/tri2b/graph_${set_name}
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b/decode_$set_name
# Decode MMI on top of LDA+MLLT.
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mmi/decode_it4_$set_name
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mmi/decode_it3_$set_name
# Decode MMI on top of LDA+MLLT with boosting. train_mmi_boost is a number e.g. 0.05
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mmi_b${train_mmi_boost}/decode_it4_$set_name || exit 1;
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mmi_b${train_mmi_boost}/decode_it3_$set_name || exit 1;
# Decoding MPE.
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 4 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mpe/decode_it4_$set_name || exit 1;
 steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
   --run-cmn $cmn --config conf/decode.config --iter 3 --nj $njobs --cmd "$decode_cmd" \
  $EXP/tri2b/graph_${set_name} $WORK/$set_name $EXP/tri2b_mpe/decode_it3_$set_name || exit 1;
done


echo "Successfully trained and evaluated all the experiments"

local/export_models.sh $EXP/tri2b
local/backup.sh
