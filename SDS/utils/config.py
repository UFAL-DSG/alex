#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import cStringIO
import pprint
import os.path

from SDS.utils.mproc import SystemLogger


class Config:
    """ Config handles configuration data necessary for all the components
    in the SDS. It implements a dictionary so that any component could
    store arbitrary structured data.

    When the configure file is loaded several automatic transformations are applied.
      1) '{cfg_abs_path}' at the beginning of strings is replaced by an absolute path of the configure files.
                          This can be used to make the configure file independent of the location of programs
                          using the configure file.

    """

    def __init__(self, file_name):
        self.config = {}

        if file_name:
            self.load(file_name)

    def __len__(self):
        return len(self.config)

    def __getitem__(self, i):
        return self.config[i]

    def __iter__(self):
        for i in self.config:
            yield i

    def __str__(self):
        sio = cStringIO.StringIO()
        pprint.pprint(self.config, sio, indent=2, width=120)
        return sio.getvalue()

    def load(self, file_name):
        """FIX: Executing external files is not ideal! It should be changed in the future!
        """
        config = None
        execfile(file_name, globals())
        if config is None:
            raise Exception("No configuration has been loaded!")
        self.config = config

        cfg_abs_dirname = os.path.dirname(os.path.abspath(file_name))
        self.config_replace('{cfg_abs_path}', cfg_abs_dirname, self.config)

    def merge(self, file_name):
        config = None
        execfile(file_name, globals())
        if config is None:
            raise Exception("No configuration has been loaded!")
        self.update_dict(self.config, config)

    def update_dict(self, d, u):
        for k, v in u.iteritems():
            if isinstance(v, collections.Mapping):
                r = self.update_dict(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

    def config_replace(self, p, s, d):
        for k, v in d.iteritems():
            if isinstance(v, collections.Mapping):
                self.config_replace(p, s, v)
            elif isinstance(v, str):
                d[k] = d[k].replace(p, s)

        return
