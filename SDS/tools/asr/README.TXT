INTRODUCTION
-------------------------------
The acoustic modelling is using the HTK and the aim is to build triphone models for different languages, for example English and Czech.

For each language or recording conditions a seperate direoctry based on some previous direcotry must be created: 

A setup for a new language and recording conditions (RCOND_LANG) would need:

Files:

./env_RCOND_LANG.sh          - settings of all important directories, and training options, e.g. cross word or word internal triphones, language model weights
./train_RCOND_LANG.sh        - the complete training script
./nohup_train_RCOND_LANG.sh  - calling the training script using nohup and redirecting the output into the .log_* file

Directories:

model_RCOND_LANG
model_RCOND_LANG/config - config contains the language or recording specific configuration files
model_RCOND_LANG/temp
model_RCOND_LANG/log
model_RCOND_LANG/train
model_RCOND_LANG/test


CREDITS AND THE LICENCE
-------------------------------
The scripts are based on the HTK Wall Street Journal Training Recipe written by Keith Vertanen (http://www.keithv.com/software/htk/).

The licence of his code is unclear so any distribution of the code is forbidden.
We have to ask for permition to distribute his code.

2012-07-19 Filip Jurcicek

Keith clarified the license. His code is relised under the new BSD licence. The lucence note is at http://www.keithv.com/software/htk/.

The note says: The scripts and configuration files in the recipe are released under a new BSD license. This excludes the decision tree phonetic questions (tree_ques.hed) and the test set index files (si_dt_05_odd.ndx, si_dt_s2.ndx, si_dt_s6.ndx) which I did not write.

2012-08-07 Filip Jurcicek

TEST RESULTS
------------------------------

+ total training data for voip_en is about 40 hours
+ total training data for voip_cs is about 8 hours
+ mixtures - there is 16 mixtures is slightly better than 8 mixtures for voip_en
+ there is no signigicant difference in alignment of transcriptions with -t 150 and -t 250
+ the Julius ASR performance is about the same as of HDecode
- HDecode works well when cross word phones are trained, however the perfomance of HVite decreases significantly
- when only word internal triphones are trained then the HDecode works, however, its perfomance is worse than the HVite with a bigram LM
+ word internal triphones work well with Julius ASR, do not forget disable CCD (it does not need context handling - though it still uses triphones)
+ there is not much gain with the trigram LM in the Caminfo domain (about 1%)

OUTSTANDING TESTS
------------------------------

- CVN
