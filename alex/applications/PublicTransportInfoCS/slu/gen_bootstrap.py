#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

if __name__ == '__main__':
    import autopath

import glob
import os
import xml.dom.minidom
import random
import sys

from collections import defaultdict

import alex.utils.various as various

from alex.corpustools.wavaskey import save_wavaskey
from alex.components.slu.base import CategoryLabelDatabase

def zastavka(f):
    return f.startswith('zastáv') or f.startswith('stanic')

def inform(f, v, c):
    e = []
    
    f = ' '.join(f)
    
    if c == 'stop':
        slot = 'from_stop'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych jet ze zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych se dostat ze zastávky {form}'.format(form=f))) if not zastavka(f) else None
        if zastavka(f):
            e.append((sem, 'chtěl bych jet ze {form}'.format(form=f)))
            e.append((sem, 'chtěl bych se dostat ze {form}'.format(form=f)))
        else:
            e.append((sem, 'chtěl bych jet z {form}'.format(form=f)))
            e.append((sem, 'chtěl bych se dostat z {form}'.format(form=f)))

        slot = 'to_stop'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych jet do zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych se dostat do zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych jet do {form}'.format(form=f)))
        e.append((sem, 'chtěl bych se dostat do {form}'.format(form=f)))

        slot = 'via_stop'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych jet přes zastávku {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych jet přes {form}'.format(form=f)))

    if c == 'city':
        slot = 'from_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych jet z města {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet z obce {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet z vesnice {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet z {form}'.format(form=f)))

        slot = 'to_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych jet do města {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet do obce {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet do vesnice {form}'.format(form=f)))
        e.append((sem, 'chtěl bych jet do {form}'.format(form=f)))

        slot = 'in_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 've městě {form}'.format(form=f)))
        e.append((sem, 'v obci {form}'.format(form=f)))
        e.append((sem, 've vesnici {form}'.format(form=f)))
        e.append((sem, 'v {form}'.format(form=f)))

        slot = 'via_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'přes město {form}'.format(form=f)))
        e.append((sem, 'přes obec {form}'.format(form=f)))
        e.append((sem, 'přes vesnici {form}'.format(form=f)))
        e.append((sem, 'přes {form}'.format(form=f)))

    return e

def confirm(f, v, c):
    e = []
    
    f = ' '.join(f)
    
    if c == 'stop':
        slot = 'from_stop'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to ze zastávky {form}'.format(form=f))) if not zastavka(f) else None
        if zastavka(f):
            e.append((sem, 'jede to ze {form}'.format(form=f)))
        else:
            e.append((sem, 'jede to z {form}'.format(form=f)))

        slot = 'to_stop'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to do zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'jede to do {form}'.format(form=f)))

        slot = 'via_stop'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to přes zastávku {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'jede to přes {form}'.format(form=f)))

    if c == 'city':
        slot = 'from_city'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to z města {form}'.format(form=f)))
        e.append((sem, 'jede to z obce {form}'.format(form=f)))
        e.append((sem, 'jede to z vesnice {form}'.format(form=f)))
        e.append((sem, 'jede to z {form}'.format(form=f)))

        slot = 'to_city'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to do města {form}'.format(form=f)))
        e.append((sem, 'jede to do obce {form}'.format(form=f)))
        e.append((sem, 'jede to do vesnice {form}'.format(form=f)))
        e.append((sem, 'jede to do {form}'.format(form=f)))

        slot = 'via_city'
        sem = 'confirm({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'jede to přes město {form}'.format(form=f)))
        e.append((sem, 'jede to přes obec {form}'.format(form=f)))
        e.append((sem, 'jede to přes vesnici {form}'.format(form=f)))
        e.append((sem, 'jede to přes {form}'.format(form=f)))

    return e
    
def main():

    cldb = CategoryLabelDatabase('../data/database.py')

    f_dupl = 0
    f_subs = 0
    examples = defaultdict(list)
    
    for f in cldb.form2value2cl:
        if len(cldb.form2value2cl[f]) >= 2:
            f_dupl += 1
            
        if len(f) < 2:
            continue
            
        for w in f:
            w = (w,)
            if w in cldb.form2value2cl:
                for v in cldb.form2value2cl[w]:
                    for c in cldb.form2value2cl[w][v]:
                        cc = c
                        break
                
                print '{w},{cc} -> {f}'.format(w=w, cc=cc, f=' '.join(f))
                break
        else:
            continue
        
        f_subs += 1
        for v in cldb.form2value2cl[f]:
            for c in cldb.form2value2cl[f][v]:
                examples[(c,cc)].extend(inform(f,v,c))
                examples[(c,cc)].extend(confirm(f,v,c))

    print "There were {f} surface forms.".format(f=len(cldb.form2value2cl))
    print "There were {f_dupl} surface form duplicits.".format(f_dupl=f_dupl)
    print "There were {f_subs} surface forms with substring surface forms.".format(f_subs=f_subs)
    
    max_examples = 100
    ex = []
    for c in sorted(examples.keys()):             
        print c
        z = examples[c]
        if max_examples < len(z):
            z = random.sample(z, max_examples)
        for s, t in z:
            print ' - ', s, '<=>', t
            ex.append((s, t))
            
    examples = ex
    
    examples.sort()
    
    sem = {}
    trn = {}
    for i, e in enumerate(examples):
        key = 'bootstrap_gen_{i:06d}.wav'.format(i=i)
        sem[key] = e[0]
        trn[key] = e[1]

    save_wavaskey('bootstrap_gen.sem', sem)
    save_wavaskey('bootstrap_gen.trn', trn)

if __name__ == '__main__':
    main()
