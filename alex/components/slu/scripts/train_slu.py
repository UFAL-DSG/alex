#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

if __name__ == "__main__":
    import argparse
    import codecs
    import sys

    try:
        import autopath
    except ImportError:
        pass

    from alex.components.slu.common import ParamModelNameBuilder, slu_factory
    from alex.utils.config import Config
    from alex.utils.excepthook import ExceptionHook
    from alex.utils.filelock import FileLock

    arger = argparse.ArgumentParser(description='Trains an SLU model.')
    arger.add_argument('-o', '--model-fname', default=None)
    arger.add_argument('-n', '--dry-run', action='store_true')
    arger.add_argument('-c', '--configs', action="store", nargs='+',
                       help='configuration files')
    args = arger.parse_args()

    # Merge configuration files specified as arguments.
    cfg = Config.load_configs(args.configs, log=False)
    # Process the configuration.
    name_builder = ParamModelNameBuilder(cfg)
    if args.model_fname is not None:
        # If model name was supplied, process just the Config.
        model_path = name_builder.set_model_name(args.model_fname,
                                                 training=True)
    else:
        # If model name has to be built, build it (building the Config as
        # a by-product).
        model_path = name_builder.build_name()

    with FileLock(model_path):
        if not args.dry_run and not name_builder.cfg_tr.get('vanilla', False):
            cfg_path = '{dir_base}.config'.format(
                dir_base=model_path[:model_path.find('.slu_model')])
            with codecs.open(cfg_path, 'w', encoding='UTF-8') as cfg_file:
                cfg_file.write(unicode(name_builder.config))

        print >>sys.stderr, ('Going to write the model to "{path}".'
                            .format(path=model_path))

        # Respect the debugging setting.
        if cfg['SLU'].get('debug', False):
            ExceptionHook.set_hook('ipdb')

        if not args.dry_run:
            # The following also saves the model, provided a filename has been
            # specified in the config.
            slu_factory(cfg, training=True, verbose=True)
