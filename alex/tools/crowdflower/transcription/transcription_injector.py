#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    This script is expecting to get at leaset 2 transcriptions per wav file (3 is better).
    It copies all "session.xml" files from provided LOG_FOLDER path subtree to "asr_transcribed.xml" and then it goes
    through all the transcriptions in TRANSCRIPTION_FILE (from CF) and injects <asr_transcription/> tag to these xmls
    with a reference to wav file and transcribed text.
    Additionally it will detect conflicts in transcriptions (e.g. two transcriptions don't match) and offer to solve
    these conflicts by hand on std input.
    When resolving conflicts it will duplicate resolved lines into TRANSCRIPTION_FILE, so next time the script is run
    these conflicts will not occur.
    Non resolved conflicts are not injected into any xml.

    For usage write transcription_injector.py -l LOG_FOLDER -t TRANSCRIPTION_FILE [-s CONFLICTS_OUT_FILE] [-o] [-r]
    - LOG_FOLDER - folder with logs from PTIEN
    - TRANSCRIPTION_FILE - file with transcriptions from crowd flower, expects header containing 'url' and 'transcribed_text' on the first line
    - CONFLICTS_OUT_FILE - file that will contain (wav_file, transcription) tuple of unresolved conflicts (default path is '/tmp/conflicts.csv'
    -o - overwrite existing transcriptions
    -r - offer manual conflict resolution on std input
"""
import codecs
from collections import Counter
from datetime import datetime
from getopt import getopt
import os
import sys
import xml.etree.ElementTree as ET
from shutil import copyfile
import wave
import pyaudio

from alex.components.nlg.tools.en import every_word_for_number


_NOISE_ = 'none'
_URL_ = 'url'  # header name - for filename association
_TEXT_ = 'transcribed_text'
_CHUNK_ = 1024  # buffer size for reading wav files


def read_file(path):
    data = []
    with codecs.open(path, 'r', 'utf8') as stream:
        for line in stream:
            if line.startswith('#'):
                continue
            data.append(line)
    return data


def save_conflicts(conf_out_file, conflicted_transcriptions):
    with codecs.open(conf_out_file, 'w', 'utf8') as stream:
        for wav in conflicted_transcriptions:
            for conflict in conflicted_transcriptions[wav][0]:
                print >> stream, "%s\t%s" % (wav, conflict)
            print >> stream, '\n'


def append_lines(path, data):
    with codecs.open(path, 'a', 'utf8') as stream:
        print >> stream, "# resolved conflicts added %s" % (str(datetime.now()),)
        for line in data:
            print >> stream, line.strip()


def get_index_of(header, column_name):
    for i, h in enumerate(header.split(',')):
        if str(h).strip() == column_name:
            return i
    return -1


def session_to_asr_transcribed(logs_path):
    """This makes sure that for each session.xml there is a asr_transcribed.xml,
     if not it makes one from session.xml as a copy."""
    sessions = [x + '/' + f for x, _, fs in os.walk(logs_path) for f in fs if f == 'session.xml']
    for s in sessions:
        asr_transcribed = '/'.join(s.split('/')[:-1] + ['asr_transcribed.xml'])
        if not os.path.exists(asr_transcribed) or os.stat(asr_transcribed).st_size < 1:
            print "Making a copy of '%s' as asr_transcribed.xml" % s
            copyfile(s, asr_transcribed)


def process(xmls, transcriptions, overwrite_existing=False):
    print "processing %i transcriptions" % len(transcriptions)
    num = 0
    used_trns = dict()
    for xml in xmls:
        # print 'Analysing: ' + xml
        tree = ET.parse(xml)
        root = tree.getroot()
        changed = False
        for turn in [t for t in root.findall("turn") if t.attrib['speaker'] == 'user']:
            fname = str(turn.find('rec').attrib['fname'])
            if fname not in transcriptions:
                continue
            trn = transcriptions[fname]
            # check for previous transcription
            if turn.findall("asr_transcription"):
                orig = turn.findall("asr_transcription")[0].text
                action = "overwriting" if overwrite_existing else "keeping"
                if orig != trn:
                    print "%i\t ANOTHER TRANSCRIPTION FOUND: %s -> %s (%s) %s" % (num, fname, trn, orig, action)
                else:
                    print "%i\t %s %s - %s" % (num, action, fname, trn)
                if not overwrite_existing:
                    continue
            else:
                print '%i\t Adding transcription for %s -> %s ' % (num, fname, trn)
                turn.append(ET.Element("asr_transcription"))
            # create tag with transcription
            turn.find('asr_transcription').text = trn
            used_trns[fname] = trn
            num += 1
            changed = True
        if changed:
            print "writing %s" % xml
            ET.ElementTree(root).write(xml, encoding='utf-8')

    unused_trns = set(transcriptions.keys()) - set(used_trns.keys())
    if unused_trns:
        print "\nunused transcriptions:\n%s" % '\n'.join(unused_trns)


def repair(text):
    text = text.lower().replace('.', '').replace('n/a', _NOISE_).replace('  ', ' ').strip().strip('"').strip()
    for suf in ['th', 'st', 'nd', 'rd']:
        text = text.replace(' %s ' % suf, '%s ' % suf)
    words = text.split()
    for suf in ['th', 'st', 'nd', 'rd']:
        for i, w in enumerate(words):
            if w.endswith(suf) and w.rstrip(suf).isdigit():
                words[i] = every_word_for_number(int(w.rstrip(suf)), True)
    words = [every_word_for_number(int(w)) if w.isdigit() else w for w in words]
    return " ".join(words)


def get_transcriptions(transcription_file):
    results = read_file(transcription_file)
    header = results[0]
    results = results[1:]

    ui = get_index_of(header, _URL_)
    ti = get_index_of(header, _TEXT_)
    # ai = -1#get_index_of(header, 'audio_exists')

    # report faulty rows (commas in transcriptions):
    faults = [i for i, l in enumerate(results) if len(l.split(',')) > len(header.split(','))]
    if faults:
        raise IndexError("WARNING: those rows have more columns than header: " + str(faults))

    # group by file name
    fn_dict = dict()
    for line in results:
        wav_file = line.split(',')[ui].split('/')[-1].strip()
        if wav_file in fn_dict:
            fn_dict[wav_file].append(line)
        else:
            fn_dict[wav_file] = [line]
    # get transcriptions to separate dict
    trn_dict = dict()
    for key in fn_dict:
        trns = [repair(l.split(',')[ti].strip()) for l in fn_dict[key]]
        trn_dict[key] = Counter(trns)

    # get transcriptions with that most solvers agreed upon, and full trn lines that are not clear
    clear = dict()
    unclear = dict()
    for key in trn_dict:
        if len(trn_dict[key]) == 1:
            clear[key] = trn_dict[key].most_common()[0][0]
            continue
        ft, fc = trn_dict[key].most_common(2)[0]
        _, sc = trn_dict[key].most_common(2)[1]
        if fc > sc:
            clear[key] = ft
        else:  # get (transcription, corresponding line) tuples for further processing
            unclear[key] = ([repair(l.split(',')[ti].strip()) for l in fn_dict[key]], fn_dict[key])

    return clear, unclear, header


def find_file(name, path):
    """Find a file by name (find the subdirectory where it sits).
    From http://stackoverflow.com/questions/1724693/find-a-file-in-python."""
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

def play_wav(wav_name, base_path):
    """Find and play a WAV file using PyAudio. Adapted from http://people.csail.mit.edu/hubert/pyaudio/."""

    wav_file = find_file(wav_name, base_path)
    wf = wave.open(wav_file, 'rb')

    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    data = wf.readframes(_CHUNK_)

    while data != '':
        stream.write(data)
        data = wf.readframes(_CHUNK_)

    stream.stop_stream()
    stream.close()

    p.terminate()


def resolve_conflicts(conflicted_transcriptions, header, logs_path):
    """
    This will offer transcriptions to the user and duplicate the selected transcription line to original transcription
    csv, so that the next time it will take the majority vote on it. It returns unresolved transcriptions.
    """
    ti = get_index_of(header, _TEXT_)
    resolved = dict()
    skipped = dict()
    resolved_lines = []

    wavs = conflicted_transcriptions.keys()
    j = 0
    while j < len(wavs):
        wav = wavs[j]
        options, lines = conflicted_transcriptions[wav]
        print '\n%s (%i/%i):' % (wav, j + 1, len(conflicted_transcriptions))
        print 's/a/q/p/m/n\tskip/abort/quit/play/merge/noise'
        for i, conflict in enumerate(options, 1):
            print "(%i)\t%s" % (i, conflict)

        choice = raw_input("choose action/number: ").strip()
        if 's' == choice:
            skipped[wav] = conflicted_transcriptions[wav]
        elif 'q' == choice:
            skipped_keys = conflicted_transcriptions.keys()[j:]
            for k in skipped_keys:
                skipped[k] = conflicted_transcriptions[k]
            j = len(wavs)  # break
        elif 'a' == choice:
            skipped = conflicted_transcriptions
            resolved = dict()
            resolved_lines = []
            j = len(wavs)  # break
        elif 'm' == choice:
            merged = raw_input("enter merged version: ").strip()
            resolved[wav] = merged
            # add the line twice to the logs so it overrides all options appearing only once
            columns = lines[0].split(',')
            columns[ti] = merged
            merged_line = ','.join(columns)
            resolved_lines.append(merged_line)
            resolved_lines.append(merged_line)
        elif 'p' == choice:
            play_wav(wav, logs_path)
            j -= 1  # stay at the same position
        elif 'n' == choice:
            resolved[wav] = _NOISE_
            columns = lines[0].split(',')
            columns[ti] = _NOISE_
            noise_line = ','.join(columns)
            # add the line twice otherwise next time there would be a tie of n+1 options
            resolved_lines.append(noise_line)
            resolved_lines.append(noise_line)
        elif choice.isdigit() and len(options) >= int(choice) > 0:
            resolved[wav] = options[int(choice) - 1]
            resolved_lines.append(lines[int(choice) - 1])
        else:
            print "Didn't recognize input '%s', skipping %s" % (options, wav)
            skipped[wav] = conflicted_transcriptions[wav]

        j += 1

    return skipped, resolved, resolved_lines


if __name__ == "__main__":
    logs_path = ""
    transcription_file = ""
    conflicts_out = "/tmp/conflicts.csv"
    resolve_confl = False
    overwrite_existing = False
    opts, files = getopt(sys.argv[1:], 'l:t:s:or')
    for opt, arg in opts:
        if opt == '-l':
            logs_path = arg
        elif opt == '-t':
            transcription_file = arg
        elif opt == '-s':
            conflicts_out = arg
        elif opt == '-r':
            resolve_confl = True
        elif opt == '-o':
            overwrite_existing = True

    if not os.path.exists(logs_path):
        print logs_path + " does not exist!"
        sys.exit(__doc__)
    if not os.path.isfile(transcription_file):
        print transcription_file + " does not exist!"
        sys.exit(__doc__)

    # make sure that each session.xml has its asr_transcribed.xml file
    session_to_asr_transcribed(logs_path)
    xmls = [x + '/' + f for x, _, fs in os.walk(logs_path) for f in fs if f == 'asr_transcribed.xml']
    legit, conflicts, header = get_transcriptions(transcription_file)
    # offer the user to resolve conflicts by hand
    if resolve_confl:
        conflicts, resolved, resolved_lines = resolve_conflicts(conflicts, header, logs_path)
        if resolved:
            legit.update(resolved)
        if resolved_lines:
            append_lines(transcription_file, resolved_lines)  # not to resolve those conflict ever again

    # save unresolved conflicts
    if conflicts:
        save_conflicts(conflicts_out, conflicts)
    # inject legit and resolved transcription tags into asr_transcribed.xml files and save them
    process(xmls, legit, overwrite_existing)
