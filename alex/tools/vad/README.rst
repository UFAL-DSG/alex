Building a voice activity detector (VAD)
========================================

This text described how to build a voice activity detector (VAD) for Alex.
This work builds multilingual VAD. That means that we do not have VADs for individual languages but rather only one.
It appears that NN VAD has the capacity to distinguish between non-speech and speech in any language.

As of now, we use VAD based on neural networks (NNs) implemented in the Theano toolkit. 
The main advantage that the same code can efficiently run both CPUs and GPUs and Theano implements automatic derivations.
Automatic derivations is very useful especially when gradient descend techniques, such as stochastic gradient descent, 
are used for model parameters optimisation.

Old GMM code is still present but it may not work and its performance would be significantly worse that of 
the current NN implementation.

Experiments and the notes for the NN VAD
----------------------------------------

- testing is performed on randomly sampled data points (20%) from the entire set 

- L2 regularisation must be very small, in addition it does not help much

- instead of MFCC, we use mel-filter banks coefficients only. It looks like the performance is the same or even better

- as of 2014-09-19 the best compromise between the model complexity and the performance appears to be.
  
  - 30 previous frames
  - 15 next frames
  - 512 hidden units
  - 4 hidden layers
  - tanh hidden layer activation
  - 4x amplification of the central frame compared to outer frames
  - discriminative pre-training

  - given this setup we get about 95.3 % frame accuracy on about 27 million of all data


Data
----

::

  data_vad_sil    # a directory with only silence, noise data and its mlf file
  data_voip_cs    # a directory where CS data reside and its MLF (phoneme alignment)
  data_voip_en    # a directory where EN data reside and its MLF (phoneme alignment)
  model_voip      # a directory where all the resulting models are stored.
  
  
Scripts
-------

::

  upload_models.sh                     # uploads all available models in ``model_voip`` onto the Alex online update server
  train_voip_nn_theano_sds_mfcc.py     # this is the main trainign script, see its help for more details
  bulk_train_nn_theano_mbo_31M_sgd.sh  # script with curently ``optimal`` setting for VAD


Comments
--------

To save some time especially for multiple experiments on the same data, we store preprocessed speech parametrisation.
The speech parametrisation is stored because it takes about 7 hours to produce.
However, it takes only 1 minute to load from a disk file. 
The ``model_voip`` directory stores this speech parametrisation in ``*.npc`` files.
There fore if new data is added, then these NPC files must be deleted.
If there are no NPC files then they are automatically generated from the available WAV files.

The ``data_voip_{cs,en}`` alignment files (mlf files) can be trained using scripts ``alex/alex/tools/htk`` or ``alex/alex/tools/kaldi``.
See the ``train_voip_{cs,en}.sh`` scripts in one of the directories.
Note that the Kaldi scripts first store alignment in ``ctm`` format and later converts it to ``mlf`` format.

