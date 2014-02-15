#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
import os
import codecs
import json
import sys


class DummyLogger():
    """A dummy logger implementation for debugging purposes that will just print to STDERR."""

    def __init__(self):
        pass

    def info(self, text):
        print >> sys.stderr, text.encode('UTF-8')

    def external_data_file(self, dummy1, dummy2):
        pass

    def get_session_dir_name(self):
        return ''


class APIRequest(object):
    """Handles functions related web API requests (logging)."""

    def __init__(self, cfg, fname_prefix, log_elem_name):
        """Initialize, given logging settings from configuration, dump file
        prefixes and the name of the referring XML element in the system log.

        :param cfg: System configuration, containing the entries \
                ['Logging']['system_logger'] and ['Logging']['session_logger'] \
                (A dummy logger with outputs to STDERR and current directory \
                is used if these entries are not present).
        :param fname_prefix: File name prefix for dumps of responses
        :param log_elem_name: Name of the system log XML element referring to \
                the dump file
        """
        self.system_logger = DummyLogger()
        self.session_logger = DummyLogger()
        if 'Logging' in cfg:
            self.system_logger = cfg['Logging']['system_logger']
            self.session_logger = cfg['Logging']['session_logger']
        self.fname_prefix = fname_prefix
        self.logger_name = log_elem_name

    def _log_response_json(self, data):
        """Log a JSON API response and create a referring element in the system log.

        :param data: The API response to be dumped as JSON.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
        fname = os.path.join(self.system_logger.get_session_dir_name(),
                             self.fname_prefix + '-{t}.json'.format(t=timestamp))
        fh = codecs.open(fname, 'w', 'UTF-8')
        # dump to JSON (default for handling datetime objects)
        json.dump(data, fh, indent=4, separators=(',', ': '),
                  ensure_ascii=False,
                  default=lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else obj)
        fh.close()
        self.session_logger.external_data_file(self.logger_name, os.path.basename(fname))
