#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import collections
import copy
from importlib import import_module
import os
import time
import pprint
import re
import sys
import tempfile
import shutil
import math
import urllib
import urllib2

import alex.utils.env as env
from alex.utils.exceptions import ConfigException


config = None

online_update_server = "https://vystadial.ms.mff.cuni.cz/download/alex/"


def as_project_path(path):
    return os.path.join(env.root(), path)

__current_size = 0  # global state variable, which exists solely as a
                    # workaround against Python 3.3.0 regression
                    # http://bugs.python.org/issue16409
                    # fixed in Python 3.3.1


def to_project_path(path):
    """Converts a relative or absoulute file system path to a path relative to project root."""
    path = os.path.abspath(path)
    root = env.root()
    if not path.startswith(root):
        raise Exception('Path is outside the root:' + path)
    path = path[len(root):]
    if path.startswith(os.path.sep):
        return path[1:]
    return path


def callback_download_progress(blocks, block_size, total_size):
    """callback function for urlretrieve that is called when connection is
    created and when once for each block

    :param blocks: number of blocks transferred so far
    :param block_size: in bytes
    :param total_size: in bytes, can be -1 if server doesn't return it
    """
    global __current_size

    width = 80

    if sys.version_info[:3] == (3, 3, 0):  # regression workaround
        if blocks == 0:  # first call
            __current_size = 0
        else:
            __current_size += block_size
        current_size = __current_size
    else:
        current_size = min(blocks * block_size, total_size)

    if total_size > 0:
        # number of dots on thermometer scale
        avail_dots = width - 2
        shaded_dots = int(math.floor(float(current_size) / total_size * avail_dots))
        progress = '[' + '.' * shaded_dots + ' ' * (avail_dots - shaded_dots) + ']'

        if progress:
            sys.stdout.write("\r" + progress)
    else:
        sys.stdout.write("\r The downloaded file is empty")


def set_online_update_server(server_name):
    """
    Set the name of the online update server. This function can be used to change the server name from inside a
    config file.


    :param server_name: the HTTP(s) path to the server and a location where the desired data reside.
    :return: None
    """
    global online_update_server

    online_update_server = server_name



__is_update_server_reachable = None

def is_update_server_reachble():
    global __is_update_server_reachable
    global online_update_server

    if __is_update_server_reachable is None:
        try:
            print "Testing connection to the update server.."
            urllib2.urlopen(online_update_server, timeout = 1)
            __is_update_server_reachable = True
        except urllib2.URLError as err:
            print "Server", online_update_server, "not reachable!"
            __is_update_server_reachable = False
    return __is_update_server_reachable


def online_update(file_name):
    """
    This function can download file from a default server if it is not available locally. The default server location
    can be changed in the config file.

    The original file name is transformed into absolute name using as_project_path function.

    :param file_name: the file name which should be downloaded from the server
    :return: a file name of the local copy of the file downloaded from the server
    """

    fn = as_project_path(file_name)

    if not is_update_server_reachble():
        return fn

    url = online_update_server + file_name
    url_time = urllib.urlopen(url).info().getdate('Last-Modified')


    if url_time:
        url_time = time.mktime(url_time)

        if os.path.exists(fn):
            file_name_time = os.path.getmtime(fn)

            if url_time <= file_name_time:
                return fn

        print "="*80
        print "Downloading file:", fn
        if os.path.exists(fn) and url_time > file_name_time:
            print "The modification time of the remote file is different. "
        print "-"*80

        # get filename for temp file in current directory
        (fd, tmpfile) = tempfile.mkstemp(".tmp", prefix=fn + ".",)
        os.close(fd)
        os.unlink(tmpfile)

        (tmpfile, headers) = urllib.urlretrieve(url, tmpfile, callback_download_progress)

        shutil.move(tmpfile, fn)
        os.utime(fn, (url_time, url_time))
    else:
        print "="*80
        print "Could not stat:", url
        print "-"*80

    print

    return fn

def _expand_file_var(text, path):
    # This method has clear limitations, since it ignores the whole Python
    # syntax.
    return text.replace('__file__', "'{p}'".format(p=path))


