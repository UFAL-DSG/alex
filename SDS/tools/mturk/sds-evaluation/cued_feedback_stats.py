#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import glob
import os.path
import collections
import xml.dom.minidom
import numpy as np
import math

verbose = True
verbose = False

def sterr(inlist):
    """
    Returns the standard error of the values in the passed list using N-1
    in the denominator (i.e., to estimate population standard error).

    Usage:   sterr(inlist)
    """
    return np.std(inlist) / float(math.sqrt(len(inlist)))
    
def getText(node):
    rc = []
    for cn in node.childNodes:
        if cn.nodeType == cn.TEXT_NODE:
            rc.append(cn.data)
    return ''.join(rc).strip()

def printStats(callLengths,phones, success):
    avgCallLengths = np.mean(callLengths)
    maxCallLengths = max(callLengths)
    minCallLengths = min(callLengths)
    medCallLengths = median(callLengths)

    phoneNumCalls = [len(phones[x]) for x in phones]
    avgPhoneNumCalls = np.mean(phoneNumCalls)
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
    print "  Yes: %d (%.2f%% +-%.2f)" % (allInfoYes, b*100, allInfoYesCI*100)
    print "  No:  %d (%.2f%% +-%.2f)" % (allInfoNo, (1.0-b)*100.0, allInfoYesCI*100)
    print
    print "The system understood me well."
    print "  Score: %.2f +-%.2f" % (np.mean([x[1] for x in scores]), sterr([x[1] for x in scores])*1.96)
    print
    print "The phrasing of the system's responses was good."
    print "  Score: %.2f +-%.2f" % (np.mean([x[2] for x in scores]), sterr([x[2] for x in scores])*1.96)
    print
    print "The system's voice was of good quality."
    print "  Score: %.2f +-%.2f" % (np.mean([x[3] for x in scores]), sterr([x[3] for x in scores])*1.96)
    print

#    f = open('comments.txt', "w")
#    for each in comments:
#        if not each:
#            continue
#        f.write("-"*80 + "\n")
#        f.write(each + "\n")
#    f.close()

class Feedback:
    def  __init__(self, dirName = None):
        if dirName:
            self.loadFeedback(dirName)
        else:
            self.phone = None
            self.worker = None
            self.system = None
            self.success = None
            self.slu = None
            self.nlg = None
            self.tts = None
            self.turns = None
            self.comments = None
            self.goal = None
            self.task = None

        return

    def __str__(self):
        s=   """-----------------------------
                Phone:    %s
                Worker:   %s
                System:   %s
                Success:  %0.1f
                SLU:      %0.1f
                NLG:      %0.1f
                TTS:      %0.1f
                Turns:    %d
                Comments: %s
                Goal:     %s
                Task:     %s""" % (self.phone,
                                    self.worker,
                                    self.system,
                                    self.success,
                                    self.slu,
                                    self.nlg,
                                    self.tts,
                                    self.turns,
                                    self.comments,
                                    self.goal,
                                    self.task)
        return s

    def loadFeedback(self,dirName):
        feedbackName = os.path.join(dirName,'feedback.xml')

        # load the file
        doc = xml.dom.minidom.parse(feedbackName)
        els = doc.getElementsByTagName("question")

        for el in els:
            name = el.getAttribute('name').strip()
            if name == "Did you find all the information you were looking for?":
                if getText(el) == "No":
                    self.success  = 0.0
                else:
                    self.success  = 1.0
            elif name == "The system understood me well.":
                self.slu = self.convertScoring(getText(el))
            elif name == "The phrasing of the system's responses was good.":
                self.nlg = self.convertScoring(getText(el))
            elif name == "The system's voice was of good quality.":
                self.tts = self.convertScoring(getText(el))

        els = doc.getElementsByTagName("comments")
        self.comments = getText(els[0])
        els = doc.getElementsByTagName("workerId")
        self.worker = getText(els[0])
        els = doc.getElementsByTagName("goal")
        self.goal = getText(els[0])
        els = doc.getElementsByTagName("task")
        self.task = getText(els[0])

        # get the phone number
        phone = os.path.basename(dirName).replace("voip-", "")
        phone = phone[:phone.index("-")]
        self.phone = phone

        # get the evaluated system
        systemLow = os.path.dirname(os.path.abspath(dirName))
        systemHigh = os.path.dirname(systemLow)
        systemLow = os.path.basename(systemLow)
        systemHigh = os.path.basename(systemHigh)
        system = systemHigh+":"+systemLow
        self.system = system
        
        # get number fo turns
        self.turns = len(glob.glob(os.path.join(dirName,'*.wav'))) - 1

        return

    def convertScoring(self,score):
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


