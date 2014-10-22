#!/bin/bash
# Copyright Ondrej Platek Apache 2.0
renice 20 $$

# Load training parameters
. ./env_voip_cs.sh
# Source optional config if exists
[ -f env_voip_cs_CUSTOM.sh ] && . ./env_voip_cs_CUSTOM.sh

. ./path.sh

# If you have cluster of machines running GridEngine you may want to
# change the train and decode commands in the file below
. ./cmd.sh

mkdir -p $WORK  $EXP
#######################################################################
#       Preparing acoustic features, LMs and helper files             #
#######################################################################

check local/data_split.sh --every_n $EVERY_N \
    $DATA_ROOT $WORK/local "$LMs" "$TEST_SETS" || exit 1

check local/create_LMs.sh $WORK/local $WORK/local/train/trans.txt \
    $WORK/local/test/trans.txt  $WORK/local/lm "$LMs" || exit 1

check local/prepare_cs_transcription.sh $WORK/local $WORK/local/dict || exit 1

check local/create_phone_lists.sh $WORK/local/dict || exit 1

check utils/prepare_lang.sh $WORK/local/dict '_SIL_' $WORK/local/lang $WORK/lang || exit 1

check local/create_G.sh $WORK/lang "$LMs" $WORK/local/lm $WORK/local/dict/lexicon.txt || exit 1

echo "Create MFCC features and storing them (Could be large)."
for s in train $TEST_SETS ; do
    check steps/make_mfcc.sh --mfcc-config common/mfcc.conf --cmd "$train_cmd" \
      --nj $njobs $WORK/local/$s $EXP/make_mfcc/$s $WORK/mfcc || exit 1;
    # Note --fake -> NO CMVN
    check steps/compute_cmvn_stats.sh $fake $WORK/local/$s \
      $EXP/make_mfcc/$s $WORK/mfcc || exit 1;
done

echo "Decoding is done for each pair (TEST_SET x LMs)"
echo "Distribute the links to MFCC feats to all LM variations."
cp $WORK/local/train/feats.scp $WORK/train/feats.scp
cp $WORK/local/train/cmvn.scp $WORK/train/cmvn.scp
for s in $TEST_SETS; do
  for lm in $LMs; do
    tgt_dir=${s}_`basename "$lm"`
    echo "cp $WORK/local/$s/feats.scp $WORK/$tgt_dir/feats.scp"
    cp $WORK/local/$s/feats.scp $WORK/$tgt_dir/feats.scp
    echo "cp $WORK/local/$s/cmvn.scp $WORK/$tgt_dir/cmvn.scp"
    cp $WORK/local/$s/cmvn.scp $WORK/$tgt_dir/cmvn.scp
  done
done

#######################################################################
#                      Training Acoustic Models                       #
#######################################################################

echo "Train monophone models on full data -> may be wastefull (can be done on subset)"
check steps/train_mono.sh  --nj $njobs --cmd "$train_cmd" $WORK/train $WORK/lang $EXP/mono || exit 1;

echo "Get alignments from monophone system."
check steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  $WORK/train $WORK/lang $EXP/mono $EXP/mono_ali || exit 1;

echo "Train tri1 [first triphone pass]"
check steps/train_deltas.sh  --cmd "$train_cmd" \
  $pdf $gauss $WORK/train $WORK/lang $EXP/mono_ali $EXP/tri1 || exit 1;

# draw-tree $WORK/lang/phones.txt $EXP/tri1/tree | dot -Tsvg -Gsize=8,10.5  > graph.svg

echo "Align tri1"
check steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  --use-graphs true $WORK/train $WORK/lang $EXP/tri1 $EXP/tri1_ali || exit 1;

echo "Train tri2b [LDA+MLLT]"
check steps/train_lda_mllt.sh  --cmd "$train_cmd" $pdf $gauss \
  $WORK/train $WORK/lang $EXP/tri1_ali $EXP/tri2b || exit 1;

echo "Align all data with LDA+MLLT system (tri2b)"
# TODO cannot use check because the checkpoint is limited to 255 name and multile align steps map to one checkpoint
# check steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
    --use-graphs true $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_ali || exit 1;

echo -e 'TODO convert alignments to phone level alignmetns'

check steps/make_denlats.sh  --nj $njobs --cmd "$train_cmd" \
   --beam $mmi_beam --lattice-beam $mmi_lat_beam \
   $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_denlats || exit 1;

echo "Train MMI on top of LDA+MLLT with boosting. train_mmi_boost is a e.g. 0.05"
check steps/train_mmi.sh  --boost ${train_mmi_boost} $WORK/train $WORK/lang \
   $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mmi_b${train_mmi_boost} || exit 1;

# echo "Train MPE."
# steps/train_mpe.sh $WORK/train $WORK/lang $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mpe || exit 1;

#######################################################################
#                       Building decoding graph                       #
#######################################################################
for lm in $LMs ; do
  lm=`basename "$lm"`
  # check utils/mkgraph.sh --mono $WORK/lang_${lm} $EXP/mono $EXP/mono/graph_${lm} || exit 1
  # check utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri1 $EXP/tri1/graph_${lm} || exit 1
  check utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri2b $EXP/tri2b/graph_${lm} || exit 1
done


#######################################################################
#                              Decoding                               #
#######################################################################
for s in $TEST_SETS ; do
  for lm in $LMs ; do
    lm=`basename "$lm"`
    tgt_dir=${s}_`basename "$lm"`

    # echo "Monophone decoding"
    # # Note: steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    # # calls the command line once for each test,
    # # and afterwards averages the WERs into (in this case $EXP/mono/decode/)
    # check steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/mono/graph_${lm} $WORK/${tgt_dir} $EXP/mono/decode_${tgt_dir}
    #
    # echo "Decode tri1"
    # check steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/tri1/graph_${lm} $WORK/$tgt_dir $EXP/tri1/decode_${tgt_dir}
    #
    # echo "Decode tri2b [LDA+MLLT]"
    # check steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b/decode_${tgt_dir}

    # Note: change --iter option to select the best model. 4.mdl == final.mdl
    echo "Decode MMI on top of LDA+MLLT with boosting. train_mmi_boost is a number e.g. 0.05"
    steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
       --config common/decode.conf --iter 4 --nj $njobs --cmd "$decode_cmd" \
      $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b_mmi_b${train_mmi_boost}/decode_it4_${tgt_dir};

    # echo "Decode MPE."
    # check steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --iter 4 --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b_mpe/decode_it4_${tgt_dir} || exit 1;
  done
done


echo "Successfully trained and evaluated all the experiments"
local/results.py $EXP | tee $EXP/results.log

check local/export_models.sh $TGT_MODELS $EXP $WORK/lang
