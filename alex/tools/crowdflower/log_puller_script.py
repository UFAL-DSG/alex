#!/usr/bin/python
from getopt import getopt
import os

import xml.etree.ElementTree as ET
import sys


def pull_data(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    turns = root.findall("turn")
    for turn in turns:
        speaker = turn.attrib['speaker']
        if speaker == 'system' and turn.find("dialogue_act") != None:
            print "system_act:" + 15*' ' + turn.find("dialogue_act").text
            if turn.find("text") is not None:
                print "system_text:" + 14*' ' + turn.find("text").text
        else:
            if turn.find('asr') is None or turn.find('slu') is None:
                continue
            hypothesis = turn.find('asr').find('hypothesis')
            interpretation = turn.find('slu').find('interpretation')
            print "user_hypothesis:" + 10*' ' + '"' + hypothesis.text + '"'
            print "user_interpretation:" + 6*' ' + interpretation.text
        print


def main():
    _, files = getopt(sys.argv[1:], '')
    call_logs_folder = files[0]

    if not os.path.exists(call_logs_folder):
        print call_logs_folder + " does not exist!"

    logs_dirs = [d for d,_,_ in os.walk(call_logs_folder) if call_logs_folder != d]

    for log_dir in logs_dirs:
        print 90 * '='
        print "PROCESSING: " + os.path.basename(log_dir)
        print 90 * '='
        sessions = [f for _,_,files in os.walk(log_dir) for f in files  if f == 'session.xml']
        if sessions:
            print
            pull_data(os.path.join(log_dir, sessions[0]))


if __name__ == '__main__':
    main()