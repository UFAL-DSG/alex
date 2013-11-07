Building of acoustic models using HTK
=====================================

In this document, we describe building of acoustic models using the HTK toolkit using the provided scripts.
These acoustic models can be used with the *OpenJulius* ASR decoder.

We build a different acoustic for a each language and acoustic condition 
pair – ``LANG_RCOND``. At this time, we provide two sets of scripts for 
building English and Czech acoustic models using the VOIP data.

In general, the scripts can be described for the language and acoustic 
condition ``LANG_RCOND`` as follows:

::

  ./env_LANG_RCOND.sh          - includes all necessary training parameters: e.g. the train and test data directories,
                                 training options including cross word or word internal triphones, language model weights
  ./train_LANG_RCOND.sh        - performs the training of acoustic models
  ./nohup_train_LANG_RCOND.sh  - calls the training script using nohup and redirecting the output into the .log_* file

The training process stores some configuration files, the intermediate files, and final models and evaluations in the
``model_LANG_RCOND`` directory:

::

  model_LANG_RCOND/config - config contains the language or recording specific configuration files
  model_LANG_RCOND/temp
  model_LANG_RCOND/log
  model_LANG_RCOND/train
  model_LANG_RCOND/test

Training models for a new language
----------------------------------

Scripts for Czech and English are already created. If you need models for a
new language, you can start by copying all the original scripts and renaming
them so as to reflect the new language in their name (substitute `_en` or
`_cs` with your new language code). You can do this by issuing the following
command (we assume ``$OLDLANG`` is set to either `en` or `cs` and
``$NEWLANG`` to your new language code):

::

  bash htk $ find . -name "*_$OLDLANG*" |
             xargs -n1 bash -c "cp -rvn \$1 \${1/_$OLDLANG/_$NEWLANG}" bash

Having done this, references to the new files' names have to be updated, too:

::

  bash htk $ find . -name "*_$NEWLANG*" -type f -execdir \
             sed --in-place s/_$OLDLANG/_$NEWLANG/g '{}' \;

Furthermore, you need to adjust language-specific resources to the new 
language in the following ways:

  ``htk/model_voip_$NEWLANG/monophones0``
    List all the phones to be recognised, and the special `sil` phone.

  ``htk/model_voip_$NEWLANG/monophones1``
    List all the phones to be recognised, and the special `sil` and 
    `sp` phones.

  ``htk/model_voip_$NEWLANG/tree_ques.hed``
    Specify phonetic questions to be used for building the decision 
    tree for phone clustering (see [HTKBook]_, Section 10.5).

  ``htk/bin/PhoneticTranscriptionCS.pl``
    You can start from this script or use a custom one. The goal is to 
    implement the orthography-to-phonetics mapping to obtain sequences of 
    phones from transcriptions you have.

  ``htk/common/cmudict.0.7a`` and ``htk/common/cmudict.ext``
    This is an alternative approach to the previous point – instead of 
    programming the orthography-to-phonetics mapping, you can list it 
    explicitly in a pronouncing dictionary.

    Depending on the way you want to implement the mapping, you want to set
    ``$OLDLANG`` to either `cs` or `en`.

To make the scripts work with your new files, you will have to update
references to scripts you created. All scripts are stored in the ``htk/bin``,
``htk/common``, and ``htk`` directories as immediate children, so you can make
the substitutions only in these files.

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


.. [HTKBook] The HTK Book, version 3.4
