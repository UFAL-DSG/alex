#!/usr/bin/env python
# vim: set fileencoding=utf-8

from __future__ import unicode_literals

answer_tpt = '{fname}\t{value!r}'
invalid_tpt = '{fname}: Error parsing the file!\n'
unset_tpt = '{fname}\t<unset>'

if __name__ == "__main__":
    import argparse
    import sys

    import autopath
    from alex.utils.config import Config

    arger = argparse.ArgumentParser()
    arger.add_argument('pattern',
                       help='config path pattern to extract;'
                            'Currently, only patterns in the form '
                            'KEY1:KEY2:... are recognised')
    arger.add_argument('configs', nargs='+',
                       help='configuration files')
    args = arger.parse_args()

    keys = args.pattern.split(':')
    for cfg_fname in args.configs:
        try:
            cfg = Config(cfg_fname)
        except:
            sys.stderr.write(invalid_tpt.format(fname=cfg_fname))
            continue
        try:
            print answer_tpt.format(fname=cfg_fname, value=cfg[keys])
        except KeyError:
            print unset_tpt.format(fname=cfg_fname)
