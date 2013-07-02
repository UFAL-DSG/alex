#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

if __name__ == "__main__":
    import argparse

    try:
        import autopath
    except ImportError:
        pass

    from alex.components.slu.common import ParamModelNameBuilder, test
    from alex.utils.config import Config
    from alex.utils.excepthook import ExceptionHook

    arger = argparse.ArgumentParser(
        description='Tests an SLU model.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arger.add_argument('-i', '--model-fname',
                       help='File name of the trained SLU model.')
    arger.add_argument('-m', '--max-examples',
                       type=int,
                       default=None,
                       help='Limit on number of test dialogues/turns.')
    arger.add_argument('-q', '--vanilla',
                       default=None,
                       action='store_true',
                       help='Do not write output files.')
    arger.add_argument('-c', '--configs', action="store", nargs='+',
                       help='configuration files')
    args = arger.parse_args()

    # Merge configuration files specified as arguments.
    cfg = Config.load_configs(args.configs, log=False)
    # Process the configuration.
    name_builder = ParamModelNameBuilder(cfg)
    if args.model_fname is not None:
        # If model name was supplied, use that one.
        model_path = name_builder.set_model_name(args.model_fname,
                                                 training=False)
    else:
        # If model name has to be built, build it.
        model_path = name_builder.build_name()

    # Update configuration from the explicit arguments.
    if args.vanilla is not None:
        name_builder.cfg_te['vanilla'] = args.vanilla
    if isinstance(args.max_examples, int):
        name_builder.cfg_te['max_examples'] = args.max_examples

    # Respect the debugging setting.
    if cfg['SLU'].get('debug', False):
        ExceptionHook.set_hook('ipdb')

    test(name_builder)