class FeedbackFilter:
    def __init__(self, feedbackList):
        self.feedbacks = feedbackList

    def __len__(self):
        return len(self.feedbacks)

    def has(self, attribute, value):
        if isinstance(value,list):
            feedbacks = [f for f in self.feedbacks if getattr(f,attribute) in value]
        else:
            feedbacks = [f for f in self.feedbacks if getattr(f,attribute) == value]
        return FeedbackFilter(feedbacks)

    def hasnot(self, attribute, value):
        if isinstance(value,list):
            feedbacks = [f for f in self.feedbacks if getattr(f,attribute) not in value]
        else:
            feedbacks = [f for f in self.feedbacks if getattr(f,attribute) != value]
        return FeedbackFilter(feedbacks)

    def getSet(self, attribute):
        l = [getattr(f,attribute) for f in self.feedbacks]
        return set(l)

    def getList(self, attribute):
        l = [getattr(f,attribute) for f in self.feedbacks]
        return l

def getSuccessStats(feedbacks):
    if len(feedbacks):
      success = sum(feedbacks.getList('success'))
      failure = len(feedbacks) - success
      ratio = success / float(len(feedbacks))
      ci = math.sqrt(ratio*(1-ratio)/len(feedbacks))*1.96
    else:
      return (None, None, None, None)
      
    return (success, failure, ratio, ci)


def perSystemAnalysis(feedbacks):
    phones = FeedbackFilter(feedbacks).getSet('phone')
    workers = FeedbackFilter(feedbacks).getSet('worker')
    systems = FeedbackFilter(feedbacks).getSet('system')

    print "Per system analysis"
    print "="*80
    print "Total number of calls: ", len(feedbacks)
    print
    print "="*80
    for system in sorted(systems):
        perSystemFeedbacks = FeedbackFilter(feedbacks).has('system', system)
        print "-"*80
        print " System: ", system
        print "-"*80

        print "     Number of calls: %d" % len(perSystemFeedbacks)
        print

        print "     Did you find all the information you were looking for?"

        success, failure, ratio, ci = getSuccessStats(perSystemFeedbacks)
        print "         Yes: %d (%.2f%% +-%.2f)" % (success, ratio*100, ci*100)
        print "         No:  %d (%.2f%% +-%.2f)" % (failure, (1.0-ratio)*100.0, ci*100)
        print

        print "     The system understood me well."
        print "         Score: %.2f +-%.2f" % (np.mean(perSystemFeedbacks.getList('slu')), sterr(perSystemFeedbacks.getList('slu'))*1.96)
        print

        print "     The phrasing of the system's responses was good."
        print "         Score: %.2f +-%.2f" % (np.mean(perSystemFeedbacks.getList('nlg')), sterr(perSystemFeedbacks.getList('nlg'))*1.96)
        print

        print "     The system's voice was of good quality."
        print "         Score: %.2f +-%.2f" % (np.mean(perSystemFeedbacks.getList('tts')), sterr(perSystemFeedbacks.getList('tts'))*1.96)
        print


def perPhoneAnalysis(feedbacks):
    phones = FeedbackFilter(feedbacks).getSet('phone')
    workers = FeedbackFilter(feedbacks).getSet('worker')
    systems = FeedbackFilter(feedbacks).getSet('system')
    
    print "="*80
    print "Per phone analysis"
    print "="*80

    print "Phone            ",
    for system in sorted(systems):
        print " %40s" % system,
    print

    numPhones = 0
    for phone in sorted(phones):
        perPhoneFeedbacks = FeedbackFilter(feedbacks).has('phone',phone)

        print "%12s" % phone.strip(),
        for system in sorted(systems):
            perSystemFeedbacks = perPhoneFeedbacks.has('system',system)

            if len(perSystemFeedbacks):
              success, failure, ratio, ci = getSuccessStats(perSystemFeedbacks)
              print " %35.2f #%3.0f" % (ratio*100,success + failure),

        print
        numPhones += 1

    print "-"*80
    print "Total phones: ", numPhones
    print "="*80

print "-"*80
print "MTURK FEEDBACK STATS"
print "-"*80

pth = "./*/voip-*"
calls = glob.glob(pth)

feedbacks = []
for call in calls:
    if verbose:
        print "Processing call: ", os.path.split(call)[1]

    try:
        feedback = Feedback(call)
        if verbose:
            print feedback
    except IOError:
        continue

    feedbacks.append(feedback)
    
phones = FeedbackFilter(feedbacks).getSet('phone')
workers = FeedbackFilter(feedbacks).getSet('worker')
systems = FeedbackFilter(feedbacks).getSet('system')

perSystemAnalysis(feedbacks)
perPhoneAnalysis(feedbacks)

minCalls = 3
exludePhones = []
for phone in phones:
    perPhone = FeedbackFilter(feedbacks).has('phone',phone)
    
    succTest = 0
    for system in systems:
        perSystem = perPhone.has('system',system)
        if len(perSystem) >= minCalls:
            succTest += 1

    if succTest < 2:
        exludePhones.append(phone)

exludePhones.append("anonymous")
filteredFeedbacks = FeedbackFilter(feedbacks).hasnot('phone',exludePhones)

print "*"*80
print "Filtered stats: minimum 3 calls for at least 2 systems each per user"
print "*"*80
perSystemAnalysis(filteredFeedbacks.feedbacks)
perPhoneAnalysis(filteredFeedbacks.feedbacks)

