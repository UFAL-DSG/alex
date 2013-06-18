#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pylint: disable-msg=E1101

import pyaudio
import wave
import time
import random
import multiprocessing
import sys
import os.path
import struct
import array
import threading
import re
import pjsuaxt as pj

from datetime import datetime
from collections import deque, defaultdict

import alex.utils.audio as audio
import alex.utils.various as various
import alex.utils.text as string

from alex.components.hub.messages import Command, Frame
from alex.utils.exception import VoipIOException
from alex.utils.sessionlogger import SessionLoggerException
from alex.utils.procname import set_proc_name

# Logging callback
logger = None

def log_cb(level, str, len):
    logger.info(str)

class AccountCallback(pj.AccountCallback):
    """ Callback to receive events from account.
    """

    sem = None
    voipio = None

    def __init__(self, cfg, account=None, voipio=None):
        pj.AccountCallback.__init__(self, account)

        self.cfg = cfg
        self.voipio = voipio

    def on_incoming_call(self, call):
        """ Notification on incoming call
        """

        current_time = time.time()
        remote_uri = call.info().remote_uri

        if not self.cfg['VoipIO']['reject_calls']:
            if self.voipio.black_list[self.voipio.get_user_from_uri(remote_uri)] < current_time:
                # answer the call
                self.voipio.call = call
                self.voipio.on_incoming_call(remote_uri)

                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug("AccountCallback::on_incoming_call - Incoming call from %s" % remote_uri)

                call_cb = CallCallback(self.cfg, call, self.voipio)
                call.set_callback(call_cb)

                call.answer()
            else:
                # rejected the call since the caller is blacklisted
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug("AccountCallback::on_incoming_call - Rejected call from blacklisted remote URI %s " % remote_uri)
                    wait_hours = (self.voipio.black_list[self.voipio.get_user_from_uri(remote_uri)] - current_time) / (60 * 60)
                    self.cfg['Logging']['system_logger'].debug("AccountCallback::on_incoming_call - Must wait for %d hours" % wait_hours)
                # respond by "Busy here"
                call.answer(486)

                self.voipio.on_rejected_call_from_blacklisted_uri(remote_uri)
        else:
            # reject the call since all calls must be rejected
            if self.cfg['VoipIO']['debug']:
                self.cfg['Logging']['system_logger'].debug("AccountCallback::on_incoming_call - Rejected call from %s" % remote_uri)

            # respond by "Busy here"
            call.answer(486)
            # respond by "Decline"
            #call.answer(603)

            self.voipio.on_rejected_call(remote_uri)

    def wait(self):
        """Wait for the registration to finish.
        """

        self.sem = threading.Semaphore(0)
        self.sem.acquire()

    def on_reg_state(self):
        """Stop waiting if the registration process ended.
        """

        if self.sem:
            if self.account.info().reg_status >= 200:
                self.sem.release()


