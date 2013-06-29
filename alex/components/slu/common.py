#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

from __future__ import unicode_literals

import autopath
import copy
import inspect
import os
import os.path
import sys

from alex.components.asr.utterance import load_utterances, load_utt_confnets
from alex.components.slu.base import ft_props, SLUInterface
from alex.components.slu.exceptions import SLUException, \
    SLUConfigurationException


# Methods for loading DAs and observations from files.
# _load_meths :: observation type -> load method
_load_meths = {'utt': load_utterances,
               'utt_nbl': NotImplemented,
               'utt_cn': load_utt_confnets,
               'prev_da': NotImplemented,
               'da_nbl': NotImplemented}
# Names of config keys whose values specify the input file for that kind of
# observations.
# _infile_cfgname :: observation type -> configuration name
_infile_cfgname = {'utt': 'utts_fname',
                   'utt_nbl': None,
                   'utt_cn': 'uttcns_fname',
                   'prev_da': None,
                   'da_nbl': None}


def get_slu_type(cfg):
    """
    Reads the SLU type from the configuration.  This should be either a string
    (currently 'slu-seq' and 'slu-tracing' are recognised), or a custom class
    implementing SLUInterface.

    """
    return cfg['SLU']['type']


def load_data(cfg_this_slu, training=False):
    """
    Loads training data for SLU.

    Arguments:
        cfg_tr -- the subconfig for this SLU type
        training -- is the SLU about to be trained (as opposed to being tested
            or used in general)?  This implies `require_model == False'.

    Returns a tuple (obss, das) of co-indexed dictionaries where `obss' has the
    training observations as values, and `das' has their corresponding DAs
    (object DialogueAct) as its values.

    """
    cfg_trte = (cfg_this_slu['training'] if training
                else cfg_this_slu['testing'])
    max_examples = cfg_trte.get('max_examples', None)

    # Find the right function for loading DAs and load them.
    if 'das_loading_fun' in cfg_this_slu:
        load_das = cfg_this_slu['das_loading_fun']
    else:
        from alex.components.slu.da import load_das
    das = load_das(cfg_trte['das_fname'], limit=max_examples)

    # Find what kinds of observations will be needed and load them.
    obs_types = set(ft_props[ft].obs_type
                    for ft in cfg_this_slu['features_type']
                    if not ft.startswith('ab_'))
    obss = {obs_type: _load_meths[obs_type](cfg_trte[_infile_cfgname[obs_type]],
                                            limit=max_examples)
            for obs_type in obs_types}

    # Ensure all observations use exactly the same set of keys.
    common_keys = reduce(set.intersection,
                         (set(typed_obss.viewkeys())
                          for typed_obss in obss.values()))
    common_keys.intersection_update(das.viewkeys())
    obss = {ot: {utt_id: obs for (utt_id, obs) in typed_obss.iteritems()
                 if utt_id in common_keys}
            for (ot, typed_obss) in obss.iteritems()}
    das = {utt_id: da for (utt_id, da) in das.iteritems()
           if utt_id in common_keys}
    return obss, das


# TODO Make the configuration structure simpler.  Blending type names with
# types, putting things into different places in the configuration, that makes
# it hard to use.

