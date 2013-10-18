
# This script takes a given HMM model set and realigns our transcriptions
# to create an updated phone and triphone level MLFs.
#
# Parameters:
#    1 - Directory name of HMM model set to use.
#    2 - HMM list to use

# DEBUG
set -e

cd $WORK_DIR

# HVite parameters:
#  -l       Path to use in the names in the output MLF
#  -o SWT   How to output labels, S remove scores,
#           W do not include words, T do not include times
#  -b       Use this word as the sentence boundary during alignment
#  -C       Config files
#  -a       Perform alignment
#  -H       HMM macro definition files
#  -i       Output to this MLF file
#  -m       During recognition keep track of model boundaries
#  -t       Enable beam searching
#  -y       Extension for output label files
#  -I       Word level MLF file
#  -S       File contain the list of MFC files

HVite -B -A -T 1 -l '*' -o SW -C $TRAIN_COMMON/config -a -H $WORK_DIR/$1/macros -H $WORK_DIR/$1/hmmdefs -i $WORK_DIR/aligned_best.mlf -m -t 250.0 -I $WORK_DIR/train_words.mlf -S $WORK_DIR/train.scp $WORK_DIR/dict_train_sp_sil $WORK_DIR/$2 >$LOG_DIR/hvite_realign.log

# We'll get a "sp sil" sequence at the end of each sentence.  Merge these
# into a single sil phone.  Also might get "sil sil", we'll merge anything
# combination of sp and sil into a single sil.
HLEd -A -T 1 -l '*' -i $WORK_DIR/aligned_best2.mlf $TRAIN_COMMON/merge_sp_sil.led $WORK_DIR/aligned_best.mlf > $LOG_DIR/hled_realign_sp_sil.log

# We may get context dependent phones forced aligned along word boundaries,
# so we'll convert back to monophones and create a new triphone MLF from
# the monophone labels.  This would only be needed if the models used in
# alignment were not monophones to begin with.
perl $TRAIN_SCRIPTS/ConvertToMono.pl $WORK_DIR/aligned_best2.mlf > $WORK_DIR/aligned_best_mono.mlf

# This converts the monophone MLF into a word internal triphone MLF.
# Note that this realignment could could the triphones1 file to change
# what it contains since we make switch to different pronunciations for
# certain words in the training set.
HLEd -A -T 1 -n $WORK_DIR/triphones1 -l '*' -i $WORK_DIR/aligned_best3.mlf $TRAIN_COMMON/mktri.led $WORK_DIR/aligned_best_mono.mlf > $LOG_DIR/hled_make_tri.log

