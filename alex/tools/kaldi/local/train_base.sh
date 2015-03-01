#!/bin/bash
set -e

local/check.sh local/create_phone_lists.sh $WORK/local/dict || exit 1

local/check.sh utils/prepare_lang.sh $WORK/local/dict '_SIL_' $WORK/local/lang $WORK/lang || exit 1

local/check.sh local/create_G.sh $WORK/lang "$LM_names" $WORK/local/lm $WORK/local/dict/lexicon.txt || exit 1


echo "Create MFCC features and storing them (Could be large)."
for s in train $TEST_SETS ; do
    local/check.sh steps/make_mfcc.sh --mfcc-config common/mfcc.conf --cmd "$train_cmd" \
      --nj $njobs $WORK/local/$s $EXP/make_mfcc/$s $WORK/mfcc || exit 1
    # Note --fake -> NO CMVN
    local/check.sh steps/compute_cmvn_stats.sh $fake $WORK/local/$s \
      $EXP/make_mfcc/$s $WORK/mfcc || exit 1
done

echo "Decoding is done for each pair (TEST_SET x LMs)"
echo "Distribute the links to MFCC feats to all LM variations."
cp -f $WORK/local/train/feats.scp $WORK/train/feats.scp
cp -f $WORK/local/train/cmvn.scp $WORK/train/cmvn.scp
for s in $TEST_SETS; do
  for lm in $LM_names; do
    tgt_dir=${s}_${lm}
    mkdir -p $WORK/$tgt_dir
    echo "cp $WORK/local/$s/feats.scp $WORK/$tgt_dir/feats.scp"
    cp -f $WORK/local/$s/feats.scp $WORK/$tgt_dir/feats.scp
    echo "cp $WORK/local/$s/cmvn.scp $WORK/$tgt_dir/cmvn.scp"
    cp -f $WORK/local/$s/cmvn.scp $WORK/$tgt_dir/cmvn.scp
  done
done

#######################################################################
#                      Training Acoustic Models                       #
#######################################################################

echo
echo "Train monophone models on full data -> may be wastefull (can be done on a subset)"
local/check.sh steps/train_mono.sh  --nj $njobs --cmd "$train_cmd" $WORK/train $WORK/lang $EXP/mono || exit 1

local/check.sh steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  $WORK/train $WORK/lang $EXP/mono $EXP/mono_ali || exit 1

echo
echo "Train tri1 [first triphone pass]"
local/check.sh steps/train_deltas.sh  --cmd "$train_cmd" \
  $pdf $gauss $WORK/train $WORK/lang $EXP/mono_ali $EXP/tri1 || exit 1

# draw-tree $WORK/lang/phones.txt $EXP/tri1/tree | dot -Tsvg -Gsize=8,10.5  > graph.svg

local/check.sh steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  --use-graphs true $WORK/train $WORK/lang $EXP/tri1 $EXP/tri1_ali || exit 1

echo
echo "Train tri2b [LDA+MLLT]"
local/check.sh steps/train_lda_mllt.sh  --cmd "$train_cmd" \
  --splice-opts "--left-context=3 --right-context=3" \
  $pdf $gauss $WORK/train $WORK/lang $EXP/tri1_ali $EXP/tri2b || exit 1

local/check.sh steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  --use-graphs true $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_ali || exit 1

local/check.sh local/get_train_ctm_phones.sh $WORK/train $WORK/lang $EXP/tri2b_ali || exit 1
local/check.sh local/ctm2mlf.py $EXP/tri2b_ali/ctm $EXP/tri2b_ali/mlf || exit 1

echo
echo "Train tri2b_bmmi [MMI on top of LDA+MLLT with boosting. train_mmi_boost is a e.g. 0.05]"
local/check.sh steps/make_denlats.sh  --nj $njobs --cmd "$train_cmd" \
   --beam $mmi_beam --lattice-beam $mmi_lat_beam \
   $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_denlats || exit 1

local/check.sh steps/train_mmi.sh --cmd "$train_cmd" \
   --boost ${train_mmi_boost} $WORK/train $WORK/lang \
   $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mmi_b${train_mmi_boost} || exit 1

local/check.sh steps/align_si.sh  --nj $njobs --cmd "$train_cmd" \
  --use-graphs true $WORK/train $WORK/lang $EXP/tri2b $EXP/tri2b_mmi_b${train_mmi_boost}_ali || exit 1

#echo
#echo "Train tri3b, which is LDA+MLLT+SAT"
#local/check.sh steps/train_sat.sh --cmd "$train_cmd" \
#  $pdf $gauss $WORK/train $WORK/lang $EXP/tri2b_ali $EXP/tri3b || exit 1;

#local/check.sh steps/align_fmllr.sh --nj $njobs --cmd "$train_cmd" \
#  $WORK/train $WORK/lang $EXP/tri3b $EXP/tri3b_ali || exit 1;

echo
echo "Train nnet"
./local/run_nnet_online.sh --gauss $gauss --pdf $pdf \
    --srcdir $EXP/tri2b \
    --tgtdir $EXP/tri4_nnet2 \
    $WORK $EXP || exit 1

