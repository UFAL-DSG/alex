'''
Distance Measures, Ecludean
'''
import numpy as np

def euclidean_distance(a, b):
    '''input are numpy.array'''
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a-b)

def squared_euclidean_distance(a, b):
    return np.sum(np.power(np.subtract(a, b), 2))
