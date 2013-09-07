The frontend for VAD should not include energy (C0) coefficient since then the VAD would depend on the volume
of the audio and whispered speech would not be detected.

It looks like that the English VAD works well even for Czech.


Experiments and the notes:

Testing is done on the first 20% of training data. If the data is 100k examples, then the test data is the first 20k examples
   and the train data is the remaining 80% of the original train data.

Evaluation of GMM vad
=========================

1) 64 mixtures, data 10k examples,
    test data accuracy (first 2k examples): 80.4 %
2) 64 mixtures, data 100k examples,
    test data accuracy (first 20k examples): 85.5 %
2) 64 mixtures, data 1000k examples,
    test data accuracy (first 200k examples): xxx %

Evaluation of NN VAD
====================

1) So far, I did not get better results using more than 1 frame. Tested only with pybrain.

2) When comparing 4 hidden layers, and 1 hidden layer,

 - 1 layer VAD is better by 3 % on 100k examples,
 - 1 layer system is about 1 % worse on 1000k and more examples

3) pybrain, 4 hidden layers, 128 units, 1 last frame
    data 100k examples, test data accuracy (first 20k examples): 82.4 %
    data 1000k examples, test data accuracy (first 200k examples): 87.5 %
    data 5000k examples, test data accuracy (first 1000k examples): 87.5 %
    iterations: 1273, 124, 24

4) pybrain, 4 hidden layers, 128 units, 10 last frames
    data 100k examples, test data accuracy (first 20k examples): 82.0 %
    data 1000k examples, test data accuracy (first 200k examples): 86.5 %
    data 5000k examples, test data accuracy (first 1000k examples): 83.5 %

    the training was not probably finished, though I did not have high hopes that I would get better results
    iterations: 550, 55, 10

5) pybrain, 4 hidden layers, 128 units, 1 last frame
    data 100k examples, test data accuracy (first 20k examples): 85.4 %
    data 1000k examples, test data accuracy (first 200k examples): 84.5 - 87.5 %
    data 5000k examples, test data accuracy (first 1000k examples): 86.5 %

    the training was not probably finished, though I did not have high hopes that I would get better results
    iterations: 811, 81, 14

5) pybrain, 4 hidden layers, 128 units, 10 last frames
    data 100k examples, test data accuracy (first 20k examples): 82.0 %
    data 1000k examples, test data accuracy (first 200k examples): 83.5 - 84.5 %
    data 5000k examples, test data accuracy (first 1000k examples): 82.5 - 83.5%

    the training was not probably finished, though I did not have high hopes that I would get better results
    iterations:  559, 52, 8

6) theanets, 4 hidden layers, 128, units, 1 last frame, hf-optimiser
    data 100k examples, test data accuracy (first 20k examples): 87.70 %
    data 1000k examples, test data accuracy (first 200k examples): X %
    data 5000k examples, test data accuracy (first 1000k examples): X %
