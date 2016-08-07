import pprint
import copy

def get_dict_value(d, key):
    '''Return the value if the key exist, return none if the key doesnt exist'''
    if key in d.keys():
        return d[key]
    else:
        return None

def override_dicts(new_des, original_des):
    '''Merge and override properties of two dicts.
    
    Args:
        new_des: A dict presenting new properties for overriding
        origianl_des: A dict which will be intergrated and overridden

    Returns:
        A dict of combining properties from two dict.
    '''
    original_des = deep_copy(original_des)
    if new_des is None:
        return original_des
    for key in new_des.keys():
        original_des[key] = new_des[key]
    return original_des 

def iscallable(o):
    '''Return True if the given object is callable'''
    if hasattr(o, '__call__'):
        return True
    return False

def iprint(s):
    pp = pprint.PrettyPrinter()
    pp.pprint(s)

def deep_copy(o):
    return copy.deepcopy(o)

def debug_print(s, mode=0, debug_mode=100):
    if mode<=debug_mode:
        print s
