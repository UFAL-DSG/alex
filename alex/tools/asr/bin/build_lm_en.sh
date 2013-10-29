#!/bin/bash
# Builds the word list and network we need for recognition

cd $WORK_DIR

# Get word list
python $TRAIN_SCRIPTS/CreateWordList.py $WORK_DIR/dict_full $TRAIN_DATA_SOURCE'/*.trn' | sort | uniq | grep -v "(" | grep -v "_" > $WORK_DIR/word_list_train
python $TRAIN_SCRIPTS/CreateWordList.py $WORK_DIR/dict_full $TEST_DATA_SOURCE'/*.trn' | sort | uniq | grep -v "(" | grep -v "_" > $WORK_DIR/word_list_test
cat $WORK_DIR/word_list_train $WORK_DIR/word_list_test | sort | uniq > $WORK_DIR/word_list_full

# We need sentence start and end symbols which match the WSJ
# standard language model and produce no output symbols.
echo "<s> [] sil" >> $WORK_DIR/dict_full
echo "</s> [] sil" >> $WORK_DIR/dict_full
echo "_INHALE_ _inhale_" >> $WORK_DIR/dict_full
echo "_LAUGH_ _laugh_" >> $WORK_DIR/dict_full
echo "_EHM_HMM_ _ehm_hmm_" >> $WORK_DIR/dict_full
echo "_NOISE_ _noise_" >> $WORK_DIR/dict_full
echo "_SIL_ sil" >> $WORK_DIR/dict_full

echo "<s> [] sil" > $WORK_DIR/dict_train
echo "</s> [] sil" >> $WORK_DIR/dict_train
echo "_INHALE_ _inhale_" >> $WORK_DIR/dict_train
echo "_LAUGH_ _laugh_" >> $WORK_DIR/dict_train
echo "_EHM_HMM_ _ehm_hmm_" >> $WORK_DIR/dict_train
echo "_NOISE_ _noise_" >> $WORK_DIR/dict_train
echo "_SIL_ sil" >> $WORK_DIR/dict_train

echo "<s> [] sil" > $WORK_DIR/dict_test
echo "</s> [] sil" >> $WORK_DIR/dict_test
echo "_INHALE_ _inhale_" >> $WORK_DIR/dict_test
echo "_LAUGH_ _laugh_" >> $WORK_DIR/dict_test
echo "_EHM_HMM_ _ehm_hmm_" >> $WORK_DIR/dict_test
echo "_NOISE_ _noise_" >> $WORK_DIR/dict_test
echo "_SIL_ sil" >> $WORK_DIR/dict_test

# Add pronunciations for each word
perl $TRAIN_SCRIPTS/WordsToDictionary.pl $WORK_DIR/word_list_train $WORK_DIR/dict_full $TEMP_DIR/dict_train
cat $TEMP_DIR/dict_train >> $WORK_DIR/dict_train
perl $TRAIN_SCRIPTS/WordsToDictionary.pl $WORK_DIR/word_list_test $WORK_DIR/dict_full $TEMP_DIR/dict_test
cat $TEMP_DIR/dict_test >> $WORK_DIR/dict_test

# Create a dictionary with a sp short pause after each word, this is
# so when we do the phone alignment from the word level MLF, we get
# the sp phone in between the words.  This version duplicates each
# entry and uses a long pause sil after each word as well.
perl $TRAIN_SCRIPTS/AddSp.pl $WORK_DIR/dict_full 1 > $WORK_DIR/dict_full_sp_sil
perl $TRAIN_SCRIPTS/AddSp.pl $WORK_DIR/dict_train 1 > $WORK_DIR/dict_train_sp_sil
perl $TRAIN_SCRIPTS/AddSp.pl $WORK_DIR/dict_test 1 > $WORK_DIR/dict_test_sp_sil

# Add to the word list non-speech events
echo "_INHALE_" >> $WORK_DIR/word_list_test
echo "_LAUGH_" >> $WORK_DIR/word_list_test
echo "_EHM_HMM_" >> $WORK_DIR/word_list_test
echo "_NOISE_" >> $WORK_DIR/word_list_test
echo "_SIL_" >> $WORK_DIR/word_list_test

echo "<s>" >> $WORK_DIR/word_list_full
echo "</s>" >> $WORK_DIR/word_list_full
echo "_INHALE_" >> $WORK_DIR/word_list_full
echo "_LAUGH_" >> $WORK_DIR/word_list_full
echo "_EHM_HMM_" >> $WORK_DIR/word_list_full
echo "_NOISE_" >> $WORK_DIR/word_list_full
echo "_SIL_" >> $WORK_DIR/word_list_full

# Build the word network as a word loop of words in the testing data
HBuild -A -T 1 -C $TRAIN_COMMON/configrawmit -u '<UNK>' -s '<s>' '</s>' $WORK_DIR/word_list_test $WORK_DIR/wdnet_zerogram > $LOG_DIR/hbuild.log

if [ -f $DATA_SOURCE_DIR/wdnet_bigram ]
then
  cp $DATA_SOURCE_DIR/wdnet_bigram $WORK_DIR/wdnet_bigram
else
  rm $WORK_DIR/all_trns $WORK_DIR/train_trns $WORK_DIR/test_trns 

  find -L $TRAIN_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/all_trns
  find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/all_trns
  find -L $TRAIN_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/train_trns
  find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/test_trns
  #find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' | sed s/\_SIL\_/\ /g >> $WORK_DIR/all_trns

  ngram-count -text $WORK_DIR/train_trns -order 2 -wbdiscount -interpolate -lm $WORK_DIR/arpa_bigram
  echo "Train data PPL"
  ngram -lm $WORK_DIR/arpa_bigram -ppl $WORK_DIR/train_trns
  echo "Test data PPL"
  ngram -lm $WORK_DIR/arpa_bigram -ppl $WORK_DIR/test_trns

  HBuild -A -T 1 -C $TRAIN_COMMON/configrawmit -u '<UNK>' -s '<s>' '</s>' -n $WORK_DIR/arpa_bigram -z $WORK_DIR/word_list_full $WORK_DIR/wdnet_bigram > $LOG_DIR/hbuild.log
fi

if [ -f $DATA_SOURCE_DIR/arpa_trigram ]
then
  cp $DATA_SOURCE_DIR/arpa_trigram $WORK_DIR/arpa_trigram
else
  rm $WORK_DIR/all_trns $WORK_DIR/train_trns $WORK_DIR/test_trns 
  
  find -L $TRAIN_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/all_trns
  find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/all_trns
  find -L $TRAIN_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/train_trns
  find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' >> $WORK_DIR/test_trns
  #find -L $TEST_DATA_SOURCE -name '*.trn' | xargs sed -e '$a\' | sed s/\_SIL\_/\ /g >> $WORK_DIR/all_trns

  ngram-count -text $WORK_DIR/train_trns -order 2 -wbdiscount -interpolate -lm $WORK_DIR/arpa_bigram

  echo "Train data PPL"
  ngram -lm $WORK_DIR/arpa_trigram -ppl $WORK_DIR/train_trns
  echo "Test data PPL"
  ngram -lm $WORK_DIR/arpa_trigram -ppl $WORK_DIR/test_trns
fi

python $TRAIN_SCRIPTS/WordListFromARPALM.py $WORK_DIR/arpa_trigram | grep -v '_SIL_' > $WORK_DIR/word_list_hdecode
perl $TRAIN_SCRIPTS/WordsToDictionary.pl $WORK_DIR/word_list_hdecode $WORK_DIR/dict_full $WORK_DIR/dict_hdecode

