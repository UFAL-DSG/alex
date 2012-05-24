__depth__ = 2

import sys
import os.path


def init_path():
    path = os.path.join(os.path.dirname(__file__), *__depth__ * [os.path.pardir])
    sys.path.append(os.path.abspath(path))
