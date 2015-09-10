from alex.components.hub.messages import Command
from alex.utils.exceptions import SessionLoggerException


class VoiceIO(object):
    def __init__(self, cfg, commands, audio_record, audio_play, close_event):
        super(VoiceIO, self).__init__()
        self.cfg = cfg
        self.message_queue = []
        self.commands = commands
        self.last_frame_id = 1
        self.last_played_frame = -1

    def get_num_played_frames(self):
        raise NotImplementedError()

    def update_current_playback_position(self, pos):
        self.last_played_frame = pos

    def update_current_playback_buffer_position(self, pos):
        self.last_frame_id = pos

    def send_message(self, msg, f_id):
        self.message_queue.append((msg, f_id))

    def send_pending_messages(self):
        """ Send all messages for which corresponding frame was already played.
        """

        del_messages = []

        for i, (message, frame_id) in enumerate(self.message_queue):
            if frame_id <= self.last_played_frame:
                self.commands.send(message)
                del_messages.append(frame_id)

        # delete the messages which were already sent
        self.message_queue = [x for x in self.message_queue if x[1] not in del_messages]

    def process_command(self, data_play):
        print 'xxxxx processing command voiceio'
        if isinstance(data_play, Command):
            print data_play
            if data_play.parsed['__name__'] == 'utterance_start':
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                self.audio_playing = data_play.parsed['fname']
                self.send_message(
                    Command('play_utterance_start(user_id="{uid}",fname="{fname}")'
                                .format(uid=data_play.parsed['user_id'], fname=data_play.parsed['fname']),
                             'VoipIO', 'HUB'),
                    self.last_frame_id)
                try:
                    if data_play.parsed['log'] == "true":
                        self.cfg['Logging']['session_logger'].rec_start("system", data_play.parsed['fname'])
                except SessionLoggerException as e:
                    self.cfg['Logging']['system_logger'].exception(e)

            if self.audio_playing and data_play.parsed['__name__'] == 'utterance_end':
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
                print 'utterance start'
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