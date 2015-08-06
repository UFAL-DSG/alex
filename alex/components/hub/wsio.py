#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import threading
import time

from alex.utils.audio import load_wav
import alex.utils.various as various

from alex.components.hub.messages import Command, Frame, ASRHyp, TTSText


class WSIO(multiprocessing.Process):
    """
    WebSocket IO.
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
        self.speex_state = None
        self.audio_to_send = ""
        self.client_connected = False

        self.router_address = self.cfg['WSIO']['router_addr']
        self.router_port = self.cfg['WSIO']['router_port']

        self.listen_address = self.cfg['WSIO']['listen_addr']
        self.listen_port = self.cfg['WSIO']['listen_port']

        self.alex_addr = self.cfg['WSIO']['alex_addr']

        self.audio_playing = None

    def process_pending_commands(self):
        """Process all pending commands.

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.
            It is not able flush data already send to the sound card.

        Return True if the process should terminate.
        """

        # TO-DO: I could use stream.abort() function to flush output buffers of pyaudio()

        if self.commands.poll():
            command = self.commands.recv()
            if self.cfg['AudioIO']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        self.audio_play.recv()

                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        self.audio_play.recv()

                    return False
            elif isinstance(command, ASRHyp):
                hyp = command.hyp
                asr_hyp = hyp.get_best()

                msg = AlexToClient()
                msg.type = AlexToClient.ASR_RESULT
                msg.asr_result = unicode(asr_hyp).lower()
                self.send_to_client(msg.SerializeToString())
            elif isinstance(command, TTSText):
                txt = command.text

                msg = AlexToClient()
                msg.type = AlexToClient.SYSTEM_PROMPT
                msg.system_prompt = unicode(txt)
                self.send_to_client(msg.SerializeToString())

        return False

    def read_write_audio(self): #, p, stream, wf, play_buffer):
        """Send some of the available data to the output.
        It should be a non-blocking operation.

        Therefore:
          1) do not send more then play_buffer_frames
          2) send only if stream.get_write_available() is more then the frame size
        """

        if self.audio_play.poll():
            while self.audio_play.poll(): # \
                #and len(play_buffer) < self.cfg['AudioIO']['play_buffer_size']:

                # send to play frames from input
                data_play = self.audio_play.recv()
                if isinstance(data_play, Frame):
                    buffer = data_play.payload
                    self.audio_to_send += buffer
                elif isinstance(data_play, Command):
                    if data_play.parsed['__name__'] == 'utterance_start':
                        self.audio_playing = data_play.parsed['fname']
                        self.message_queue.append(
                            (Command('play_utterance_start(user_id="{uid}",fname="{fname}")'
                                        .format(uid=data_play.parsed['user_id'], fname=data_play.parsed['fname']),
                                     'VoipIO', 'HUB'),
                             self.last_frame_id))
                        try:
                            if data_play.parsed['log'] == "true":
                                self.cfg['Logging']['session_logger'].rec_start("system", data_play.parsed['fname'])
                        except SessionLoggerException as e:
                            self.cfg['Logging']['system_logger'].exception(e)

                    if self.audio_playing and data_play.parsed['__name__'] == 'utterance_end':
                        self.audio_playing = None
                        self.message_queue.append(
                            (Command('play_utterance_end(user_id="{uid}",fname="{fname})'
                                     .format(uid=data_play.parsed['user_id'], fname=data_play.parsed['fname']),
                                     'VoipIO', 'HUB'),
                             self.last_frame_id))
                        try:
                            if data_play.parsed['log'] == "true":
                                self.cfg['Logging']['session_logger'].rec_end(data_play.parsed['fname'])
                        except SessionLoggerException as e:
                            self.cfg['Logging']['system_logger'].exception(e)



                #if isinstance(data_play, Frame):
                #    stream.write(data_play.payload)
                #
                #    play_buffer.append(data_play)
                #
                #    if self.cfg['AudioIO']['debug']:
                #        print '.',
                #        sys.stdout.flush()

                #elif isinstance(data_play, Command):
                #    if data_play.parsed['__name__'] == 'utterance_start':
                #        self.commands.send(Command('play_utterance_start()', 'AudioIO', 'HUB'))
                #    if data_play.parsed['__name__'] == 'utterance_end':
                #        self.commands.send(Command('play_utterance_end()', 'AudioIO', 'HUB'))

        while len(self.audio_to_send) > 640:
            buffer = self.audio_to_send[:640]
            self.audio_to_send = self.audio_to_send[640:]

            encoded, self.speex_state = audiospeex.lin2speex(buffer, sample_rate=16000, state=self.speex_state)
            msg = AlexToClient()
            msg.type = AlexToClient.SPEECH
            msg.speech = encoded
            self.send_to_client(msg.SerializeToString())
            print 'sending audio'

    def run(self):
        try:
            self.cfg['Logging']['session_logger'].cancel_join_thread()

            global logger
            logger = self.cfg['Logging']['system_logger']

            #factory = WebSocketServerFactory("ws://0.0.0.0:9000", debug=False)
            #factory.protocol = create_alex_websocket_protocol(self)

            #def run_ws():
            #    print 'running ws'
            #    reactor.listenTCP(9000, factory)
            #    reactor.run(installSignalHandlers=0)

            #t = Thread(target=run_ws) #lambda *args: run_ws())
            #t.setDaemon(True)
            #print 'starting thread'-
            #t.start()
            self.key = gen_key()

            ws_server_factory=WebSocketServerFactory("ws://%s:%d" % (self.listen_address, self.listen_port, ), debug=False)
            ws_server_factory.protocol = create_ws_protocol(self)
            reactor.listenTCP(self.listen_port, ws_server_factory)

            ws_ping_factory = AlexPingFactory(self.router_address, self.router_port, self)
            reactor.connectTCP(self.router_address, self.router_port, ws_ping_factory)


            conns = threading.Thread(target=reactor.run, kwargs=dict(installSignalHandlers=0))
            conns.setDaemon(True)
            conns.start()


            # process incoming audio play and send requests
            while 1:
                time.sleep(1)
                # Check the close event.
                if self.close_event.is_set():
                    return

                #import ipdb; ipdb.set_trace()

                # process all pending commands
                if self.process_pending_commands():
                    return

                print '.'

                ## process audio data
                self.read_write_audio() #p, stream, wf, play_buffer)
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in VAD process.')
            self.close_event.set()
            raise

    def on_client_connected(self, protocol, request):
        #self.commands.send(Command('client_connected()', 'WSIO', 'HUB'))
        self.commands.send(Command('call_confirmed(remote_uri="%s")' % "PubAlex", 'WSIO', 'HUB'))
        self.ws_protocol = protocol
        self.client_connected = True

    def on_client_closed(self):
        self.ws_protocol = None
        #self.commands.send(Command('client_connected()', 'WSIO', 'HUB'))
        self.commands.send(Command('call_disconnected(remote_uri="%s", code="%s")' % ("PubAlex", "---"), 'VoipIO', 'HUB'))
        self.client_connected = False
        self.key = gen_key()

    def send_to_client(self, data):
        if self.ws_protocol:
            reactor.callFromThread(self.ws_protocol.sendMessage, data, True)
        else:
            self.cfg['Logging']['system_logger'].warning("Send to client called but the connection is not opened.")

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory, WebSocketClientFactory, WebSocketClientProtocol
import audiospeex

#from wshub_messages_pb2
from wsio_messages_pb2 import ClientToAlex, AlexToClient, WSRouterRequestProto, PingProto
import random
import string


def gen_key():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))


def create_ws_protocol(wsio_):
    class AlexWebsocketProtocol(WebSocketServerProtocol):
        wsio = wsio_
        speex_state = None

        def onConnect(self, request):
            print self.factory, id(self)
            print("Client connecting: {0}".format(request.peer))
            self.wsio.on_client_connected(self, request)

        def onOpen(self):
            print("WebSocket connection open.")

        def onMessage(self, payload, isBinary):
            if isBinary:
                msg = ClientToAlex()
                msg.ParseFromString(payload)
                if msg.key == self.wsio.key:
                    decoded, self.speex_state = audiospeex.speex2lin(msg.speech, 16000, self.speex_state)
                    #decoded = self.speex.decode(msg.speech.body)
                    #with open('x.speex', 'w') as f_out:
                    #    f_out.write(msg.speech.body)

                    #print len(msg.speech.body), type(decoded), len(decoded)
                    #print decoded
                    #print len(msg.speech.body)
                    #decoded = msg.speech.body

                    self.wsio.audio_record.send(Frame(decoded))  #msg.speech.body))


        def onClose(self, wasClean, code, reason):
            print("WebSocket connection closed: {0}".format(reason))
            self.wsio.on_client_closed()

    return AlexWebsocketProtocol


class AlexPingFactory(WebSocketClientFactory):
    def __init__(self, addr, port, wsio):
        super(AlexPingFactory, self).__init__("ws://%s:%d" % (addr, port), debug=True)
        self.protocol = AlexPingProtocol

        self.wsio = wsio

    def get_ping_msg(self):
        msg = WSRouterRequestProto()
        msg.type = WSRouterRequestProto.PING
        if self.wsio.client_connected:
            msg.ping.status = PingProto.BUSY
        else:
            msg.ping.status = PingProto.AVAILABLE

        msg.ping.key = self.wsio.key
        msg.ping.addr = self.wsio.alex_addr

        return msg


class AlexPingProtocol(WebSocketClientProtocol):
    def onOpen(self):
        def ping():
            msg = self.factory.get_ping_msg()
            self.sendMessage(msg.SerializeToString(), True)
            self.factory.reactor.callLater(1, ping)

        ping()

    def clientConnectionFailed(self, connector, reason):
        print("Ping connection failed .. retrying ..")
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        print("Ping connection lost .. retrying ..")
        self.retry(connector)