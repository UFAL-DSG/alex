#!/usr/bin/env python
# encoding: utf-8

"""
Extracts wavs from call logs
and runs the Kaldi decoding using the AM and HCLG graph from models directory
"""

import os
import xml.dom.minidom
import fnmatch
import argparse

import autopath

import alex.utils.various as various
from alex.utils.config import Config
from alex.components.asr.common import asr_factory
from alex.corpustools.text_norm_cs import normalise_text, exclude_asr
from alex.corpustools.wavaskey import save_wavaskey
from alex.corpustools.asrscore import score


def main(indomain_data_dir, file_trn_lst, file_dec_lst, cfg):
    glob = 'asr_transcribed.xml'
    asr = asr_factory(cfg)

    print 'Collecting files under %s with glob %s' % (indomain_data_dir, glob)
    files = []
    for root, dirnames, filenames in os.walk(indomain_data_dir, followlinks=True):
        for filename in fnmatch.filter(filenames, glob):
            files.append(os.path.join(root, filename))

    # files = [
    #     '/ha/projects/vystadial/data/call-logs/2013-05-30-alex-aotb-prototype/part1/2013-06-27-09-33-25.116055-CEST-00420221914256/asr_transcribed.xml']  # DEBUG example

    trn, dec = [], []
    for fn in files:
        doc = xml.dom.minidom.parse(fn)
        turns = doc.getElementsByTagName("turn")
        f_dir = os.path.dirname(fn)

        for turn in turns:
            if turn.getAttribute('speaker') != 'user':
                continue

            recs = turn.getElementsByTagName("rec")
            trans = turn.getElementsByTagName("asr_transcription")

            if len(recs) != 1:
                print "Skipping a turn {turn} in file: {fn} - recs: {recs}".format(turn=turn.getAttribute('turn_number'), fn=fn, recs=len(recs))
                continue

            if len(trans) == 0:
                print "Skipping a turn in {fn} - trans: {trans}".format(fn=fn, trans=len(trans))
                continue

            wav_file = recs[0].getAttribute('fname')
            # FIXME: Check whether the last transcription is really the best! FJ
            t = various.get_text_from_xml_node(trans[-1])
            t = normalise_text(t)

            if exclude_asr(t):
                continue

            # TODO is it still valid? OP
            # The silence does not have a label in the language model.
            t = t.replace('_SIL_', '')
            trn.append((wav_file, t))

            wav_path = os.path.join(f_dir, wav_file)
            dec_trans = asr.rec_wav_file(wav_path)
            best = unicode(dec_trans.get_best())
            dec.append((wav_file, best))

            print 'Decoded %s' % str(wav_path)
            print 'reference %s' % t
            print 'decoded %s' % best

    trn_dict = dict(trn)
    dec_dict = dict(dec)

    save_wavaskey(file_trn_lst, trn_dict)
    save_wavaskey(file_dec_lst, dec_dict)
    score(file_trn_lst, file_dec_lst)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=""" TODO """)

    parser.add_argument('-c', '--configs', nargs='+', help='additional configuration files')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)
    indomain_data_dir = "indomain_data"
    file_trn_lst = 'file_trn.txt'
    file_dec_lst = 'file_dec.txt'

    main(indomain_data_dir, file_trn_lst, file_dec_lst, cfg)
