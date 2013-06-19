#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyaudio
from jinja2.loaders import FileSystemLoader
from jinja2 import Environment

import wave
import multiprocessing
import sys
import os.path
from datetime import datetime
import urlparse
import Queue
import BaseHTTPServer
from threading import Thread

from alex.utils.audio import load_wav
import alex.utils.various as various

from alex.components.hub.messages import Command, Frame


class WebIO(multiprocessing.Process):
    """
    Web frontend to interact with the dialogue system.

    So far provides only interface for injecting wav files from a directory
    (i.e. as if it was said through microphone).
    """

    def __init__(self, cfg, commands, audio_record, audio_play, close_event):
        """ Initialize WebIO

        cfg - configuration dictionary

        audio_record - inter-process connection for sending recorded audio.
          Audio is divided into frames, each with the length of samples_per_frame.

        audio_play - inter-process connection for receiving audio which should to be played.
          Audio must be divided into frames, each with the length of samples_per_frame.

        """

        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.audio_record = audio_record
        self.audio_play = audio_play
        self.close_event = close_event

        self.web_queue = Queue.Queue()  # stack requests made from the web UI

        self.output_file_name = os.path.join(self.cfg['AudioIO']['output_dir'],
                                             'all-' + datetime.now().isoformat('-').replace(':', '-') + '.wav')

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
                        _ = self.audio_play.recv()

                    # stop recording and playing
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()

                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        _ = self.audio_play.recv()

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

    def get_webserver(self):
        """Build a HTTP server instance."""
        server_address = ('', self.cfg['WebHub']['port'])
        handler_class = WebIOHttpHandler
        httpd = WebIOHttpServer(self.web_queue, server_address, handler_class)
        return httpd

    def send_wav(self, filename, stream=None):
        """Send given wavfile to the dialogue system as if it was said throught
        microphone."""
        # load wav
        wav = load_wav(self.cfg, filename)
        wav = various.split_to_bins(
            wav, 2 * self.cfg['Audio']['samples_per_frame'])

        # frame by frame send it
        for frame in wav:
            if stream is not None:
                stream.write(frame)
            self.audio_record.send(Frame(frame))

        # send some silence so that VAD recognizes end of recording
        for _ in range(10):
            self.audio_record.send(Frame(b"\x00\x00" * self.cfg['Audio']['samples_per_frame']))

    def run(self):
        try:
            # caputre the dialogue
            wf = wave.open(self.output_file_name, 'w')
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.cfg['Audio']['sample_rate'])

            # start webserver for the webinterface
            httpd = self.get_webserver()
            t = Thread(target = lambda *args: httpd.serve_forever())
            t.start()

            # open audio pipe to the speakers
            p = pyaudio.PyAudio()
            # open stream
            stream = p.open(format=p.get_format_from_width(pyaudio.paInt32),
                            channels=1,
                            rate=self.cfg['Audio']['sample_rate'],
                            input=True,
                            output=True,
                            frames_per_buffer=self.cfg['Audio']['samples_per_frame'])

            # this is a play buffer for synchronization with recorded audio
            play_buffer = []

            # process incoming audio play and send requests
            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    return

                # process all pending commands
                if self.process_pending_commands(p, stream, wf):
                    return

                # process each web request
                while not self.web_queue.empty():
                    for filename in self.web_queue.get():
                        try:
                            self.send_wav(filename, stream)
                        except:
                            self.cfg['Logging']['session_logger'].exception(
                                'Error processing file: ' + filename)

                # process audio data
                self.read_write_audio(p, stream, wf, play_buffer)
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in VAD process.')
            self.close_event.set()
            raise


class WebIOHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Provides the user interface."""

    def do_GET(self):
        """Process GET request."""
        # headers
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        print >> self.wfile  # blank line after headers

        # parse get arguments
        _, qs = self.get_qs()
        if 'play' in qs:  # if user requested to play something, tell DM
            self.server.comm_queue.put(qs['play'])
        dirname = qs.get('dir', [None])[0]

        # create context
        context = {}
        if dirname is not None:
            context['recs'] = self.get_recordings(dirname)  # root dir for listing
        else:
            context['recs'] = None
        context['dir'] = dirname

        self.render_template("webio_tpl/index.html", context, self.wfile)
        self.wfile.close()

    def get_qs(self):
        """Parse GET parameters."""
        qs = {}
        path = self.path
        if '?' in path:
            path, tmp = path.split('?', 1)
            qs = urlparse.parse_qs(tmp)

        return path, qs

    def get_recordings(self, path):
        """Get recordings from the given directory."""
        recs = [os.path.join(path, i) for i in os.listdir(path)]
        return recs

    def render_template(self, tpl_name, context, f_out):
        """Render given context into given template and save it to given file."""
        env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)),
                         trim_blocks=True)

        print >> f_out, env.get_template(tpl_name).render(**context)


class WebIOHttpServer(BaseHTTPServer.HTTPServer):
    """Simple HTTP server with queue for processing requests."""
    def __init__(self, comm_queue, *args, **kwargs):
        self.comm_queue = comm_queue
        BaseHTTPServer.HTTPServer.__init__(self, *args, **kwargs)

