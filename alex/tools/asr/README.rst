Building of acoustic models using HTK
=====================================

In this document, we describe building of acoustic models using the HTK toolkit using the provided scripts.
These acoustic models can be used with the *OpenJulius* ASR decoder.

We build a different acoustic for a each language and acoustic condition pair - LANG_RCOND. At this time, we provide
two sets of scripts for building English and Czech acoustic models using the VOIP data.

In general, the scripts can be described for the language and acoustic condition LANG_RCOND as follows:

::

  ./env_LANG_RCOND.sh          - includes all necessary training parameters: e.g. the train and test data directories,
                                 training options including cross word or word internal triphones, language model weights
  ./train_LANG_RCOND.sh        - performs the training of acoustic models
  ./nohup_train_LANG_RCOND.sh  - calling the training script using nohup and redirecting the output into the .log_* file

The training process stores some configuration files, the intermediate files, and final models and evaluations in the
model_LANG_RCOND directory:

::

  model_LANG_RCOND/config - config contains the language or recording specific configuration files
  model_LANG_RCOND/temp
  model_LANG_RCOND/log
  model_LANG_RCOND/train
  model_LANG_RCOND/test

Scripts for the Czech and English languages are already created. If you need models for a new language, you can start
by cloning one of the existing scripts,

Credits and the licence
-------------------------------
The scripts are based on the HTK Wall Street Journal Training Recipe written by Keith Vertanen (http://www.keithv.com/software/htk/).
His code is released under the new BSD licence. The licence note is at http://www.keithv.com/software/htk/.
As a result we can re-license the code under the APACHE 2.0 license.

The results
------------------------------
- total training data for voip_en is about 20 hours
- total training data for voip_cs is about 8 hours
- mixtures - there is 16 mixtures is slightly better than 8 mixtures for voip_en
- there is no significant difference in alignment of transcriptions with -t 150 and -t 250
- the Julius ASR performance is about the same as of HDecode
- HDecode works well when cross word phones are trained, however the 
  -	performance of HVite decreases significantly
- when only word internal triphones are trained then the HDecode works, 
  - however, its performance is worse than the HVite with a bigram LM
- word internal triphones work well with Julius ASR, do not forget disable CCD (it does not need context handling -
  though it still uses triphones)
- there is not much gain using the trigram LM in the Caminfo domain (about 1%)

