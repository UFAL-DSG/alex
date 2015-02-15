#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import multiprocessing
import time
import random
import cPickle as pickle
import argparse
import codecs
import re

from alex.components.hub.vio import VoipIO
from alex.components.hub.vad import VAD
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command
from alex.utils.config import Config


def load_sentences(file_name):
    f = codecs.open(file_name, 'r', 'UTF-8')

    r = []
    for s in f:
        s = s.strip()
        r.append(s)

    f.close()

    return r


def sample_sentence(l):
    return random.choice(l)


def load_database(file_name):
    db = dict()
    try:
        f = open(file_name, 'r')
        db = pickle.load(f)
        f.close()
    except IOError:
        pass

    if 'calls_from_start_end_length' not in db:
        db['calls_from_start_end_length'] = dict()

    return db


def save_database(file_name, db):
    f = open(file_name, 'w+')
    pickle.dump(db, f)
    f.close()


def get_stats(db, remote_uri):
    num_all_calls = 0
    total_time = 0
    last24_num_calls = 0
    last24_total_time = 0
    try:
        for s, e, l in db['calls_from_start_end_length'][remote_uri]:
            if l > 0:
                num_all_calls += 1
                total_time += l

                # do counts for last 24 hours
                if s > time.time() - 24 * 60 * 60:
                    last24_num_calls += 1
                    last24_total_time += l
    except:
        pass

    return num_all_calls, total_time, last24_num_calls, last24_total_time


def play_intro(cfg, tts_commands, intro_id, last_intro_id):
    for i in range(len(cfg['RepeatAfterMe']['introduction'])):
        last_intro_id = str(intro_id)
        intro_id += 1
        tts_commands.send(Command('synthesize(user_id="%s",text="%s")' % (last_intro_id, cfg['RepeatAfterMe']['introduction'][i]), 'HUB', 'TTS'))

    return intro_id, last_intro_id


def ram():
    return random.choice(cfg['RepeatAfterMe']['ram'])

