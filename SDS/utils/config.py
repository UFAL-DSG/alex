#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import cStringIO
import pprint
import os.path
import re
import copy

import SDS.utils.env as env

config = None


class Config(object):
    """\
    Config handles configuration data necessary for all the components
    in the SDS. It implements a dictionary so that any component could
    store arbitrary structured data.

    When the configuration file is loaded, several automatic transformations
    are applied.
        1) '{cfg_abs_path}' as a substring of atomic attributes is replaced by
            an absolute path of the configuration files.  This can be used to
            make the configuration file independent of the location of programs
            using the configuration file.

    """

    def __init__(self, file_name=None, project_root=False, config={}):
        self.config = config

        if project_root:
            file_name = os.path.join(env.root(), file_name)

        if file_name:
            self.load(file_name)

    def get(self, i, default=None):
        return self.config.get(i, default)

    def __delitem(self, i):
        del self.config[i]

    def __len__(self):
        return len(self.config)

    def __getitem__(self, i):
        return self.config[i]

    def __setitem__(self, key, val):
        self.config[key] = val

    def __iter__(self):
        for i in self.config:
            yield i

    def __str__(self):
        """ Converts the the config into a pretty print string.

        It removes all lines which include word:
            - password

        to prevent password logging.
        """
        sio = cStringIO.StringIO()
        pprint.pprint(self.config, sio, indent=2, width=120)
        cfg = sio.getvalue()

        cfg = re.sub(r".*password.*", "# this line was removed since it" +
                     "included a password", cfg)

        return cfg

    def load(self, file_name):
        """\
        FIXME: Executing external files is not ideal!
        It should be changed in the future!
        """
        # pylint: disable-msg=E0602

        global config
        config = None

        execfile(file_name, globals())
        assert config is not None
        self.config = config

        cfg_abs_dirname = os.path.dirname(os.path.abspath(file_name))
        self.config_replace('{cfg_abs_path}', cfg_abs_dirname)

    def merge(self, other):
        """Merges self's config with other's config and saves it as a new
        self's config.

        Keyword arguments:
            - other: a Config object whose configuration dictionary to merge
                     into self's one

        """
        # pylint: disable-msg=E0602
        if type(other) is str:
            other = Config(other)
        self.update(other.config)

    def update(self, new_config, config_dict=None):
        """Updates the nested configuration dictionary by another, potentially
        also nested dictionary.

        Keyword arguments:
            - new_config: the new dictionary to update with
            - config_dict: the config dictionary to be updated

        """
        if config_dict is None:
            config_dict = self.config
        for key, val in new_config.iteritems():
            if isinstance(val, collections.Mapping):
                subdict = self.update(val, config_dict.get(key, {}))
                config_dict[key] = subdict
            else:
                config_dict[key] = new_config[key]
        return config_dict

    def config_replace(self, p, s, d=None):
        """\
        Replace a pattern p with string s in the whole config
        (recursively) or in a part of the config given in d.

        """
        if d is None:
            d = self.config
        for k, v in d.iteritems():
            if isinstance(v, collections.Mapping):
                self.config_replace(p, s, v)
            elif isinstance(v, str):
                d[k] = d[k].replace(p, s)
        return

    def unfold_lists(self, pattern):
        """\
        Unfold lists under keys matching the given pattern
        into several config objects, each containing one item.
        If pattern is None, all lists are expanded.
        """
        for k, v in self.config.iteritems():
            if type(v) is list and (pattern is None or re.search(pattern, k)):
                unfolded = []
                for item in v:
                    ci = Config(config=copy.deepcopy(self.config))
                    ci[k] = item
                    unfolded.extend(ci.unfold_lists(pattern))
                return unfolded
        return [self]
