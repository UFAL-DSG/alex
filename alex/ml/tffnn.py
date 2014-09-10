#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    def __init__(self, n_inputs, n_hidden_units, n_hidden_layers, n_outputs,
                 training_set_x, training_set_y, prev_frames = 0, next_frames = 0, amplify_center_frame = 1.0, 
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
        self.n_hidden_activation = hidden_activation
        self.weight_l2 = weight_l2

        self.training_set_x = training_set_x
        self.training_set_y = training_set_y

        self.prev_frames = prev_frames
        self.next_frames = next_frames
        self.batch_size = batch_size

        self.amp_min = 1.0/amplify_center_frame
        self.amp_max = 1.0
         
        amp_prev = [self.amp_min + (float(i) / self.prev_frames) * (self.amp_max - self.amp_min) for i in range(0, self.prev_frames)]
        amp_next = [self.amp_min + (float(i) / self.next_frames) * (self.amp_max - self.amp_min) for i in range(0, self.next_frames)]
        self.amp = amp_prev + [self.amp_max,] + list(reversed(amp_next))

        self.build_model(n_hidden_units, n_hidden_layers)
        self.rprop_init()

    def build_model(self, n_hidden_units, n_hidden_layers):
        # Model definition.
        x = T.fmatrix('X')
        y = x

        # Keep model params here.
        self.params = []  

        # Build the layered neural network.
        self.n_hidden = [n_hidden_units,]*n_hidden_layers
        
        activations = [self.hidden_activation,]*len(self.n_hidden)
        activations.extend([T.nnet.softmax,]) # NOTE: The last function goes to the output layer.

        assert len(self.n_hidden) + 1 == len(activations)
        
        layers = [self.n_inputs] + self.n_hidden + [self.n_outputs]
        
        # Iterate over pairs of adjacent layers.
        for i, (n1, n2, act) in enumerate(zip(layers[:-1], layers[1:], activations)):
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
        loss = T.mean(loss)                            # SUM log-likelihood.

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
        ''' It is like a building a complete network, you have to just initialise the network using the parameters
        from the previous network.
        ''' 
        
        # Model definition.
        x = T.fmatrix('X')
        y = x

        # Keep model params here.
        prev_params = copy.deepcopy(self.params)
        self.params = []  

        # Build the layered neural network.
        self.n_hidden = self.n_hidden + [n_hidden_units,]
        
        activations = [self.hidden_activation,]*len(self.n_hidden)
        activations.extend([T.nnet.softmax,]) # NOTE: The last function goes to the output layer.

        assert len(self.n_hidden) + 1 == len(activations)
        
        layers = [self.n_inputs] + self.n_hidden + [self.n_outputs]

        # Iterate over pairs of adjacent layers.
        for i, (n1, n2, act) in enumerate(zip(layers[:-1], layers[1:], activations)):
            if 2*i < len(prev_params) - 2:
                # init an existing layer
                w = theano.shared(prev_params[2*i].get_value(), 'W%d' % i, borrow=True)
                b = theano.shared(prev_params[2*i+1].get_value(), 'b%d' % (i + 1))
            else:
                # init a new layer
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
        loss = T.mean(loss)                            # SUM log-likelihood.

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

    def predict(self, data_x, batch_size = 0, prev_frames = 0, last_frames = 0, data_y = None):
        if not batch_size:
            mx = self.frame_multiply_x(data_x, prev_frames, last_frames)
            if data_y != None:
                my = self.frame_multiply_y(data_y, prev_frames, last_frames)
                return self.f_y(mx), my
                                
            return self.f_y(mx)
        else:
            res = []
            resy = []
            for i in range(0, len(data_x), batch_size):
                mx = self.frame_multiply_x(data_x[i:i+batch_size], prev_frames, last_frames)
                if data_y != None:
                    my = self.frame_multiply_y(data_y[i:i+batch_size], prev_frames, last_frames)
                    resy.append(my)
                    
                res.append(self.f_y(mx))
                
            if data_y != None:
                return np.vstack(res), np.concatenate(resy) 
                                
            return np.vstack(res)

    def rprop_init(self):
        self.d_max = 1e+2
        self.d_min = 1e-6

        self.n_plus = 1.2
        self.n_minus = 0.5

        self.old_grad = {}
        self.rprop_d = {}

    def rprop(self, grad, id = 0, learning_rate = 0.1):
        if id not in self.old_grad:
            # new gradient, and we do not have old
            self.old_grad[id] = grad
            learning_rate = 0.001
            self.rprop_d[id] = learning_rate*np.ones_like(grad)
            change = np.multiply(np.sign(grad), self.rprop_d[id])
            return change

        for i in np.ndindex(grad.shape):
            # print i
            if self.old_grad[id][i]*grad[i] > 0:
                # directions agree
                self.rprop_d[id][i] = min(self.rprop_d[id][i]*self.n_plus, self.d_max)
            elif self.old_grad[id][i]*grad[i] < 0:
                # directions disagree
                self.rprop_d[id][i] = max(self.rprop_d[id][i]*self.n_minus, self.d_min)
                grad[i] = 0

        self.old_grad[id] = grad

        change = np.multiply(np.sign(grad), self.rprop_d[id])

        return change

    def sgrad_minibatch(self, data_x, data_y, prediction = False):
        """ Standard gradient of a minibatch fo data.
        :param data:
        :return:
        """
        if prediction:
            loss = self.f_loss(data_x, data_y)
            acc = np.mean(np.equal(np.argmax(self.f_y(data_x), axis=1), data_y))
        else:
            loss = 0.0
            acc = 1.0

        # compute gradient
        gradients = self.f_g_loss(data_x, data_y)
        
        return loss, acc, gradients

    def frame_multiply_x(self, x, prev_frames, next_frames):
        rows = [(c, c + len(x) - (self.prev_frames + 1 + self.next_frames)) for c in range(0, self.prev_frames + 1 + self.next_frames)]
         
        mx = np.hstack([a*x[l:r] for a, (l, r) in zip(self.amp, rows)])
        return mx

    def frame_multiply_y(self, y, prev_frames, next_frames):
        my = y[prev_frames:len(y) - 1 - next_frames]
        return my

    def train(self, method = 'ng', n_iters = 1, learning_rate = 0.1):
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
        
                    mini_x = self.frame_multiply_x(mini_x, self.prev_frames, self.next_frames)
                    mini_y = self.frame_multiply_y(mini_y, self.prev_frames, self.next_frames)
                    
                    log_lik = self.f_train_ret_loss(mini_x, mini_y, learning_rate)
										
                    #log_lik = - self.f_train2(m, learning_rate)

                    if (m % m_minibatches) == 0:
                        print "iteration (%d)" % ni, "minibatch (%d)" % m, "log likelihood %.4f" % log_lik

        elif 'rprop' in method:
            gradients_all_mb = []

            print 'Minibatch size:', self.batch_size, '# minibatches:', n_minibatches, "# total data:", len(self.training_set_x)
            for ni in range(n_iters):
                for m in range(n_minibatches):
                    mini_x = self.training_set_x[m*self.batch_size:(m+1)*self.batch_size]
                    mini_y = self.training_set_y[m*self.batch_size:(m+1)*self.batch_size]

                    mini_x = self.frame_multiply_x(mini_x, self.prev_frames, self.next_frames)
                    mini_y = self.frame_multiply_y(mini_y, self.prev_frames, self.next_frames)

                    if (m % m_minibatches) == 0:
                        log_lik, acc, gradients = self.sgrad_minibatch(mini_x, mini_y, prediction = True)
                        print "iteration (%d)" % ni, "minibatch (%d)" % m, "log likelihood %.4f" % log_lik, "accuracy %.2f" % (acc*100.0)
                    else:
                        log_lik, acc, gradients = self.sgrad_minibatch(mini_x, mini_y, prediction = False)

                    gradients_all_mb.append(gradients)


            # compute the total gradients
            gradients = {}

            for mg in gradients_all_mb:
                for j, g in enumerate(mg):
                    if j in gradients:
                        gradients[j] += g
                    else:
                        gradients[j] = g

            gradients = [gradients[k] for k in sorted(gradients.keys())]

            # iRPROP- update of parameters.
            for p, g in zip(self.params, gradients):
                # gradient update
                p.set_value(p.get_value() + learning_rate * g)
        else:
            print "Unknown update method"
            return

