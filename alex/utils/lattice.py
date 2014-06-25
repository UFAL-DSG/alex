#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
'''
This module stores functionality which requires pysft module installed.
See https://github.com/UFAL-DSG/pyfst
Most of the functionality is related with Kaldi lattice decoder output.
'''

import fst
from math import exp, log

def fst_shortest_path_to_word_lists(fst_shortest):
    # There are n - eps arcs from 0 state which mark beginning of each list
    # Following one path there are 2 eps arcs at beginning
    # and one at the end before final state
    first_arcs, nb_list = [], []
    if len(fst_shortest) > 0:
        first_arcs = [a for a in fst_shortest[0].arcs]
    for arc in first_arcs:
        # first arc is epsilon arc
        assert(arc.ilabel == 0 and arc.olabel == 0)
        arc = fst_shortest[arc.nextstate].arcs.next()
        # second arc is also epsilon arc
        assert(arc.ilabel == 0 and arc.olabel == 0)
        path = []
        # start with third arc
        arc = fst_shortest[arc.nextstate].arcs.next()
        try:
            while arc.olabel != 0:
                path.append((arc.olabel, float(arc.weight)))
                # TODO use the Weights plus operation explicitly
                arc = fst_shortest[arc.nextstate].arcs.next()
            # append epsilon symbol and last arc weight
            path.append((0, float(arc.weight)))
        except StopIteration:
            pass

        nb_list.append(path)
    nb_list.sort()
    return nb_list


def fst_shortest_path_to_lists(fst_shortest):
    # There are n - eps arcs from 0 state which mark beginning of each list
    # Following one path there are 2 eps arcs at beginning
    # and one at the end before final state
    first_arcs, word_ids = [], []
    if len(fst_shortest) > 0:
        first_arcs = [a for a in fst_shortest[0].arcs]
    for arc in first_arcs:
        # first arc is epsilon arc
        assert(arc.ilabel == 0 and arc.olabel == 0)
        arc = fst_shortest[arc.nextstate].arcs.next()
        # second arc is also epsilon arc
        assert(arc.ilabel == 0 and arc.olabel == 0)
        # assuming logarithmic semiring
        path, weight = [], 0
        # start with third arc
        arc = fst_shortest[arc.nextstate].arcs.next()
        try:
            while arc.olabel != 0:
                path.append(arc.olabel)
                weight += float(arc.weight)  # TODO use the Weights plus operation explicitly
                arc = fst_shortest[arc.nextstate].arcs.next()
            weight += float(arc.weight)
        except StopIteration:
            pass

        word_ids.append((float(weight), path))
    word_ids.sort()
    return word_ids


def lattice_to_nbest(lat, n=1):
    # Log semiring -> no best path
    # Converting the lattice to tropical semiring
    std_v = fst.StdVectorFst(lat)
    p = std_v.shortest_path(n)
    return fst_shortest_path_to_lists(p)


def lattice_to_word_posterior_lists(lat, n=1):
    # Log semiring -> no best path
    # Converting the lattice to tropical semiring
    std_v = fst.StdVectorFst(lat)
    p = std_v.shortest_path(n)
    return fst_shortest_path_to_word_lists(p)

def lattice_calibration(lat, calibration_table):
    #print lat
    def find_approx(weight):
        for i, (min, max, p) in enumerate(calibration_table):
            if min <= weight < max:
                #print (weight, p),
                return p

        print "Lattice calibration warning: cannot map input score."
        return weight

    for state in lat.states:
        cum = 0.0
        for arc in state.arcs:
            weight = exp(-float(arc.weight))
            aprx = find_approx(weight)
            cum +=aprx
            arc.weight = fst.LogWeight(-log(aprx))

        for arc in state.arcs:
            arc.weight = fst.LogWeight( -log(exp(-float(arc.weight)) / cum) )
    return lat
