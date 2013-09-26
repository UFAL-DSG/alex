#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Apart from training SLU, this script has the use of expanding SLU training
# data (the placeholders in the artificial examples).  It is not written
# nicely; all that needs to be done to switch between these two functionalities
# is commenting one or the other of the two last lines of the script.

from __future__ import unicode_literals

if __name__ == "__main__":
    import autopath

import codecs
import os.path
import random

from alex.components.asr.utterance import load_utterances
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import load_das, DialogueAct


DEFAULTS_SLU_TYPE = (('type', 'cl-tracing', 'ty_{0}'), )
DEFAULTS_SLU = {
    'cl-tracing': (('do_preprocessing', True, 'noprep'),
                   ('features_type', ('ngram', ), 'ft_{0}'), ),
    'cl-seq'    : (('do_preprocessing', True, 'noprep'), ),
}
DEFAULTS_SLU_TR = {
    'cl-tracing': (('abstractions', ('concrete', 'abstract'), 'abs_{0}'),
                   ('max_examples', None, 'top{0}'),
                   ('clser_type', 'logistic', '{0}'),
                   ('min_feat_count', 10, 'minf{0}'),
                   ('min_feat_count_conc', 5, 'minfc{0}'),
                   ('min_dai_count', 10, 'mind{0}'),
                   ('balance', True, 'nobal'),
                   ('calibrate', True, 'nocal'),
                   ('sparsification', 1., 's{0}'),
                   # ('utts_fname', os.path.join('train_slu_expanded.txt'),
                       # 'trn_{0}'),
                   ('utts_fname', os.path.join('train_slu.txt'),
                       'trn_{0}'),
                   # ('das_fname', os.path.join('train_slu_expanded.sem'),
                       # 'sem_{0}'), ),
                   ('das_fname', os.path.join('train_slu.sem'),
                       'sem_{0}'), ),
    'cl-seq'    : (('min_feat_count', 10, 'minf{0}'),
                   ('min_dai_count', 10, 'mind{0}'),
                   ('max_examples', None, 'top{0}'),
                   ('sparsification', 1., 's{0}'), ),
}
TRN_FNAME = os.path.join('data', 'train_slu.txt')
SEM_FNAME = os.path.join('data', 'train_slu.sem')
EXPANDED_TRN_FNAME = 'train_slu_expanded.txt'
EXPANDED_SEM_FNAME = 'train_slu_expanded.sem'


# Load data.
def load_data(cfg):
    cfg_slu = cfg['SLU']
    slu_type = cfg_slu.get('type', 'cl-tracing')
    cfg_this_slu = cfg_slu[slu_type]
    cfg_tr = cfg_this_slu['training']

    utterances = load_utterances(cfg_tr['utts_fname'],
                                 limit=cfg_tr.get('max_examples', None))
    das = load_das(cfg_tr['das_fname'],
                   limit=cfg_tr.get('max_examples', None))
    # Load preprocessing data and routines.
    if cfg_this_slu.get('do_preprocessing', True):
        # Load processing data and configuration.
        cldb = CategoryLabelDatabase(cfg_this_slu['cldb_fname'])
        preprocessing = SLUPreprocessing(cldb)
    else:
        preprocessing = None

    return utterances, das, preprocessing, cldb


