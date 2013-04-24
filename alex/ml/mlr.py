#!/bin/env python

import os
import os.path
import numpy as np
from datetime import datetime

class MulticlassLogisticRegression:
    """Implementation of multiclass logistic regression. It provides two ways
    of training:
      1) normal gradient descent
      2) natural gradient descent

      Note that the natural gradient descend is much faster, however, it is
    also much more memory demanding (its memory complexity is O(N^2)).

    """

    def __init__(self, num_clases, phi_size, name=None):
        """ Initialize the classifier:

          1) num_classes - number of output classes
          2) phi_size    - number of features of the classifier

        """

        self.num_clases = num_clases
        self.phi_size = phi_size
        self.theta = np.zeros((phi_size, 1), dtype=np.float64)
        self.name = name

    def __str__(self):
        return "MulticlassLogisticRegression: " + str(self.name)

    def w(self, phis):
        """Compute the product of the parameters and the features."""

        w = []
        for phi in phis:
            prod = float(np.dot(self.theta.T, phi))
            if prod < -1e16 or prod > 1e16:
                print ("MulticlassLogisticRegression::w - too small/large "
                       "numbers")
            w.append(prod)
        return np.array(w)

    def ew(self, phis):
        """Compute exponentiate of the product of the parameters and the
        features."""
        return np.exp(self.w(phis))

    def Pcf(self, cls, phis):
        """Returns probability of the cls class given the phis (class)
        features."""

        ew = self.ew(phis)
        p = ew[cls]/sum(ew)

        return p

    def logPcf(self, cls, phis):
        """Return log of Pcf."""
        return np.log(self.Pcf(cls, phis))

    def gradLogPcf(self, cls, phis):
        """Compute the gradient of the logPcf."""
        ew = self.ew(phis)
        lgp = phis[cls].copy()

        x = np.zeros_like(self.theta)
        for ewi, phi in zip(ew, phis):
            # this could be faster
            # ...as in `x = np.sum(np.array(map(self.ew, phis)) * phis)'?
            x += ewi*phi

        lgp -= 1/sum(ew)*x

        return lgp

    def logLikelihood(self, examples):
        """Compute the likelihood of the examples."""
        l = 0.0
        for episode in examples:
            for cls, phis in episode:
                l += self.logPcf(cls, phis)

        # normalize for the size of the corpus
        l /= len(examples)

        return l

    def gradLogLikelihood(self, examples):
        """Compute the gradient of the likelihood of the examples and at the
        same time also compute the likelihood.

        Normalize both the gradient and the likelihood for the number of the
        data points.
        """

        gl = np.zeros_like(self.theta)
        l = 0.0
        for episode in examples:
            for cls, phis in episode:
                gl += self.gradLogPcf(cls, phis)
                l  += self.logPcf(cls, phis)

        # normalize for the size of the corpus
        gl /= len(examples)
        l /= len(examples)

        return gl, l

    def regLogLikelihood(self, examples, regularization = 0.0):
        """This is the objective function of the training:
            - the likelihood of examples - L2 regularization of parameters.
        """
        return self.logLikelihood(examples) - float(regularization*np.dot(self.theta.T, self.theta))

    def gradRegLogLikelihood(self, examples, regularization = 0.0):
        """This is gradient of the objective function of the training
            - the gradient of the likelihood function + gradient of the regularization

        """
        g, l = self.gradLogLikelihood(examples)
        rg = g - regularization*self.theta
        rl = l - float(regularization*np.dot(self.theta.T, self.theta))

        return rg,  rl

    def naturalGradRegLogLikelihood(self, examples, regularization = 0.0):
        """This is natural gradient of the objective function
            - it also computes the likelihood of the examples
        """

        l = 0.0
        A = []
        gl = np.zeros_like(self.theta)
        i = 0.0
        for episode in examples:
            for cls, phis in episode:
                l  += self.logPcf(cls, phis)
                g   = self.gradLogPcf(cls, phis)
                gl += g

                A.append(g.T)

                i += 1.0

        # normalize for the size of the corpus
        gl /= len(examples)
        l /= len(examples)

        A = np.vstack(A)
        F = np.dot(A.T, A)/i
        # regularize the F
        F += 0.001 * np.identity(self.phi_size)
        invF = np.linalg.pinv(F)

        ng = np.dot(invF, gl)


        # regularize
        rng = ng - regularization*self.theta

        return rng, l

    def update(self, examples, alg = "plain", step_size = 1.0, regularization = 0.0):
        """The theta parameters get updated by either:
            - 'plain' gradient or
            - natural gradient

          1) examples  - an list of training examples [exmpl1, exmpl2, ...]
                            exmpl* = [class_num, phi_vect]

          2) alg       - optimization algorithm. In both cases, the likelihood
                         of the examples is computed.
                            plain - plain gradient
                            natural - natural gradient

          3) step_size - step size of the gradient ascend

          4) regularization - L2 regularization coefficient


        """
        if alg == 'plain':
            g, l = self.gradRegLogLikelihood(examples, regularization)
            s = step_size*g
            self.theta += s
        elif alg == 'natural':
            g, l = self.naturalGradRegLogLikelihood(examples, regularization)
            s = step_size*g
            self.theta += s

        lprint("-"*80)
        lprint("Grad norm:     ", np.linalg.norm(g))
        lprint("Step norm:     ", np.linalg.norm(s))
        lprint("Theta norm:    ", np.linalg.norm(self.theta))
        lprint("Log likelihood:", l)
        lprint('')

        return l

    def load(self, fileName):
        """Load the previously stored theta vector."""

        f = open(fileName, "r")
        self.theta = np.array([float(x.strip()) for x in f])
        self.theta = np.reshape(self.theta, (self.phi_size, 1))
        f.close()

    def save(self, fileName):
        """Store the theta vector in the fileName file."""

        f = open(fileName, "w")

        for theta in self.theta:
            f.write("%f\n" % theta)

        f.close()

# The next function is just for inspiration when using the MLR class. It should
# be moved to an independent test class.

def test():

    num_clases = 2
    phi_size = 2
    examples =  [ [1, [ 0.0, 0.0, 1.0 ],
                  [0, [ 0.5, 0.1, 1.0 ],
                  [0, [ 0.5, 0.2, 1.0 ],
                  [1, [-0.5, 0.2, 1.0 ],
                ]

    LR = MulticlassLogisticRegression(num_clases, phi_size)

    # for all iterations
    for i in range(0, 100):
        print("="*80)
        print('Working on a new iteration:', i)
        print('Date:', datetime.today())

        l = LR.update(examples, )

        LR.save(os.path.join("MLR.%03d.thetas" %i))
