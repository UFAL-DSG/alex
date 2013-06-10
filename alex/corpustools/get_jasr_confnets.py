#!/usr/bin/python
# vim: set fileencoding=UTF-8 :
#
# Taken from an interactive python session.
# This shows how to ask Julius to extract word confnets from wav files.

from __future__ import unicode_literals

import codecs
from os.path import basename
import re

from alex.components.asr.julius import JuliusASR
from alex.components.hub.messages import Frame
from alex.utils.audio import load_wav
from alex.utils.config import Config
from alex.utils.exception import ASRException
from alex.utils.fs import find


def get_wav_fnames(dirname):
    """\
    Finds WAV files that should be decoded.

    Returns a list of tuples (filename, WAV unique ID).

    Arguments:
        dirname -- the directory to search for WAVs

    """
    wav_fnames = find(dirname, '*.wav', mindepth=0, maxdepth=None,
                      notrx=re.compile('^.*_all\\.wav$'))
    return [(fname, basename(fname)) for fname in wav_fnames]


def main(dirname, outfname, jul):
    """\

    Arguments:
        dirname -- the directory to search for WAVs
        outfname -- path towards the file to output to
        jul -- an instance of the Julius wrapper

    """
    wavs = get_wav_fnames(dirname)

    with codecs.open(outfname, 'w', encoding='UTF-8') as outfile:
        for wav_fname, wav_id in wavs:
            mywav = load_wav(cfg, wav_fname)
            for startidx in xrange(0, len(mywav), 256):
                jul.rec_in(Frame(mywav[startidx:startidx + 256]))
            try:
                hyp = jul.hyp_out()
            except ASRException:
                hyp = 'None'
            outfile.write('{id_} => {hyp!r}\n'.format(id_=wav_id, hyp=hyp))


if __name__ == "__main__":
    import argparse
    arger = argparse.ArgumentParser(
        description=('Finds WAVs in the directory specified and decodes them '
                     'as confnets.'))
    arger.add_argument('dirname',
                       help='directory name where to search for WAVs')
    arger.add_argument('outfname', help='path towards the output file')
    arger.add_argument('-c', '--configs', nargs='+',
                       help='configuration files',
                       required=True)
    args = arger.parse_args()

    cfg = Config()
    for next_cfg in args.configs:
        cfg.merge(next_cfg)

    jul = JuliusASR(cfg)
    try:
        main(args.dirname, args.outfname, jul)
    finally:
        jul.kill_my_julius()
