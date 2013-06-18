# TODO: Remove dependencies on this file (substitute by `autopath.py') and
# delete this file.

import sys
import os.path

# Add the directory containing the alex package to python path
path, directory = os.path.split(os.path.abspath(__file__))
while directory and directory != 'alex':
    path, directory = os.path.split(path)
if directory == 'alex':
    sys.path.append(path)
