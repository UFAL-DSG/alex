Building of acoustic models using KALDI
=======================================

In this document, we describe building of acoustic models 
using the KALDI toolkit using the provided scripts.
These acoustic models can be used with the *Kaldi* decoders
and especially with the Python wrapper of ``LatgenFasterDecoder``
which is integrated with Alex.

We build a different acoustic for a each language and acoustic condition 
pair – ``LANG_RCOND``. At this time, we provide two sets of scripts for 
building English and Czech acoustic models using the VOIP data.

In general, the scripts can be described for the language and acoustic 
condition ``LANG_RCOND`` as follows:

Summary
-------
* This KALDI recipe is based on Voxforge KALDI recipe 
  http://vpanayotov.blogspot.cz/2012/07/voxforge-scripts-for-kaldi.html.
* Requires KALDI installation and Linux environment. (Tested on Ubuntu 10.04, 12.04 and 12.10.)
* Recipes deployed with the Kaldi toolkit are located at
  ``$KALDI_ROOT/egs/name_of_recipe/s[1-5]/``.  
  This recipe requires to set up ``$KALDI_ROOT`` variable 
  so it can use Kaldi binaries and scripts from  ``$KALDI_ROOT/egs/wsj/s5/``.


Details
-------
* Our scripts prepare the data to the expected format to ``data`` directory.
* Experiment files are stored to ``exp`` directory.
* The symbolic links to ``$KALDI_ROOT/wsj/s5/utils`` and ``$KALDI_ROOT/wsj/s5/steps`` are automatically created.
* The ``local`` directory contains scripts for data preparation.
* The files ``path.sh``, ``cmd.sh`` and  ``conf/*`` 
  contain configurations for the recipe.
* Language model (LM) is either built from the training data using 
  `SRILM <http://www.speech.sri.com/projects/srilm/>`_  or we supply one in 
  the ARPA format.


Running experiments
-------------------
Before running the experiments, check that:

* you have the Kaldi toolkit compiled: 
  http://sourceforge.net/projects/kaldi/.
* you have `SRILM <http://www.speech.sri.com/projects/srilm/>`_ compiled. (This is needed for building a language model)
  unless you supply your own LM in the ARPA format.)
* the ``run.sh`` script will see the Kaldi scripts and binaries.
  Check for example that ``$KALDI_ROOT/egs/wsj/s5/utils/parse_options.sh`` is valid path. 
* links in the ``conf`` directory point to the right data and that the 
  setup fits your needs.
* in ``cmd.sh``, you switched to run the training on a SGE[*] grid if 
  required (disabled by default) and 
  ``njobs`` is less than number of your CPU cores.

Start the recipe by running ``bash run.sh``.
It will create ``mfcc``, ``data`` and ``exp`` directories.
If any of them exists, it will ask you if you want them to be overwritten.
After running the experiments, the ``exp`` directory will be backed up to 
the ``Results`` directory.

.. [*] Sun Grid Engine

Extracting the results and trained models
-----------------------------------------
The main script, ``run.sh``, performs not only training of the acoustic 
models, but also decoding.
The acoustic models are evaluated during running the scripts and evaluation 
reports are printed to the standard output.

The ``local/results.py exp`` command extracts the results from the ``exp`` directory.
It is invoked at the end of the ``run.sh`` script and the results are 
thereby stored to ``exp/results.log``.

If you want to use the trained acoustic model outside the prepared script,
you need to build the ``HCLG`` decoding graph yourself.  (See 
http://kaldi.sourceforge.net/graph.html for general introduction to the FST 
framework in Kaldi.)

The simplest way to start with decoding is to use the same LM which
was used by the ``run.sh`` script.  Let's say you want to decode with 
the acoustic model stored in ``exp/tri1``.
Then you need just 3 files:

----

============================  ============================================================================
``exp/tri1/graph/HCLG.fst``   # decoding graph
``exp/tri1/graph/words.txt``  # Word symbol table, a mapping between words and integers which are decoded.
``exp/tri1/final.mdl``        # trained acoustic model 
============================  ============================================================================

----

The ``HCLG.fst`` decoding graph is created by ``utils/mkgraph.sh`` see ``run.sh`` for details.

Credits and license
------------------------
The scripts are based on Voxforge KALDI recipe http://vpanayotov.blogspot.cz/2012/07/voxforge-scripts-for-kaldi.html . The original scripts as well as theses scripts are licensed under APACHE 2.0 license.
