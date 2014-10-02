#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import math
import random
import copy
import numpy as np
import numpy.random as rng

from exceptions import FFNNException

class FFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function tanh
      -- output layer - activation function softmax
    """
    def __init__(self):
        self.weights = []
        self.biases = []

    def __str__(self):
        return unicode(self)

    def __unicode__(self):
        s = []
        s.append("Network layers:")
        for w, b in zip(self.weights, self.biases):
            s.append(str(w.shape)+" : " + str(b.shape))

        return "\n".join(s)

    def add_layer(self, w, b):
        """ Add next layer into the network.

        :param w: next layer weights
        :param b: next layer biases
        :return: none
        """

        if self.weights:
            s = self.weights[-1].shape
            n_s_w = w.shape
            n_s_b = b.shape

            if s[1] != n_s_w[0] or n_s_w[1] != n_s_b[0]:
                raise FFNNException("Adding an incompatible layer: cur_layer: " + str(s) + " next w: " + str(n_s_w) + " next s: " + str(n_s_b))

        self.weights.append(w)
        self.biases.append(b)

    def set_input_norm(self, m, std):
        self.input_m = m
        self.input_std = std
    
    def sigmoid(self, y):
        y =  1/ (1 + np.exp(-y))
        return y

    def tanh(self, y):
        y =  np.tanh(y)
        return y

    def softmax(self, y):
        ey = np.exp(y - y.max(axis=0))
        y = ey / ey.sum(axis=0)

        # print ey
        # print np.sum(ey, axis = 0)
        # print np.sum(ey)
        # print sum(ey)

        return y

    def predict(self, input):
        """ Returns the output of the last layer.

         As it is output of a layer with softmax activation function, the output is a vector of probabilities of
           the classes being predicted.

        :param input: input vector for the first NN layer.
        :return: return the output of the last activation layer
        """

        try:
            input -= self.input_m
            input /= self.input_std
            
            y = input
            
            for w, b in zip(self.weights[:-1], self.biases[:-1]):
                y = self.tanh(np.dot(y,w)+b)

            y = self.softmax(np.dot(y,self.weights[-1])+self.biases[-1])
        except ValueError:
            print "y.shape:", y.shape
            print "w.shape:", w.shape
            print "b.shape:", b.shape
            print "w[-1].shape:", self.weights[-1].shape
            print "b[-1].shape:", self.biases[-1].shape

        return y

    def load(self, file_name):
        """ Loads saved NN.

        :param file_name: file name of the saved NN
        :return: None
        """
        with open(file_name, "rb") as f:
            self.weights, self.biases, self.input_m, self.input_std = pickle.load(f)

    def save(self, file_name):
        """ Saves the NN into a file.

        :param file_name: name of the file where the NN will be saved
        :return: None
        """
        with open(file_name, "wb") as f:
            pickle.dump((self.weights, self.biases, self.input_m, self.input_std), f)