def load_as_module(path, force=False, encoding='UTF-8', text_transforms=list()):
    """
    Loads a file pointed to by `path' as a Python module with minimal impact on
    the global program environment.  The file name should end in '.py'.

    Arguments:
        path -- path towards the file
        force -- whether to load the file even if its name does not end in
            '.py'
        encoding -- character encoding of the file
        text_transforms -- collection of functions to be run on the original
            file text

    Returns the loaded module object.

    """
    do_delete_temp = False
    if not path.endswith('.py'):
        if force:
            happy = False
            while not happy:
                temp_fd, temp_path = tempfile.mkstemp(suffix='.py')
                dirname, basename = os.path.split(temp_path)
                modname = basename[:-3]
                if modname not in sys.modules:
                    happy = True
            with codecs.open(path, 'rb', encoding=encoding) as orig_file:
                text = orig_file.read()
            text = _expand_file_var(text, path)
            for transform in text_transforms:
                text = transform(text)
            temp_file = os.fdopen(temp_fd, 'wb')
            temp_file.write(text.encode(encoding))
            temp_file.close()
            do_delete_temp = True
        else:
            raise ValueError(("Path `{path}' should be loaded as module but "
                              "does not end in '.py' and `force' wasn't set.")
                             .format(path=path))
    else:
        dirname, basename = os.path.split(path)
        modname = basename[:-3]
    sys.path.insert(0, dirname)
    mod = import_module(modname)
    sys.path.pop(0)
    if do_delete_temp:
        os.unlink(temp_path)
        del sys.modules[modname]
    return mod


