#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import wget

""" This is a set functions which helps with building domain specific language models.
"""

def download_general_LM_data(language):
    """ Downloads a general text corpus for the specified language into a local directory. If the

    :param language: abbreviation of teh desired language. It can be either in ISO 639/1 or 639/3
    :return: Returns a file name of the downloaded data.
    """
    lngs = {'eng': 'eng',
            'en':  'eng',
            'ces': 'ces',
            'cs':  'ces',
            'fra': 'fra',
            'fr':  'fra',
            'spa': 'spa',
            'sp':  'spa',
            'ita': 'ita',
            'it':  'ita',
            'deu': 'ita',
            'de':  'ita',
            }

    if os.path.exists("%s.txt.gz" % lngs[language]):
        return "%s.txt.gz" % lngs[language]
    elif language in lngs:
        url = "https://ufal-point.mff.cuni.cz/repository/xmlui/bitstream/handle/11858/00-097C-0000-0022-6133-9/%s.txt.gz" % lngs[language]
        fn = wget.download(url)
        print
        return fn

    raise Exception("Missing a supported language name:")
