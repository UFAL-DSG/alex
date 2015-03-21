#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pylint: disable-msg=E1101

import time
import multiprocessing
import os.path
import os
import threading
import re
import pjsuaxt as pj

from datetime import datetime
from collections import deque, defaultdict

from alex.components.hub.messages import Command, Frame
from alex.utils.exceptions import SessionLoggerException
from alex.components.hub.exceptions import VoipIOException
from alex.utils.exdec import catch_ioerror
from alex.utils.procname import set_proc_name

# Logging callback
logger = None

@catch_ioerror
def log_cb(level, str, len):
    if logger:
        logger.info(str)

def get_user_from_uri(uri):
    p = re.search(r'sip:([a-zA-Z0-9_\.]+)@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?', uri)
    if not p:
        return None

    return p.group(1)

phone_number_hash = {}
def hash_remote_uri(cfg, remote_uri):
    if not cfg['VoipIO']['phone_number_obfuscation']:
        return remote_uri
    global phone_number_hash

    user = get_user_from_uri(remote_uri)
    h = hex(abs(hash(user)))[2:]
    phone_number_hash[h] = user
    converted_uri = remote_uri.replace(user, h)

    print "-"*120
    print "  Hashing a user {user} to {h}".format(user=user,h=h)
    print "  Converted {uri1} to {uri2}".format(uri1=remote_uri,uri2=converted_uri)
    print "-"*120
    print 

    return converted_uri

def is_phone_number_hash(h):
    return h in phone_number_hash

def recover_phone_number_from_hash(h):
    user = phone_number_hash[h]
    
    print "-"*120
    print "  Recovering a user {user} from hash {h}".format(user=user,h=h)
    print "-"*120
    print 
    
    return user

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

        try:
            current_time = time.time()
            remote_uri = hash_remote_uri(self.cfg, call.info().remote_uri)

            if not self.cfg['VoipIO']['reject_calls']:
                if self.voipio.black_list[get_user_from_uri(remote_uri)] < current_time:
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
                        wait_hours = (self.voipio.black_list[get_user_from_uri(remote_uri)] - current_time) / (60 * 60)
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
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the AccountCallback class.')
            raise

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
        try:
            if self.cfg['VoipIO']['debug']:
                self.system_logger.debug(
                    ("CallCallback::on_state : Call with {uri!s} is {st!s} last "
                     "code = {code!s} ({reas!s})").format(
                        uri=hash_remote_uri(self.cfg, self.call.info().remote_uri),
                        st=self.call.info().state_text,
                        code=self.call.info().last_code,
                        reas=self.call.info().last_reason))

            if self.call.info().state == pj.CallState.CONNECTING:
                self.voipio.on_call_connecting(hash_remote_uri(self.cfg, self.call.info().remote_uri))

            if self.call.info().state == pj.CallState.CONFIRMED:
                call_slot = self.call.info().conf_slot

                # Construct the output file names.
                timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S.%f')
                self.output_file_name_recorded = os.path.join(self.system_logger.get_session_dir_name(),'all-{stamp}.recorded.wav'.format(stamp=timestamp))
                self.output_file_name_played = os.path.join(self.system_logger.get_session_dir_name(),'all-{stamp}.played.wav'.format(stamp=timestamp))
 
                self.session_logger.dialogue_rec_start("system", os.path.basename(self.output_file_name_played))
                self.session_logger.dialogue_rec_start("user", os.path.basename(self.output_file_name_recorded))

                # Create wave recorders.
                self.recorded_id = pj.Lib.instance().create_recorder(self.output_file_name_recorded)
                recorded_slot = pj.Lib.instance().recorder_get_slot(self.recorded_id)
                self.played_id = pj.Lib.instance().create_recorder(self.output_file_name_played)
                played_slot = pj.Lib.instance().recorder_get_slot(self.played_id)

                # Connect the call to the wave recorder.
                pj.Lib.instance().conf_connect(call_slot, recorded_slot)
                # Connect the memory player to the wave recorder.
                pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot, played_slot)

                # Connect the call to the memory capture.
                pj.Lib.instance().conf_connect(call_slot, self.voipio.mem_capture.port_slot)
                # Connect the memory player to the call.
                pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot, call_slot)

                # Send the callback.
                self.voipio.on_call_confirmed(hash_remote_uri(self.cfg, self.call.info().remote_uri))

            if self.call.info().state == pj.CallState.DISCONNECTED:
                # call can be disconnected even if it was never connected (e.g. if it was ringing and never answered)
                if self.output_file_name_played:
                    self.session_logger.dialogue_rec_end(os.path.basename(self.output_file_name_played))
                if self.output_file_name_recorded:
                    self.session_logger.dialogue_rec_end(os.path.basename(self.output_file_name_recorded))

                self.voipio.call = None

                if self.recorded_id:
                    pj.Lib.instance().recorder_destroy(self.recorded_id)
                    self.recorded_id = None

                if self.played_id:
                    pj.Lib.instance().recorder_destroy(self.played_id)
                    self.played_id = None

                # Send the callback.
                self.voipio.on_call_disconnected(hash_remote_uri(self.cfg, self.call.info().remote_uri), self.call.info().last_code)
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the CallCallback class.')
            raise

    def on_transfer_status(self, code, reason, final, cont):
        try:
            if self.cfg['VoipIO']['debug']:
                m = []
                m.append("CallCallback::on_transfer_status : Call with %s " % hash_remote_uri(self.cfg, self.call.info().remote_uri))
                m.append("is %s " % self.call.info().state_text)
                m.append("last code = %s " % self.call.info().last_code)
                m.append("(%s)" % self.call.info().last_reason)
                self.system_logger.debug(''.join(m))

            print code, reason, final, cont

            return True
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the CallCallback class.')
            raise

    def on_transfer_request(self, dst, code):
        try:
            if self.cfg['VoipIO']['debug']:
                m = "CallCallback::on_transfer_request : Remote party transferring the call to %s %s" % (dst, code)
                self.system_logger.debug(''.join(m))

            return 202
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the CallCallback class.')
            raise

    def on_media_state(self):
        """
        Notification when call's media state has changed.
        """
        try:
            if self.call.info().media_state == pj.MediaState.ACTIVE:
                if self.cfg['VoipIO']['debug']:
                    self.system_logger.debug("CallCallback::on_media_state : Media is now active")
            else:
                if self.cfg['VoipIO']['debug']:
                    self.system_logger.debug("CallCallback::on_media_state : Media is inactive")
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the CallCallback class.')
            raise

    def on_dtmf_digit(self, digits):
        try:
            if self.cfg['VoipIO']['debug']:
                self.system_logger.debug("Received digits: %s" % digits)

            self.voipio.on_dtmf_digit(digits)
        except:
            self.voipio.close_event.set()
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the CallCallback class.')
            raise


