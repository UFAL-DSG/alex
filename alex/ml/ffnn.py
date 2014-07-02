#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import math
import numpy as np

import theano
from theano import function
from theano import tensor as T
import numpy.random as rng

import pycuda
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import scikits.cuda.linalg as culinalg

culinalg.init()

from exceptions import FFNNException

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

    def sigmoid(self, y):
        y =  1/ (1 + np.exp(-y))
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
            y = input
            for w, b in zip(self.weights[:-1], self.biases[:-1]):
                y = self.sigmoid(np.dot(y,w)+b)

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
            self.weights, self.biases = pickle.load(f)

    def save(self, file_name):
        """ Saves the NN into a file.

        :param file_name: name of the file where the NN will be saved
        :return: None
        """
        with open(file_name, "wb") as f:
            pickle.dump((self.weights, self.biases), f)

class TheanoFFNN(object):
    """ Implements simple feed-forward neural network with:

      -- input layer - activation function linear
      -- hidden layers - activation function tanh
      -- output layer - activation function softmax
    """
    def __init__(self, n_inputs, n_hidden_units, n_hidden_layers, n_outputs, hidden_activation = T.tanh, weight_l2 = 1e-6):
        self.n_inputs = n_inputs
        self.n_hidden_units = n_hidden_units
        self.n_hidden_layers = n_hidden_layers
        self.hidden_activation = hidden_activation
        self.n_outputs = n_outputs
        self.n_hidden_activation = hidden_activation

        self.n_hidden = [n_hidden_units,]*n_hidden_layers
        self.activations = [self.hidden_activation,]*self.n_hidden_layers
        self.activations.extend([T.nnet.softmax,]) # NOTE: The last function goes to the output layer.

        assert len(self.n_hidden) + 1 == len(self.activations)

        # Model definition.
        x = T.vector('x')
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
                                                      size=(n2, n1)),
                                          dtype=theano.config.floatX),
                               'w%d' % i, borrow=True)
            b = theano.shared(np.zeros(n2), 'b%d' % (i + 1))
            self.params.append((w, b))

            y = act(T.dot(w, y) + b)

        self.f_y = function([x], y) # PREDICTION FUNCTION

        # Define the loss function.
        y_real = T.iscalar('y_real')  # The desired output vector.
        loss = -T.log(y[0][y_real])  # Negative log-likelihood.

        # Add regularization.
        l2 = 0
        for w, b in self.params:
            l2 += (w**2).sum() + (b**2).sum()
        loss += weight_l2 * l2

        self.f_loss = function([x, y_real], loss, allow_input_downcast=True)

        # Derive the gradients for the parameters.
        self.f_g_losses = []
        for w, b in self.params:
            g_loss = T.grad(loss, wrt=[w, b])
            f_g_loss = function([x, y_real], g_loss)
            self.f_g_losses.append(f_g_loss)


        self.rprop_init()

    def predict(self, data_x):
        res = []
        for t_x in data_x:
            res.append(self.f_y(t_x))

        return np.array(res)

    def cudasolve(self, A, b, tol=1e-3):
        """ Conjugate gradient solver for dense system of linear equations.

            Ax = b

            Returns: x = A^(-1)b
        """
        N = len(b)
        b = b.reshape((N,1))
        x = gpuarray.zeros_like(b)
        # print 'A', A.shape
        # print 'b', b.shape
        # print 'x', x.shape
        r = b - culinalg.dot(A,x)
        # print 'r', r.shape
        p = r.copy()
        rsold = culinalg.dot(r,r, transa='T')[0][0].get()
        # print 'rsold', rsold
        for i in range(N):
            Ap = culinalg.dot(A,p)
            # print 'A', A.shape
            # print 'p', p.shape
            # print 'Ap', Ap.shape

            pAp = culinalg.dot(p, Ap, transa='T')[0][0].get()
            # print 'p^(T)Ap', pAp
            alpha = rsold / pAp
            # print 'alpha', alpha

            x += alpha*p
            # print 'x', x.shape
            r -= alpha*Ap
            rsnew = culinalg.dot(r,r, transa='T')[0][0].get()
            # print 'rsnew', math.sqrt(rsnew)

            if math.sqrt(rsnew) < tol:
                break
            else:
                p = r + (rsnew/rsold)*p
                rsold = rsnew

        print 'cudasolve> Iterations required on GPU:', i

        return x.reshape(N)

    def rprop_init(self):
        self.d_max = 1e+2
        self.d_min = 1e-6

        self.n_plus = 1.2
        self.n_minus = 0.5

        self.old_grad = {}
        self.rprop_d = {}

    def rprop(self, grad, id = 0):
        if id not in self.old_grad:
            # new gradient, and we do not have old
            self.old_grad[id] = grad
            self.rprop_d[id] = 1e-3*np.ones_like(grad)
            return self.rprop_d[id]

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

        #print change

        return change

    def train(self, data, method = 'ng', n_iters = 1, alpha = 1e-3, learning_rate = 0.1, batch_size = 100000):
        # Do batch-gradient descent to learn the parameters.

        data_all = data
        if batch_size > 0 and batch_size < len(data_all[0]):
            n_minibatches = int(len(data_all[0]) / batch_size)
        else:
            n_minibatches = 1
            batch_size = len(data_all[0])

        print 'Minibatch size:', batch_size, '# minibatches:', n_minibatches, "# total data:", len(data_all[0])
        for ni in range(n_iters):
            for m in range(n_minibatches):
                data_x = data_all[0][m*batch_size:m*batch_size+batch_size]
                data_y = data_all[1][m*batch_size:m*batch_size+batch_size]

                data = [data_x, data_y]

                total_loss = 0.0

                # Prepare accumulating variables for gradients of the parameters.
                gradients = []
                n_F = 0
                for w, b in self. params:
                    w_s = w.shape.eval()
                    b_s = b.shape.eval()
                    tg_w = np.zeros(w_s, dtype=theano.config.floatX)
                    tg_b = np.zeros(b_s, dtype=theano.config.floatX)
                    gradients.append((tg_w, tg_b))

                    n_F += w_s[0]*w_s[1] + b_s[0]

                t_cg = np.zeros(n_F, np.float32)

                # Go through the data, compute gradient at each point and accumulate it.
                l_cg = []
                for ii, (t_x, t_y) in enumerate(zip(data[0], data[1])):
                    total_loss += self.f_loss(t_x, t_y)

                    cg = []
                    for f_g_loss, (tg_w, tg_b) in zip(self.f_g_losses, gradients):
                        g_w, g_b = f_g_loss(t_x, t_y)
                        tg_w += g_w
                        tg_b += g_b

                        if method == 'ng':
                            cg.append(g_w.flatten())
                            cg.append(g_b)


                    if method == 'ng':
                        cg = np.concatenate(cg)
                        cg = cg.astype(np.float32)
                        l_cg.append(cg)
                        t_cg += cg

                total_loss /= len(data[0])

                if method == 'g':
                    for tg_w, tg_b in gradients:
                        tg_w /= len(data[0])
                        tg_b /= len(data[0])

                if method == 'ng':
                    t_cg /= len(data[0])

                    l_cg = np.vstack(l_cg)

                    # print '#2', l_cg.shape
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
                    gpu_t_F = culinalg.dot(gpu_l_cg, gpu_l_cg, transa='T')
                    gpu_t_F /= len(data[0])
                    #t_F = gpu_t_F.get()

                    # print '3'
                    gpu_identity = gpuarray.to_gpu(alpha*np.identity(n_F))
                    gpu_t_F += gpu_identity

                    # print '4', t_F.shape
                    gpu_t_ng = self.cudasolve(gpu_t_F, gpu_t_cg)
                    t_ng = gpu_t_ng.get()

                    # print '5'


                print "iteration (%d)" % ni, "minibatch (%d)" % m, "likelihood %.4f" % total_loss

                t_ng_i = 0
                # Update parameters.
                for i, ((w, b), (tg_w, tg_b)) in enumerate(zip(self.params, gradients)):
                    if method == 'ng':
                        # ng update
                        tg_w_s = tg_w.shape
                        tg_b_s = tg_b.shape

                        tng_w = t_ng[t_ng_i:t_ng_i+tg_w_s[0]*tg_w_s[1]]
                        tng_w = tng_w.reshape(tg_w_s)
                        t_ng_i = t_ng_i+tg_w_s[0]*tg_w_s[1]

                        tng_b = t_ng[t_ng_i:t_ng_i+tg_b_s[0]]
                        t_ng_i = t_ng_i+tg_b_s[0]

                        w.set_value(w.get_value() - learning_rate * tng_w)
                        b.set_value(b.get_value() - learning_rate * tng_b)
                    elif method == 'g':
                        # g update
                        w.set_value(w.get_value() - learning_rate * tg_w)
                        b.set_value(b.get_value() - learning_rate * tg_b)
                    elif method == 'rpropg':
                        # RPROP- g update
                        w.set_value(w.get_value() - self.rprop(tg_w, (i, 0)))
                        b.set_value(b.get_value() - self.rprop(tg_b, (i, 1)))