class Config(object):
    """
    Config handles configuration data necessary for all the components
    in Alex. It is implemented using a dictionary so that any component can use
    arbitrarily structured configuration data.

    Before the configuration file is loaded, it is transformed as follows:

        1. '{cfg_abs_path}' as a string anywhere in the file is replaced by an
            absolute path of the configuration files.  This can be used to make
            the configuration file independent of the location of programs
            that use it.

    """
    DEFAULT_CFG_PPATH = os.path.join('resources', 'default.cfg')
    ### This was the earlier functionality, which I found a bit inflexible. MK
    # When the configuration file is loaded, several automatic transformations
    # are applied:
    #
    #     1. '{cfg_abs_path}' as a substring of atomic attributes is replaced by
    #         an absolute path of the configuration files.  This can be used to
    #         make the configuration file independent of the location of programs
    #         using the configuration file.

    # TODO: Enable setting requirements on the configuration variables and
    # checking that they are met (i.e., 2 things:
    #   - requirements = property(get_reqs, set_reqs)
    #   - def check_requirements_are_met(self)

    def __init__(self, file_name=None, project_root=False, config=None):
        """
        Initialises a new Config object.

        Arguments:
            file_name -- path towards the configuration file
            project_root -- whether the path is only relative wrt the project
                root directory (i.e., the 'alex' directory)
            config -- a ready-to-use config dictionary (if specified,
                `file_name' should NOT be specified, otherwise the config from
                `file_name' overwrites the one specified via `config'

        """
        if config is None:
          config = {}

        self.config = config

        if project_root:
            file_name = os.path.join(env.root(), file_name)

        if file_name:
            self.load(file_name)

    def get(self, i, default=None):
        return self.config.get(i, default)

    def getpath(self, path, default=None):
        path_components = path.split('/')
        curr_config = self.config
        for component in path_components:
            if component in curr_config:
                curr_config = curr_config[component]
            else:
                curr_config = default
                break

        return curr_config

    def __delitem__(self, i):
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
        import warnings
        warnings.warn('Use unicode() instead of str().', DeprecationWarning)
        return unicode(self).decode('UTF-8', 'ignore')

    def __unicode__(self):
        """Returns the config as a pretty-printed string.

        It removes all lines which include word:
            - password
            - api_key
            - user_id

        to prevent password logging.
        """
        cfg_str = pprint.pformat(self.config, indent=2, width=120)
        cfg_str = re.sub(r".*password.*",
                         "# this line was removed since it included a password",
                         cfg_str)
        cfg_str = re.sub(r".*user_id.*",
                         "# this line was removed since it included a password",
                         cfg_str)
        cfg_str = re.sub(r".*api_key.*",
                         "# this line was removed since it included a password",
                         cfg_str)
        return cfg_str

    @classmethod
    def _remove_repeated(cls, sequence):
        """Removes any repeated occurrences of items in `sequence'."""
        new = list()
        for item in sequence:
            if item not in new:
                new.append(item)
        return new

    @classmethod
    def load_configs(cls, config_flist=list(), use_default=True, log=True,
                     *init_args, **init_kwargs):
        """
        Loads and merges configs from paths listed in `config_flist'.  Use this
        method instead of direct loading configs, as it takes care of not only
        merging them but also processing some options in a special way.

        Arguments:
            config_flist -- list of paths to config files to load and merge;
                order matters (default: [])
            use_default -- whether to insert the default config
                ($ALEX/resources/default.cfg) at the beginning of
                `config_flist' (default: True)
            log -- whether to log the resulting config using the system logger
                (default: True)
            init_args -- additional positional arguments will be passed to
                constructors for each config
            init_kwargs -- additional keyword arguments will be passed to
                constructors for each config

        """

        # Interpret arguments.
        if config_flist is None:
            config_flist = list()

        # Insert the default config if asked to, remove duplicate entries
        # (retain the last one).
        cfg_fnames = list(reversed(config_flist))
        if use_default:
            cfg_fnames.append(as_project_path(cls.DEFAULT_CFG_PPATH))
        cfg_fnames = list(reversed(cls._remove_repeated(cfg_fnames)))

        # Construct the entire config dictionary.
        if not cfg_fnames:
            cfg = Config(*init_args, **init_kwargs)
        else:
            cfg = Config(cfg_fnames[0], *init_args, **init_kwargs)
            for next_cfg_fname in cfg_fnames[1:]:
                cfg.merge(next_cfg_fname)

        # Print out the resulting config if asked to.
        if log:
            indent = ' ' * len('config = ')
            cfg_str = unicode(cfg).replace('\n', '\n' + indent)
            cfg['Logging']['system_logger'].info('config = ' + cfg_str)

        return cfg

    def contains(self, *path):
        """
        Check if configuration contains given keys (= path in config tree).
        """
        curr = self.config
        for path_part in path:
            if path_part in curr:
                curr = curr[path_part]
            else:
                return False

        return True

    def load(self, file_name):
        # pylint: disable-msg=E0602
        global config

        cfg_abs_dirname = os.path.dirname(os.path.abspath(file_name))

        # self.config_replace('{cfg_abs_path}', cfg_abs_dirname)
        expand_cap = lambda text: text.replace('{cfg_abs_path}',
                                               cfg_abs_dirname)

        self.config = config = load_as_module(file_name, force=True, text_transforms=(expand_cap,)).config

        self.load_includes()

    def load_includes(self):
        if not self.contains("General", "include"):
            return
        for include in self["General"]["include"]:
            self.merge(include)

    def merge(self, other):
        """Merges self's config with other's config and saves it as a new
        self's config.

        Keyword arguments:
            - other: a Config object whose configuration dictionary to merge
                     into self's one
        """
        # pylint: disable-msg=E0602
        if type(other) is str or type(other) is unicode:
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
        if not isinstance(config_dict, collections.Mapping):
            raise ConfigException('Assigning a suboption to a config option '
                                  'originally atomic.')
        for key, val in new_config.iteritems():
            if isinstance(val, collections.Mapping):
                subdict = self.update(val, config_dict.get(key, {}))
                config_dict[key] = subdict
            else:
                config_dict[key] = new_config[key]
        return config_dict

    def config_replace(self, p, s, d=None):
        """
        Replace a pattern p with string s in the whole config
        (recursively) or in a part of the config given in d.

        """
        if d is None:
            d = self.config
        for k, v in d.iteritems():
            if isinstance(v, collections.Mapping):
                self.config_replace(p, s, v)
            elif isinstance(v, basestring):
                d[k] = d[k].replace(p, s)
        return

    def unfold_lists(self, pattern, unfold_id_key=None, part=[]):
        """
        Unfold lists under keys matching the given pattern
        into several config objects, each containing one item.
        If pattern is None, all lists are expanded.

        Stores a string representation of the individual unfolded values
        under the unfold_id_key if this parameter is set.

        Only expands a part of the whole config hash (given by list of
        keys forming a path to this part) if the path parameter is set.
        """
        # find the part of the config we're dealing with
        dict_to_unfold = self.config
        for key in part:
            dict_to_unfold = dict_to_unfold[key]
        # go through it and search for lists to unfold
        for k, v in dict_to_unfold.iteritems():
            # unfold lists
            if type(v) is list and (pattern is None or re.search(pattern, k)):
                unfolded = []
                for item in v:
                    # create a copy and replace with the unfolded item
                    ci = Config(config=copy.deepcopy(self.config))
                    target_dict = ci
                    for key in part:
                        target_dict = target_dict[key]
                    target_dict[k] = item
                    # store the value of the unfolded items under the given key
                    if unfold_id_key is not None:
                        str_rep = unicode(item)
                        ci[unfold_id_key] = ci[unfold_id_key] + '_' + str_rep \
                                            if unfold_id_key in ci else str_rep
                    # unfold other variables
                    unfolded.extend(ci.unfold_lists(pattern, unfold_id_key))
                return unfolded
            # recurse deeper into dictionaries
            elif type(v) is dict:
                return self.unfold_lists(pattern, unfold_id_key, part + [k])
        return [self]
