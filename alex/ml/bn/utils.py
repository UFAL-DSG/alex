#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from itertools import repeat
from alex.ml.bn.factor import DiscreteFactor, to_log


def constant_factory(value):
    """Create function returning constant value."""
    return repeat(value).next


def constant_factor(variables, variables_dict, length, logarithmetic=True):
    if logarithmetic:
        factor = DiscreteFactor(variables, variables_dict, to_log(np.ones(length)), logarithmetic)
    else:
        factor = DiscreteFactor(variables, variables_dict, np.ones(length), logarithmetic)
    return factor