def slu_factory(cfg, slu_type=None, require_model=False, training=False,
                verbose=True):
    """
    Creates an SLU parser.

    Arguments:
        slu_type -- a string specifying the type of SLU to use; currently
            supported are:
                'slu-seq' ...  the original classifier with category label
                    abstraction, with sequential numbering of category labels
                'slu-tracing' ... category label substitution with tracing the
                    original surface string and substituting it back adaptively
                    based on the classifier instantiation applied

            Alternatively, a custom Python class implementing SLUInterface can
            be specified here.
        cfg -- the Config object (the cfg['SLU'] field is relevant here)

            The preprocessing object can be supplied through the
                cfg['SLU'][<clser_type_name>]['preprocessing_cls']
            configuration option, and the CLDB filename through the
                cfg['SLU'][<clser_type_name>]['cldb_fname']
            option.
        require_model -- boil out if model cannot be loaded (e.g. none was
            specified in the config)?
        training -- is the SLU about to be trained (as opposed to being tested
            or used in general)?  This implies `require_model == False'.
        verbose -- be verbose?

    """
    # Preprocess the configuration a bit.
    cfg_slu = cfg['SLU']
    if slu_type is None:
        slu_type = cfg_slu.get('type', 'cl-tracing')
    is_custom_class = inspect.isclass(slu_type)
    if is_custom_class:
        if not issubclass(slu_type, SLUInterface):
            msg = ('The class specified for the SLU parser in configuration '
                   'must implement SLUInterface!')
            raise SLUException(msg)
    cfg_this_slu = cfg_slu.get(slu_type, dict())

    # Allow for specifying a Python class as the clser type (as opposed to its
    # name).
    if is_custom_class:
        if require_model:
            msg = 'Unable to ensure a model with a custom-class SLU.'
            raise SLUException(msg)

        clser_class = slu_type
        from alex.components.slu.base import CategoryLabelDatabase, \
            SLUPreprocessing
    # Load appropriate classes based on the classifier type required.
    elif slu_type == 'cl-seq':
        from alex.components.slu.dai_clser_fj import DAILogRegClassifier
        from alex.components.slu.base_fj import CategoryLabelDatabase, \
            SLUPreprocessing
        clser_class = DAILogRegClassifier
    elif slu_type == 'cl-tracing':
        from alex.components.slu.dailrclassifier import DAILogRegClassifier
        from alex.components.slu.base import CategoryLabelDatabase, \
            SLUPreprocessing
        clser_class = DAILogRegClassifier
    else:
        raise SLUException('Unsupported SLU parser type: {type_}'
                           .format(type_=slu_type))

    # Prepare the classifier.
    if 'clser' in cfg_this_slu:
        dai_clser = cfg_this_slu['clser']
    else:
        # Preprocessing
        if cfg_this_slu.get('do_preprocessing', True):
            # Load the CLDB.
            cldb_fname = cfg_this_slu.get('cldb_fname', None)
            if cldb_fname is None:
                msg = ('Was asked for SLU preprocessing but no CLDB filename '
                       'specified in config (in cfg["SLU"][<clser_type>]'
                       '["cldb_fname"])!')
                raise SLUException(msg)
            try:
                cldb = CategoryLabelDatabase(cldb_fname)
            except:
                msg = ('Could not load the CLDB from the filename specified: '
                       '{fname}.'.format(fname=cldb_fname))
                raise SLUException(msg)

            # Load the preprocessing class.
            # XXX No other preprocessing class is expected in the SLU part of
            # the code, but this would be the place to swap the class for
            # another one.
            preprocessing_cls = cfg_this_slu.get('preprocessing_cls',
                                                 SLUPreprocessing)
            preprocessing = preprocessing_cls(cldb)
        else:
            preprocessing = None

        # Get all the kwargs that should be used to construct the classifier.
        clser_kwargs = dict()
        if training:
            cfg_tr = cfg_this_slu['training']
            if slu_type in ('cl-seq', 'cl-tracing'):
                if 'clser_type' in cfg_tr:
                    clser_kwargs['clser_type'] = cfg_tr['clser_type']
                if 'features_type' in cfg_this_slu:
                    clser_kwargs['features_type'] = cfg_this_slu[
                        'features_type']
                if 'abstractions' in cfg_tr:
                    clser_kwargs['abstractions'] = cfg_tr['abstractions']

        dai_clser = clser_class(preprocessing=preprocessing, cfg=cfg,
                                **clser_kwargs)

        # If a model needs to be trained yet,
        if training:
            # Construct the inputs and the outputs for learning.
            obss, das = load_data(cfg_this_slu, training=training)
            dai_clser.extract_features(das=das, obss=obss, verbose=verbose)
            dai_clser.prune_features(
                min_feature_count=cfg_tr.get('min_feat_count', None),
                min_conc_feature_count=cfg_tr.get('min_feat_count_conc', None),
                verbose=verbose)
            dai_clser.prune_classifiers(
                min_dai_count=cfg_tr.get('min_dai_count', None))
            if verbose:
                dai_clser.print_classifiers()

            # Train the model.
            dai_clser.train(balance=cfg_tr.get('balance', None),
                            calibrate=cfg_tr.get('calibrate', None),
                            sparsification=cfg_tr.get('sparsification', None),
                            verbose=verbose)
            # Save the model.
            model_fname = cfg_tr.get('model_fname', None)
            if model_fname is not None:
                dai_clser.save_model(model_fname)
                print >>sys.stderr, ('SLU model saved to "{fname}".'
                                     .format(fname=model_fname))
        else:
            # Try to load the model.
            model_fname = cfg_this_slu.get('testing', dict()
                                           ).get('model_fname', None)
            try:
                dai_clser.load_model(model_fname)
            except:
                if require_model:
                    msg = 'Could not load SLU model.'
                    if model_fname is None:
                        msg += '  None was specified in the config.'
                    else:
                        msg += '  Tried to load it from "{fname}".'.format(
                            frame=model_fname)
                    raise SLUException(msg)

    return dai_clser


