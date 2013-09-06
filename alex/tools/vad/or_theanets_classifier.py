#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle
import gzip
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import tempfile
import theano
import lmj.cli
import theanets

lmj.cli.enable_default_logging()

X = np.array([
               [0.0, 0.0],
               [0.0, 1.0],
               [1.0, 0.0],
               [1.0, 1.0],
             ])

Y = np.array([0, 1, 1, 1, ])

print X.shape
print Y.shape

train = [X,  Y.astype('int32')]

n_iter = 1000
n_hidden = 3

e = theanets.Experiment(theanets.Classifier,
                        layers=(2, n_hidden, 2),
#                        activation = 'tanh',
                        learning_rate=1.01,
                        learning_rate_decay=0.0,
                        momentum=0.0,
                        patience=1,
                        optimize="sgd",
                        num_updates=1,
                        validate=1,
#                        tied_weights=False,
#                        batch_size=32,
                        )

for i in xrange(n_iter):
    e.run(train, train)

print e.network.predict(X)


