'''
Sampling a value from given distribution
'''

import random
from numpy.random.mtrand import dirichlet
import pdb

def sample_from_dict(dt):
    '''
    Given a dict, representing a multinomial distribution, 
    of the form:
    
      { 
        'key1' : prob1,
        'key2' : prob2,
        ...
      }

    sample a key according to the distribution of probs.
    '''
    r = random.random()
    s = 0.0
    for f in dt:
        s += dt[f]
        if (r < s):
            return f
    raise RuntimeError,'Didnt sample anything from this hash: %s (r=%f)' % (str(dt),r)

def sample_dirichlet_from_dict(dt):
    '''
    Sample one set or dirichlet distribution for given dictionary
    '''
    alphas = dt.values()
    raw_dist = dirichlet(alphas)
    return dict( zip((dt.keys()), (raw_dist)) )

def sample_from_list(lst, num=1, repeat=False):
    '''Sample num number of elemetns in given list lst, which a value may be chosen repeatedly when the flag repeat set to True'''
    if isinstance(lst, set):
        lst = list(lst)

    if num>len(lst) and not repeat:
        raise ValueError('Number of element required is exceed the size of given list while repeatation wasn\'t allowed')
    ret = []
    i = 0
    while i<num:
        id = random.randint(0, len(lst)-1)
        element = lst[id]
        if element not in ret or repeat:
            #ret.append(str(element))
            ret.append(element)
            i = i + 1
    if num==1: return ret[0]
    return ret

def random_filter_list(lst, keep_prob=0.5):
    '''Filter randomly the given list with keeping probablity given'''
    lst_out = []
    for s in lst:
        if random.random()<keep_prob:
            lst_out.append(s)
    return lst_out

def sample_a_prob(accept_prob):
    return random.random()<accept_prob
