from alex.components.hub.messages import Command
from alex.utils.exceptions import SessionLoggerException



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
        self.utt_info = {}

    def update_current_utterance_id(self, utt_id):
        print 'curr utterance id', self.curr_utt, 'new:', utt_id
        if utt_id != self.curr_utt:
            if self.curr_utt != -1:
                if not self._send_play_cmd("end", self.curr_utt):
                    return

            if utt_id != -1:
                if not self._send_play_cmd("start", utt_id):
                    return

        self.curr_utt = utt_id

    def _send_play_cmd(self, which, utt_id):
        if not utt_id in self.utt_info:
            return False
        else:
            data = self.utt_info[utt_id]
            cmd = Command('play_utterance_{which}(user_id="{uid}",fname="{fname})'
                                 .format(which=which, uid=data['user_id'], fname=data['fname']),
                                 'VoipIO', 'HUB')
            self.commands.send(cmd)

            return True

    def process_command(self, data_play):
        if isinstance(data_play, Command):
            if data_play.parsed['__name__'] == 'utterance_start':
                self.utt_info[self.utt_ndx] = data_play.parsed
                self.utt_ndx += 1

                try:
                    if data_play.parsed['log'] == "true":
                        self.cfg['Logging']['session_logger'].rec_start("system", data_play.parsed['fname'])
                except SessionLoggerException as e:
                    self.cfg['Logging']['system_logger'].exception(e)

            if data_play.parsed['__name__'] == 'utterance_end':
                try:
                    if data_play.parsed['log'] == "true":
                        self.cfg['Logging']['session_logger'].rec_end(data_play.parsed['fname'])
                except SessionLoggerException as e:
                    self.cfg['Logging']['system_logger'].exception(e)


