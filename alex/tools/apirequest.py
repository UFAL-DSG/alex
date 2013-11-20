#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
import os
import codecs
import json


class APIRequest(object):
    """Handles functions related web API requests (logging)."""

    def __init__(self, cfg, fname_prefix, log_elem_name):
        """Initialize, given logging settings from configuration, dump file
        prefixes and the name of the referring XML element in the system log.

        :param cfg: System configuration, containing the entries \
                ['Logging']['system_logger'] and ['Logging']['session_logger']
        :param fname_prefix: File name prefix for dumps of responses
        :param log_elem_name: Name of the system log XML element referring to \
                the dump file
        """
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
        json.dump(data, fh, indent=4, separators=(',', ': '),
                  ensure_ascii=False)
        fh.close()
        self.session_logger.external_data_file(self.logger_name, os.path.basename(fname))