echo
echo "Train nnet discriminatively [SMBR]"
./local/run_nnet_online-discriminative.sh --gauss $gauss --pdf $pdf \
    --srcdir $EXP/tri4_nnet2 \
    --tgtdir $EXP/tri4_nnet2_smbr \
    $WORK $EXP || exit 1

# Cleaning does not help a lot
# local/check.sh local/data_clean.sh --thresh 0.1 --cleandir $EXP/tri2b_mmi_b${train_mmi_boost}_selected \
#   $WORK/train $WORK/lang $EXP/tri2b_mmi_b${train_mmi_boost} $WORK/train_cleaned || exit 1
#
# echo "Train MMI on top of LDA+MLLT with boosting. train_mmi_boost is a e.g. 0.05 on CLEANED data"
# local/check.sh steps/train_mmi.sh  --boost ${train_mmi_boost} $WORK/train_cleaned $WORK/lang \
#    $EXP/tri2b_ali $EXP/tri2b_denlats $EXP/tri2b_mmi_b${train_mmi_boost}_cleaned || exit 1



#######################################################################
#                       Building decoding graph                       #
#######################################################################
for lm in $LM_names ; do
  # local/check.sh utils/mkgraph.sh --mono $WORK/lang_${lm} $EXP/mono $EXP/mono/graph_${lm} || exit 1
  # local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri1 $EXP/tri1/graph_${lm} || exit 1
  local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri2b $EXP/tri2b/graph_${lm} || exit 1
#  local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri3b $EXP/tri3b/graph_${lm} || exit 1
  local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri4_nnet2 $EXP/tri4_nnet2/graph_${lm} || exit 1
  local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri4_nnet2_smbr $EXP/tri4_nnet2_smbr/graph_${lm} || exit 1
done


#######################################################################
#                              Decoding                               #
#######################################################################
for s in $TEST_SETS ; do
  for lm in $LM_names ; do
    tgt_dir=${s}_${lm}

    # echo "Monophone decoding"
    # # Note: steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    # # calls the command line once for each test,
    # # and afterwards averages the WERs into (in this case $EXP/mono/decode/)
    # local/check.sh steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/mono/graph_${lm} $WORK/${tgt_dir} $EXP/mono/decode_${tgt_dir}
    #
    # echo "Decode tri1"
    # local/check.sh steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #    --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/tri1/graph_${lm} $WORK/$tgt_dir $EXP/tri1/decode_${tgt_dir}
    #
     echo "Decode tri2b [LDA+MLLT]"
     local/check.sh steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
        --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
       $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b/decode_${tgt_dir};

    # Note: change --iter option to select the best model. 4.mdl == final.mdl
    echo "Decode tri2b_mmi_b${train_mmi_boost} [LDA+MLLT with MMI + boosting]. train_mmi_boost is a number e.g. 0.05"
    local/check.sh steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
       --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
      $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b_mmi_b${train_mmi_boost}/decode_${tgt_dir}

#    echo "Decode tri3b [LDA+MLLT+SAT]"
#    local/check.sh steps/decode_fmllr.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
#       --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
#      $EXP/tri3b/graph_${lm} $WORK/$tgt_dir $EXP/tri3b/decode_${tgt_dir}

    # echo "On Cleaned data:Decode MMI on top of LDA+MLLT with boosting. train_mmi_boost is a number e.g. 0.05: RESULTS on vystadial 0.95% of all data and WER improvement of 0.02 for tri2 + bMMI_b005 model"
    # local/check.sh steps/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
    #   --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
    #   $EXP/tri2b/graph_${lm} $WORK/$tgt_dir $EXP/tri2b_mmi_b${train_mmi_boost}_cleaned/decode_it4_${tgt_dir}

    echo "Decode nnet2 online"
    local/check.sh steps/online/nnet2/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
      --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
      $EXP/tri4_nnet2/graph_${lm} $WORK/$tgt_dir $EXP/tri4_nnet2_online/decode_${tgt_dir}

    echo "Decode nnet2 discriminative [SMBR] online"
    local/check.sh steps/online/nnet2/decode.sh --scoring-opts "--min-lmw $min_lmw --max-lmw $max_lmw" \
      --config common/decode.conf --nj $njobs --cmd "$decode_cmd" \
      $EXP/tri4_nnet2_smbr/graph_${lm} $WORK/$tgt_dir $EXP/tri4_nnet2_smbr_online/decode_${tgt_dir}

  done
done


for x in $EXP/*/decode*; do [ -d $x ] && grep WER $x/wer_* | utils/best_wer.sh; done
# for d in `find $EXP/ -name '*decode*' -type d` ; do local/call_runtime.sh $d ; done

local/results.py $EXP | tee $EXP/results.log
cp $EXP/results.log $WORK/../results/`date -u +"%Y-%m-%d--%H-%M-%S"`-results-`basename $WORK`.log

echo "Successfully trained and evaluated all the experiments"
local/export_models.sh $TGT_MODELS $EXP $WORK/lang