class CallCallback(pj.CallCallback):
    """ Callback to receive events from Call
    """

    def __init__(self, cfg, call=None, voipio=None):
        pj.CallCallback.__init__(self, call)

        self.cfg = cfg
        self.voipio = voipio
        self.system_logger = self.cfg['Logging']['system_logger']
        self.session_logger = self.cfg['Logging']['session_logger']

        self.rec_id = None
        self.output_file_name_recorded = ''
        self.output_file_name_played = ''

        self.recorded_id = None
        self.played_id = None

    # Notification when call state has changed
    def on_state(self):
        if self.cfg['VoipIO']['debug']:
            self.system_logger.debug(
                ("CallCallback::on_state : Call with {uri!s} is {st!s} last "
                 "code = {code!s} ({reas!s})").format(
                    uri=self.call.info().remote_uri,
                    st=self.call.info().state_text,
                    code=self.call.info().last_code,
                    reas=self.call.info().last_reason))

        if self.call.info().state == pj.CallState.CONNECTING:
            self.voipio.on_call_connecting(self.call.info().remote_uri)

        if self.call.info().state == pj.CallState.CONFIRMED:
            call_slot = self.call.info().conf_slot

            # Construct the output file names.
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
            self.output_file_name_recorded = os.path.join(
                self.system_logger.get_session_dir_name(),
                'all-{stamp}.recorded.wav'.format(stamp=timestamp))
            self.output_file_name_played = os.path.join(
                self.system_logger.get_session_dir_name(),
                'all-{stamp}.played.wav'.format(stamp=timestamp))

            while 1:
                try:
                    # this can fail if the session.xml is not created yet
                    self.session_logger.dialogue_rec_start(
                        "system",
                        os.path.basename(self.output_file_name_played))
                    self.session_logger.dialogue_rec_start(
                        "user",
                        os.path.basename(self.output_file_name_recorded))
                except IOError:
                    # Sleep for a while to let others react to the previous
                    # messages.
                    time.sleep(self.cfg['Hub']['main_loop_sleep_time'])
                    # Then try again.
                    continue
                # Everything was OK, so exit the loop.
                break

            # Create wave recorders.
            self.recorded_id = pj.Lib.instance().create_recorder(
                self.output_file_name_recorded)
            recorded_slot = pj.Lib.instance().recorder_get_slot(
                self.recorded_id)
            self.played_id = pj.Lib.instance().create_recorder(
                self.output_file_name_played)
            played_slot = pj.Lib.instance().recorder_get_slot(self.played_id)

            # Connect the call to the wave recorder.
            pj.Lib.instance().conf_connect(call_slot, recorded_slot)
            # Connect the memory player to the wave recorder.
            pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot,
                                           played_slot)

            # Connect the call to the memory capture.
            pj.Lib.instance().conf_connect(call_slot,
                                           self.voipio.mem_capture.port_slot)
            # Connect the memory player to the call.
            pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot,
                                           call_slot)

            # Send the callback.
            self.voipio.on_call_confirmed(self.call.info().remote_uri)

        if self.call.info().state == pj.CallState.DISCONNECTED:
            self.session_logger.dialogue_rec_end(
                os.path.basename(self.output_file_name_played))
            self.session_logger.dialogue_rec_end(
                os.path.basename(self.output_file_name_recorded))

            self.voipio.call = None

            if self.recorded_id:
                pj.Lib.instance().recorder_destroy(self.recorded_id)
            if self.played_id:
                pj.Lib.instance().recorder_destroy(self.played_id)
            self.voipio.on_call_disconnected(self.call.info().remote_uri)

    def on_transfer_status(self, code, reason, final, cont):
        if self.cfg['VoipIO']['debug']:
            m = []
            m.append("CallCallback::on_transfer_status : Call with %s " % self.call.info().remote_uri)
            m.append("is %s " % self.call.info().state_text)
            m.append("last code = %s " % self.call.info().last_code)
            m.append("(%s)" % self.call.info().last_reason)
            self.system_logger.debug(''.join(m))

        print code, reason, final, cont

        return True

    def on_transfer_request(self, dst, code):
        if self.cfg['VoipIO']['debug']:
            m = "CallCallback::on_transfer_request : Remote party transferring the call to %s %s" % (dst, code)
            self.system_logger.debug(''.join(m))

        return 202

    # Notification when call's media state has changed.
    def on_media_state(self):
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            if self.cfg['VoipIO']['debug']:
                self.system_logger.debug("CallCallback::on_media_state : Media is now active")
        else:
            if self.cfg['VoipIO']['debug']:
                self.system_logger.debug("CallCallback::on_media_state : Media is inactive")

    def on_dtmf_digit(self, digits):
        if self.cfg['VoipIO']['debug']:
            self.system_logger.debug("Received digits: %s" % digits)

        self.voipio.on_dtmf_digit(digits)


