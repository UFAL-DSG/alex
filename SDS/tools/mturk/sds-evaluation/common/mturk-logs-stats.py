#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import glob
import os.path
import collections
import xml.dom.minidom
from numpy import *
import math

verbose = True
verbose = False

def sterr(inlist):
    """
    Returns the standard error of the values in the passed list using N-1
    in the denominator (i.e., to estimate population standard error).

    Usage:   sterr(inlist)
    """
    return std(inlist) / float(math.sqrt(len(inlist)))
    
def feedbackYes(feedback):
    fb = open(feedback, "r")
    fbl = fb.readlines()
    fb.close()

    for l in fbl:
        if ">Yes</question>" in l:
            return True

    return False

def feedbackNo(feedback):
    fb = open(feedback, "r")
    fbl = fb.readlines()
    fb.close()

    for l in fbl:
        if ">No</question>" in l:
            return True

    return False

def getText(node):
    rc = []
    for cn in node.childNodes:
        if cn.nodeType == cn.TEXT_NODE:
            rc.append(cn.data)
    return ''.join(rc).strip()
    
def convertScoring(score):
    score = score.strip()
    
    if score == "strongly disagree":
        return 0.0
    if score == "disagree":
        return 1.0
    if score == "lightly disagree":
        return 2.0
    if score == "slightly agree":
        return 3.0
    if score == "agree":
        return 4.0
    if score == "strongly agree":
        return 5.0

    raise "Unexpected input: %s" % score
    
def getScoring(feedbackName):
    # scores: q1, q2, q3, q4, comments
    scores = [0.0,0.0,0.0,0.0, ""]
    
    # load the file
    doc = xml.dom.minidom.parse(feedbackName)
    els = doc.getElementsByTagName("question")

    for el in els:
        name = el.getAttribute('name').strip()
        if verbose:
            print name
        if name == "Did you find all the information you were looking for?":
            if getText(el) == "No":
                scores[0] = 0.0
            else:
                scores[0] = 1.0
        elif name == "The system understood me well.":
            scores[1] = convertScoring(getText(el))
        elif name == "The phrasing of the system's responses was good.":
            scores[2] = convertScoring(getText(el))
        elif name == "The system's voice was of good quality.":
            scores[3] = convertScoring(getText(el))

    if verbose:
        print "comments"
    els = doc.getElementsByTagName("comments")
    scores[4] = getText(els[0])

    if verbose:
        print scores
    
    return scores
    
print "-"*80
print "MTURK LOG STATS"
print "-"*80

#pth = os.path.join(os.path.abspath(""),"Aug09VoIP-CamInfo", "voip-*")
pth = "voip-*"
calls = glob.glob(pth)

phones = collections.defaultdict(list)
callLengths = []
allInfoYes = 0
allInfoNo = 0
scores = []
comments = []
for call in calls:
    if verbose:
        print "Processing call: ", os.path.split(call)[1]
    feedback = os.path.join(call,'feedback.xml')
    
    phone = os.path.split(call)[1].replace("voip-", "")
    phone = phone[:phone.index("-")]
    if verbose:
        print phone
    
    try:
        if feedbackYes(feedback):
            allInfoYes += 1
        if feedbackNo(feedback):
            allInfoNo += 1
    except IOError:
        continue
        
    score = getScoring(feedback)
    scores.append(score)
    comments.append(score[4])
    
    turns = len(glob.glob(os.path.join(call,'*.wav'))) - 1
    if verbose:
        print "  # of turns:", turns
    callLengths.append(turns)

    phones[phone].append(turns)


avgCallLengths = mean(callLengths)
maxCallLengths = max(callLengths)
minCallLengths = min(callLengths)
medCallLengths = median(callLengths)

phoneNumCalls = [len(phones[x]) for x in phones]
avgPhoneNumCalls = mean(phoneNumCalls)
maxPhoneNumCalls = max(phoneNumCalls)
minPhoneNumCalls = min(phoneNumCalls)
medPhoneNumCalls = median(phoneNumCalls)

print "The number of total calls:        ", len(calls)
print "The number of calls with feedback:", len(callLengths)
print "The average number of turns:      ", avgCallLengths
print "The max number of turns:          ", maxCallLengths
print "The min number of turns:          ", minCallLengths
print "The median number of turns:       ", medCallLengths
print
print "Historgam of the call lengths:    ", histogram(callLengths, range(0,60,4), new=True)
print
print "Number of different phone numbers:            ", len(phones)
print "The average number of calls per phone number: ", avgPhoneNumCalls
print "The max number of calls per phone number:     ", maxPhoneNumCalls
print "The min number of calls per phone number:     ", minPhoneNumCalls
print "The median number of calls per phone number:  ", medPhoneNumCalls
print
print "Historgam of the number of calls: ", histogram(phoneNumCalls, range(0,30,2), new=True)
print
print
print "Did you find all the information you were looking for?"
b =float(allInfoYes)/len(callLengths)
allInfoYesCI = math.sqrt(b*(1-b)/len(callLengths))*1.96
print "  Yes: %d (%.2f%% �%.2f)" % (allInfoYes, b*100, allInfoYesCI*100)
print "  No:  %d (%.2f%% �%.2f)" % (allInfoNo, (1.0-b)*100.0, allInfoYesCI*100)
print
print "The system understood me well."
print "  Score: %.2f �%.2f" % (mean([x[1] for x in scores]), sterr([x[1] for x in scores])*1.96)
print
print "The phrasing of the system's responses was good."
print "  Score: %.2f �%.2f" % (mean([x[2] for x in scores]), sterr([x[2] for x in scores])*1.96)
print
print "The system's voice was of good quality."
print "  Score: %.2f �%.2f" % (mean([x[3] for x in scores]), sterr([x[3] for x in scores])*1.96)
print

f = open('comments.txt', "w")
for each in comments:
    if not each:
        continue
    f.write("-"*80 + "\n")
    f.write(each + "\n")
f.close()