def expand_trdata(cfg):
    slu_type = cfg['SLU'].get('type', 'cl-tracing')
    cfg_tr = cfg['SLU'][slu_type]['training']
    cfg_tr['utts_fname'] = TRN_FNAME
    cfg_tr['das_fname'] = SEM_FNAME

    utterances, das, preprocessing, cldb = load_data(cfg)
    utterances2 = {}
    das2 = {}
    key = 0

    for (uk, utterance), da in zip(utterances.iteritems(), das.values()):
        for expansion in xrange(5):
            new_utterance = utterance
            new_da = da

            # import ipdb; ipdb.set_trace()
            for slot in ['time', 'stop', 'tt', 'ampm']:
                if slot == 'stop':
                    placeholders = ('$from$', '$to$')
                else:
                    placeholders = ('${0}$'.format(slot), )

                for placeholder in placeholders:
                    while placeholder in new_utterance.utterance:
                        try:
                            slot_val = random.choice(
                                cldb.database[slot].keys())
                        except KeyError:
                            # If this slot is not available from the database,
                            # continue with other slots.
                            break
                        slot_surf = random.choice(
                            cldb.database[slot][slot_val])
                        new_utterance = new_utterance.replace((placeholder, ),
                                                              slot_surf)
                        new_da = DialogueAct(
                            unicode(new_da).replace(placeholder, slot_val, 1))

            utterances2[key] = new_utterance
            das2[key] = new_da
            key += 1

    with codecs.open(EXPANDED_TRN_FNAME, 'w', encoding='UTF-8') as utt_out:
        for key, utt in utterances2.iteritems():
            utt_out.write('{key} => {utt}\n'.format(key=key, utt=utt))

    with codecs.open(EXPANDED_SEM_FNAME, 'w', encoding='UTF-8') as da_out:
        for key, da in das2.iteritems():
            da_out.write('{key} => {da}\n'.format(key=key, da=da))


def main(cfg):
    from alex.components.slu.common import slu_factory
    # The following also saves the model, provided a filename has been
    # specified in the config.
    slu_factory(cfg, training=True, verbose=True)


if __name__ == "__main__":
    import argparse
    from datetime import date
    import os
    import sys

    from alex.utils.config import Config

    arger = argparse.ArgumentParser(
        description='Trains an SLU model from transcriptions')
    arger.add_argument('-o', '--model-fname', default=None)
    arger.add_argument('-n', '--dry-run', action='store_true')
    arger.add_argument('-c', '--configs', nargs='+',
                       help='configuration files')
    args = arger.parse_args()

    # Merge configuration files specified as arguments.
    cfg = Config.load_configs(args.configs)

    # If the configuration is apparently insufficient, fill in defaults.
    cfg_slu = cfg.setdefault('SLU', dict())
    slu_type = cfg_slu.setdefault('type', 'cl-tracing')

    this_slu_defaults = dict((name, default) for (name, default, _)
                             in DEFAULTS_SLU.get(slu_type, tuple()))
    cfg_this_slu = cfg_slu.setdefault(slu_type, this_slu_defaults)
    for name, default, _ in DEFAULTS_SLU.get(slu_type, tuple()):
        if name not in cfg_this_slu:
            cfg_this_slu[name] = default

    this_tr_defaults = dict((name, default) for (name, default, _)
                            in DEFAULTS_SLU_TR.get(slu_type, tuple()))
    cfg_tr = cfg_this_slu.setdefault('training', this_tr_defaults)
    for name, default, _ in DEFAULTS_SLU_TR.get(slu_type, tuple()):
        if name not in cfg_tr:
            cfg_tr[name] = default

    # Build the filename for the model and save it to the config.
    if args.model_fname is None:
        param_strs = list()
        for cfg_dict, defaults in (
                (cfg_slu, DEFAULTS_SLU_TYPE),
                (cfg_this_slu, DEFAULTS_SLU.get(slu_type, tuple())),
                (cfg_tr, DEFAULTS_SLU_TR.get(slu_type, tuple()))):
            for name, default, tpt in defaults:
                val = cfg_dict[name]
                if val != default:
                    if isinstance(val, tuple) or isinstance(val, list):
                        val_str = ','.join(val)
                    else:
                        val_str = str(val)
                    param_strs.append(tpt.format(val_str))
        # TODO? Substitute date with the current git version.
        model_fname = '{d}_{params}.slu_model.gz'.format(
            d=date.strftime(date.today(), '%y%m%d'),
            params='-'.join(param_strs))
        args.model_fname = os.path.join(cfg_tr['models_dir'], model_fname)
        if not os.path.isdir(cfg_tr['models_dir']):
            os.makedirs(cfg_tr['models_dir'])
        print >>sys.stderr, ('Going to write the model to "{path}".'
                             .format(path=args.model_fname))
        # [TODO] Write the output there (with the .out extension) too.
        # Solved temporarily by providing the -n flag.
    cfg_tr['model_fname'] = args.model_fname

    if not args.dry_run:
        expand_trdata(cfg)
        # main(cfg)
