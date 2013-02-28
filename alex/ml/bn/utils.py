#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from itertools import repeat
from bn.factor import DiscreteFactor

def constant_factory(value):
    """Create function returning constant value."""
    return repeat(value).next

def constant_factor(variables, variables_dict, length):
    factor = DiscreteFactor(variables, variables_dict, np.ones(length))
    return factor
