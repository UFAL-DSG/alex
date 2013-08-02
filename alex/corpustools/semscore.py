#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import argparse
from collections import defaultdict
import numpy as np
from operator import itemgetter
import re
import sys

import autopath

from alex.components.slu.da import DialogueAct, DialogueActItem

_nan = np.nan
_dai_val_rx = re.compile('(?<==")([^"]*)')


class SemScorer(object):
    _TP, _FP, _FN = 0, 1, 2

    def __init__(self, cfgor):
        self.cfgor = cfgor

    def load_das(self, das_fname=None):
        if 'das_loading_fun' in self.cfgor.cfg_te:
            load_das = self.cfgor.cfg_te['das_loading_fun']
        elif 'das_loading_fun' in self.cfgor.cfg_this_slu:
            load_das = self.cfgor.cfg_this_slu['das_loading_fun']
        else:
            from alex.components.slu.da import load_das
        max_examples = self.cfgor.cfg_te.get('max_examples', None)
        das_fname = (self.cfgor.cfg_te['das_fname'] if das_fname is None
                     else das_fname)
        return load_das(das_fname, limit=max_examples)

    @staticmethod
    def get_scores(stats, percent=True):
        coef = 100. if percent else 1.
        tp, fp, fn = stats
        tot_p = float(tp + fp)   # total positive
        tot_ap = float(tp + fn)  # total actual positive
        precision = coef * tp / tot_p if tot_p > 0. else _nan
        recall = coef * tp / tot_ap if tot_ap > 0. else _nan

        # DEBUG
        if precision > 1 + 99 * percent:
            import ipdb
            ipdb.set_trace()
        if recall > 1 + 99 * percent:
            import ipdb
            ipdb.set_trace()

        return precision, recall, SemScorer.hmean(precision, recall)

    @staticmethod
    def hmean(a, b):
        if a + b > 0.:
            # DEBUG
            if np.isinf(a) or np.isinf(b):
                import ipdb
                ipdb.set_trace()
            return 2 * a * b / (a + b)
        elif a == b == 0.:
            return 0.
        else:
            return _nan

    @classmethod
    def get_da_stats(cls, da, ref_da):
        # Handle 'null()' specially.
        if not da.dais:
            da.dais.append(DialogueActItem('null'))
        if not ref_da.dais:
            ref_da.dais.append(DialogueActItem('null'))

        # Count TP, FP, FN.
        stats = [0, 0, 0]
        dai_stats = defaultdict(lambda: [0, 0, 0])
        for dai in da:
            dai_str = _dai_val_rx.sub('*', unicode(dai))
            if dai in ref_da:
                stats[SemScorer._TP] += 1
                dai_stats[dai_str][SemScorer._TP] += 1
            else:
                stats[SemScorer._FP] += 1
                dai_stats[dai_str][SemScorer._FP] += 1
        for dai in ref_da:
            if dai not in da:
                dai_str = _dai_val_rx.sub('*', unicode(dai))
                stats[SemScorer._FN] += 1
                dai_stats[dai_str][SemScorer._FN] += 1
        return stats, dai_stats

    @classmethod
    def score_dicts(cls, das_dict, ref_dict):
        """Computes counts and scores for two co-indexed dictionaries of DAs.

        Arguments:
            das_dict -- DAs whose scores should be measured
            ref_dict -- reference DAs

        Returns a triple (stats, scores, dai_scores) where

            - stats consist of triples (true positives, false positives,
                                        false negatives)
            - scores consist of triples (precision, recall, f-score)

        and

            - items without "dai_" contain global numbers (over all DAIs)
            - items with "dai_" are indexed with particular DAIs at the first
                level

        The `scores' return item contains a macro-average of the scores.

        """

        get_scores = SemScorer.get_scores
        stats = np.zeros(3, dtype=int)
        scores = np.empty((len(ref_dict), 3), dtype=float)
        dai_stats = defaultdict(lambda: np.zeros(3, dtype=int))
        # dai_scores = defaultdict(lambda: list())
        dai_scores = dict()

        # Count stats, store scores.
        for da_idx, (da_key, ref_da) in enumerate(ref_dict.iteritems()):
            obs_stats, obs_dai_stats = cls.get_da_stats(
                das_dict.get(da_key, DialogueAct()), ref_da)
            stats += obs_stats
            scores[da_idx, :] = get_scores(obs_stats)
            for dai, one_dai_stats in obs_dai_stats.iteritems():
                dai_stats[dai] += one_dai_stats
                # dai_scores[dai].append(get_scores(one_dai_stats))
        stats = np.sum(dai_stats.values(), axis=0)

        # Aggregate.
        macro_scores = list()
        macro_scores.append(np.mean(scores[~np.isnan(scores[:, 0]), 0]))
        macro_scores.append(np.mean(scores[~np.isnan(scores[:, 1]), 1]))
        macro_scores.append(SemScorer.hmean(macro_scores[0], macro_scores[1]))
        for dai in dai_stats:
            # This computes DAI scores as micro-averages.
            dai_scores[dai] = SemScorer.get_scores(dai_stats[dai])
            # This would compute DAI scores as macro-averages.
            # dai_scores[dai] = [
            #     np.mean(filter(lambda score: not np.isnan(score),
            #                    map(itemgetter(stat_type), dai_scores[dai])))
            #     for stat_type in (0, 1, 2)]

        return stats, macro_scores, dai_scores

    def score(self, ref, das, item_level=True, outfile=sys.stdout):
        """Prints out evaluation of proposed semantics against a reference.

        Arguments:
            das, ref -- proposed semantics, reference semantics;  each can be
                either a dictionary mapping from a common set of utterance keys
                to DialogueAct objects, or path towards a file capturing such
                a dictionary in the ``wavaskey'' format
            item_level -- whether to print out a detailed report also for each
                DAI (dialogue act item)  (default: True)
            outfile -- a file-like object open for writing where the output
                should be written (default: sys.stdout)

        """

        # Load the dictionaries.
        if not isinstance(das, dict):
            das = self.load_das(das)
        if not isinstance(ref, dict):
            ref = self.load_das(ref)

        # Intersect the dictionaries to the common keys.
        outfile.write('The results are based on {num} DAs.\n'.format(
            num=len(das)))
        das = {key: val for (key, val) in das.iteritems() if key in ref}
        ref = {key: val for (key, val) in ref.iteritems() if key in das}

        stats, macro_scores, dai_scores = self.score_dicts(das, ref)
        micro_scores = SemScorer.get_scores(stats)

        width = 80
        sep = "-" * width + '\n'

        # Print out scores for individual DAIs.
        if item_level:
            line_tpt = '{dai: >40} {s[0]: >10} {s[1]: >10} {s[2]: >10}\n'
            outfile.write(sep)
            outfile.write(line_tpt.format(dai='Dialogue act item',
                                          s=('Precision', 'Recall', 'F-score'))
                          )
            line_tpt = '{dai: >40} {s[0]: 10.2f} {s[1]: 10.2f} {s[2]: 10.2f}\n'
            for dai, one_dai_scores in sorted(dai_scores.iteritems()):
                outfile.write(line_tpt.format(dai=dai, s=one_dai_scores))
            outfile.write(sep)
            outfile.write('\n')

        # Print out total scores.
        outfile.write('           {mac: >6}  {mic: >6}\n'.format(mac='macro',
                                                                 mic='micro'))
        outfile.write(sep)
        outfile.write("Precision: {mac:6.2f}  {mic:6.2f}\n".format(
            mac=macro_scores[0], mic=micro_scores[0]))
        outfile.write("Recall:    {mac:6.2f}  {mic:6.2f}\n".format(
            mac=macro_scores[1], mic=micro_scores[1]))
        outfile.write("F-score:   {mac:6.2f}  {mic:6.2f}\n".format(
            mac=macro_scores[2], mic=micro_scores[2]))


if __name__ == '__main__':
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      Compute scores of a semantic parser output against reference semantics.
      The scores include total precision and recall, and slot level
      precision and recall.

      The files structures must be as follows:
        sem_name    => sem_content
        ----------------------------------------
        0000001.wav => inform(food="Chinese")
        0000002.wav => request(phone)

      The semantics from the test file and the reference file is matched
      based on the sem_name.
      """)

    arger.add_argument('refsem', metavar='FILE',
                       help='path towards a file with reference semantics')
    arger.add_argument('testsem', metavar='FILE',
                       help='path towards an evaluated file with semantics')
    arger.add_argument('-i', '--item-level', action="count",
                       help='toggle printing item-level (DAI) scores '
                            '(default: printing enabled)')
    arger.add_argument('-c', '--configs', nargs='+',
                       help='configuration files')
    args = arger.parse_args()

    from alex.components.slu.common import DefaultConfigurator
    from alex.utils.config import Config

    scorer = SemScorer(DefaultConfigurator(Config.load_configs(args.configs)))
    scorer.score(args.refsem, args.testsem, bool(1 + args.item_level))
