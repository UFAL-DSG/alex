#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import random
import numpy as np

import theano
from theano import function
from theano import tensor as T
import numpy.random as rng

rng.seed(0)


def discrete_dropout(x, dropout, dropout_on=None):
    """
    Implements drop out for a discrete input.

    It means that a dropout proportion is randomly replaced by 0.

    :param x:       the input variable to which the dropout is applied
    :param dropout: the proportion of elements dropped out from the input
    :return:
    """
    if dropout:
        if not dropout_on:
            dropout_on = theano.shared(np.int32(1))

        rng = np.random.RandomState(0)
        srng = T.shared_randomstreams.RandomStreams(rng.randint(999999))

        # p is a probability of success
        mask = srng.binomial(n=1, p=1.0 - dropout, size=x.shape)
        x = x * dropout_on * T.cast(mask, 'int32') \
            + x * (1 - dropout_on)

    else:
        if not dropout_on:
            dropout_on = theano.shared(np.int32(0))

    return x, dropout_on

def continuous_dropout(x, dropout, dropout_on=None):
    """
    Implements drop out for a continuous input.

    It means that a dropout proportion is randomly replaced by 0.0.

    :param x:       the input variable to which the dropout is applied
    :param dropout: the proportion of elements dropped out from the input
    :return:
    """
    if dropout:
        if not dropout_on:
            dropout_on = theano.shared(np.cast[theano.config.floatX](1.0), borrow=True)

        rng = np.random.RandomState(0)
        srng = T.shared_randomstreams.RandomStreams(rng.randint(999999))

        # p is a probability of success
        mask = srng.binomial(n=1, p=1.0 - dropout, size=x.shape)
        x = x * dropout_on *  T.cast(mask, theano.config.floatX) +\
            x * (1 - dropout_on) * (1 - dropout)

    else:
        if not dropout_on:
            dropout_on = theano.shared(np.cast[theano.config.floatX](0.0), borrow=True)

    return x, dropout_on

class TheanoFFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function tanh
      -- output layer - activation function softmax
    """

    def __init__(self, n_inputs=0, n_hidden_units=0, n_hidden_layers=0, n_outputs=0,
                 training_set_x=None, training_set_y=None, prev_frames=0, next_frames=0, amplify_center_frame=1.0,
                 batch_size=0, hidden_activation='tanh', weight_l2=1e-6, classifier='categorical', weight_bias=None,
                 gradient_treatment='clipping', g_min=-1e6, g_max=1e6,
                 move_training_set_to_GPU=False,
                 input_dropout=None,
                 embedding_dropout=None,
                 max_pooling_dropout=None,
                 hidden_dropout=None,
                 embedding_size=0,
                 vocabulary_size=0,
                 # x - number of convolved input elements
                 # the smallest meaningful convolution is 2 (of 2 elements from the input)
                 convolution_size=0,
                 max_pooling=False,
    ):
        self.n_inputs = n_inputs

        if hidden_activation == 'tanh':
            self.hidden_activation = T.tanh
        elif hidden_activation == 'sigmoid':
            self.hidden_activation = T.nnet.sigmoid
        elif hidden_activation == 'softplus':
            self.hidden_activation = T.nnet.softplus
        elif hidden_activation == 'relu':
            self.hidden_activation = lambda x: T.maximum(0, x)
        else:
            raise NotImplementedError

        self.classifier = classifier
        self.weight_bias = weight_bias
        self.gradient_treatment = gradient_treatment
        self.g_min = g_min
        self.g_max = g_max
        self.move_training_set_to_GPU = move_training_set_to_GPU
        self.input_dropout = input_dropout
        self.embedding_dropout = embedding_dropout
        self.max_pooling_dropout = max_pooling_dropout
        self.hidden_dropout = hidden_dropout
        self.embedding_size = embedding_size
        self.convolution_size = convolution_size
        self.max_pooling = max_pooling
        self.vocabulary_size = vocabulary_size

        self.n_outputs = n_outputs
        self.weight_l2 = weight_l2

        self.training_set_x = training_set_x
        self.training_set_y = training_set_y

        self.prev_frames = prev_frames
        self.next_frames = next_frames
        self.batch_size = batch_size

        amp_min = 1.0 / amplify_center_frame
        amp_max = 1.0

        amp_prev = [amp_min + (float(i) / self.prev_frames) * (amp_max - amp_min) for i in range(0, self.prev_frames)]
        amp_next = [amp_min + (float(i) / self.next_frames) * (amp_max - amp_min) for i in range(0, self.next_frames)]
        self.amp = amp_prev + [amp_max, ] + list(reversed(amp_next))
        self.amp_vec = np.repeat(self.amp, n_inputs / (self.prev_frames + 1 + self.next_frames))

        if n_inputs:
            self.build_model(n_hidden_units, n_hidden_layers)

    def build_model(self, n_hidden_units, n_hidden_layers, old_params=None):
        if self.classifier == 'categorical':
            self.output_activation = T.nnet.softmax
        elif self.classifier == 'binary-set':
            def binary_softmax(y):
                y1 = y[:, :y.shape[1] / 2]
                y0 = y[:, y.shape[1] / 2:]

                m = T.maximum(y1, y0)

                # removing max(y1, y0) to prevent +inf from exp(y)
                # adding a small constant to prevent a division by zero
                e1 = T.exp(y1 - m) + 1e-20
                e0 = T.exp(y0 - m) + 1e-20

                sum_e = e1 + e0

                e1 = e1 / sum_e
                e0 = e0 / sum_e

                bs = T.concatenate((e1, e0), axis=1)

                return bs

            self.output_activation = binary_softmax

        else:
            raise NotImplementedError
            
        # Keep model params here.
        self.params = []

        # input
        x = T.imatrix('X')

        x, self.input_dropout_on = discrete_dropout(x, self.input_dropout)


        if old_params:
            e = theano.shared(old_params.pop(0), 'E')
        else:
            e = theano.shared(np.asarray(rng.uniform(-0.01, 0.01, size=(self.vocabulary_size, self.embedding_size)), dtype=theano.config.floatX), 'E')

        self.params.append(e)

        ex = e[x]

        ex, self.embedding_dropout_on = continuous_dropout(ex, self.embedding_dropout)

        if self.convolution_size > 1:
            conv_ex = [ex[:,i:i + ex.shape[1]-self.convolution_size+1] for i in range(0, self.convolution_size)]
            conv_ex = T.concatenate(conv_ex, axis=2)

            if old_params:
                w = theano.shared(old_params.pop(0), 'conv_W', borrow=True)
                b = theano.shared(old_params.pop(0), 'conv_b')
            else:
                n1 = self.embedding_size * self.convolution_size
                n2 = self.embedding_size
                w = theano.shared(
                    np.asarray(rng.uniform(
                        low=-np.sqrt(6. / (n1 + n2)),
                        high=np.sqrt(6. / (n1 + n2)),
                        size=(n1, n2)),
                               dtype=theano.config.floatX),
                    'conv_W', borrow=True)
                b = theano.shared(np.zeros(n2, dtype=theano.config.floatX), 'conv_b')
            self.params.append(w)
            self.params.append(b)

            ex = T.tensordot(conv_ex, w, 1) + b

        if self.max_pooling:
            y = ex.max(axis=1)
        else:
            y = ex.reshape((x.shape[0],  ex.shape[0]*ex.shape[1]*ex.shape[2] // x.shape[0]))

        y, self.max_pooling_dropout_on = continuous_dropout(y, self.max_pooling_dropout)

        # Build the layered neural network.
        if old_params:
            self.n_hidden = self.n_hidden + [n_hidden_units, ] * n_hidden_layers
        else:
            self.n_hidden = [n_hidden_units, ] * n_hidden_layers

        activations = [self.hidden_activation, ] * len(self.n_hidden)
        # NOTE: The last function goes to the output layer.
        activations.extend([self.output_activation, ])

        assert len(self.n_hidden) + 1 == len(activations)

        if not self.max_pooling:
            layers = [self.n_inputs*self.embedding_size] + self.n_hidden + [self.n_outputs]
        else:
            layers = [self.embedding_size] + self.n_hidden + [self.n_outputs]

        if self.hidden_dropout:
            self.hidden_dropout_on = theano.shared(np.cast[theano.config.floatX](1.0), borrow=True)
        else:
            self.hidden_dropout_on = theano.shared(np.cast[theano.config.floatX](1.0), borrow=True)

        # Iterate over pairs of adjacent layers.
        for i, (n1, n2, act) in enumerate(zip(layers[:-1], layers[1:], activations)):
            # print i, n1, n2, act
            last_layer = False if i < len(layers) - 2  else True

            if old_params:
                #print "using old params"
                # init an existing layer
                w = theano.shared(old_params.pop(0), 'W%d' % i, borrow=True)
                b = theano.shared(old_params.pop(0), 'b%d' % (i + 1))
            else:
                #print "sampling new params"
                w = theano.shared(
                    np.asarray(rng.uniform(
                        low=-np.sqrt(6. / (n1 + n2)),
                        high=np.sqrt(6. / (n1 + n2)),
                        size=(n1, n2)),
                               dtype=theano.config.floatX),
                    'W%d' % i, borrow=True)
                b = theano.shared(np.zeros(n2, dtype=theano.config.floatX), 'b%d' % (i + 1))
            self.params.append(w)
            self.params.append(b)

            y = act(T.dot(y, w) + b)

            if not last_layer:
                y, self.hidden_dropout_on = continuous_dropout(y, self.hidden_dropout, self.hidden_dropout_on)

        self.f_y = function([x], y)  # PREDICTION FUNCTION

        # Define the loss function.
        if self.classifier == 'categorical':
            # The desired output vector. For each data point in X, onlu one number
            true_y = T.ivector('true_Y')
            # log-likelihood
            L = T.log(y[T.arange(y.shape[0]), true_y])
            # MEAN log-likelihood.
            loss = T.mean(L)
        elif self.classifier == 'binary-set':
            # The desired output matrix, NOTE: that we have multiple binary labels for each entry data point.
            true_y = T.fmatrix('true_Y')
            # log-likelihood 
            if self.weight_bias != None:
                L = self.weight_bias * true_y * T.log(y)
            else:
                L = true_y * T.log(y)

            # MEAN log-likelihood - using the mean to make it independent of the size of outputs and the size of a
            # mini-batch
            loss = T.mean(L)
        else:
            raise NotImplementedError

        # Add regularization.
        l2 = 0
        for p in self.params[1::2]:
            l2 += (p ** 2).sum()
        loss -= self.weight_l2 * l2

        self.f_loss = function([x, true_y], loss, allow_input_downcast=True)

        # Derive the gradients for the parameters.
        g_loss = T.grad(loss, wrt=self.params)
        self.f_g_loss = function([x, true_y], g_loss)

        # Create a training function for maximization
        updates = []
        learning_rate = T.fscalar()
        for p, g in zip(self.params, g_loss):
            if self.gradient_treatment == 'clipping':
                updates.append((p, p + learning_rate * g.clip(self.g_min, self.g_max)))
            elif self.gradient_treatment == 'normalisation':
                updates.append((p, p + learning_rate * g / g.norm(2)))
            else:
                raise NotImplementedError

        if (not self.move_training_set_to_GPU) or self.prev_frames or self.next_frames:
            self.f_train_ret_loss = function(
                inputs=[x, true_y, learning_rate],
                outputs=loss,
                updates=updates,
                allow_input_downcast=True
            )

        else:
            # GPU data multiplications, it appears that this version is not faster compared to the CPU version
            self.shared_training_set_x = theano.shared(self.training_set_x, 'training_set_x')
            self.shared_training_set_y = theano.shared(self.training_set_y, 'training_set_y')

            m = T.lscalar()
            self.f_train_ret_loss_GPU = function(
                inputs=[m, learning_rate],
                outputs=loss,
                updates=updates,
                givens={
                    x:      self.shared_training_set_x[m * self.batch_size:(m + 1) * self.batch_size],
                    true_y: self.shared_training_set_y[m * self.batch_size:(m + 1) * self.batch_size],
                },
                allow_input_downcast=True
            )

    def add_hidden_layer(self, n_hidden_units):
        ''' It is like a building a complete network, you have to just initialise the network using 
        the parameters from the previous network.
        '''

        # Keep model params here.
        old_params = [p.get_value() for p in self.params]

        # Remove the last layer parameters
        old_params = old_params[:-2]

        self.build_model(n_hidden_units, 1, old_params)

    def set_input_norm(self, m, std):
        self.input_m = m
        self.input_std = std

    def set_input_dropout(self, dropout):
        self.input_dropout_on.set_value(dropout)

    def set_embedding_dropout(self, dropout):
        self.embedding_dropout_on.set_value(dropout)

    def set_max_pooling_dropout(self, dropout):
        self.max_pooling_dropout_on.set_value(dropout)

    def set_hidden_dropout(self, dropout):
        self.hidden_dropout_on.set_value(dropout)

    def enable_dropout(self):
        self.set_input_dropout(1)
        self.set_embedding_dropout(1)
        self.set_max_pooling_dropout(1)
        self.set_hidden_dropout(1)

    def disable_dropout(self):
        self.set_input_dropout(0)
        self.set_embedding_dropout(0)
        self.set_max_pooling_dropout(0)
        self.set_hidden_dropout(0)

    def set_params(self, params):
        """ Set new NN params and build the network model.
        """
#       self.input_m, \
#       self.input_std, \
        old_params, \
        self.n_hidden, \
        self.hidden_activation, \
        self.n_inputs, \
        self.n_outputs, \
        self.weight_l2, \
        self.prev_frames, \
        self.next_frames, \
        self.batch_size, \
        self.amp, \
        self.amp_vec, \
        self.input_dropout, \
        self.embedding_dropout, \
        self.max_pooling_dropout, \
        self.hidden_dropout, \
        self.embedding_size, \
        self.vocabulary_size, \
        self.convolution_size, \
        self.max_pooling, \
        self.classifier = params

        self.build_model(0, 0, old_params=old_params)

    def get_params(self):
        """ Get all NN params.
        """
        params = (
#                  self.input_m,
#                  self.input_std,
                  [p.get_value() for p in self.params],
                  self.n_hidden,
                  self.hidden_activation,
                  self.n_inputs,
                  self.n_outputs,
                  self.weight_l2,
                  self.prev_frames,
                  self.next_frames,
                  self.batch_size,
                  self.amp,
                  self.amp_vec,
                  self.input_dropout,
                  self.embedding_dropout,
                  self.max_pooling_dropout,
                  self.hidden_dropout,
                  self.embedding_size,
                  self.vocabulary_size,
                  self.convolution_size,
                  self.max_pooling,
                  self.classifier,
        )
        return params

    def load(self, file_name):
        """ Loads saved NN.

        :param file_name: file name of the saved NN
        :return: None
        """
        with open(file_name, "rb") as f:
            self.set_params(pickle.load(f))

    def save(self, file_name):
        """ Saves the NN into a file.

        :param file_name: name of the file where the NN will be saved
        :return: None
        """
        with open(file_name, "wb") as f:
            pickle.dump(self.get_params(), f)

    def predict(self, data_x, batch_size=0, prev_frames=0, next_frames=0, data_y=None):
        self.disable_dropout()

        if not batch_size:
            if prev_frames or next_frames:
                mx = self.frame_multiply_x(data_x, prev_frames, next_frames)
            else:
                mx = data_x

            if data_y != None:
                my = self.frame_multiply_y(data_y, prev_frames, next_frames)
                return self.f_y(mx), my

            return self.f_y(mx)
        else:
            res = []
            resy = []
            for i in range(0, len(data_x), batch_size):
                if prev_frames or next_frames:
                    mx = self.frame_multiply_x(data_x[i:i + batch_size], prev_frames, next_frames)
                else:
                    mx = data_x[i:i + batch_size]

                if data_y != None:
                    my = self.frame_multiply_y(data_y[i:i + batch_size], prev_frames, next_frames)
                    resy.append(my)

                res.append(self.f_y(mx))

            if data_y != None:
                return np.vstack(res), np.concatenate(resy)

            return np.vstack(res)

    def predict_normalise(self, input, batch_size=0):
        input = input - self.input_m
        input /= self.input_std
        input *= self.amp_vec

        return self.predict(input, batch_size)

    def frame_multiply_x(self, x, prev_frames, next_frames):
        rows = [(c, c + len(x) - (self.prev_frames + 1 + self.next_frames)) for c in
                range(0, self.prev_frames + 1 + self.next_frames)]

        mx = np.hstack([a * x[l:r] for a, (l, r) in zip(self.amp, rows)])
        return mx

    def frame_multiply_y(self, y, prev_frames, next_frames):
        my = y[prev_frames:len(y) - 1 - next_frames]
        return my

    def train(self, method='fixedlr', n_iters=1, learning_rate=0.1):
        self.enable_dropout()

        # Do batch-gradient descent to learn the parameters.

        if self.batch_size > 0 and self.batch_size <= len(self.training_set_x):
            n_minibatches = int(len(self.training_set_x) / self.batch_size)
        else:
            n_minibatches = 1
            batch_size = len(self.training_set_x)

        m_minibatches = n_minibatches / 10
        if m_minibatches <= 0:
            m_minibatches = 1

        if 'fixedlr' in method:
            print 'Minibatch size:', self.batch_size, '# minibatches:', n_minibatches, "# total data:", len(
                self.training_set_x)
            for ni in range(n_iters):
                for m in random.sample(range(n_minibatches), n_minibatches):
                    if not self.move_training_set_to_GPU:
                        mini_x = self.training_set_x[m * self.batch_size:(m + 1) * self.batch_size]
                        mini_y = self.training_set_y[m * self.batch_size:(m + 1) * self.batch_size]

                        if self.prev_frames or self.next_frames:
                            mini_x = self.frame_multiply_x(mini_x, self.prev_frames, self.next_frames)
                            mini_y = self.frame_multiply_y(mini_y, self.prev_frames, self.next_frames)

                        log_lik = self.f_train_ret_loss(mini_x, mini_y, learning_rate)
                    else:
                        log_lik = self.f_train_ret_loss_GPU(m, learning_rate)

                    if np.isinf(log_lik) or np.isnan(log_lik):
                        print log_lik
                        print ni, m

                        if not self.move_training_set_to_GPU:
                            print mini_x.max(), mini_x.min()
                            print mini_y.max(), mini_y.min()
                            pmax = max([p.get_value(borrow=True).max() for p in self.params])
                            pmin = min([p.get_value(borrow=True).min() for p in self.params])
                            print pmin, pmax

                        # the next line is supposed to stop the code!
                        print stop

                    if (m % m_minibatches) == 0:
                        print "iteration (%d)" % ni, "minibatch (%03d)" % m, "log likelihood %.6f" % log_lik
        else:
            print "Unknown update method"
            return

