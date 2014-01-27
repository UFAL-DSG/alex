#!/usr/bin/env python
# -*- coding: utf-8 -*-

#this cannot be used with GASR
#from __future__ import unicode_literals

import urllib2
import json

from os import remove
from tempfile import mkstemp

import alex.utils.audio as audio

from alex.components.asr.utterance import Utterance, UtteranceNBList


class GoogleASR():
    """ Uses Google ASR service to recognize recorded audio in a specific language, e.g. en, cs.

    The main function recognize returns a list of recognised hypotheses.

    Regarding the supported sample rate, it appears that Google supports 8k and 16k audio.

    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.language = self.cfg['ASR']['Google']['language']
        self.maxresults  = self.cfg['ASR']['Google']['maxresults']
        self.rec_buffer = []

    def flush(self):
        self.rec_buffer = []

    def get_asr_hypotheses(self, flac_file_name):
        """ Access Google ASR service and multiple hypotheses.

        Note that the returned hypotheses are in JSON format.

        """
        baseurl = "http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=%s&maxresults=%d" % (self.language, self.maxresults)

        header = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11",
                  "Content-Type": "audio/x-flac; rate=%d" % self.cfg['Audio']['sample_rate']}

        data = open(flac_file_name, "rb").read()

        request = urllib2.Request(baseurl, data, header)
        json_hypotheses = urllib2.urlopen(request).read()

        if self.cfg['ASR']['Google']['debug']:
            print json_hypotheses

        return json_hypotheses

    def recognize(self, wav):
        """ Produces hypotheses for the input audio data.

        Remember that GoogleASR works only with complete wave files.

        Returns an n-best list of hypotheses.
        """

        #making a file temp for manipulation
        handle, flac_file_name = mkstemp('TmpSpeechFile.flac')

        try:
            # convert wav to flac
            audio.save_flac(self.cfg, flac_file_name, wav)
            json_hypotheses = self.get_asr_hypotheses(flac_file_name)
        except (urllib2.HTTPError, urllib2.URLError) as e:
            self.cfg['Logging']['system_logger'].exception('GoogleASR HTTP/URL error.')
        
            json_hypotheses = [[{'confidence': 1.0, 'utterance': '__google__ __asr__ __exception__'},],]
        finally:
            remove(flac_file_name)

        try:
            hyp = json.loads(json_hypotheses)

            # print "###", hyp

            nblist = UtteranceNBList()

            if hyp['status'] == 0:
                n = len(hyp['hypotheses'])
                for i, h in enumerate(hyp['hypotheses']):
                    if i == 0:
                        nblist.add(h['confidence'], Utterance(h['utterance']))
                        conf1 = hyp['hypotheses'][0]['confidence']
                    else:
                        # guess the confX score
                        nblist.add((1.0-conf1)*(n-i)/(n-1.0)/(n-0.0)*2.0, Utterance(h['utterance']))
            elif hyp['status'] == 5:
                nblist.add(1.0, Utterance('_other_'))
        except:
            nblist = UtteranceNBList()

        nblist.merge()
        nblist.add_other()
        
        return nblist

    def rec_in(self, frame):
        """ This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech segment that should be
        recognized.

        Since the Google ASR only performs synchronized ASR, this function just buffer the data.

        Output hypotheses is obtained by calling hyp_out().
        """

        self.rec_buffer.append(frame.payload)
        return

    def hyp_out(self):
        """ This defines asynchronous interface for speech recognition.

        Returns recognizers hypotheses about the input speech audio.
        """
        wav = b''.join(self.rec_buffer)
        self.rec_buffer = []

        nblist = self.recognize(wav)

        return nblist
