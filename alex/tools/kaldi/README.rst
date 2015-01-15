Building of acoustic models using KALDI
=======================================

In this document, we describe building of acoustic models 
using the KALDI toolkit and the provided scripts.
These acoustic models can be used with the *Kaldi* decoders
and especially with the Python wrapper of ``LatgenFasterDecoder``
which is integrated with Alex.

We build a different acoustic model for a each language and acoustic condition 
pair – ``LANG_RCOND``. At this time, we provide two sets of scripts for 
building English and Czech acoustic models using the VOIP data.

In general, the scripts can be described for the language and acoustic 
condition ``LANG_RCOND`` as follows:

Summary
-------
* Requires KALDI installation and Linux environment. (Tested on Ubuntu 10.04, 12.04 and 12.10.)
  Note: We recommend Kaldi fork `Pykaldi <http://github.com/UFAL-DSG/pykaldi>`_, 
  because you will need it also for integrated Kaldi decoder to Alex.
* Recipes deployed with the Kaldi toolkit are located at
  ``$KALDI_ROOT/egs/name_of_recipe/s[1-5]/``.  
  This recipe requires to set up ``$KALDI_ROOT`` variable 
  so it can use Kaldi binaries and scripts from  ``$KALDI_ROOT/egs/wsj/s5/``.


Details
-------
* The recommended settings are stored at ``env_LANG_RCONG.sh`` e.g ``env_voip_en.sh``
* We recommend to adjust the settings in file `env_LANG_RCONG_CUSTOM.sh`` e.g. ``env_voip_en_CUSTOM.sh``. See below.
  Do not commit this file to the git repository!
* Our scripts prepare the data to the expected format to ``$WORK`` directory.
* Experiment files are stored to ``$EXP`` directory.
* The symbolic links to ``$KALDI_ROOT/wsj/s5/utils`` and ``$KALDI_ROOT/wsj/s5/steps`` are automatically created.
* The files ``path.sh``, ``cmd.sh`` are necessary to ``utils`` and ``steps`` scripts. Do not relocate them! 
* Language model (LM) is either built from the training data using 
  `SRILM <http://www.speech.sri.com/projects/srilm/>`_  or specified in ``env_LANG_RCOND.sh``.


Example of ``env_voip_en_CUSTOM.sh``

.. code-block:: bash

    # uses every utterance for the recipe every_N=10 is nice for debugging
    export EVERY_N=1   
    # path to built Kaldi library and scripts
    export KALDI_ROOT=/ha/work/people/oplatek/pykaldi-cluster

    export DATA_ROOT=/net/projects/vystadial/data/asr/cs/voip/
    export LM_paths="build0 $DATA_ROOT/arpa_bigram"
    export LM_names="build0 vystadialbigram"

    export CUDA_VISIBLE_DEVICES=0  # only card 0 (Tesla on Kronos) will be used for DNN training


Running experiments
-------------------
Before running the experiments, check that:

* you have the Kaldi toolkit compiled: 
  - http://github.com/UFAL-DSG/pykaldi (Recommended Kaldi fork, tested, necessary for further Alex integration)
  - http://sourceforge.net/projects/kaldi/ (alternative, main Kaldi repository) 
  - In order to compile Kaldi we suggest:

.. code-block:: bash

      # build openfst
      pushd kaldi/tools
      make openfst_tgt
      popd

.. code-block:: bash
        
      # download ATLAS headers
      pushd kaldi/tools
      make atlas
      popd

.. code-block:: bash

      # generate Kaldi makefile ``kaldi.mk`` and compile Kaldi
      pushd kaldi/src
      ./configure
      make && make test
      popd

* you have `SRILM <http://www.speech.sri.com/projects/srilm/>`_ compiled. (This is needed for building a language model)
  unless you supply your own LM in the ARPA format.)

.. code-block:: bash

  pushd kaldi/tools
  # download the srilm.tgz archive from http://www.speech.sri.com/projects/srilm/download.html
  ./install_srilm.sh
  pushd

* the ``train_LANG_RCOND`` script will see the Kaldi scripts and binaries.
  Check for example that ``$KALDI_ROOT/egs/wsj/s5/utils/parse_options.sh`` is valid path. 
* in ``cmd.sh``, you switched to run the training on a SGE[*] grid if 
  required (disabled by default) and 
  ``njobs`` is less than number of your CPU cores.

Start the recipe by running ``bash train_LANG_RCOND.sh``.

.. [*] Sun Grid Engine

Extracting the results and trained models
-----------------------------------------
The main script, ``bash train_LANG_RCOND.sh``, performs not only training of the acoustic 
models, but also decoding.
The acoustic models are evaluated during running the scripts and evaluation 
reports are printed to the standard output.

The ``local/results.py exp`` command extracts the results from the ``$EXP`` directory.
It is invoked at the end of the ``train_LANG_RCOND.sh`` script.

If you want to use the trained acoustic model outside the prepared script,
you need to build the ``HCLG`` decoding graph yourself.  (See 
http://kaldi.sourceforge.net/graph.html for general introduction to the FST 
framework in Kaldi.)
The ``HCLG.fst`` decoding graph is created by ``utils/mkgraph.sh``.
See ``run.sh`` for details.

Credits and license
------------------------
The scripts were based on Voxforge KALDI recipe 
http://vpanayotov.blogspot.cz/2012/07/voxforge-scripts-for-kaldi.html . 
The original scripts as well as theses scripts are licensed under APACHE 2.0 license.