class VoipIO(multiprocessing.Process):
    """ VoipIO implements IO operations using a SIP protocol.

    If enabled then it logs all recorded and played audio into a file.
    The file is in RIFF wave in stereo, where left channel contains recorded audio and the right channel contains
    played audio.
    """

    def __init__(self, cfg, commands, audio_record, audio_play, close_event):
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

        self.close_event = close_event

        self.black_list = defaultdict(int)

    def recv_input_locally(self):
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

        while self.local_commands:
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
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    self.local_audio_play.clear()
                    self.mem_player.flush()
                    self.audio_playing = False

                    # flush the recorded data
                    while self.mem_capture.get_read_available():
                        data_rec = self.mem_capture.get_frame()
                    self.mem_capture.flush()
                    self.audio_recording = False

                    self.commands.send(Command("flushed()", 'VoipIO', 'HUB'))

                    return False

                if command.parsed['__name__'] == 'flush_out':
                    # discard all data in play buffer
                    while self.audio_play.poll():
                        data_play = self.audio_play.recv()

                    self.local_audio_play.clear()
                    self.mem_player.flush()
                    self.audio_playing = False

                    self.commands.send(Command("flushed_out()", 'VoipIO', 'HUB'))
                    
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
        self.message_queue = [x for x in self.message_queue if x[1] not in del_messages]

    def read_write_audio(self):
        """Send as much possible of the available data to the output and read as much as possible from the input.

        It should be a non-blocking operation.
        """

        if (self.local_audio_play and
                (self.mem_player.get_write_available() > self.cfg['Audio']['samples_per_frame'] * 2)):
            # send a frame from input to be played
            data_play = self.local_audio_play.popleft()

            if self.audio_playing and isinstance(data_play, Frame):
                if len(data_play) == self.cfg['Audio']['samples_per_frame'] * 2:
                    self.last_frame_id = self.mem_player.put_frame(data_play.payload)
                    self.cfg['Logging']['session_logger'].rec_write(self.audio_playing, data_play.payload)

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

        if (self.mem_capture.get_read_available() > self.cfg['Audio']['samples_per_frame'] * 2):
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
        p = re.search(r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
        if not p:
            return False

        return True

    def get_sip_uri(self, dst):
        p = re.search(r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
        if not p:
            return None

        return p.group(0)

    def is_phone_number(self, dst):
        """ Check whether it is a phone number.
        """
        p = re.search('(^(\+|00)?[0-9]{1,12}$)', dst)
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
        elif is_phone_number_hash(uri):
            pn = recover_phone_number_from_hash(uri)
            if self.is_accepted_phone_number(pn):
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

    def make_call(self, remote_uri):
        """ Call provided URI. Check whether it is allowed.
        """

        # *WARNING* pjsip only handles standard string, not UNICODE !
        remote_uri = str(remote_uri)
        try:
            uri = remote_uri
            if is_phone_number_hash(uri):
                uri = recover_phone_number_from_hash(uri)

            remote_uri = self.normalise_uri(remote_uri)
            uri = self.normalise_uri(uri)

            if self.cfg['VoipIO']['debug']:
                print "-"*120
                print "  Remote uri:      ", remote_uri
                print "  Making a call to:", uri
                print "-"*120
                print 

            if self.is_sip_uri(uri):
                # create a call back for the call
                call_cb = CallCallback(self.cfg, None, self)
                self.call = self.acc.make_call(uri, cb=call_cb)

                # send a message that we are calling to uri
                self.commands.send(Command('make_call(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

                return self.call
            elif uri == "blocked":
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug('VoipIO.make_call: Calling a blocked phone number - %s' % uri)
                # send a message that the provided uri is blocked
                self.commands.send(Command('blocked_uri(remote_uri="%s")' % remote_uri, 'VoipIO', 'HUB'))
            else:
                self.cfg['Logging']['system_logger'].error('VoipIO.make_call: Calling SIP URI which is not recognised as valid SIP URI - %s' % uri)
                # send a message that the provided uri is invalid
                self.commands.send(Command('invalid_uri(remote_uri="%s")' % remote_uri, 'VoipIO', 'HUB'))

        except pj.Error as e:
            print "Exception: " + unicode(e)
            return None

    def transfer(self, uri):
        """FIXME: This does not work yet!"""
        return

        try:
            if self.cfg['VoipIO']['debug']:
                self.cfg['Logging']['system_logger'].debug("Transferring the call to %s" % uri)
            return self.call.transfer(uri)
        except pj.Error as e:
            print "Exception: " + unicode(e)
            return None

    def hangup(self):
        try:
            if self.call:
                if self.cfg['VoipIO']['debug']:
                    self.cfg['Logging']['system_logger'].debug("Hangup the call")

                return self.call.hangup()
        except pj.Error as e:
            print "Exception: " + unicode(e)
            return None

    def on_incoming_call(self, remote_uri):
        """ Signals an incoming call.
        """
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_incoming_call - from %s" % remote_uri)

        # send a message that there is a new incoming call
        self.commands.send(Command('incoming_call(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_rejected_call(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_rejected_call - from %s" % remote_uri)

        # send a message that we rejected an incoming call
        self.commands.send(Command('rejected_call(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_rejected_call_from_blacklisted_uri(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_rejected_call_from_blacklisted_uri - from %s" % remote_uri)

        # send a message that we rejected an incoming call from blacklisted user
        self.commands.send(Command('rejected_call_from_blacklisted_uri(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_connecting(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_connecting")

        # send a message that the call is connecting
        self.commands.send(Command('call_connecting(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_confirmed(self, remote_uri):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_confirmed")

        # enable recording of audio
        self.audio_recording = True

        # send a message that the call is confirmed
        self.commands.send(Command('call_confirmed(remote_uri="%s")' % get_user_from_uri(remote_uri), 'VoipIO', 'HUB'))

    def on_call_disconnected(self, remote_uri, code):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_call_disconnected")

        # disable recording of audio
        self.audio_recording = False

        # send a message that the call is disconnected
        self.commands.send(Command('call_disconnected(remote_uri="%s", code="%s")' % (get_user_from_uri(remote_uri), str(code)), 'VoipIO', 'HUB'))

    def on_dtmf_digit(self, digits):
        if self.cfg['VoipIO']['debug']:
            self.cfg['Logging']['system_logger'].debug("VoipIO::on_dtmf_digit")

        # send a message that a digit was recieved
        self.commands.send(Command('dtmf_digit(digit="%s")' % digits, 'VoipIO', 'HUB'))

    def run(self):
        try:
            set_proc_name("Alex_VIO")
            self.cfg['Logging']['session_logger'].cancel_join_thread()

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

            my_sip_uri = "sip:" + self.transport.info().host + ":" + unicode(self.transport.info().port)

            # Create memory player
            self.mem_player = pj.MemPlayer(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
            self.mem_player.create()

            # Create memory capture
            self.mem_capture = pj.MemCapture(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
            self.mem_capture.create()

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    print 'Received close event in: %s' % multiprocessing.current_process().name
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                s = (time.time(), time.clock())

                self.recv_input_locally()

                # process all pending commands
                if self.process_pending_commands():
                    return

                # send all pending messages which has to be synchronized with played frames
                self.send_pending_messages()

                # process audio data
                for i in range(self.cfg['VoipIO']['n_rwa']):
                    # process at least n_rwa frames
                    self.read_write_audio()

                d = (time.time() - s[0], time.clock() - s[1])
                if d[0] > 0.200:
                    print "EXEC Time inner loop: VIO t = {t:0.4f} c = {c:0.4f}\n".format(t=d[0], c=d[1])

            # Shutdown the library
            self.transport = None
            self.acc.delete()
            self.acc = None
            self.lib.destroy()
            self.lib = None

        except KeyboardInterrupt:
            self.lib.destroy()
            self.lib = None

            print 'KeyboardInterrupt exception in: %s' % multiprocessing.current_process().name
            self.close_event.set()
            return
        except:
            self.lib.destroy()
            self.lib = None

            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the VIO process.')
            self.close_event.set()
            raise
