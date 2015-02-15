#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import random
import copy
import numpy as np
import sys

import theano
from theano import function
from theano import tensor as T
import numpy.random as rng

rng.seed(0)

class TheanoFFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function tanh
      -- output layer - activation function softmax
    """
    def __init__(self, n_inputs = 0, n_hidden_units = 0, n_hidden_layers = 0, n_outputs = 0,
                 training_set_x = None, training_set_y = None, prev_frames = 0, next_frames = 0, amplify_center_frame = 1.0,
                 batch_size = 0, hidden_activation = 'tanh', weight_l2 = 1e-6):
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

        self.n_outputs = n_outputs
        self.weight_l2 = weight_l2

        self.training_set_x = training_set_x
        self.training_set_y = training_set_y

        self.prev_frames = prev_frames
        self.next_frames = next_frames
        self.batch_size = batch_size

        amp_min = 1.0/amplify_center_frame
        amp_max = 1.0
         
        amp_prev = [amp_min + (float(i) / self.prev_frames) * (amp_max - amp_min) for i in range(0, self.prev_frames)]
        amp_next = [amp_min + (float(i) / self.next_frames) * (amp_max - amp_min) for i in range(0, self.next_frames)]
        self.amp = amp_prev + [amp_max,] + list(reversed(amp_next))
        self.amp_vec = np.repeat(self.amp, n_inputs / (self.prev_frames + 1 + self.next_frames))

        if n_inputs:
            self.build_model(n_hidden_units, n_hidden_layers)

    def build_model(self, n_hidden_units, n_hidden_layers, old_params = None):
        # Model definition.
        x = T.fmatrix('X')
        y = x

        # Keep model params here.
        self.params = []  

        # Build the layered neural network.
        if not old_params:
            self.n_hidden = [n_hidden_units,]*n_hidden_layers
        else:
            self.n_hidden = self.n_hidden + [n_hidden_units,]*n_hidden_layers
        
        activations = [self.hidden_activation,]*len(self.n_hidden)
        activations.extend([T.nnet.softmax,]) # NOTE: The last function goes to the output layer.

        assert len(self.n_hidden) + 1 == len(activations)
        
        layers = [self.n_inputs] + self.n_hidden + [self.n_outputs]
        
        # Iterate over pairs of adjacent layers.
        for i, (n1, n2, act) in enumerate(zip(layers[:-1], layers[1:], activations)):
            #print i, n1, n2, act
            
            if old_params and (2*i < len(old_params)):
                #print "using old params"
                # init an existing layer
                w = theano.shared(old_params[2*i], 'W%d' % i, borrow=True)
                b = theano.shared(old_params[2*i+1], 'b%d' % (i + 1))
            else:
                #print "sampling new params"
                w = theano.shared(
                                   np.asarray(rng.uniform(
                                                          low=-np.sqrt(6. / (n1 + n2)),
                                                          high=np.sqrt(6. / (n1 + n2)),
                                                          size=(n1, n2)),
                                              dtype=np.float32),
                                   'W%d' % i, borrow=True)
                b = theano.shared(np.zeros(n2, dtype=np.float32), 'b%d' % (i + 1))
            self.params.append(w)
            self.params.append(b)

            y = act(T.dot(y, w) + b)

        self.f_y = function([x], y) # PREDICTION FUNCTION

        # Define the loss function.
        true_y = T.ivector('true_Y')  # The desired output vector.
        loss = T.log(y[T.arange(y.shape[0]), true_y])  # log-likelihood.
        loss = T.mean(loss)                            # MEAN log-likelihood.

        # Add regularization.
        l2 = 0
        for p in self.params:
            l2 += (p**2).sum()
        loss -= self.weight_l2 * l2

        self.f_loss = function([x, true_y], loss, allow_input_downcast=True)

        # Derive the gradients for the parameters.
        g_loss = T.grad(loss, wrt=self.params)
        self.f_g_loss = function([x, true_y], g_loss)

        # Create a training function for maximization
        updates = []
        learning_rate = T.fscalar()
        for p, g in zip(self.params, g_loss):
            updates.append((p, p + learning_rate * g))

        self.f_train_ret_loss = function([x, true_y, learning_rate], loss, updates = updates)

        # GPU data multiplications, it appears that this version is not faster compared to the CPU version
#        self.shared_training_set_x = theano.shared(training_set_x, 'training_set_x')
#        self.shared_training_set_y = theano.shared(training_set_y, 'training_set_y')
#        xlr = [(c, c + self.batch_size - (self.prev_frames + self.next_frames)) for c in range(self.prev_frames + self.next_frames, -1, -1)]
#        ylr = (self.prev_frames, self.batch_size - self.next_frames)

#        print >> sys.stderr, xlr
#        print >> sys.stderr, ylr
#        print >> sys.stderr, [self.shared_training_set_x.get_value()[0*self.batch_size+l:0*self.batch_size+r].shape for l, r in xlr]

#        m = T.lscalar()
#        self.f_train2 = function(inputs = [m, learning_rate],
#                                outputs = loss,
#                                updates = updates,
#                                givens = {
#                                    x: T.concatenate([self.shared_training_set_x[m*self.batch_size+l:m*self.batch_size+r] for l, r in xlr],
#                                                     axis = 1),
#                                    true_y: self.shared_training_set_y[m*self.batch_size + ylr[0]:m*self.batch_size + ylr[1]]
                                    
                                    #x: self.shared_training_set_x[m*self.batch_size:(m+1)*self.batch_size],
                                    #true_y: self.shared_training_set_y[m*self.batch_size: (m+1)*self.batch_size]
#                                })

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

    def set_params(self, params):
        """ Set new NN params and build the network model.
        """
        self.input_m, \
        self.input_std, \
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
        self.amp_vec = params

        self.build_model(0, 0, old_params = old_params)
                
    def get_params(self):
        """ Get all NN params.
        """
        params = (self.input_m, 
		            self.input_std, 
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
                
    def predict(self, data_x, batch_size = 0, prev_frames = 0, next_frames = 0, data_y = None):
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
                    mx = self.frame_multiply_x(data_x[i:i+batch_size], prev_frames, next_frames)
                else:
                    mx = data_x[i:i+batch_size]
                    
                if data_y != None:
                    my = self.frame_multiply_y(data_y[i:i+batch_size], prev_frames, next_frames)
                    resy.append(my)
                    
                res.append(self.f_y(mx))
                
            if data_y != None:
                return np.vstack(res), np.concatenate(resy) 
                                
            return np.vstack(res)

    def predict_normalise(self, input):
        input -= self.input_m
        input /= self.input_std
        input *= self.amp_vec
        
        return self.predict(input)
        
    def frame_multiply_x(self, x, prev_frames, next_frames):
        rows = [(c, c + len(x) - (self.prev_frames + 1 + self.next_frames)) for c in range(0, self.prev_frames + 1 + self.next_frames)]
         
        mx = np.hstack([a*x[l:r] for a, (l, r) in zip(self.amp, rows)])
        return mx

    def frame_multiply_y(self, y, prev_frames, next_frames):
        my = y[prev_frames:len(y) - 1 - next_frames]
        return my

    def train(self, method = 'fixedlr', n_iters = 1, learning_rate = 0.1):
        # Do batch-gradient descent to learn the parameters.

        if self.batch_size > 0 and self.batch_size <= len(self.training_set_x):
            n_minibatches = int(len(self.training_set_x) / self.batch_size)
        else:
            n_minibatches = 1
            batch_size = len(self.training_set_x)
            
        m_minibatches = n_minibatches/10
        if m_minibatches <= 0:
            m_minibatches = 1
            
        if 'fixedlr' in method:
            print 'Minibatch size:', self.batch_size, '# minibatches:', n_minibatches, "# total data:", len(self.training_set_x)
            for ni in range(n_iters):
                for m in random.sample(range(n_minibatches), n_minibatches):
                    mini_x = self.training_set_x[m*self.batch_size:(m+1)*self.batch_size]
                    mini_y = self.training_set_y[m*self.batch_size:(m+1)*self.batch_size]

                    if self.prev_frames or self.next_frames:
                        mini_x = self.frame_multiply_x(mini_x, self.prev_frames, self.next_frames)
                        mini_y = self.frame_multiply_y(mini_y, self.prev_frames, self.next_frames)
                    
                    log_lik = self.f_train_ret_loss(mini_x, mini_y, learning_rate)
										
                    #log_lik = - self.f_train2(m, learning_rate)

                    if (m % m_minibatches) == 0:
                        print "iteration (%d)" % ni, "minibatch (%d)" % m, "log likelihood %.4f" % log_lik
        else:
            print "Unknown update method"
            return

