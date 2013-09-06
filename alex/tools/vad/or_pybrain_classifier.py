#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime

from collections import deque

from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure import TanhLayer, SigmoidLayer, SoftmaxLayer
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer, RPropMinusTrainer

import __init__

n_epoch = 10000
sigmoid = True
bprop = True

n_hidden = 3

if sigmoid:
    net = buildNetwork(2,n_hidden,2, hiddenclass=SigmoidLayer, outclass=SoftmaxLayer, bias = True)
else:
    net = buildNetwork(2,n_hidden,2, hiddenclass=TanhLayer, outclass=SoftmaxLayer, bias = True)

ds = SupervisedDataSet(2, 2)

ds.addSample((0,0), (1,0))
ds.addSample((0,1), (0,1))
ds.addSample((1,0), (0,1))
ds.addSample((1,1), (0,1))

if bprop:
    trainer = BackpropTrainer(net, dataset = ds)
else:
    trainer = RPropMinusTrainer(net, dataset = ds)

for i in range(n_epoch):
    trainer.train()

print net.activateOnDataset(ds)

