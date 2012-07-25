INTRODUCTION
-------------------------------
The acoustic modelling is using the HTK and the aim is to build word internal triphone models for different languages, for example English and Czech.

For each language or recording conditions a seperate direoctry based on some previous direcotry must be created: 

A setup for a new language and recording conditions (RCOND_LANG) would need:

Files:

./env_RCOND_LANG.sh          - settings of all importan directories
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


OUTSTANDING TESTS
------------------------------

+ total training data for voip_en is about 40 hours
+ total training data for voip_cs is about 8 hours
+ mixtures - there is 16 mixtures is slightly better than 8 mixtures for voip_en
+ there is no signigicant difference in alignment of transcriptions with -t 150 and -t 250

- add to voip_en non speech events also add files only with silence! or noise (hesitation)
- CVN
- test with Julius and the trigram language model
