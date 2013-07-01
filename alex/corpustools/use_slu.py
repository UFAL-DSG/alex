#!/usr/bin/env python
# vim: set fileencoding=utf-8

from __future__ import unicode_literals


def main(args):
    import codecs
    import os.path
    import sys

    from alex.components.slu.common import load_data, slu_factory, \
        DefaultConfigurator
    from alex.utils.config import Config

    # Merge configuration files specified as arguments.
    cfg = Config.load_configs(args.configs, log=False)
    # Process the configuration.
    cfgor = DefaultConfigurator(cfg)

    # Update configuration from the explicit arguments.
    if args.infname.endswith('uttcn'):
        cfgor.cfg_te['uttcns_fname'] = args.infname
    else:
        cfgor.cfg_te['utts_fname'] = args.infname

    # Initialisation.
    cls_threshold = None
    cls_thresholds = None
    dai_clser = slu_factory(cfgor.config, require_model=True)
    obss, _ = load_data(cfgor.cfg_this_slu, training=False, with_das=False)

    # Do the classification.
    random_ot_obss = obss.values()[0]
    with codecs.open(args.outfname, 'w', encoding='UTF-8') as outfile:
        for utt_key in random_ot_obss.iterkeys():
            turn_obs = {ot: obss[ot].get(utt_key, None) for ot in obss}

            # FIXME Another method than parse_1_best should perhaps be called.
            # This requires well-thought changes in the whole code.
            da_confnet = dai_clser.parse_1_best(obs=turn_obs,
                                                verbose=args.verbose)

            # Bias the decisions if asked to.
            if cfgor.cfg_te.get('threshold', None):
                cls_threshold = cfgor.cfg_te['threshold']
            elif hasattr(dai_clser, 'cls_thresholds'):
                cls_thresholds = dai_clser.cls_thresholds
            elif hasattr(dai_clser, 'cls_threshold'):
                cls_threshold = dai_clser.cls_threshold
            else:
                cls_threshold = 0.5

            # Decode and output.
            dah = da_confnet.get_best_da_hyp(threshold=cls_threshold,
                                             thresholds=cls_thresholds)
            outfile.write('{key} => {da}\n'.format(key=utt_key,
                                                   da=unicode(dah.da)))
            if args.verbose:
                sys.stderr.write('.')
                sys.stderr.flush()


if __name__ == "__main__":
    import argparse

    arger = argparse.ArgumentParser(
        description="Applies SLU to parse input from a file in the `wavaskey' "
                    "format.")
    arger.add_argument('infname', metavar='INFILE')
    arger.add_argument('outfname', metavar='OUTFILE')
    arger.add_argument('-c', '--configs', nargs='+',
                       help='configuration files')
    arger.add_argument('-v', '--verbose', action="store_true",
                       help='be verbose')
    args = arger.parse_args()

    main(args)
