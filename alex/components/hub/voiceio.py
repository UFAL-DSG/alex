from alex.components.hub.messages import Command, Frame
from alex.utils.exceptions import SessionLoggerException


class PlayedUtteranceInfo(object):
    def __init__(self, info):
        self.data = info
        self.frame_queue = []
        self.end_msg = None
        self.beg_msg = None

    def queue_frame(self, frame):
        self.frame_queue.append(frame)

    def pop_queue(self):
        res = self.frame_queue[:]
        del self.frame_queue[:]

        return res


class VoiceIO(object):
    """Abstract class that provides high-level functionality for any voice input/output sub-class."""
    def __init__(self, cfg, commands, audio_record, audio_play, close_event):
        super(VoiceIO, self).__init__()
        self.cfg = cfg
        self.message_queue = []
        self.commands = commands
        self.last_frame_id = 1
        self.last_played_frame = -1
        self.last_utterance_data = None
        self.buffered_utterances = []
        self.curr_utt = -1
        self.utt_ndx = 0
        self.utt_filling = -1
        self.utt_info = {}

    def update_current_utterance_id(self, utt_id):
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        print 'curr utterance id', self.curr_utt, 'new:', utt_id


        if self.curr_utt != -1:
            self._log_audio()

        if utt_id != self.curr_utt:
            if self.curr_utt != -1:
                info = self.utt_info[self.curr_utt]
                try:
                    if info.end_msg.parsed['log'] == "true":
                        self.cfg['Logging']['session_logger'].rec_end(info.end_msg.parsed['fname'])
                except SessionLoggerException as e:
                    self.cfg['Logging']['system_logger'].exception(e)

                self._send_play_cmd("end", self.curr_utt)
                del self.utt_info[self.curr_utt]

            if utt_id != -1:
                info = self.utt_info[utt_id]
                try:
                    if info.beg_msg.parsed['log'] == "true":
                        self.cfg['Logging']['session_logger'].rec_start("system", info.beg_msg.parsed['fname'])
                except SessionLoggerException as e:
                    self.cfg['Logging']['system_logger'].exception(e)

                self._send_play_cmd("start", utt_id)

        self.curr_utt = utt_id

    def _log_audio(self):
        info = self.utt_info[self.curr_utt]
        frames = info.pop_queue()

        for audio_play_msg in frames:
            self.cfg['Logging']['session_logger'].rec_write(info.data['fname'], audio_play_msg.payload)

    def _send_play_cmd(self, which, utt_id):
        info = self.utt_info[utt_id]
        cmd = Command('play_utterance_{which}(user_id="{uid}",fname="{fname})'
                             .format(which=which, uid=info.data['user_id'], fname=info.data['fname']),
                             'VoipIO', 'HUB')
        self.commands.send(cmd)

    def process_msg(self, msg):
        if isinstance(msg, Frame):
            if self.utt_filling == -1:
                self.cfg['Logging']['system_logger'].warning('Trying to log a frame but no utterance belongs to it. Perhaps caused by prematurely ended call.')
                return
            else:
                self.utt_info[self.utt_filling].queue_frame(msg)

        if isinstance(msg, Command):
            if msg.parsed['__name__'] == 'utterance_start':
                self.utt_filling = self.utt_ndx
                self.utt_info[self.utt_filling] = PlayedUtteranceInfo(msg.parsed)
                self.utt_info[self.utt_filling].beg_msg = msg
                self.utt_ndx += 1

            if msg.parsed['__name__'] == 'utterance_end':
                self.utt_info[self.utt_filling].end_msg = msg
                self.utt_filling = -1

            if msg.parsed['__name__'] == 'reset':
                self.utt_filling = -1
                self.curr_utt = -1
                self.utt_ndx = 0
                self.utt_info = {}


