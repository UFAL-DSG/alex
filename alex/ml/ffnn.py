#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import math
import random
import numpy as np

import theano
from theano import function
from theano.gradient import jacobian
from theano import tensor as T
import numpy.random as rng

import pycuda
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import scikits.cuda.linalg as culinalg

culinalg.init()

from exceptions import FFNNException

rng.seed(0)

class FFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function sigmoid
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
                #y = self.sigmoid(np.dot(y,w)+b)
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

class TheanoFFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function tanh
      -- output layer - activation function softmax
    """
    def __init__(self, n_inputs, n_hidden_units, n_hidden_layers, n_outputs, hidden_activation = 'tanh', weight_l2 = 1e-6):
        self.n_inputs = n_inputs
        self.n_hidden_units = n_hidden_units
        self.n_hidden_layers = n_hidden_layers

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

        self.n_hidden = [n_hidden_units,]*n_hidden_layers
        self.activations = [self.hidden_activation,]*self.n_hidden_layers
        self.activations.extend([T.nnet.softmax,]) # NOTE: The last function goes to the output layer.

        assert len(self.n_hidden) + 1 == len(self.activations)

        # Model definition.
        x = T.fmatrix('X')
        self.params = []  # Keep model params here.

        # Build the layered neural network.
        y = x
        layers = [self.n_inputs] + self.n_hidden + [self.n_outputs]

        # Iterate over pairs of adjacent layers.
        for i, (n1, n2, act) in enumerate(zip(layers[:-1], layers[1:], self.activations)):
            w = theano.shared(
                               np.asarray(rng.uniform(
                                                      low=-np.sqrt(6. / (n1 + n2)),
                                                      high=np.sqrt(6. / (n1 + n2)),
                                                      size=(n1, n2)),
                                          dtype=np.float32),
                               'W%d' % i, borrow=True)
            b = theano.shared(np.zeros(n2, dtype=np.float32), 'b%d' % (i + 1))
            self.params.append((w, b))

            y = act(T.dot(y, w) + b)

        self.f_y = function([x], y) # PREDICTION FUNCTION

        # Define the loss function.
        true_y = T.ivector('true_Y')  # The desired output vector.
        loss = -T.log(y[T.arange(y.shape[0]), true_y])  # Negative log-likelihood.
        toss = T.sum(loss)                              # SUM negative log-likelihood.

        # Add regularization.
        l2 = 0
        for w, b in self.params:
            l2 += (w**2).sum() + (b**2).sum()
        loss += weight_l2 * l2

        self.f_toss = function([x, true_y], toss, allow_input_downcast=True)

        # Derive the gradients for the parameters.
        self.f_g_losses = []
        self.f_j_losses = []
        for w, b in self.params:
            g_loss = T.grad(toss, wrt=[w, b])
            f_g_loss = function([x, true_y], g_loss)
            self.f_g_losses.append(f_g_loss)
            
            j_loss = jacobian(loss, wrt=[w, b])
            f_j_loss = function([x, true_y], j_loss)
            self.f_j_losses.append(f_j_loss)

        self.rprop_init()

    def predict(self, data_x, batch_size = 0):
        if not batch_size:
            return self.f_y(data_x)
        else:
            i = 0.0
            res = []
            for i in range(0, len(data_x), batch_size):
                res.append(self.f_y(data_x[i:i+batch_size]))
                
            return np.vstack(res)

    def cudasolve(self, A, b, tol=1e-3, normal=False, regA = 1.0, regI = 0.0):
        """ Conjugate gradient solver for dense system of linear equations.

            Ax = b
            
            Returns: x = A^(-1)b
            
            If the system is normal, then it solves  
            
            (regA*A'A +regI*I)x= b
            
            Returns: x = (A'A +reg*I)^(-1)b
        """

        N = len(b)
        b = b.reshape((N,1))
        b_norm = culinalg.norm(b)
        x = b.copy()
        if not normal:
            r = b - culinalg.dot(A,x)
        else:
            r = b - regA*culinalg.dot(A,culinalg.dot(A,x), transa='T') - regI*x
        p = r.copy()
        rsold = culinalg.dot(r,r, transa='T')[0][0].get()
        for i in range(N):
            if not normal:
                Ap = culinalg.dot(A,p)
            else:
                Ap = regA*culinalg.dot(A,culinalg.dot(A,p), transa='T') + regI*p
                
            pAp = culinalg.dot(p, Ap, transa='T')[0][0].get()
            alpha = rsold / pAp

            x += alpha*p
            r -= alpha*Ap
            rsnew = culinalg.dot(r,r, transa='T')[0][0].get()

            if math.sqrt(rsnew)/b_norm < tol:
                break
            else:
                p = r + (rsnew/rsold)*p
                rsold = rsnew

        return x.reshape(N)

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

    def sgrad_minibatch(self, data_x, data_y):
        """ Standard gradient
        :param data:
        :return:
        """
        loss = self.f_toss(data_x, data_y) / len(data_x)
        acc = np.mean(np.equal(np.argmax(self.f_y(data_x), axis=1), data_y))
        
        # compute gradient
        gradients = [ [np.asarray(gg) / float(len(data_x)) for gg in g(data_x, data_y)] for g in self.f_g_losses]
        
        return -loss, acc, gradients

    def ngrad_minibatch(self, data_x, data_y, alpha = 1e-3):
        """ Natural gradient gradient
        :param data:
        :return:
        """
        loss = self.f_toss(data_x, data_y) / len(data_x)
        acc = np.mean(np.equal(np.argmax(self.f_y(data_x), axis=1), data_y))
        
        # compute the dimensions of FIM
        n_F = 0
        for w, b in self.params:
            w_s = w.shape.eval()
            b_s = b.shape.eval()
            n_F += w_s[0]*w_s[1] + b_s[0]

        # compute jacobians
        jacobians = [ j(data_x, data_y) for j in self.f_j_losses]
        
        for j in jacobians:
            j0s = j[0].shape
            j[0] = j[0].reshape((j0s[0], j0s[1]*j0s[2]))

        jacobians = [jj for j in jacobians for jj in j]
        
        l_cg = np.hstack(jacobians)
        t_cg = np.mean(l_cg, axis=0)
        
        #print '#2', l_cg.shape
        # t_F = np.dot(l_cg.T , l_cg)
        # t_F /= len(data[0])
        # print '#3', t_F.shape
        # t_F += alpha*np.identity(n_F)
        #
        # print '#4', t_F.shape
        # t_ng = np.linalg.solve(t_F,t_cg)
        # print '#5'

        # print '2', l_cg.shape
        gpu_t_cg = gpuarray.to_gpu(t_cg)
        gpu_l_cg = gpuarray.to_gpu(l_cg)
        # explict representation of FIM is for inefficient if the size of a minibatch is significantly smaller compared
        # to the number of the

        # model parameters  
#        gpu_t_F = culinalg.dot(gpu_l_cg, gpu_l_cg, transa='T')
#        gpu_t_F /= len(data_x)
#        gpu_identity = gpuarray.to_gpu(alpha*np.identity(n_F))
#        gpu_t_F += gpu_identity
#        gpu_t_ng = self.cudasolve(gpu_t_F, gpu_t_cg)

        gpu_t_ng = self.cudasolve(gpu_l_cg, gpu_t_cg, normal=True, regA = 1/float(len(data_x)), regI = alpha)
        t_ng = gpu_t_ng.get()

        # print '5'

        ngradients = []
        t_ng_i = 0
        for tg_w, tg_b in gradients:
            # save natural gradients
            tg_w_s = tg_w.shape
            tg_b_s = tg_b.shape

            tng_w = t_ng[t_ng_i:t_ng_i+tg_w_s[0]*tg_w_s[1]]
            tng_w = tng_w.reshape(tg_w_s)
            t_ng_i = t_ng_i+tg_w_s[0]*tg_w_s[1]

            tng_b = t_ng[t_ng_i:t_ng_i+tg_b_s[0]]
            t_ng_i = t_ng_i+tg_b_s[0]

            ngradients.append((tng_w, tng_b))

        return -loss, acc, ngradients

    def train(self, train_x, train_y, method = 'ng', n_iters = 1, learning_rate = 0.1, batch_size = 100000):
        # Do batch-gradient descent to learn the parameters.

        if batch_size > 0 and batch_size <= len(train_x):
            n_minibatches = int(len(train_x) / batch_size)
        else:
            n_minibatches = 1
            batch_size = len(train_x)
            
        m_minibatches = n_minibatches/10
        if m_minibatches <= 0:
            m_minibatches = 1
            
        if 'fixedlr' in method:
            print 'Minibatch size:', batch_size, '# minibatches:', n_minibatches, "# total data:", len(train_x)
            for ni in range(n_iters):
                for m in random.sample(range(n_minibatches), n_minibatches):
                    mini_x = train_x[m*batch_size:(m+1)*batch_size]
                    mini_y = train_y[m*batch_size:(m+1)*batch_size]

                    if 'sg-' in method:
                        log_lik, acc, gradients = self.sgrad_minibatch(mini_x, mini_y)
                    elif 'ng-' in method:
                        log_lik, acc, gradients = self.ngrad_minibatch(mini_x, mini_y)
                    else:
                        print "Unknown gradient method"
                        return

                    if (m % m_minibatches) == 0:
                        print "iteration (%d)" % ni, "minibatch (%d)" % m, "log likelihood %.4f" % log_lik, "accuracy %.2f" % (acc*100.0)

                    # Update parameters.
                    for i, ((w, b), (tg_w, tg_b)) in enumerate(zip(self.params, gradients)):
                        # gradient update
                        w.set_value(w.get_value() - learning_rate * tg_w)
                        b.set_value(b.get_value() - learning_rate * tg_b)
        elif 'rprop' in method:
            gradients_all_mb = []

            print 'Minibatch size:', batch_size, '# minibatches:', n_minibatches, "# total data:", len(train_x)
            for ni in range(n_iters):
                for m in range(n_minibatches):
                    mini_x = train_x[m*batch_size:(m+1)*batch_size]
                    mini_y = train_y[m*batch_size:(m+1)*batch_size]

                    if 'sg-' in method:
                        log_lik, acc, gradients = self.sgrad_minibatch(mini_x, mini_y)
                    elif 'ng-' in method:
                        log_lik, acc, gradients = self.ngrad_minibatch(mini_x, mini_y)
                    else:
                        print "Unknown gradient method"
                        return

                    gradients_all_mb.append(gradients)

                    if (m % m_minibatches) == 0:
                        print "iteration (%d)" % ni, "minibatch (%d)" % m, "log likelihood %.4f" % log_lik, "accuracy %.2f" % (acc*100.0)

            # compute the total gradients
            gradients = {}

            for i, g in enumerate(gradients_all_mb):
                for j, (tg_w, tg_b) in enumerate(g):
                    if j in gradients:
                        gradients[j][0] += tg_w
                        gradients[j][1] += tg_b
                    else:
                        gradients[j] = [tg_w, tg_b]

            gradients = [(gradients[k][0], gradients[k][1]) for k in sorted(gradients.keys())]

            # iRPROP- update of parameters.
            for i, ((w, b), (tg_w, tg_b)) in enumerate(zip(self.params, gradients)):
                w.set_value(w.get_value() - self.rprop(tg_w, (i, 0), learning_rate))
                b.set_value(b.get_value() - self.rprop(tg_b, (i, 1), learning_rate))
        else:
            print "Unknown update method"
            return

