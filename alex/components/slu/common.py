#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

from __future__ import unicode_literals

import inspect
from alex.components.slu.base import CategoryLabelDatabase, SLUInterface
from alex.components.slu.exceptions import SLUException
from alex.components.slu.dailrclassifier import DAILogRegClassifier

def get_slu_type(cfg):
    """
    Reads the SLU type from the configuration.
    """
    return cfg['SLU']['type']

def slu_factory(cfg, slu_type=None):
    """
    Creates an SLU parser.

    :param cfg:
    :param slu_type:
    :param require_model:
    :param training:
    :param verbose:

    """

    #This new and simple factory code.
    if slu_type is None:
        slu_type = get_slu_type(cfg)

    if inspect.isclass(slu_type) and issubclass(slu_type, DAILogRegClassifier):
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        slu = slu_type(cldb, preprocessing)
        slu.load_model(cfg['SLU'][slu_type]['model_fname'])
        return slu
    elif inspect.isclass(slu_type) and issubclass(slu_type, SLUInterface):
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        slu = slu_type(preprocessing, cfg)
        return slu

    raise SLUException('Unsupported SLU parser: %s' % slu_type)

#import copy
#import inspect
#import os
#import sys
#
#from collections import namedtuple
#
#from alex.components.asr.utterance import load_utterances, load_utt_confnets, load_utt_nblists
#from alex.components.slu.base import ft_props, CategoryLabelDatabase, SLUInterface

