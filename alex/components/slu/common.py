#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

from __future__ import unicode_literals
import autopath
import inspect

from alex.components.slu.base import SLUInterface
from alex.components.slu.exception import SLUException


def get_slu_type(cfg):
    """\
    Reads the SLU type from the configuration.  This should be either a string
    (currently 'slu-seq' and 'slu-tracing' are recognised), or a custom class
    implementing SLUInterface.

    """
    return cfg['SLU']['type']


# TODO Make the configuration structure simpler.  Blending type names with
# types, putting things into different places in the configuration, that makes
# it hard to use.

def slu_factory(slu_type, cfg, require_model=False):
    """\
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

    """
    # Preprocess the configuration a bit.
    cfg_slu = cfg['SLU']
    slu_type = cfg_slu.get('type', 'cl-tracing')
    is_custom_class = inspect.isclass(slu_type)
    if is_custom_class:
        if not issubclass(slu_type, SLUInterface):
            msg = ('The class specified for the SLU parser in configuration '
                   'must implement SLUInterface!')
            raise SLUException(msg)
        slu_typename = slu_type.__name__
        cfg_this_slu = cfg_slu.get(slu_typename, dict())
    else:
        cfg_this_slu = cfg_slu.get(slu_type, dict())

    # Allow for specifying a Python class as the clser type (as opposed to its
    # name).
    if is_custom_class:
        if require_model:
            msg = 'Unable to ensure a model with a custom-class SLU.'
            raise SLUException(msg)

        clser_class = slu_type
        from alex.components.slu.dailrclassifier import DAILogRegClassifier
        from alex.components.slu.base import CategoryLabelDatabase, \
            SLUPreprocessing
        # # Load the CLDB and the preprocessing.
        # from alex.components.slu.base import CategoryLabelDatabase, \
            # SLUPreprocessing
        # preprocessing = None
        # cldb = CategoryLabelDatabase(cfg_this_slu.get('cldb_fname', None))
        # if cldb is not None:
            # preprocessing_cls = cfg_this_slu.get('preprocessing_cls',
                                                 # SLUPreprocessing)
            # if preprocessing_cls is not None:
                # preprocessing = preprocessing_cls(cldb)
        # return slu_type(preprocessing=preprocessing, cfg=cfg)
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
                msg = ('Could not load the CLDB from the filename specified:  '
                       '{fname}.'.format(fname=cldb_fname))
                raise SLUException(msg)

            # Load the preprocessing class.
            # XXX No other preprocessing class is expected in the SLU part of
            # the code, but this would be the place to swap the class for
            # another one.
            preprocessing_cls = cfg_slu.get('preprocessing_cls',
                                            SLUPreprocessing)
            preprocessing = preprocessing_cls(cldb)
        else:
            preprocessing = None
        # Try to load the model.
        dai_clser = clser_class(preprocessing=preprocessing, cfg=cfg)
        try:
            model_fname = cfg_te.get('model_fname', None)
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
