#!/usr/bin/env python
# vim: set fileencoding=utf-8

from __future__ import unicode_literals

from itertools import islice


def load_wavaskey(fname, constructor, limit=None, encoding='UTF-8'):
    """
    Loads a dictionary of objects stored in the "wav as key" format.

    The input file is assumed to contain lines of the following form:

        [whitespace..]<key>[whitespace..]=>[whitespace..]<obj_str>[whitespace..]

    or just (without keys):

        [whitespace..]<obj_str>[whitespace..]

    where <obj_str> is to be given as the only argument to the `constructor'
    when constructing the objects stored in the file.

    Arguments:
        fname -- path towards the file to read the objects from
        constructor -- function that will be called on each string stored in
            the file and whose result will become a value of the returned
            dictionary
        limit -- limit on the number of objects to read
        encoding -- the file encoding

    Returns a dictionary with objects constructed by `constructor' as values.

    """
    with codecs.open(fname, encoding=encoding) as infile:
        ret_dict = {}
        for line_idx, line in enumerate(islice(infile, 0, limit)):
            line = line.strip()
            if not line:
                continue

            parts = map(unicode.strip, line.split("=>"), 1)

            # Distinguish the case with a key and without a key.
            if len(parts) == 2:
                key, utt_str = parts
            else:
                key = unicode(line_idx)
                utt_str = parts[0]

            ret_dict[key] = constructor(utt_str)
    return ret_dict
