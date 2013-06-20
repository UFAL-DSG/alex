#!/usr/bin/python
# vim: set fileencoding=UTF-8 :
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Makes Julius extract word confnets from wav files.
Run with the -h flag for an overview of arguments.

An example ignore list file could contain the following three lines:

/some-path/call-logs/log_dir/some_id.wav
some_id.wav
jurcic-??[13579]*.wav

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.

The second one is an example of a literal glob.

The last one is an example of a more advanced glob. It says basically that
all odd dialogue turns should be ignored.

"""
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

from alex.components.asr.exception import ASRException
from alex.components.asr.julius import JuliusASR
from alex.components.hub.messages import Frame
from alex.corpustools.cued import find_matching
from alex.utils.audio import load_wav
from alex.utils.config import Config
from alex.utils.io import GrepFilter

DEBUG = False
# DEBUG = True
FRAME_SIZE = 256  # size of an audio frame in bytes
RT_RATIO = 0.0    # determines how long to give Julius before asking him for
                  # results
SLEEP_TIME = RT_RATIO * FRAME_SIZE / 32000.


def get_wav_fnames(dirname, ignore_list_file=None):
    """
    Finds WAV files that should be decoded.

    Returns a list of tuples (filename, WAV unique ID).

    Arguments:
        dirname -- the directory to search for WAVs
        ignore_list_file -- a file of absolute paths or globs (can be mixed)
            specifying logs that should be skipped

    """
    find_kwargs = {'mindepth': 0,
                   'maxdepth': None,
                   'notrx': re.compile('^.*_all\\.wav$')}
    wav_fnames = find_matching(dirname, '*.wav',
                               ignore_list_file=ignore_list_file,
                               find_kwargs=find_kwargs)
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


def main(dirname, outfname, cfg, skip=0, ignore_list_file=None):
    """

    Arguments:
        dirname -- the directory to search for WAVs
        outfname -- path towards the file to output to
        jul -- an instance of the Julius wrapper
        skip -- how many wavs to skip (default: 0)

    """
    wavs = sorted(get_wav_fnames(dirname, ignore_list_file), key=itemgetter(1))

    # Start Julius.
    jul, grep, errfile = start_julius(cfg, on_no_context)

    try:
        with codecs.open(outfname, 'a+', encoding='UTF-8') as outfile:
            for wav_fname, wav_id in wavs[skip:]:
                mywav = load_wav(cfg, wav_fname)

                # Insist on feeding all the input data to Julius, regardless of
                # how many times it crashes.
                exception = 1
                while exception:
                    try:
                        for startidx in xrange(0, len(mywav), FRAME_SIZE):
                            jul.rec_in(Frame(
                                mywav[startidx:startidx + FRAME_SIZE]))
                            sleep(SLEEP_TIME)
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
    arger.add_argument('-g', '--ignore',
                       type=argparse.FileType('r'),
                       metavar='FILE',
                       help='Path towards a file listing globs of CUED '
                            'call log files that should be ignored.\n'
                            'The globs are interpreted wrt. the current '
                            'working directory. For an example, see the '
                            'source code.')
    args = arger.parse_args()

    cfg = Config()
    for next_cfg in args.configs:
        cfg.merge(next_cfg)

    try:
        main(args.dirname, args.outfname, cfg, args.skip, args.ignore)
    finally:
        JuliusASR.kill_all_juliuses()
