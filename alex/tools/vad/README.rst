Building a voice activity detector (VAD)
========================================

It looks like that the English VAD works well even for Czech. However, language independent VAD should be trained
on all available languages.

The goal is to train a robust multi-language VAD.

Experiments and the notes for the NN VAD
----------------------------------------

- testing is done on the first 20% of training data. If the data is 100k examples, then the test data is the first 20k examples
  and the train data is the remaining 80% of the original train data.

- dropouts in hidden layers does not work with the HF optimiser
 
- HF preconditioner does not impact the performance of training, it converges without it so enabling it does not help
 
- L2 regularisation must be very small less then 0.001 for network with 55k parameters

- test MFCC with C0  (on a small training data 100k - it can give up to 2% absolute improvement)

- training on last 10 frames gives only 0.5 % absolute improvement (5 % relative error reduction) on the training data 1M,
  on less data it is worse by 4 % absolute

  - maybe on more then 10M training data it would help more
  - please note that this improvement was achieved only with small number of hidden units - 32, 64

- experiment N. 16 is the best:

  - NN 32 hidden units, 1M training examples, 1 last frame, using C0

Using theano-nets
~~~~~~~~~~~~~~~~~
To train the neural nets please download from http://github.com/lmjohns3/theano-nets or

::

  $ git clone git@github.com:lmjohns3/theano-nets.git

Missing test
~~~~~~~~~~~~
There are no missing tests at this moment.


Experiments
~~~~~~~~~~~~~~~~~~~~
This is a list of evaluation notes and experiments:

#. When comparing 4 hidden layers, and 1 hidden layer,

   - 1 layer VAD is better by 3 % on 100k examples,
   - 1 layer system is about 1 % worse on 1000k and more examples

#. pybrain, 4 hidden layers, 128 units, 1 last frame

   - data 100k examples, test data accuracy (first 20k examples): 82.4 %
   - data 1000k examples, test data accuracy (first 200k examples): 87.5 %
   - data 5000k examples, test data accuracy (first 1000k examples): 87.5 %
   - iterations: 1273, 124, 24

#. pybrain, 4 hidden layers, 128 units, 10 last frames

   - data 100k examples, test data accuracy (first 20k examples): 82.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 86.5 %
   - data 5000k examples, test data accuracy (first 1000k examples): 83.5 %
   - the training was not probably finished, though I did not have high hopes that I would get better results
   - iterations: 550, 55, 10

#. pybrain, 4 hidden layers, 128 units, 1 last frame

   - data 100k examples, test data accuracy (first 20k examples): 85.4 %
   - data 1000k examples, test data accuracy (first 200k examples): 84.5 - 87.5 %
   - data 5000k examples, test data accuracy (first 1000k examples): 86.5 %
   - the training was not probably finished, though I did not have high hopes that I would get better results
   - iterations: 811, 81, 14

#. pybrain, 4 hidden layers, 128 units, 10 last frames

   - data 100k examples, test data accuracy (first 20k examples): 82.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 83.5 - 84.5 %
   - data 5000k examples, test data accuracy (first 1000k examples): 82.5 - 83.5%
   - the training was not probably finished, though I did not have high hopes that I would get better results
   - iterations:  559, 52, 8

#. theanets, 4 hidden layers, 128, units, 1 last frame, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 87.7 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.5 %
   - data 5000k examples, test data accuracy (first 1000k examples): 89.5 % # iter 18/30

#. theanets, 4 hidden layers, 128, units, 10 last frames, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 82.5 - 84.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.5 % # iter 26/30 - from 21/30 not improving

#. theanets, 4 hidden layers, 256, units, 1 last frame, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 87.4 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.4 % # iter 21/30

#. theanets, 4 hidden layers, 256, units, 10 last frames, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 85.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 88.9 % # iter 18/30

#. theanets, 4 hidden layers, 64, units, 1 last frame, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 88.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.8 %

#. theanets, 4 hidden layers, 64, units, 10 last frames, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 84.4 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.9 %

#. theanets, 4 hidden layers, 64, units, 1 last frame, hf-optimiser, USING C0

   - data 100k examples, test data accuracy (first 20k examples): 88.0 %
   - data 1000k examples, test data accuracy (first 200k examples): 91.4 %

#. theanets, 4 hidden layers, 64, units, 10 last frames, hf-optimiser, USING C0

   - data 100k examples, test data accuracy (first 20k examples): 88.9 %
   - data 1000k examples, test data accuracy (first 200k examples): 91.8 %

#. theanets, 4 hidden layers, 32, units, 1 last frame, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 88.7 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.6 %
   - data 5000k examples, test data accuracy (first 1000k examples): 89.6 %

#. theanets, 4 hidden layers, 32, units, 10 last frames, hf-optimiser

   - data 100k examples, test data accuracy (first 20k examples): 86.7 %
   - data 1000k examples, test data accuracy (first 200k examples): 89.9 %
   - data 5000k examples, test data accuracy (first 1000k examples): 90.1 %

#. theanets, 4 hidden layers, 32, units, 1 last frame, hf-optimiser, USING C0

   - data 100k examples, test data accuracy (first 20k examples): 90.9 %
   - data 1000k examples, test data accuracy (first 200k examples): 91.3 %
   - data 5000k examples, test data accuracy (first 1000k examples): 91.4 %

#. theanets, 4 hidden layers, 32, units, 10 last frames, hf-optimiser, USING C0

   - data 100k examples, test data accuracy (first 20k examples): 90.6 %
   - data 1000k examples, test data accuracy (first 200k examples): 91.1 %
   - data 5000k examples, test data accuracy (first 1000k examples): 91.7 %

Evaluation of the GMM VAD
-------------------------
Clearly, the NN VAD achieves about 5 % absolute better results in frame accuracy.

#. 64 mixtures, data 10k examples,

   - test data accuracy (first 2k examples): 80.4 %

#. 64 mixtures, data 100k examples,

   - test data accuracy (first 20k examples): 85.5 %

#. 64 mixtures, data 1000k examples,

   - test data accuracy (first 200k examples): 85.7 %

#. 64 mixtures, data 5000k examples,

   - test data accuracy (first 2000k examples): X %
