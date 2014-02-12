#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import glob
import os
import xml.dom.minidom
import random
import autopath
import sys

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
        e.append((sem, 'chtěl bych je ze zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych je z {form}'.format(form=f)))

        slot = 'to_stop'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych je do zastávky {form}'.format(form=f))) if not zastavka(f) else None
        e.append((sem, 'chtěl bych je do {form}'.format(form=f)))

    if c == 'city':
        slot = 'from_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych je z města {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je z obce {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je z vesnice {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je z {form}'.format(form=f)))

        slot = 'to_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 'chtěl bych je do města {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je do obce {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je do vesnice {form}'.format(form=f)))
        e.append((sem, 'chtěl bych je do {form}'.format(form=f)))

        slot = 'to_city'
        sem = 'inform({slot}="{value}")'.format(slot=slot, value=v)
        e.append((sem, 've městě {form}'.format(form=f)))
        e.append((sem, 'v obci {form}'.format(form=f)))
        e.append((sem, 've vesnici {form}'.format(form=f)))
        e.append((sem, 'v {form}'.format(form=f)))

    return e
    
def main():
    cldb = CategoryLabelDatabase('../data/database.py')

    examples = []
    for f in cldb.form2value2cl:
        if len(cldb.form2value2cl[f]) <= 1:
            continue
            
        for v in cldb.form2value2cl[f]:
            for c in cldb.form2value2cl[f][v]:
                examples.extend(inform(f,v,c))

                print '\n'.join(' <=> '.join(e) for e in examples)
                print
                examples = []
                
                
                
                
    
if __name__ == '__main__':
    main()