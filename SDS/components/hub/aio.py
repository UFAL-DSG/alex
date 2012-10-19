#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyaudio
import wave
import time
import random
import multiprocessing
import sys
import os.path
import struct
import array
from datetime import datetime

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.messages import Command, Frame

"""
FIXME: There is confusion in naming packets, frames, and samples.
       Ideally frames should be blocks of samples.

"""

class AudioIO(multiprocessing.Process):
    """ AudioIO implements IO operation with a soundcard. Currently, it uses the default sound device for both input
    and output. I enabled then it logs all recorded and played audio into a file.

    The file is in RIFF wave in stereo, where left channel contains recorded audio and the right channel contains
    played audio.
    """

    def __init__(self, cfg, commands, audio_record, audio_play, audio_played):
        """ Initialize AudioIO

        cfg - configuration dictionary

        audio_record - inter-process connection for sending recorded audio.
          Audio is divided into frames, each with the length of samples_per_frame.

        audio_play - inter-process connection for receiving audio which should to be played.
          Audio must be divided into frames, each with the length of samples_per_frame.

        audio_played - inter-process connection for sending audio which was played.
          Audio is divided into frames and synchronised with the recorded audio.
        """

        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.audio_record = audio_record
        self.audio_play = audio_play
        self.audio_played = audio_played

        self.output_file_name = os.path.join(self.cfg['Logging']['output_dir'],
                                             'all-'+datetime.now().isoformat('-').replace(':', '-')+'.wav')

    def process_pending_commands(self, p, stream, wf):
        """Process all pending commands.

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.
            It is not able flush data already send to the sound card.

        Return True if the process should terminate.
        """

        #TO-DO: I could use stream.abort() function to flush output buffers of pyaudio()

        if self.commands.poll():
            command = self.commands.recv()
            if self.cfg['AudioIO']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    # stop recording and playing
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()

                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    return False

        return False

    def read_write_audio(self, p, stream, wf, play_buffer):
        """Send some of the available data to the output.
        It should be a non-blocking operation.

        Therefore:
          1) do not send more then play_buffer_frames
          2) send only if stream.get_write_available() is more then the frame size
        """
        if self.audio_play.poll():
            while self.audio_play.poll() \
                  and len(play_buffer) < self.cfg['AudioIO']['play_buffer_size'] \
                  and stream.get_write_available() > self.cfg['Audio']['samples_per_frame']:

                # send to play frames from input
                data_play = self.audio_play.recv()
                if isinstance(data_play, Frame):
                    stream.write(data_play.payload)

                    play_buffer.append(data_play)

                    if self.cfg['AudioIO']['debug']:
                        print '.',
                        sys.stdout.flush()

                elif isinstance(data_play, Command):
                    if data_play.parsed['__name__'] == 'utterance_start':
                        self.commands.send(Command('play_utterance_start()', 'AudioIO', 'HUB'))
                    if data_play.parsed['__name__'] == 'utterance_end':
                        self.commands.send(Command('play_utterance_end()', 'AudioIO', 'HUB'))

        else:
            data_play = Frame(b"\x00\x00"*self.cfg['Audio']['samples_per_frame'])

            play_buffer.append(data_play)
            if self.cfg['AudioIO']['debug']:
                print '.',
                sys.stdout.flush()

        # record one packet of audio data
        # it will be blocked until the data is recorded
        data_rec = stream.read(self.cfg['Audio']['samples_per_frame'])
        # send recorded data it must be read at the other end
        self.audio_record.send(Frame(data_rec))

        # get played audio block
        data_play = play_buffer.pop(0)

        # send played audio
        self.audio_played.send(data_play)

        # save the recorded and played data
        data_stereo = bytearray()
        for i in range(self.cfg['Audio']['samples_per_frame']):
            data_stereo.extend(data_rec[i*2])
            data_stereo.extend(data_rec[i*2+1])

            # there might not be enough data to be played
            # then add zeros
            try:
                data_stereo.extend(data_play[i*2])
            except IndexError:
                data_stereo.extend(b'\x00')

            try:
                data_stereo.extend(data_play[i*2+1])
            except IndexError:
                data_stereo.extend(b'\x00')

        wf.writeframes(data_stereo)

    def run(self):
        wf = wave.open(self.output_file_name, 'w')
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(self.cfg['Audio']['sample_rate'])

        play_buffer_frames = 0

        p = pyaudio.PyAudio()
        # open stream
        stream = p.open(format = p.get_format_from_width(pyaudio.paInt32),
                        channels = 1,
                        rate = self.cfg['Audio']['sample_rate'],
                        input = True,
                        output = True,
                        frames_per_buffer = self.cfg['Audio']['samples_per_frame'])


        # this is a play buffer for synchronization with recorded audio
        play_buffer = []

        while 1:
            # process all pending commands
            if self.process_pending_commands(p, stream, wf):
                return

            # process audio data
            self.read_write_audio(p, stream, wf, play_buffer)