##TODO Make the configuration structure simpler.  Blending type names with
##types, putting things into different places in the configuration, that makes
##it hard to use.
#def slu_factory(cfg, slu_type=None, require_model=False, training=False, verbose=True):
#    """
#    Creates an SLU parser.
#
#    :param cfg:
#    :param slu_type:
#    :param require_model:
#    :param training:
#    :param verbose:
#
#    Arguments:
#        slu_type -- a string specifying the type of SLU to use; currently
#            supported are:
#                'slu-seq' ...  the original classifier with category label
#                    abstraction, with sequential numbering of category labels
#                'slu-tracing' ... category label substitution with tracing the
#                    original surface string and substituting it back adaptively
#                    based on the classifier instantiation applied
#
#            Alternatively, a custom Python class implementing SLUInterface can
#            be specified here.
#        cfg -- the Config object (the cfg['SLU'] field is relevant here)
#
#            The preprocessing object can be supplied through the
#                cfg['SLU'][<clser_type_name>]['preprocessing_cls']
#            configuration option, and the CLDB filename through the
#                cfg['SLU'][<clser_type_name>]['cldb_fname']
#            option.
#        require_model -- boil out if model cannot be loaded (e.g. none was
#            specified in the config)?
#        training -- is the SLU about to be trained (as opposed to being tested
#            or used in general)?  This implies `require_model == False'.
#        verbose -- be verbose?
#
#    """
#
#    #This new and simple factory code.
#    if issubclass(slu_type, DAILogRegClassifier):
#        cldb = CategoryLabelDatabase(cfg[SLU][slu_type]['cldb_fname'])
#        preprocessing = cfg[SLU][slu_type]['preprocessing_cls'](cldb)
#        slu = slu_type(cldb, preprocessing)
#        return slu
#    elif issubclass(slu_type, SLUInterface):
#        cldb = CategoryLabelDatabase(cfg[SLU][slu_type]['cldb_fname'])
#        preprocessing = cfg[SLU][slu_type]['preprocessing_cls'](cldb)
#        slu = slu_type(preprocessing)
#        return slu
#
#    #This below is kept here just for MK its old code compatibility
#
#    # Preprocess the configuration a bit.
#    cfg_slu = cfg['SLU']
#    if slu_type is None:
#        slu_type = cfg_slu.get('type', 'cl-tracing')
#    is_custom_class = inspect.isclass(slu_type)
#    if is_custom_class:
#        if not issubclass(slu_type, SLUInterface):
#            msg = ('The class specified for the SLU parser in configuration '
#                   'must implement SLUInterface!')
#            raise SLUException(msg)
#    cfg_this_slu = cfg_slu.get(slu_type, dict())
#
#    # Allow for specifying a Python class as the clser type (as opposed to its
#    # name).
#    if is_custom_class:
#        if require_model:
#            msg = 'Unable to ensure a model with a custom-class SLU.'
#            raise SLUException(msg)
#
#        clser_class = slu_type
#        from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
#    # Load appropriate classes based on the classifier type required.
#    elif slu_type == 'cl-seq':
#        from alex.components.slu.dailrclassifier_old import DAILogRegClassifier
#        from alex.components.slu.base_fj import CategoryLabelDatabase, SLUPreprocessing
#        clser_class = DAILogRegClassifier
#    elif slu_type == 'cl-tracing':
#        from alex.components.slu.dailrclassifier_mk import DAILogRegClassifier
#        from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
#        clser_class = DAILogRegClassifier
#    else:
#        raise SLUException('Unsupported SLU parser type: {type_}'.format(type_=slu_type))
#
#    # Prepare the classifier.
#    if 'clser' in cfg_this_slu:
#        dai_clser = cfg_this_slu['clser']
#    else:
#        # Preprocessing
#        if cfg_this_slu.get('do_preprocessing', True):
#            # Load the CLDB.
#            cldb_fname = cfg_this_slu.get('cldb_fname', None)
#            if cldb_fname is None:
#                msg = ('Was asked for SLU preprocessing but no CLDB filename '
#                       'specified in config (in cfg["SLU"][<clser_type>]'
#                       '["cldb_fname"])!')
#                raise SLUException(msg)
#            try:
#                cldb = CategoryLabelDatabase(cldb_fname)
#            except:
#                msg = ('Could not load the CLDB from the filename specified: '
#                       '{fname}.'.format(fname=cldb_fname))
#                raise SLUException(msg)
#
#            # Load the preprocessing class.
#            # XXX No other preprocessing class is expected in the SLU part of
#            # the code, but this would be the place to swap the class for
#            # another one.
#            preprocessing_cls = cfg_this_slu.get('preprocessing_cls',SLUPreprocessing)
#            preprocessing = preprocessing_cls(cldb)
#        else:
#            preprocessing = None
#
#        # Get all the kwargs that should be used to construct the classifier.
#        clser_kwargs = dict()
#        if training:
#            cfg_tr = cfg_this_slu['training']
#            if slu_type in ('cl-seq', 'cl-tracing'):
#                if 'clser_type' in cfg_tr:
#                    clser_kwargs['clser_type'] = cfg_tr['clser_type']
#                if 'features_type' in cfg_this_slu:
#                    clser_kwargs['features_type'] = cfg_this_slu[
#                        'features_type']
#                if 'abstractions' in cfg_tr:
#                    clser_kwargs['abstractions'] = cfg_tr['abstractions']
#
#        dai_clser = clser_class(preprocessing=preprocessing, cfg=cfg, **clser_kwargs)
#
#        # If a model needs to be trained yet,
#        if training:
#            # Construct the inputs and the outputs for learning.
#            obss, das = load_data(cfg_this_slu, training=training)
#            dai_clser.extract_features(das=das, obss=obss, verbose=verbose)
#            dai_clser.prune_features(
#                min_feature_count=cfg_tr.get('min_feat_count', None),
#                min_conc_feature_count=cfg_tr.get('min_feat_count_conc', None),
#                verbose=verbose)
#            dai_clser.prune_classifiers(
#                min_dai_count=cfg_tr.get('min_dai_count', None))
#            if verbose:
#                dai_clser.print_classifiers()
#
#            # Train the model.
#            dai_clser.train(balance=cfg_tr.get('balance', None),
#                            calibrate=cfg_tr.get('calibrate', None),
#                            inverse_regularisation=cfg_tr.get('sparsification', None),
#                            verbose=verbose)
#            # Save the model.
#            model_fname = cfg_tr.get('model_fname', None)
#            if model_fname is not None:
#                dai_clser.save_model(model_fname)
#                print >>sys.stderr, ('SLU model saved to "{fname}".'
#                                     .format(fname=model_fname))
#        else:
#            # Try to load the model.
#            model_fname = cfg_this_slu.get('testing', dict()
#                                           ).get('model_fname', None)
#            try:
#                dai_clser.load_model(model_fname)
#            except Exception as e:
#                if require_model:
#                    msg = 'Could not load SLU model.'
#                    if model_fname is None:
#                        msg += '  None was specified in the config.'
#                    else:
#                        msg += '  Tried to load it from "{fname}".'.format(
#                            fname=model_fname)
#                        msg += ('  The original exception was: {cls}{args}: '
#                                '"{ex}".').format(cls=ex.__class__.__name__, args=e.args, ex=e)
#                    raise SLUException(msg)
#
#    return dai_clser
#
## Methods for loading DAs and observations from files.
## _load_meths :: observation type -> load method
#_load_meths = {'utt': load_utterances,
#               'utt_nbl': load_utt_nblists,
#               'utt_cn': load_utt_confnets,
#               'prev_da': NotImplemented,
#               'da_nbl': NotImplemented}
## Names of config keys whose values specify the input file for that kind of
## observations.
## _infile_cfgname :: observation type -> configuration name
#_infile_cfgname = {'utt': 'utts_fname',
#                   'utt_nbl': 'uttcns_fname',
#                   'utt_cn': 'uttcns_fname',
#                   'prev_da': None,
#                   'da_nbl': None}
#
## Used in testing.
#CorrLists = namedtuple('CorrLists', ['corr', 'incorr'])
#
#
#
#def load_data(cfg_this_slu, training=False, with_das=True):
#    """
#    Loads training data for SLU.
#
#    Arguments:
#        cfg_tr -- the subconfig for this SLU type
#        training -- is the SLU about to be trained (as opposed to being tested
#            or used in general)?  This implies `require_model == False'.
#        with_das -- load also DAs?  If set to False, the second item in the
#            return tuple will be None.
#
#    Returns a tuple (obss, das) of co-indexed dictionaries where `obss' has the
#    training observations as values, and `das' has their corresponding DAs
#    (object DialogueAct) as its values.
#
#    """
#    cfg_trte = (cfg_this_slu['training'] if training
#                else cfg_this_slu['testing'])
#    max_examples = cfg_trte.get('max_examples', None)
#
#    # Find the right function for loading DAs and load them.
#    # TODO Enable this kind of cascading elsewhere too.
#    if with_das:
#        if 'das_loading_fun' in cfg_trte:
#            load_das = cfg_trte['das_loading_fun']
#        elif 'das_loading_fun' in cfg_this_slu:
#            load_das = cfg_this_slu['das_loading_fun']
#        else:
#            from alex.components.slu.da import load_das
#        das = load_das(cfg_trte['das_fname'], limit=max_examples)
#    else:
#        das = None
#
#    # Find what kinds of observations will be needed and load them.
#    obs_types = set(ft_props[ft].obs_type
#                    for ft in cfg_this_slu['features_type']
#                    if not ft.startswith('ab_'))
#    obss = {obs_type: _load_meths[obs_type](cfg_trte[_infile_cfgname[obs_type]],
#                                            limit=max_examples)
#            for obs_type in obs_types}
#
#    # Ensure all observations use exactly the same set of keys.
#    common_keys = reduce(set.intersection,
#                         (set(typed_obss.viewkeys())
#                          for typed_obss in obss.values()))
#    # FIXME: Impose the max_examples limit only after doing intersection (using
#    # _load_meths as generators).
#    if with_das:
#        common_keys.intersection_update(das.viewkeys())
#        das = {utt_id: da for (utt_id, da) in das.iteritems()
#               if utt_id in common_keys}
#    obss = {ot: {utt_id: obs for (utt_id, obs) in typed_obss.iteritems()
#                 if utt_id in common_keys}
#            for (ot, typed_obss) in obss.iteritems()}
#    return obss, das
#
#
#
#def _count_prf(true_pos, clsed_pos, act_pos):
#    if true_pos == clsed_pos == act_pos == 0:
#        return float('nan'), float('nan'), float('nan')
#    precision = true_pos / float(clsed_pos) if clsed_pos else 0.
#    recall = true_pos / float(act_pos) if act_pos else 0.
#    if precision + recall > 0.:
#        fscore = 2 * precision * recall / (precision + recall)
#    else:
#        fscore = 0.
#    return precision, recall, fscore
#
#
#def _get_scores(guessed, correct):
#    true_pos = 0
#    for item in guessed:
#        true_pos += (item in correct)
#    return _count_prf(true_pos, len(guessed), len(correct))
#
#
#def _assess_clsers(our_clser_cooccs, our_clser_scores, guessed, correct):
#    guessed_set = set(guessed)
#    correct_set = set(correct)
#
#    all_set = set.union(guessed_set, correct_set)
#    cls_tup = {dai: (dai in guessed_set, dai in correct_set)
#               for dai in all_set}
#
#    for dai, tup in cls_tup.iteritems():
#        # Register the score for each DAI.
#        our_clser_scores[dai].append(tup)
#        # Check only misclassified dais.
#        if tup[0] == tup[1]:
#            continue
#        # Remember co-occurrences of classifiers' responses.
#        for other, other_tup in cls_tup.iteritems():
#            if dai == other:
#                continue
#            our_clser_cooccs[dai][tup][other][other_tup] += 1
#
#
#def _values2catlabs(dais, slotval2catlab):
#    dais_with_cl = copy.deepcopy(dais)
#    for dai in dais_with_cl:
#        if dai.value in slotval2catlab:
#            dai.value2category_label(slotval2catlab[dai.value])
#    return dais_with_cl
#
#
#def _print_cooc_stats(dai_cooccs, our_scores, cfg_te, outfile=sys.stdout):
#    dai_stats = list()
#    for other, other_stats in dai_cooccs.iteritems():
#        ft = other_stats[(False, True)]
#        tf = other_stats[(True, False)]
#        tt = other_stats[(True, True)]
#        dai_stats.append((ft + tf + tt, ft, tf, tt, other))
#    for tot, ft, tf, tt, other in sorted(dai_stats, key=lambda tup: -tup[0]):
#        perc = 100. * tot / float(len(our_scores))
#        if perc < cfg_te.get('min_perc', 50.):
#            continue
#        outfile.write(("{perc:3.0f}% ... {ft:2d} FN; {tf:2d} FP; {tt:2d} "
#                       "TP:  {other}\n").format(**locals()))
#
#
#def test(cfgor):
#    """Tests the model according to current configuration.
#
#    Arguments:
#        cfgor -- a DefaultConfigurator, containing the preprocessed
#            current configuration
#
#    """
#
#    # Imports.
#    from collections import defaultdict
#    from numpy import mean, std
#
#    from alex.components.slu.da import save_das
#    from alex.corpustools.semscore_mk import SemScorer
#
#    # Shorthands.
#    model_fname = cfgor.cfg_te['model_fname']
#    model_fbase = model_fname[:model_fname.index('.slu_model')]
#    dai_clser = slu_factory(cfgor.config, require_model=True)
#
#    # Initialisation.
#    cls_threshold = None
#    cls_thresholds = None
#
#    # Load test data.
#    obss, das = load_data(cfgor.cfg_this_slu, training=False)
#
#    # Do the classification.
#    parsed_das = dict()
#    dai_occs = defaultdict(int)
#    probs_corr_or_incorr = CorrLists(list(), list())
#    fscores = list()
#    our_clser_fscores = defaultdict(list)
#    our_clser_cooccs = defaultdict(
#        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
#
#    out_fname = '{0}.teout.gz'.format(model_fbase)
#    import gzip
#    with gzip.open(out_fname, 'w') as outfile:
#        sep = '=' * 41 + '\n'
#        for utt_key in das.iterkeys():
#            turn_obs = {ot: obss[ot].get(utt_key, None) for ot in obss}
#
#            # FIXME Another method than parse_1_best should perhaps be called.
#            # This requires well-thought changes in the whole code.
#            da_confnet, cl_map = dai_clser.parse_1_best(
#                obs=turn_obs, ret_cl_map=True, verbose=True)
#
#            # Renormalise.
#            if cfgor.cfg_te.get('renormalise', False):
#                da_confnet.normalise_by_slot()
#
#            # Bias the decisions if asked to.
#            if cfgor.cfg_te.get('threshold', None):
#                cls_threshold = cfgor.cfg_te['threshold']
#            elif hasattr(dai_clser, 'cls_thresholds'):
#                cls_thresholds = dai_clser.cls_thresholds
#            elif hasattr(dai_clser, 'cls_threshold'):
#                cls_threshold = dai_clser.cls_threshold
#            else:
#                cls_threshold = 0.5
#
#            # Decode, print the logprob rather than prob.
#            dah = da_confnet.get_best_da_hyp(use_log=True,
#                                             threshold=cls_threshold,
#                                             thresholds=cls_thresholds)
#            parsed_das[utt_key] = dah.da
#
#            outfile.write('\n')
#            outfile.write('Resulting confnet:\n{cn}\n'.format(cn=da_confnet))
#            outfile.write('Best DA hyp: {da}\n'.format(da=dah))
#            outfile.write('Correct DAIs: ')
#            outfile.write('; '.join(unicode(dai) for dai in das[utt_key]))
#            outfile.write('\n')
#
#            # Remember probs assigned to correct, and to incorrect dais.
#            # Correct:
#            for dai in das[utt_key]:
#                probs_corr_or_incorr.corr.append(
#                    da_confnet.get_marginal(dai) or 0.)
#            # Incorrect:
#            for dai in dah.da:
#                if dai in das[utt_key]:
#                    continue
#                probs_corr_or_incorr.incorr.append(
#                    da_confnet.get_marginal(dai) or 0.)
#
#            # Evaluate individual classifiers' performance.
#            slotval2catlab = {val_form[0]: catlab
#                            for (catlab, val_form) in cl_map.iteritems()}
#
#            our_dais_with_cl = _values2catlabs(dah.da.dais, slotval2catlab)
#            correct_dais_with_cl = _values2catlabs(das[utt_key].dais,
#                                                slotval2catlab)
#            for dai in correct_dais_with_cl:
#                dai_occs[dai] += 1
#            _assess_clsers(our_clser_cooccs, our_clser_fscores,
#                        our_dais_with_cl, correct_dais_with_cl)
#
#            # Print fscores for this input.
#            if das[utt_key].dais:
#                # Our fscores.
#                precision, recall, fscore = _get_scores(dah.da.dais,
#                                                        das[utt_key].dais)
#                fscores.append((precision, recall, fscore))
#                outfile.write(
#                    'Scores          (P/R/F): {p:.2f}/{r:.2f}/{f:.2f}\n'
#                    .format(p=precision, r=recall, f=fscore))
#                outfile.write(sep)
#                outfile.write('\n')
#
#        # Save the decoded DAs.
#        if not cfgor.cfg_te.get('vanilla', False):
#            das_outfname = '{0}.das'.format(model_fbase)
#            save_das(das_outfname, parsed_das)
#
#            score_outfname = '{0}.score'.format(model_fbase)
#            scorer = SemScorer(cfgor)
#            with open(score_outfname, 'w') as score_file:
#                scorer.score(cfgor.cfg_te['das_fname'], parsed_das, True,
#                             score_file)
#
#        outfile.write('\n')
#        outfile.write(sep)
#        outfile.write("Per classifier statistics:\n")
#        for dai, our_cscores in our_clser_fscores.iteritems():
#            assert our_cscores
#            true_pos = our_cscores.count((True, True))
#            false_pos = our_cscores.count((True, False))
#            false_neg = our_cscores.count((False, True))
#            precision, recall, fscore = _count_prf(true_pos,
#                                                   true_pos + false_pos,
#                                                   true_pos + false_neg)
#
#            outfile.write('{dai}\n'.format(dai=unicode(dai)))
#            outfile.write("Total occurrences: {tot} (ours: {otot})\n".format(
#                          otot=len(our_cscores), tot=dai_occs[dai]))
#            outfile.write("P/R/F (ours): {p:.3f}/{r:.3f}/{f:.3f}\n".format(
#                p=precision, r=recall, f=fscore))
#            if our_clser_cooccs[dai][(True, False)]:
#                outfile.write("FP cooccurrences (ours):\n")
#                _print_cooc_stats(our_clser_cooccs[dai][(True, False)],
#                                  our_cscores, cfgor.cfg_te, outfile=outfile)
#            if our_clser_cooccs[dai][(False, True)]:
#                outfile.write("FN cooccurrences (ours):\n")
#                _print_cooc_stats(our_clser_cooccs[dai][(False, True)],
#                                  our_cscores, cfgor.cfg_te, outfile=outfile)
#            outfile.write('\n')
#        outfile.write(sep)
#
#        n_data = len(fscores)
#        mean_precision = sum(score[0] for score in fscores) / n_data
#        mean_recall = sum(score[1] for score in fscores) / n_data
#        mean_fscore = sum(score[2] for score in fscores) / n_data
#        outfile.write('\n')
#        outfile.write(
#            ("Mean prob assigned to correct/incorrect DAIs: "
#             "{corr:.2f}+-{corrst:.2f}/{incorr:.2f}+-{incorrst:.2f}\n")
#            .format(corr=mean(probs_corr_or_incorr.corr),
#                    corrst=std(probs_corr_or_incorr.corr),
#                    incorr=mean(probs_corr_or_incorr.incorr),
#                    incorrst=std(probs_corr_or_incorr.incorr)))
#        outfile.write("Overall fscores (macro-average): "
#                      "{p:.2f}/{r:.2f}/{f:.2f}\n".format(p=mean_precision,
#                                                         r=mean_recall,
#                                                         f=mean_fscore))
#
#
#class DefaultConfigurator(object):
#    DEFAULTS_SLU_TYPE = {'type': ('cl-tracing', 'ty_{0}')}
#    DEFAULTS_SLU = {
#        'cl-tracing': {'do_preprocessing': (True, 'noprep'),
#                       'features_type': (('ab_ngram', 'ngram', ), 'ft_{0}'), },
#        'cl-seq'    : {'do_preprocessing': (True, 'noprep'), },
#    }
#    DEFAULTS_SLU_TR = {
#        'cl-tracing': {'abstractions': (('abstract', ), 'abs_{0}'),
#                       'max_examples': (None, 'top{0}'),
#                       'clser_type': ('logistic', '{0}'),
#                       'min_feat_count': (10, 'minf{0}'),
#                       'min_feat_count_conc': (5, 'minfc{0}'),
#                       'min_dai_count': (10, 'mind{0}'),
#                       'balance': (True, 'nobal'),
#                       'calibrate': (True, 'nocal'),
#                       'sparsification': (1., 's{0}'), },
#        'cl-seq'    : dict(),
#    }
#    DEFAULTS_SLU_TE = {
#        'cl-tracing': {
#            'max_examples': None,
#            'min_perc': 80,
#            'renormalise': True,    # Whether to normalise alternative values
#                                    # for same slots.
#            'threshold': None,      # set to None to use the learned one
#        },
#        'cl-seq': {
#            'max_examples': None,
#        },
#    }
#    for shared_key in ('max_examples', 'min_feat_count', 'min_dai_count',
#                       'sparsification'):
#        DEFAULTS_SLU_TR['cl-seq'][shared_key] = (
#            DEFAULTS_SLU_TR['cl-tracing'][shared_key])
#
#    def __init__(self, cfg=None, more_defaults=dict(),
#                 more_defaults_type=dict(), more_defaults_tr=dict(),
#                 more_defaults_te=dict()):
#        """
#        Initialises this object for SLU configuration maintenance.
#
#        Arguments:
#            cfg -- the Config object to be represented by this Configurator
#            more_defaults, more_defaults_type, more_defaults_tr -- dictionaries
#                providing additional defaults for config options, whose
#                terminal values are of the following form:
#
#                    (default_value, fname_template)
#
#                where fname_template is a template string which is used in case
#                a non-default value is supplied in the config for this option.
#                This template is then used in building the model file name,
#                expanding '{0}' into a string representation of the option
#                value actually used.
#
#                - more_defaults provides defaults for the 'SLU' config
#                    suboption.
#                - more_defaults_type provides defaults for the ['SLU']['type']
#                    config suboption
#                - more_defaults_tr provides defaults for the
#                    ['SLU'][<type>]['training'] config suboption, skipping the
#                    'training' key but providing the <type> key at the first
#                    level (see the class' code)
#
#            more_defaults_te -- like more_defaults_tr, but the option values
#                are just
#
#                    default_value
#
#                not including the fname_template (since no files are given
#                new names at testing-time)
#
#        """
#        # Copy the class defaults.
#        self.def_slu_type = copy.deepcopy(self.DEFAULTS_SLU_TYPE)
#        self.def_slu = copy.deepcopy(self.DEFAULTS_SLU)
#        self.def_slu_tr = copy.deepcopy(self.DEFAULTS_SLU_TR)
#        self.def_slu_te = copy.deepcopy(self.DEFAULTS_SLU_TE)
#        # Update them with defaults supplied by the caller.
#        self.def_slu.update(more_defaults)
#        self.def_slu_type.update(more_defaults_type)
#        self.def_slu_tr.update(more_defaults_tr)
#        self.def_slu_te.update(more_defaults_te)
#        # Build the config.
#        self.build_config(cfg)
#
#    def build_config(self, cfg=None):
#        """Builds a sufficiently complete config for training an SLU model.
#
#        Where the provided config `cfg' does not specify a required value, the
#        default is substituted.
#
#        Arguments:
#            cfg -- the Config object to use in this training;  if None, the
#                default config is used
#
#        Returns None.  The resulting Config is saved in `self.config'.
#
#        """
#
#        # Process arguments.
#        if cfg is None:
#            from alex.utils.config import Config
#            cfg = Config.load_configs(log=False)
#
#        # Find actual configurations to be used.
#        self.config = cfg
#        cfg_slu = self.config.config.setdefault('SLU', dict())
#        slu_type = cfg_slu.setdefault('type', self.def_slu_type['type'][0])
#        try:
#            cfg_this_slu = cfg_slu[slu_type]
#        except KeyError:
#            cfg_this_slu = {name: default for (name, (default, _))
#                            in self.def_slu[slu_type].iteritems()}
#
#        # - Build the training dictionary by merging `cfg' into the defaults.
#        cfg_tr_orig = cfg_this_slu.get('training', dict())
#        cfg_tr_defaults = {name: default for (name, (default, _))
#                           in self.def_slu_tr[slu_type].iteritems()}
#        cfg_tr = cfg_this_slu['training'] = cfg_tr_defaults
#        cfg_tr.update(cfg_tr_orig)
#
#        # - Build the testing dictionary by merging `cfg' into the defaults.
#        cfg_te_orig = cfg_this_slu.get('testing', dict())
#        cfg_te = cfg_this_slu['testing'] = copy.deepcopy(self.def_slu_te)
#        cfg_te.update(cfg_te_orig)
#
#        # Save shorthand variables pointing to config subdicts.
#        self.cfg_slu = cfg_slu
#        self.slu_type = slu_type
#        self.cfg_this_slu = cfg_this_slu
#        self.cfg_tr = cfg_tr
#        self.cfg_te = cfg_te
#
#    def set_model_name(self, model_fname, training=False):
#        """
#        Sets the model filename option in the config.
#
#        Arguments:
#            model_fname -- path towards the model file;  if no such file is
#                found, this argument is interpreted as a path relative to the
#                models directory configured
#            training -- whether we are in the training phase (the alternative
#                being the testing phase).  This selects the appropriate
#                configuration subdictionary.
#
#        """
#        # Provide for model_fname specifying just the file name within the
#        # models directory.
#        if not os.path.isfile(model_fname):
#            model_fname = os.path.join(self.cfg_tr['models_dir'], model_fname)
#        cfg_trte = self.cfg_tr if training else self.cfg_te
#        cfg_trte['model_fname'] = model_fname
#        return model_fname
#
#
#class ParamModelNameBuilder(DefaultConfigurator):
#    """Class that can build model filename from configuration settings."""
#    from datetime import date
#
#    _lock_tpt = os.path.join('{dir_}', '{base}.lock')
#
#    @classmethod
#    def clean_arg(cls, arg):
#        """Cleans an argument value for use in the model file name."""
#        if isinstance(arg, tuple) or isinstance(arg, list):
#            arg_str = ','.join(arg)
#        elif isinstance(arg, float):
#            arg_str = '{0:.1f}'.format(arg)
#        else:
#            arg_str = str(arg)
#        # Clean path arguments: take the basename.
#        arg_str = arg_str[arg_str.rfind(os.sep) + 1:]
#        # Shorten the argument and replace dashes.
#        return arg_str[-7:].replace('-', '_')
#
#    @classmethod
#    def _lock_exists(cls, dirname, basename):
#        return os.path.exists(cls._lock_tpt.format(dir_=dirname,
#                                                   base=basename))
#
#    def build_name(self, existing=False, lock=True):
#        """Builds a name for the model to be trained.
#
#        Arguments:
#            existing -- whether to look for an existing model, or rather avoid
#                clashes (default: False -- avoid clashes)
#            lock -- whether to create a lock for the created filename
#
#        Returns path (not necessarily an absolute path) to the model file.
#
#        """
#
#        # Build the model name.
#        param_strs = list()
#        for cfg_dict, defaults in (
#                (self.cfg_slu, self.def_slu_type),
#                (self.cfg_this_slu, self.def_slu.get(self.slu_type, tuple())),
#                (self.cfg_tr, self.def_slu_tr.get(self.slu_type, tuple()))):
#            for name, (default, tpt) in sorted(defaults.iteritems()):
#                val = cfg_dict[name]
#                if val != default:
#                    param_strs.append(tpt.format(self.clean_arg(val)))
#        model_bname = '{d}_{params}.slu_model.gz'.format(
#            d=self.date.strftime(self.date.today(), '%y%m%d'),
#            params='-'.join(param_strs))
#        model_dir = self.cfg_tr['models_dir']
#        # Ensure the model directory exists.
#        if not os.path.isdir(model_dir):
#            os.makedirs(model_dir)
#        # Ensure the model name is free to use.
#        bname_base = model_bname[:-len('.slu_model.gz')]
#        model_fname = os.path.join(model_dir, model_bname)
#        model_num = 0
#        while (os.path.exists(model_fname)
#               or (lock and self._lock_exists(model_dir, model_bname))):
#            model_num += 1
#            model_bname = '{base}.{num}.slu_model.gz'.format(base=bname_base,
#                                                             num=model_num)
#            model_fname = os.path.join(model_dir, model_bname)
#        # Save the resulting name and return.
#        self.cfg_tr['model_fname'] = model_fname
#        return model_fname
