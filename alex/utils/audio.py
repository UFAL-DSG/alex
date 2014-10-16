#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import os
import pysox
import audioop
import wave
import subprocess
import contextlib

from os import remove, fdopen
from tempfile import mkstemp

import alex.utils.various as various

""" The audio module implements some basic audio data manipulation.

The default format for audio data is uncompressed mono pmc16 data.
This format should the default options whenever audio data is passed
in a string. The sample rate is defined by the value in the config file.

By convention, the variables storing audio in the default format will
be named as "wav" or "wav_*".

"""


def wav_duration(wav_file): 
    with contextlib.closing(wave.open(wav_file,'r')) as f:
        frames = f.getnframes() 
        rate = f.getframerate() 
        duration = frames / float(rate) 
        return duration


def load_wav(cfg, file_name):
    """
    Reads all audio data from the file and returns it in a string.

    The content is re-sampled into the default sample rate.

    """

    try:
        wf = wave.open(file_name, 'r')
        if wf.getnchannels() != 1:
            raise Exception('Input wave is not in mono')

        if wf.getsampwidth() != 2:
            raise Exception('Input wave is not in 16bit')

        sample_rate = wf.getframerate()

        # read all the samples
        chunk = 1024
        wav = b''
        wavPart = wf.readframes(chunk)
        while wavPart:
            wav += str(wavPart)
            wavPart = wf.readframes(chunk)
    except EOFError:
        raise Exception('Input wave is corrupted: End of file.')
    else:
        wf.close()

    # resample audio if not compatible
    if sample_rate != cfg['Audio']['sample_rate']:
        wav, state = audioop.ratecv(wav, 2, 1, sample_rate,
                                    cfg['Audio']['sample_rate'], None)

    return wav


def convert_wav(cfg, wav):
    """
    Convert the given WAV byte buffer into the desired sample rate
    using SoX. Assumes mono + 16-bit sample size.
    """
    sample_rate = cfg['Audio']['sample_rate']

    # write the buffer to a temporary file
    tmp1fh, tmp1path = mkstemp()
    tmp1fh = fdopen(tmp1fh, 'wb')
    tmp1fh.write(wav)
    tmp1fh.close()

    # transform the temporary file using SoX (can't do this in memory :-()
    tmp2fh, tmp2path = mkstemp()
    sox_in = pysox.CSoxStream(tmp1path)
    sox_out = pysox.CSoxStream(tmp2path, 'w', pysox.CSignalInfo(sample_rate, 1, 16), fileType='wav')
    sox_chain = pysox.CEffectsChain(sox_in, sox_out)
    sox_chain.add_effect(pysox.CEffect("rate", [str(sample_rate)]))
    sox_chain.flow_effects()
    sox_out.close()

    # read the transformation results back to the buffer
    return load_wav(cfg, fdopen(tmp2fh, 'rb'))

def change_tempo(cfg, tempo, wav):
    """
    Change tempo of an input WAV byte buffer.
    """
    sample_rate = cfg['Audio']['sample_rate']

    # write the buffer to a temporary file
    tmp1fh, tmp1path = mkstemp()
    save_wav(cfg, tmp1path, wav)

    # transform the temporary file using SoX (can't do this in memory :-()
    tmp2fh, tmp2path = mkstemp()
    sox_in = pysox.CSoxStream(tmp1path)
    sox_out = pysox.CSoxStream(tmp2path, 'w', pysox.CSignalInfo(sample_rate, 1, 16), fileType='wav')
    sox_chain = pysox.CEffectsChain(sox_in, sox_out)
    sox_chain.add_effect(pysox.CEffect("tempo", [str(tempo)]))
    sox_chain.flow_effects()
    sox_out.close()

    # read the transformation results back to the buffer
    return load_wav(cfg, fdopen(tmp2fh, 'rb'))

def save_wav(cfg, file_name, wav):
    """
    Writes content of a audio string into a RIFF WAVE file.

    The file is truncated before the data is written in it.

    """

    try:
        wf = wave.open(file_name, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(cfg['Audio']['sample_rate'])
        wf.writeframes(wav)
    except wave.Error as e:
        raise e
    else:
        wf.close()

    return

def save_flac(cfg, file_name, wav):
    """ Writes content of a audio string into a FLAC file. """

    handle, wav_file_name = mkstemp('TmpSpeechFlacFile.wav')
    devnull = open(os.devnull, 'w')

    try:
        save_wav(cfg, wav_file_name, wav)
        subprocess.call(['flac', '-f', wav_file_name, '-o', file_name], stderr=devnull)
    finally:
        os.close(handle)
        devnull.close()
        remove(wav_file_name)

    return

def convert_mp3_to_wav(cfg, mp3_string):
    """
    Convert a string with mp3 to a string with audio in the default format
    (mono, pcm16, default sample rate).

    """

    sample_rate = cfg['Audio']['sample_rate']

    # write the buffer to a temporary file
    tmp1fh, tmp1path = mkstemp()
    tmp1fh = fdopen(tmp1fh, 'wb')
    tmp1fh.write(mp3_string)
    tmp1fh.close()

    # transform the temporary file using SoX (can't do this in memory :-()
    tmp2fh, tmp2path = mkstemp()
    sox_in = pysox.CSoxStream(tmp1path, fileType='mp3')
    sox_out = pysox.CSoxStream(tmp2path, 'w', pysox.CSignalInfo(sample_rate, 1, 16), fileType='wav')
    sox_chain = pysox.CEffectsChain(sox_in, sox_out)
    sox_chain.add_effect(pysox.CEffect("rate", [str(sample_rate)]))
    sox_chain.flow_effects()
    sox_out.close()

    # read the transformation results back to the buffer
    return load_wav(cfg, fdopen(tmp2fh, 'rb'))

def play(cfg, wav):
    pass