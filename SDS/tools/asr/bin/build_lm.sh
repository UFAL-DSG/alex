#!/bin/bash
# Builds the word list and network we need for recognition 

cd $WORK_DIR

# Create a dictionary with a sp short pause after each word, this is
# so when we do the phone alignment from the word level MLF, we get
# the sp phone inbetween the words.  This version duplicates each
# entry and uses a long pause sil after each word as well.  
perl $TRAIN_SCRIPTS/AddSp.pl $WORK_DIR/cmu_ext_dict 1 > $WORK_DIR/cmu_ext_dict_sp

# We need a dictionary that has the word "silence" with the mapping to the sil phone
cat $WORK_DIR/cmu_ext_dict_sp >$TEMP_DIR/cmu_ext_dict_temp
echo "silence sil" >> $TEMP_DIR/cmu_ext_dict_temp
sort $TEMP_DIR/cmu_ext_dict_temp | uniq > $TEMP_DIR/cmu_ext_dict_sp_sil

# We have to add sent start and sent end symbols
echo "<s> [] sil" > $WORK_DIR/cmu_ext_dict_sp_sil
echo "</s> [] sil" >> $WORK_DIR/cmu_ext_dict_sp_sil
cat $TEMP_DIR/cmu_ext_dict_sp_sil >> $WORK_DIR/cmu_ext_dict_sp_sil

# Get word list
python $TRAIN_SCRIPTS/CreateWordList.py $TRAIN_DATA_SOURCE'/*.trn' | sort | uniq | grep -v "(" > $WORK_DIR/word_list_train
python $TRAIN_SCRIPTS/CreateWordList.py $TEST_DATA_SOURCE'/*.trn' | sort | uniq | grep -v "(" > $WORK_DIR/word_list_test

# We need sentence start and end symbols which match the WSJ
# standard language model and produce no output symbols.
echo "<s> [] sil" > $WORK_DIR/dict_train
echo "</s> [] sil" >> $WORK_DIR/dict_train

echo "<s> [] sil" > $WORK_DIR/dict_test
echo "</s> [] sil" >> $WORK_DIR/dict_test

# Add pronunciations for each word
perl $TRAIN_SCRIPTS/WordsToDictionary.pl $WORK_DIR/word_list_train $WORK_DIR/cmu_ext_dict_sp $TEMP_DIR/dict_train
cat $TEMP_DIR/dict_train >> $WORK_DIR/dict_train
perl $TRAIN_SCRIPTS/WordsToDictionary.pl $WORK_DIR/word_list_test $WORK_DIR/cmu_ext_dict_sp $TEMP_DIR/dict_test
cat $TEMP_DIR/dict_test >> $WORK_DIR/dict_test


# Build the word network as a word loop of words in the testing data
HBuild -A -T 1 -u '<UNK>' -s '<s>' '</s>' $WORK_DIR/word_list_test $WORK_DIR/wdnet_zerogram > $LOG_DIR/hbuild.log

if [ -f $DATA_SOURCE_DIR/wdnet_bigram ]
then
  cp $DATA_SOURCE_DIR/wdnet_bigram $WORK_DIR/wdnet_bigram
fi