#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import StringIO
import mad
import pyaudio
import audioop
import wave
import subprocess
import time

from os import remove
from tempfile import mkstemp

import SDS.utils.various as various

""" The audio module implements some basic audio data manipulation.

The default format for audio data is uncompressed mono pmc16 data.
This format should the default options whenever audio data is passed
in a string. The sample rate is defined by the value in the config file.

By convention, the variables storing audio in the default format will
be named as "wav" or "wav_*".

"""


def load_wav(cfg, file_name):
    """Reads all audio data from the file and returns it in a string.

    The content is re-sampled into the default sample rate.

    """

    try:
        wf = wave.open(file_name, 'r')
    except EOFError:
        raise Exception('Input wave is corrupted: End of file.')

    if wf.getnchannels() != 1:
        raise Exception('Input wave is not in mono')

    if wf.getsampwidth() != 2:
        raise Exception('Input wave is not in 16bit')

    sample_rate = wf.getframerate()

    # read all the samples
    chunk = 1024
    wav = ''
    wavPart = wf.readframes(chunk)
    while wavPart:
        wav += str(wavPart)
        wavPart = wf.readframes(chunk)

    wf.close()

    # resample audio if not compatible
    if sample_rate != cfg['Audio']['sample_rate']:
        wav, state = audioop.ratecv(
            wav, 2, 1, sample_rate, cfg['Audio']['sample_rate'], None)

    return wav


def save_wav(cfg, file_name, wav):
    """Writes content of a audio string into a RIFF WAVE file.

    The file is truncated before the data is written in it.

    """

    wf = wave.open(file_name, 'w')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(cfg['Audio']['sample_rate'])
    wf.writeframes(wav)
    wf.close()

    return


def save_flac(cfg, file_name, wav):
    """ Writes content of a audio string into a FLAC file. """

    handle, wav_file_name = mkstemp('TmpSpeechFile.wav')

    try:
        save_wav(cfg, wav_file_name, wav)
        subprocess.call("flac -f %s -o %s 2> /dev/null" % (
            wav_file_name, file_name), shell=True)
    finally:
        remove(wav_file_name)

    return


def convert_mp3_to_wav(cfg, mp3_string):
    """ Convert a string with mp3 to a string with audio
    in the default format (mono, pcm16, default sample rate).

    """

    mp3_file = StringIO.StringIO(mp3_string)
    mf = mad.MadFile(mp3_file)
    sample_rate = mf.samplerate()
    # pymad always produce stereo pcm16 audio data

    # read all the samples
    chunk = 1024
    wav = ''
    wavPart = mf.read(chunk)
    while wavPart:
        wav += str(wavPart)
        wavPart = mf.read(chunk)

    # convert to mono and resample
    wav_mono = audioop.tomono(wav, 2, 0.5, .5)
    wav_resampled, state = audioop.ratecv(
        wav_mono, 2, 1, sample_rate, cfg['Audio']['sample_rate'], None)

    return wav_resampled


def play(cfg, wav):
    # open the audio device
    p = pyaudio.PyAudio()

    chunk = 160
    # open stream
    stream = p.open(format=p.get_format_from_width(pyaudio.paInt32),
                    channels=1,
                    rate=cfg['Audio']['sample_rate'],
                    output=True,
                    frames_per_buffer=chunk)

    wav = various.split_to_bins(wav, chunk)
    for w in wav:
        stream.write(w)

    stream.stop_stream()
    stream.close()
    p.terminate()