class DefaultConfigurator(object):
    DEFAULTS_SLU_TYPE = {'type': ('cl-tracing', 'ty_{0}')}
    DEFAULTS_SLU = {
        'cl-tracing': {'do_preprocessing': (True, 'noprep'),
                       'features_type': (('ab_ngram', 'ngram', ), 'ft_{0}'), },
        'cl-seq'    : {'do_preprocessing': (True, 'noprep'), },
    }
    DEFAULTS_SLU_TR = {
        'cl-tracing': {'abstractions': (('concrete', 'abstract'), 'abs_{0}'),
                       'max_examples': (None, 'top{0}'),
                       'clser_type': ('logistic', '{0}'),
                       'min_feat_count': (10, 'minf{0}'),
                       'min_feat_count_conc': (5, 'minfc{0}'),
                       'min_dai_count': (10, 'mind{0}'),
                       'balance': (True, 'nobal'),
                       'calibrate': (True, 'nocal'),
                       'sparsification': (1., 's{0}'), },
        'cl-seq'    : dict(),
    }
    for shared_key in ('max_examples', 'min_feat_count', 'min_dai_count',
                       'sparsification'):
        DEFAULTS_SLU_TR['cl-seq'][shared_key] = (
            DEFAULTS_SLU_TR['cl-tracing'][shared_key])

    def __init__(self, more_defaults=dict(), more_defaults_type=dict(),
                 more_defaults_tr=dict()):
        # Copy the class defaults.
        self.def_slu_type = copy.deepcopy(self.DEFAULTS_SLU_TYPE)
        self.def_slu = copy.deepcopy(self.DEFAULTS_SLU)
        self.def_slu_tr = copy.deepcopy(self.DEFAULTS_SLU_TR)
        # Update them with defaults supplied by the caller.
        self.def_slu.update(more_defaults)
        self.def_slu_type.update(more_defaults_type)
        self.def_slu_tr.update(more_defaults_tr)
        # Bookkeeping.
        self.config = None

    def build_config(self, cfg):
        """Builds a sufficiently complete config for training an SLU model.

        Where the provided config `cfg' does not specify a required value, the
        default is substituted.

        Arguments:
            cfg -- the Config object to use in this training

        Returns None.  The resulting Config is saved in `self.config'.
        """
        # Find actual configurations to be used.
        self.config = cfg
        cfg_slu = self.config.config.setdefault('SLU', dict())
        slu_type = cfg_slu.setdefault('type', self.def_slu_type['type'][0])
        try:
            cfg_this_slu = cfg_slu[slu_type]
        except KeyError:
            cfg_this_slu = {name: default for (name, (default, _))
                            in self.def_slu[slu_type].iteritems()}
        cfg_tr_orig = cfg_this_slu.get('training', dict())
        cfg_tr_defaults = {name: default for (name, (default, _))
                           in self.def_slu_tr[slu_type].iteritems()}
        cfg_tr = cfg_this_slu['training'] = cfg_tr_defaults
        cfg_tr.update(cfg_tr_orig)
        # Save shorthand variables pointing to config subdicts.
        self.cfg_slu = cfg_slu
        self.slu_type = slu_type
        self.cfg_this_slu = cfg_this_slu
        self.cfg_tr = cfg_tr

    def set_model_name(self, model_fname):
        model_fname = os.path.join(self.cfg_tr['models_dir'], model_fname)
        self.cfg_tr['model_fname'] = model_fname
        return model_fname


class ParamModelNameBuilder(DefaultConfigurator):
    """Class that can build model filename from configuration settings."""
    from datetime import date

    @classmethod
    def clean_arg(cls, arg):
        """Cleans an argument value for use in the model file name."""
        if isinstance(arg, tuple) or isinstance(arg, list):
            arg_str = ','.join(arg)
        elif isinstance(arg, float):
            arg_str = '{0:.1f}'.format(arg)
        else:
            arg_str = str(arg)
        # Clean path arguments: take the basename.
        arg_str = arg_str[arg_str.rfind(os.sep) + 1:]
        # Shorten the argument and replace dashes.
        return arg_str[-7:].replace('-', '_')

    def build_name(self, cfg=None):
        """Builds a name for the model to be trained.

        Arguments:
            cfg -- the Config object to use as configuration;  considered only
                if `build_config' has not been called before for this object,
                and in that case, it is required

        Returns path (not necessarily an absolute path) to the model file.

        """
        # Ensure there is a valid config prepared.
        if self.config is None:
            if cfg is None:
                raise SLUConfigurationException('No config specified.')
            self.build_config(cfg)
            assert self.config is not None
        # Build the model name.
        param_strs = list()
        for cfg_dict, defaults in (
                (self.cfg_slu, self.def_slu_type),
                (self.cfg_this_slu, self.def_slu.get(self.slu_type, tuple())),
                (self.cfg_tr, self.def_slu_tr.get(self.slu_type, tuple()))):
            for name, (default, tpt) in sorted(defaults.iteritems()):
                val = cfg_dict[name]
                if val != default:
                    param_strs.append(tpt.format(self.clean_arg(val)))
        model_fname = '{d}_{params}.slu_model.gz'.format(
            d=self.date.strftime(self.date.today(), '%y%m%d'),
            params='-'.join(param_strs))
        # Ensure the model directory exists.
        if not os.path.isdir(self.cfg_tr['models_dir']):
            os.makedirs(self.cfg_tr['models_dir'])
        # Save the resulting name and return.
        model_fname = os.path.join(self.cfg_tr['models_dir'], model_fname)
        self.cfg_tr['model_fname'] = model_fname
        return model_fname