class VoipIO(multiprocessing.Process):
    """ VoipIO implements IO operations using a SIP protocol.

    If enabled then it logs all recorded and played audio into a file.
    The file is in RIFF wave in stereo, where left channel contains recorded audio and the right channel contains
    played audio.
    """

    def __init__(self, cfg, commands, audio_record, audio_play):
        """ Initialize VoipIO

        cfg - configuration dictionary

        audio_record - inter-process connection for sending recorded audio.
          Audio is divided into frames, each of the length of
          samples_per_frame.

        audio_play - inter-process connection for receiving audio to be played.
          Audio must be divided into frames, each with the length of
          samples_per_frame.

        """

        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.acc = None
        self.acc_cb = None
        self.call = None

        self.commands = commands
        self.local_commands = deque()

        self.audio_record = audio_record
        self.audio_recording = False

        self.audio_play = audio_play
        self.audio_playing = False
        self.local_audio_play = deque()

        self.last_frame_id = 1
        self.message_queue = []

        self.black_list = defaultdict(int)

    def recv_input_localy(self):
        """ Copy all input from input connections into local queue objects.

        This will prevent blocking the senders.
        """

        while self.commands.poll():
            command = self.commands.recv()
            self.local_commands.append(command)

        while self.audio_play.poll():
            frame = self.audio_play.recv()
            self.local_audio_play.append(frame)

    def process_pending_commands(self):
        """Process all pending commands.

        Available commands:
          stop()    - stop processing and exit the process
          flush()   - flush input buffers.
            Now it only flushes the input connection.
            It is not able flush data already send to the sound card.

          call(dst)     - make a call to the destination dst
          transfer(dst) - transfer the existing call to the destination dst
          hangup()      - hang up the existing call

          black_list(remote_uri, expire) - black list the specified uri until the expire time
                          - remote uri is get_user_from_uri provided by the on_call_confirmed call back
                          - expire is the time in second since the epoch that is time provided by time.time() function

        Return True if the process should terminate.

        """

        if self.local_commands:
            command = self.local_commands.popleft()

            if isinstance(command, Command):
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug(command)

                if command.parsed['__name__'] == 'stop':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    return True

                if command.parsed['__name__'] == 'flush':
                    self.local_commands.clear()

                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    self.local_audio_play.clear()
                    self.mem_player.flush()
                    self.audio_playing = False

                    return False

                if command.parsed['__name__'] == 'flush_out':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    self.local_audio_play.clear()
                    self.mem_player.flush()
                    self.audio_playing = False

                    return False

                if command.parsed['__name__'] == 'make_call':
                    # make a call to the passed destination
                    self.make_call(command.parsed['destination'])
                    return False

                if command.parsed['__name__'] == 'transfer':
                    # transfer the current call to the passed destination
                    self.transfer(command.parsed['destination'])

                    return False

                if command.parsed['__name__'] == 'hangup':
                    # hangup the current call
                    self.hangup()

                    return False

                if command.parsed['__name__'] == 'black_list':
                    # black list the passed remote uri, VoipIO will not accept any
                    # calls until the current time will be higher then the expire variable
                    remote_uri = command.parsed['remote_uri']
                    expire = int(command.parsed['expire'])

                    self.black_list[remote_uri] = expire

                    return False

                raise VoipIOException('Unsupported command: ' + command)

        return False

    def send_pending_messages(self):
        """ Send all messages for which corresponding frame was already played.
        """
        num_played_frames = self.mem_player.get_num_played_frames()

        del_messages = []

        for i, (message, frame_id) in enumerate(self.message_queue):
            if frame_id <= num_played_frames:
                self.commands.send(message)
                del_messages.append(frame_id)

        # delete the messages which were already sent
        self.message_queue = [x for x in self.message_queue if x[1]
                              not in del_messages]

    def read_write_audio(self):
        """Send as much possible of the available data to the output and read as much as possible from the input.

        It should be a non-blocking operation.
        """

        while (self.local_audio_play and
                (self.mem_player.get_write_available()
                 > self.cfg['Audio']['samples_per_frame'] * 2)):
            # send a frame from input to be played
            data_play = self.local_audio_play.popleft()

            if self.audio_playing and isinstance(data_play, Frame):
                if len(data_play) == self.cfg['Audio']['samples_per_frame'] * 2:
                    self.last_frame_id = self.mem_player.put_frame(data_play.payload)

            elif isinstance(data_play, Command):
                if data_play.parsed['__name__'] == 'utterance_start':
                    self.audio_playing = True
                    self.message_queue.append(
                        (Command('play_utterance_start(user_id="{uid}",fname="{fname}")'
                                    .format(uid=data_play.parsed['user_id'], fname=data_play.parsed['fname']),
                                 'VoipIO', 'HUB'),
                         self.last_frame_id))
                    try:
                        self.cfg['Logging']['session_logger'].rec_start("system", data_play.parsed['fname'])
                    except SessionLoggerException as ex:
                        print ex
                        pass

                if self.audio_playing and data_play.parsed['__name__'] == 'utterance_end':
                    self.audio_playing = False
                    self.message_queue.append(
                        (Command('play_utterance_end(user_id="{uid}",fname="{fname})'
                                 .format(uid=data_play.parsed['user_id'], fname=data_play.parsed['fname']),
                                 'VoipIO', 'HUB'),
                         self.last_frame_id))
                    try:
                        self.cfg['Logging']['session_logger'].rec_end(data_play.parsed['fname'])
                    except SessionLoggerException as ex:
                        print ex
                        pass

        while (self.mem_capture.get_read_available() > self.cfg['Audio']['samples_per_frame'] * 2):
            # Get and send recorded data, it must be read at the other end.
            data_rec = self.mem_capture.get_frame()

            # send the audio only if the call is connected
            # ignore any audio signal left after the call was disconnected
            if self.audio_recording:
                self.audio_record.send(Frame(data_rec))

    def is_sip_uri(self, dst):
        """ Check whether it is a SIP URI.
        """
        return dst.startswith('sip:')

    def has_sip_uri(self, dst):
        p = re.search(
            r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
        if not p:
            return False

        return True

    def get_sip_uri(self, dst):
        p = re.search(
            r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
        if not p:
            return None

        return p.group(0)

    def get_user_from_uri(self, uri):
        p = re.search(
            r'sip:([a-zA-Z0-9_\.]+)@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?', uri)
        if not p:
            return None

        return p.group(1)

    def is_phone_number(self, dst):
        """ Check whether it is a phone number.
        """
        p = re.search('(^\+?[0-9]{1,12}$)', dst)
        if not p:
            return False

        return True

    def construct_sip_uri_from_phone_number(self, dst):
        """ Construct a valid SIP URI for given phone number.
        """
        sip_uri = "sip:" + dst + '@' + self.cfg['VoipIO']['domain']
        return sip_uri

    def is_accepted_phone_number(self, dst):
        """ Check the phone number against the positive and negative patterns.
        """

        if self.cfg['VoipIO']['allowed_phone_numbers']:
            p = re.search(self.cfg['VoipIO']['allowed_phone_numbers'], dst)
            if not p:
                return False

        if self.cfg['VoipIO']['forbidden_phone_number']:
            p = re.search(self.cfg['VoipIO']['forbidden_phone_number'], dst)
            if p:
                return False

        return True

    def is_accepted_sip_uri(self, dst):
        """ Check the SIP URI against the positive and negative patterns.
        """

        sip_uri = pj.SIPUri(dst)

        if self.cfg['VoipIO']['allowed_users']:
            p = re.search(self.cfg['VoipIO']['allowed_users'], sip_uri.user)
            if not p:
                return False

        if self.cfg['VoipIO']['forbidden_users']:
            p = re.search(self.cfg['VoipIO']['forbidden_users'], sip_uri.user)
            if p:
                return False

        if self.cfg['VoipIO']['allowed_hosts']:
            p = re.search(self.cfg['VoipIO']['allowed_hosts'], sip_uri.host)
            if not p:
                return False

        if self.cfg['VoipIO']['forbidden_hosts']:
            p = re.search(self.cfg['VoipIO']['forbidden_hosts'], sip_uri.host)
            if p:
                return False

        return True

    def normalise_uri(self, uri):
        """ normalise the phone number or sip uri with a contact name into a clear SIP URI.
        """

        if self.is_phone_number(uri):
            if self.is_accepted_phone_number(uri):
                uri = self.construct_sip_uri_from_phone_number(uri)
            else:
                return "blocked"
        elif self.has_sip_uri(uri):
            uri = self.get_sip_uri(uri)
            if self.is_accepted_sip_uri(uri):
                uri = self.get_sip_uri(uri)
            else:
                return "blocked"

        return uri

    def make_call(self, uri):
        """ Call provided URI. Check whether it is allowed.
        """
        try:
            uri = self.normalise_uri(uri)

            if self.cfg['VoipIO']['debug']:
                print "Making a call to", uri

            if self.is_sip_uri(uri):
                # create a call back for the call
                call_cb = CallCallback(self.cfg, None, self)
                self.call = self.acc.make_call(uri, cb=call_cb)

                # send a message that there is a new incoming call
                self.commands.send(Command('make_call(remote_uri="%s")' % self.get_user_from_uri(uri), 'VoipIO', 'HUB'))

                return self.call
            elif uri == "blocked":
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug('VoipIO : Blocked call to a forbidden phone number - %s' % uri)
            else:
                raise VoipIOException(
                    'Making call to SIP URI which is not SIP URI - ' + uri)

        except pj.Error, e:
            print "Exception: " + str(e)
            return None

    def transfer(self, uri):
        """FIXME: This does not work yet!"""
        return

        try:
            if self.cfg['VoipIO']['debug']:
                self.cfg['Logging']['system_logger'].debug("Transferring the call to %s" % uri)
            return self.call.transfer(uri)
        except pj.Error, e:
            print "Exception: " + str(e)
            return None

    def hangup(self):
        try:
            if self.call:
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug("Hangup the call")

                return self.call.hangup()
        except pj.Error, e:
            print "Exception: " + str(e)
            return None

    def on_incoming_call(self, remote_uri):
        """ Signals an incoming call.
        """
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_incoming_call - from %s" % remote_uri)

        # send a message that there is a new incoming call
        self.commands.send(Command('incoming_call(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_rejected_call(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_rejected_call - from %s" % remote_uri)

        # send a message that we rejected an incoming call
        self.commands.send(Command('rejected_call(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_rejected_call_from_blacklisted_uri(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_rejected_call_from_blacklisted_uri - from %s" % remote_uri)

        # send a message that we rejected an incoming call from blacklisted user
        self.commands.send(Command('rejected_call_from_blacklisted_uri(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_connecting(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_connecting")

        # send a message that the call is connecting
        self.commands.send(Command('call_connecting(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_confirmed(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_confirmed")

        # enable recording of audio
        self.audio_recording = True

        # send a message that the call is confirmed
        self.commands.send(Command('call_confirmed(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_disconnected(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_disconnected")

        # disable recording of audio
        self.audio_recording = False

        # send a message that the call is disconnected
        self.commands.send(Command('call_disconnected(remote_uri="%s")' % self.get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_dtmf_digit(self, digits):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_dtmf_digit")

        # send a message that a digit was recieved
        self.commands.send(Command('dtmf_digit(digit="%s")' % digits, 'VoipIO', 'HUB'))

    def run(self):
        set_proc_name("alex_VIO")
        try:
            global logger
            logger = self.cfg['Logging']['system_logger']

            # Create library instance
            self.lib = pj.Lib()

            # Init library with default config with some customization.
            ua_cfg = pj.UAConfig()
            ua_cfg.max_calls = 1

            log_cfg = pj.LogConfig()
            log_cfg.level = self.cfg['VoipIO']['pjsip_log_level']
            log_cfg.callback = log_cb

            media_cfg = pj.MediaConfig()
            media_cfg.clock_rate = self.cfg['Audio']['sample_rate']
            media_cfg.audio_frame_ptime = int(1000 * self.cfg['Audio']['samples_per_frame'] / self.cfg['Audio']['sample_rate'])
            media_cfg.no_vad = True
            media_cfg.enable_ice = False

            self.lib.init(ua_cfg, log_cfg, media_cfg)
            self.lib.set_null_snd_dev()

            # disable all codecs except for PCM?
            for c in self.lib.enum_codecs():
                if c.name not in ["PCMU/8000/1", "PCMA/8000/1"]:
                    self.lib.set_codec_priority(c.name, 0)
            m = []
            m.append("Enabled codecs:")
            for c in self.lib.enum_codecs():
                if c.priority:
                    m.append("  Codec: %s priority: %d" % (c.name, c.priority))
            self.cfg['Logging']['system_logger'].info('\n'.join(m))

            # Create UDP transport which listens to any available port
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            self.cfg['Logging']['system_logger'].info("Listening on %s port %s" % (self.transport.info().host, self.transport.info().port))

            # Start the library
            self.lib.start()

            acc_cfg = pj.AccountConfig(self.cfg['VoipIO']['domain'],
                                       self.cfg['VoipIO']['user'],
                                       self.cfg['VoipIO']['password'])
            acc_cfg.allow_contact_rewrite = False

            self.acc = self.lib.create_account(acc_cfg)

            self.acc_cb = AccountCallback(self.cfg, self.acc, self)
            self.acc.set_callback(self.acc_cb)
            self.acc_cb.wait()

            self.cfg['Logging']['system_logger'].info("Registration complete, status = %s (%s)" %
                                                      (self.acc.info().reg_status, self.acc.info().reg_reason))

            my_sip_uri = "sip:" + self.transport.info().host + ":" + str(self.transport.info().port)

            # Create memory player
            self.mem_player = pj.MemPlayer(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
            self.mem_player.create()

            # Create memory capture
            self.mem_capture = pj.MemCapture(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
            self.mem_capture.create()

            while 1:
                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                self.recv_input_localy()

                # process all pending commands
                if self.process_pending_commands():
                    return

                # send all pending messages which has to be synchronized with played frames
                self.send_pending_messages()

                # process audio data
                self.read_write_audio()

            # Shutdown the library
            self.transport = None
            self.acc.delete()
            self.acc = None
            self.lib.destroy()
            self.lib = None

        except pj.Error, e:
            print "Exception: " + str(e)
            self.lib.destroy()
            self.lib = None
