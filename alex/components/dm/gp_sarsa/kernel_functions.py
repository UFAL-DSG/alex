'''
Kernel Functions
'''

import numpy as np
from distance_measures import squared_euclidean_distance

def polyminal_kernel_fun(a, b, sigma=1, p=1):
    '''Poliminal Kernel, default sigma=1, p=1 is linear kernel'''
    return float(np.power(np.dot(a, b) + pow(sigma,2), p))

def gaussian_kernel_fun(a, b, p=4, sigma=5):
    '''Gaussian Kernel Function, default parameter is used in Gasic's papers'''
    return pow(p, 2)*radial_basic_kernel_fun(a, b, sigma)
    

def radial_basic_kernel_fun(a, b, sigma):
    '''Gaussian Radial Basic Function Kernel (RBF)'''
    return np.exp(-(float(squared_euclidean_distance(a, b))/(2.0*pow(sigma,2))))

def kronecker_delta_kernel_fun(a, b):
    return 1 if a==b else 0
