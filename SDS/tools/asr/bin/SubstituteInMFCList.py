#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Assumes to be called with two arguments:
#   mfc_fname ... path towards a file with a list
#   subs ... a substitution string,
#
# where the file referred to as `mfc_fname' should contain lines in the format:
#
# <word0><whitespace><word1><whatever else>
#
# This script changes the lines to look like this:
#
# <word0><whitespace><subs>/<word1><whatever else>
#
# (The forward slash is OS-specific. It would be a backslash on Dows.)


import sys
import os.path


if __name__ == "__main__":
    # Process arguments.
    try:
        mfc_fname = sys.argv[1]
        subs = sys.argv[2]
    except IndexError, e:
        return 1

    with open(mfc_fname, 'r') as mfc_file:
        for line in mfc_file:
            words = line.strip().split()

            basename = os.path.basename(words[1])
            words[1] = os.path.join(subs, basename)

            print ' '.join(words)
    return 0
