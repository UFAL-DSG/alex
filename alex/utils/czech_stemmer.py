#!python
# encoding: utf8
''' Czech stemmer
Copyright © 2010 Luís Gomes <luismsgomes@gmail.com>.

Ported from the Java implementation available at:
    http://members.unine.ch/jacques.savoy/clef/index.html

'''
import re
import sys

def cz_stem(word, aggressive=False):
    if not re.match(u"^\\w+$", word):
        return word
    if not word.islower() and not word.istitle() and not word.isupper():
        return word
    s = word.lower() # all our pattern matching is done in lowercase
    s = _remove_case(s)
    s = _remove_possessives(s)
    if aggressive:
        s = _remove_comparative(s)
        s = _remove_diminutive(s)
        s = _remove_augmentative(s)
        s = _remove_derivational(s)
    if word.isupper():
        return s.upper()
    if word.istitle():
        return s.title()
    return s

def _remove_case(word):
    if len(word) > 7 and word.endswith(u"atech"):
        return word[:-5]
    if len(word) > 6:
        if word.endswith(u"ětem"):
            return _palatalise(word[:-3])
        if word.endswith(u"atům"):
            return word[:-4]
    if len(word) > 5:
        if word[-3:] in {u"ech", u"ich", u"ích", u"ého", u"ěmi", u"emi", u"ému",
                         u"ete", u"eti", u"iho", u"ího", u"ími", u"imu"}:
            return _palatalise(word[:-2])
        if word[-3:] in {u"ách", u"ata", u"aty", u"ých", u"ama", u"ami",
                         u"ové", u"ovi", u"ými"}:
            return word[:-3]
    if len(word) > 4:
        if word.endswith(u"em"):
            return _palatalise(word[:-1])
        if word[-2:] in {u"es", u"ém", u"ím"}:
            return _palatalise(word[:-2])
        if word[-2:] in {u"ům", u"at", u"ám", u"os", u"us", u"ým", u"mi", u"ou"}:
            return word[:-2]
    if len(word) > 3:
        if word[-1] in u"eiíě":
            return _palatalise(word)
        if word[-1] in u"uyůaoáéý":
            return word[:-1]
    return word

def _remove_possessives(word):
    if len(word) > 5:
        if word[-2:] in {u"ov", u"ův"}:
            return word[:-2]
        if word.endswith(u"in"):
            return _palatalise(word[:-1])
    return word

def _remove_comparative(word):
    if len(word) > 5:
        if word[-3:] in {u"ejš", u"ějš"}:
            return _palatalise(word[:-2])
    return word

def _remove_diminutive(word):
    if len(word) > 7 and word.endswith(u"oušek"):
        return word[:-5]
    if len(word) > 6:
        if word[-4:] in {u"eček", u"éček", u"iček", u"íček", u"enek", u"ének",
                         u"inek", u"ínek"}:
            return _palatalise(word[:-3])
        if word[-4:] in {u"áček", u"aček", u"oček", u"uček", u"anek", u"onek",
                         u"unek", u"ánek"}:
            return _palatalise(word[:-4])
    if len(word) > 5:
        if word[-3:] in {u"ečk", u"éčk", u"ičk", u"íčk", u"enk", u"énk",
                         u"ink", u"ínk"}:
            return _palatalise(word[:-3])
        if word[-3:] in {u"áčk", u"ačk", u"očk", u"učk", u"ank", u"onk",
                         u"unk", u"átk", u"ánk", u"ušk"}:
            return word[:-3]
    if len(word) > 4:
        if word[-2:] in {u"ek", u"ék", u"ík", u"ik"}:
            return _palatalise(word[:-1])
        if word[-2:] in {u"ák", u"ak", u"ok", u"uk"}:
            return word[:-1]
    if len(word) > 3 and word[-1] == u"k":
        return word[:-1]
    return word

def _remove_augmentative(word):
    if len(word) > 6 and word.endswith(u"ajzn"):
        return word[:-4]
    if len(word) > 5 and word[-3:] in {u"izn", u"isk"}:
        return _palatalise(word[:-2])
    if len(word) > 4 and word.endswith(u"ák"):
        return word[:-2]
    return word

def _remove_derivational(word):
    if len(word) > 8 and word.endswith(u"obinec"):
        return word[:-6]
    if len(word) > 7:
        if word.endswith(u"ionář"):
            return _palatalise(word[:-4])
        if word[-5:] in {u"ovisk", u"ovstv", u"ovišt", u"ovník"}:
            return word[:-5]
    if len(word) > 6:
        if word[-4:] in {u"ásek", u"loun", u"nost", u"teln", u"ovec", u"ovík",
                         u"ovtv", u"ovin", u"štin"}:
            return word[:-4]
        if word[-4:] in {u"enic", u"inec", u"itel"}:
            return _palatalise(word[:-3])
    if len(word) > 5:
        if word.endswith(u"árn"):
            return word[:-3]
        if word[-3:] in {u"ěnk", u"ián", u"ist", u"isk", u"išt", u"itb", u"írn"}:
            return _palatalise(word[:-2])
        if word[-3:] in {u"och", u"ost", u"ovn", u"oun", u"out", u"ouš",
                         u"ušk", u"kyn", u"čan", u"kář", u"néř", u"ník",
                         u"ctv", u"stv"}:
            return word[:-3]
    if len(word) > 4:
        if word[-2:] in {u"áč", u"ač", u"án", u"an", u"ář", u"as"}:
            return word[:-2]
        if word[-2:] in {u"ec", u"en", u"ěn", u"éř", u"íř", u"ic", u"in", u"ín",
                         u"it", u"iv"}:
            return _palatalise(word[:-1])
        if word[-2:] in {u"ob", u"ot", u"ov", u"oň", u"ul", u"yn", u"čk", u"čn",
                         u"dl", u"nk", u"tv", u"tk", u"vk"}:
            return word[:-2]
    if len(word) > 3 and word[-1] in u"cčklnt":
        return word[:-1]
    return word

def _palatalise(word):
    if word[-2:] in {u"ci", u"ce", u"či", u"če"}:
        return word[:-2] + u"k"

    if word[-2:] in {u"zi", u"ze", u"ži", u"že"}:
        return word[:-2] + u"h"

    if word[-3:] in {u"čtě", u"čti", u"čtí"}:
        return word[:-3] + u"ck"

    if word[-3:] in {u"ště", u"šti", u"ští"}:
        return word[:-3] + u"sk"
    return word[:-1]

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in (u"light", u"aggressive"):
        sys.exit(u"usage: {} light|aggressive".format(sys.argv[0]))
    aggressive = sys.argv[1] == u"aggressive"
    for line in sys.stdin:
        print u" ".join([cz_stem(word, aggressive=aggressive)
                for word in line.split()])
