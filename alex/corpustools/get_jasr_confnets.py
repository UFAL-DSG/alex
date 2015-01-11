#!/usr/bin/env python
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
if __name__ == "__main__":
    import autopath

import argparse
import codecs
from operator import itemgetter
from os.path import basename
import re
import socket
from subprocess import PIPE
import sys
from time import sleep
import traceback

from alex.components.asr.exceptions import ASRException
from alex.components.asr.julius import JuliusASR
from alex.components.hub.messages import Frame
from alex.corpustools.cued import find_with_ignorelist
from alex.utils.audio import load_wav
from alex.utils.config import Config
from alex.utils.fs import GrepFilter

DEBUG = False
# DEBUG = True


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
    wav_fnames = find_with_ignorelist(dirname, '*.wav',
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


def clean_up(jul, grep, errfile):
    jul.kill_my_julius()
    grep.flush()
    grep.terminate()
    errfile.close()


def main(dirname, outfname, cfg, skip=0, ignore_list_file=None):
    """

    Arguments:
        dirname -- the directory to search for WAVs
        outfname -- path towards the file to output to
        cfg -- a configuration dictionary (of the Config class)
        skip -- how many wavs to skip (default: 0)
        ignore_list_file -- a file open for reading whose lines specify path
            globs for logs that should be ignored, or None if no such file
            should be used.  The format of this file is described in
            some alex/corpustools scripts.

    """

    # Fetch relevant config arguments.
    frame_size = cfg['corpustools']['get_jasr_confnets']['frame_size']
    rt_ratio = cfg['corpustools']['get_jasr_confnets']['rt_ratio']
    sleep_time = rt_ratio * frame_size / 32000.

    wavs = sorted(get_wav_fnames(dirname, ignore_list_file), key=itemgetter(1))

    jul = None
    try:
        with codecs.open(outfname, 'a+', encoding='UTF-8') as outfile:
            for wav_fname, wav_id in wavs[skip:]:
                # Load the wav.
                mywav = load_wav(cfg, wav_fname)
                # Start Julius.
                if jul is None:
                    jul, grep, errfile = start_julius(cfg, on_no_context)

                # Insist on feeding all the input data to Julius, regardless of
                # how many times it crashes.
                exception = 1
                while exception:
                    try:
                        for startidx in xrange(0, len(mywav), frame_size):
                            jul.rec_in(Frame(
                                mywav[startidx:startidx + frame_size]))
                            sleep(sleep_time)
                        # sleep(rt_ratio * len(mywav) / 32000.)
                    except socket.error as e:
                        # Julius crashing results in
                        # error: [Errno 104] Connection reset by peer
                        # Catch only that one.
                        if e.errno != 104:
                            raise e
                        exception = e
                        traceback.print_exc()
                        print "get_jasr_confnets: Restarting Julius."
                        clean_up(jul, grep, errfile)
                        jul, grep, errfile = start_julius(cfg, on_no_context)
                    else:
                        exception = None

                exception = None
                try:
                    hyp = jul.hyp_out()
                except ASRException as e:
                    exception = e
                except socket.error as e:
                    # Julius crashing results in
                    # error: [Errno 104] Connection reset by peer
                    # Catch only that one.
                    if e.errno != 104:
                        raise e
                    exception = e
                if exception is not None:
                    traceback.print_exc()
                    clean_up(jul, grep, errfile)
                    jul = None
                    hyp = 'None'
                    exception = None

                outfile.write('{id_} => {hyp!r}\n'.format(id_=wav_id, hyp=hyp))
                sys.stderr.write('.')
                sys.stderr.flush()
    finally:
        if jul is not None:
            clean_up(jul, grep, errfile)


if __name__ == '__main__':
    arger = argparse.ArgumentParser(
        description=('Finds WAVs in the directory specified and decodes them '
                     'as confnets.'))
    arger.add_argument('dirname',
                       help='directory name where to search for WAVs;  in '
                            'fact, it can be path towards a file listing '
                            'paths to the files in question or path globs or '
                            'paths to their immediate parent directories')
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

    cfg = Config.load_configs(args.configs, log=False)

    try:
        DEBUG = cfg['General']['debug']
    except KeyError:
        pass

    main(args.dirname, args.outfname, cfg, args.skip, args.ignore)