#########################################################################
#########################################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Repeat After Me dialogue system records repeated utterances by users of the system.
        When a user calls the system, the systems rejects the call. Then in a few seconds,
        it calls back to the user, informs about how to use the system and the recording data.
        When it is done, it says goodbye to the user.

        The systems calls back to the user to prevent any call fees on the user's side.

        The program reads the default config in the resources directory ('../resources/default.cfg')
        and the ram_hub.cfg config in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument('-c', action="store", dest="configs", nargs='+',
                        help='additional configure file')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Repeat After Me dialogue system\n" + "=" * 120)

    sample_sentences = load_sentences(cfg['RepeatAfterMe']['sentences_file'])

    vio_commands, vio_child_commands = multiprocessing.Pipe()  # used to send commands to VoipIO
    vio_record, vio_child_record = multiprocessing.Pipe()      # I read from this connection recorded audio
    vio_play, vio_child_play = multiprocessing.Pipe()          # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()   # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

    tts_commands, tts_child_commands = multiprocessing.Pipe()   # used to send commands to TTS
    tts_text_in, tts_child_text_in = multiprocessing.Pipe()     # used to send TTS text

    command_connections = [vio_commands, vad_commands, tts_commands]

    non_command_connections = [vio_record, vio_child_record,
                               vio_play, vio_child_play,
                               vad_audio_out, vad_child_audio_out,
                               tts_text_in, tts_child_text_in]

    close_event = multiprocessing.Event()

    vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play, close_event)
    vad = VAD(cfg, vad_child_commands, vio_record, vad_child_audio_out, close_event)
    tts = TTS(cfg, tts_child_commands, tts_child_text_in, vio_play, close_event)

    vio.start()
    vad.start()
    tts.start()

    cfg['Logging']['session_logger'].set_close_event(close_event)
    cfg['Logging']['session_logger'].set_cfg(cfg)
    cfg['Logging']['session_logger'].start()

    # init the system
    call_connected = False
    call_start = 0
    count_intro = 0
    intro_played = False
    reject_played = False
    intro_id = 0
    last_intro_id = -1
    end_played = False
    s_voice_activity = False
    s_last_voice_activity_time = 0
    u_voice_activity = False
    u_last_voice_activity_time = 0
    n_calls = 0

    db = load_database(cfg['RepeatAfterMe']['call_db'])

    for remote_uri in db['calls_from_start_end_length']:
        num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

        m = []
        m.append('')
        m.append('=' * 120)
        m.append('Remote SIP URI: %s' % remote_uri)
        m.append('-' * 120)
        m.append('Total calls:             %d' % num_all_calls)
        m.append('Total time (s):          %f' % total_time)
        m.append('Last 24h total calls:    %d' % last24_num_calls)
        m.append('Last 24h total time (s): %f' % last24_total_time)
        m.append('-' * 120)

        current_time = time.time()
        if last24_num_calls > cfg['RepeatAfterMe']['last24_max_num_calls'] or \
                last24_total_time > cfg['RepeatAfterMe']['last24_max_total_time']:

            # add the remote uri to the black list
            vio_commands.send(Command('black_list(remote_uri="%s",expire="%d")' % (remote_uri,
                                                                                   current_time + cfg['RepeatAfterMe']['blacklist_for']), 'HUB', 'VoipIO'))
            m.append('BLACKLISTED')
        else:
            m.append('OK')

        m.append('-' * 120)
        m.append('')
        cfg['Logging']['system_logger'].info('\n'.join(m))

    call_back_time = -1
    call_back_uri = None

    while 1:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])

        if vad_audio_out.poll():
            data_vad = vad_audio_out.recv()

        if call_back_time != -1 and call_back_time < time.time():
            vio_commands.send(Command('make_call(destination="%s")' % call_back_uri, 'HUB', 'VoipIO'))
            call_back_time = -1
            call_back_uri = None

        # read all messages
        if vio_commands.poll():
            command = vio_commands.recv()

            if isinstance(command, Command):
                if command.parsed['__name__'] == "incoming_call" or command.parsed['__name__'] == "make_call":
                    cfg['Logging']['system_logger'].session_start(command.parsed['remote_uri'])
                    cfg['Logging']['session_logger'].session_start(cfg['Logging']['system_logger'].get_session_dir_name())

                    cfg['Logging']['system_logger'].session_system_log('config = ' + unicode(cfg))
                    cfg['Logging']['system_logger'].info(command)

                    cfg['Logging']['session_logger'].config('config = ' + unicode(cfg))
                    cfg['Logging']['session_logger'].header(cfg['Logging']["system_name"], cfg['Logging']["version"])
                    cfg['Logging']['session_logger'].input_source("voip")

                if command.parsed['__name__'] == "rejected_call":
                    cfg['Logging']['system_logger'].info(command)

                    call_back_time = time.time() + cfg['RepeatAfterMe']['wait_time_before_calling_back']
                    # call back a default uri, if not defined call back the caller
                    if ('call_back_uri_subs' in cfg['RepeatAfterMe']) and cfg['RepeatAfterMe']['call_back_uri_subs']:
                        ru = command.parsed['remote_uri']
                        for pat, repl in cfg['RepeatAfterMe']['call_back_uri_subs']:
                            ru = re.sub(pat, repl, ru)
                        call_back_uri = ru
                    elif ('call_back_uri' in cfg['RepeatAfterMe']) and cfg['RepeatAfterMe']['call_back_uri']:
                        call_back_uri = cfg['RepeatAfterMe']['call_back_uri']
                    else:
                        call_back_uri = command.parsed['remote_uri']

                if command.parsed['__name__'] == "rejected_call_from_blacklisted_uri":
                    cfg['Logging']['system_logger'].info(command)

                    remote_uri = command.parsed['remote_uri']

                    num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

                    m = []
                    m.append('')
                    m.append('=' * 120)
                    m.append('Rejected incoming call from blacklisted URI: %s' % remote_uri)
                    m.append('-' * 120)
                    m.append('Total calls:             %d' % num_all_calls)
                    m.append('Total time (s):          %f' % total_time)
                    m.append('Last 24h total calls:    %d' % last24_num_calls)
                    m.append('Last 24h total time (s): %f' % last24_total_time)
                    m.append('=' * 120)
                    m.append('')
                    cfg['Logging']['system_logger'].info('\n'.join(m))

                if command.parsed['__name__'] == "call_connecting":
                    cfg['Logging']['system_logger'].info(command)

                if command.parsed['__name__'] == "call_confirmed":
                    cfg['Logging']['system_logger'].info(command)

                    remote_uri = command.parsed['remote_uri']
                    num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

                    m = []
                    m.append('')
                    m.append('=' * 120)
                    m.append('Incoming call from :     %s' % remote_uri)
                    m.append('-' * 120)
                    m.append('Total calls:             %d' % num_all_calls)
                    m.append('Total time (s):          %f' % total_time)
                    m.append('Last 24h total calls:    %d' % last24_num_calls)
                    m.append('Last 24h total time (s): %f' % last24_total_time)
                    m.append('-' * 120)

                    if last24_num_calls > cfg['RepeatAfterMe']['last24_max_num_calls'] or \
                            last24_total_time > cfg['RepeatAfterMe']['last24_max_total_time']:

                        tts_commands.send(Command('synthesize(text="%s")' % cfg['RepeatAfterMe']['rejected'], 'HUB', 'TTS'))
                        call_connected = True
                        reject_played = True
                        s_voice_activity = True
                        vio_commands.send(Command('black_list(remote_uri="%s",expire="%d")' % (remote_uri, time.time() + cfg['RepeatAfterMe']['blacklist_for']), 'HUB', 'VoipIO'))
                        m.append('CALL REJECTED')
                    else:
                        # init the system
                        call_connected = True
                        call_start = time.time()
                        count_intro = 0
                        intro_played = False
                        reject_played = False
                        end_played = False
                        s_voice_activity = False
                        s_last_voice_activity_time = 0
                        u_voice_activity = False
                        u_last_voice_activity_time = 0

                        intro_id, last_intro_id = play_intro(cfg, tts_commands, intro_id, last_intro_id)

                        m.append('CALL ACCEPTED')

                    m.append('=' * 120)
                    m.append('')
                    cfg['Logging']['system_logger'].info('\n'.join(m))

                    try:
                        db['calls_from_start_end_length'][
                            remote_uri].append([time.time(), 0, 0])
                    except:
                        db['calls_from_start_end_length'][
                            remote_uri] = [[time.time(), 0, 0], ]
                    save_database(cfg['RepeatAfterMe']['call_db'], db)

                if command.parsed['__name__'] == "call_disconnected":
                    cfg['Logging']['system_logger'].info(command)

                    remote_uri = command.parsed['remote_uri']

                    vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
                    vad_commands.send(Command('flush()', 'HUB', 'VAD'))
                    tts_commands.send(Command('flush()', 'HUB', 'TTS'))

                    cfg['Logging']['system_logger'].session_end()
                    cfg['Logging']['session_logger'].session_end()

                    try:
                        s, e, l = db[
                            'calls_from_start_end_length'][remote_uri][-1]

                        if e == 0 and l == 0:
                            # there is a record about last confirmed but not disconnected call
                            db['calls_from_start_end_length'][remote_uri][-1] = [s, time.time(), time.time() - s]
                            save_database('call_db.pckl', db)
                    except KeyError:
                        # disconnecting call which was not confirmed for URI calling for the first time
                        pass

                    intro_played = False
                    call_connected = False
                    n_calls += 1

                if command.parsed['__name__'] == "play_utterance_start":
                    cfg['Logging']['system_logger'].info(command)
                    s_voice_activity = True

                if command.parsed['__name__'] == "play_utterance_end":
                    cfg['Logging']['system_logger'].info(command)

                    s_voice_activity = False
                    s_last_voice_activity_time = time.time()

                    if command.parsed['user_id'] == last_intro_id:
                        intro_played = True
                        s_last_voice_activity_time = 0

        if vad_commands.poll():
            command = vad_commands.recv()
            cfg['Logging']['system_logger'].info(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == "speech_start":
                    u_voice_activity = True
                if command.parsed['__name__'] == "speech_end":
                    u_voice_activity = False
                    u_last_voice_activity_time = time.time()

        if tts_commands.poll():
            command = tts_commands.recv()
            cfg['Logging']['system_logger'].info(command)

        current_time = time.time()

    #  print
    #  print intro_played, end_played
    #  print s_voice_activity, u_voice_activity,
    #  print call_start,  current_time, u_last_voice_activity_time, s_last_voice_activity_time
    #  print current_time - s_last_voice_activity_time > 5, u_last_voice_activity_time - s_last_voice_activity_time > 0

        if reject_played == True and s_voice_activity == False:
            # be careful it does not hangup immediately
            reject_played = False
            vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))
            vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
            vad_commands.send(Command('flush()', 'HUB', 'VoipIO'))
            tts_commands.send(Command('flush()', 'HUB', 'VoipIO'))

        if intro_played and current_time - call_start > cfg['RepeatAfterMe']['max_call_length'] and s_voice_activity == False:
            # hovor trval jiz vice nez deset minut
            if not end_played:
                s_voice_activity = True
                last_intro_id = str(intro_id)
                intro_id += 1
                tts_commands.send(Command('synthesize(text="%s")' % cfg['RepeatAfterMe']['closing'], 'HUB', 'TTS'))
                end_played = True
            else:
                intro_played = False
                # be careful it does not hangup immediately
                vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))
                vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
                vad_commands.send(Command('flush()', 'HUB', 'VAD'))
                tts_commands.send(Command('flush()', 'HUB', 'TTS'))

        if intro_played and \
            s_voice_activity == False and \
            u_voice_activity == False and \
            current_time - s_last_voice_activity_time > 5 and current_time - u_last_voice_activity_time > 0.6:

            if not cfg['RepeatAfterMe']['silence']:
                s_voice_activity = True

                s1 = ram()
                tts_commands.send(Command('synthesize(text="%s")' % s1, 'HUB', 'TTS'))
                s2 = sample_sentence(sample_sentences)
                tts_commands.send(Command('synthesize(text="%s")' % s2, 'HUB', 'TTS'))

                s = s1 + ' ' + s2

                m = []
                m.append('=' * 120)
                m.append('Say: ' + s)
                m.append('=' * 120)

                cfg['Logging']['system_logger'].info('\n'.join(m))

        if not call_connected and n_calls >= 1:
            break

    # stop processes
    vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))
    vad_commands.send(Command('stop()', 'HUB', 'VAD'))
    tts_commands.send(Command('stop()', 'HUB', 'TTS'))

    # clean connections
    for c in command_connections:
        while c.poll():
            c.recv()

    for c in non_command_connections:
        while c.poll():
            c.recv()

    # wait for processes to stop
    # do not join, because in case of exception the join will not be successful
    #vio.join()
    #system_logger.debug('VIO stopped.')
    #vad.join()
    #system_logger.debug('VAD stopped.')
    #tts.join()
    #system_logger.debug('TTS stopped.')

    print 'Exiting: %s. Setting close event' % multiprocessing.current_process().name
    close_event.set()
