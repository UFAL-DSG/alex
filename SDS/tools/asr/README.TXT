INTRODUCTION
-------------------------------
The acoustic modelling is using the HTK and the aim is to build word internal triphone models for different languages, for example English and Czech.

For each language or recording conditions a seperate direoctry based on some previous direcotry must be created: 

A setup for a new language and recording conditions (RCOND_LANG) would need:

Files:

./env_RCOND_LANG.sh    - settings of all importan directories
./train_RCOND_LANG.sh  - the complete trainign script

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
We have to ask for permition to distribute hic code.

2012-07-19 Filip Jurcicek


