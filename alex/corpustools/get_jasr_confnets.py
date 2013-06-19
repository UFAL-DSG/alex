#!/usr/bin/python
# vim: set fileencoding=UTF-8 :
#
# Makes Julius extract word confnets from wav files.
# Run with the -h flag for an overview of arguments.
#
# 2013-06
# Matěj Korvas

from __future__ import unicode_literals

import codecs
from operator import itemgetter
from os.path import basename
import re
import socket
from subprocess import PIPE
import sys
from time import sleep
import traceback

from alex.components.asr.julius import JuliusASR
from alex.components.hub.messages import Frame
from alex.utils.audio import load_wav
from alex.utils.config import Config
from alex.components.asr.exception import ASRException
from alex.utils.fs import find
from alex.utils.io import GrepFilter

DEBUG = False
# DEBUG = True
FRAME_SIZE = 256  # size of an audio frame in bytes
RT_RATIO = 0.0    # determines how long to give Julius before asking him for
                  # results
SLEEP_TIME = RT_RATIO * FRAME_SIZE / 32000.


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


def on_no_context(outstr):
    if DEBUG:
        print "REACHED ON_NO_CONTEXT"
    raise ASRException('Julius said: "NO CONTEXT?"')


def start_julius(cfg, callback, err_fname='julius.err'):
    popen_kwargs = {'stderr': PIPE}
    jul = JuliusASR(cfg, popen_kwargs)

    # Start the grepping filter on Julius' stderr.
    errfile = open(err_fname, 'a+')
    grep = GrepFilter(jul.julius_server.stderr, errfile)
    grep.add_listener(re.compile('NO CONTEXT\?'), callback)
    grep.start()

    return jul, grep, errfile


def main(dirname, outfname, cfg, skip=0):
    """\

    Arguments:
        dirname -- the directory to search for WAVs
        outfname -- path towards the file to output to
        jul -- an instance of the Julius wrapper
        skip -- how many wavs to skip (default: 0)

    """
    wavs = sorted(get_wav_fnames(dirname), key=itemgetter(1))

    # Start Julius.
    jul, grep, errfile = start_julius(cfg, on_no_context)

    try:
        with codecs.open(outfname, 'a+', encoding='UTF-8') as outfile:
            for wav_fname, wav_id in wavs[skip:]:
                mywav = load_wav(cfg, wav_fname)

                # Insist on feeding all the input data to Julius, regardless of how
                # many times it crashes.
                exception = 1
                while exception:
                    try:
                        for startidx in xrange(0, len(mywav), FRAME_SIZE):
                            jul.rec_in(Frame(mywav[startidx:startidx + FRAME_SIZE]))
                            # sleep(SLEEP_TIME)
                        # sleep(RT_RATIO * len(mywav) / 32000.)
                    except socket.error as er:
                        # Julius crashing results in
                        # error: [Errno 104] Connection reset by peer
                        # Catch only that one.
                        if er.errno != 104:
                            raise er
                        exception = er
                        traceback.print_exc()
                        print "get_jasr_confnets: Restarting Julius."
                        jul.kill_all_juliuses()
                        errfile.close()
                        jul, grep, errfile = start_julius(cfg, on_no_context)
                    else:
                        exception = None

                exception = None
                try:
                    hyp = jul.hyp_out()
                except ASRException as ex:
                    exception = ex
                except socket.error as er:
                    # Julius crashing results in
                    # error: [Errno 104] Connection reset by peer
                    # Catch only that one.
                    if er.errno != 104:
                        raise er
                    exception = er
                if exception is not None:
                    traceback.print_exc()
                    jul.kill_all_juliuses()
                    errfile.close()
                    jul, grep, errfile = start_julius(cfg, on_no_context)
                    hyp = 'None'
                    exception = None

                outfile.write('{id_} => {hyp!r}\n'.format(id_=wav_id, hyp=hyp))
                sys.stderr.write('.')
                sys.stderr.flush()
    finally:
        grep.flush()
        grep.terminate()
        errfile.close()


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
    arger.add_argument('-s', '--skip', type=int,
                       help="how many wavs to skip")
    args = arger.parse_args()

    cfg = Config()
    for next_cfg in args.configs:
        cfg.merge(next_cfg)

    try:
        main(args.dirname, args.outfname, cfg, args.skip)
    finally:
        JuliusASR.kill_all_juliuses()
