#!/usr/bin/python
import sys
import os
from collections import defaultdict
import itertools

import autopath
import alex.utils.pdbonerror

from alex.utils.config import as_project_path
from alex.components.nlg.tectotpl.core.run import Scenario




TECTO_CFG = {
            'scenario': [
                {'block': 'read.TectoTemplates', 'args': {'encoding': None}},
                {'block': 't2a.CopyTTree'},
                {'block': 't2a.cs.ReverseNumberNounDependency'},
                {'block': 't2a.cs.InitMorphcat'},
                {'block': 't2a.cs.GeneratePossessiveAdjectives'},
                {'block': 't2a.cs.MarkSubject'},
                {'block': 't2a.cs.ImposePronZAgr'},
                {'block': 't2a.cs.ImposeRelPronAgr'},
                {'block': 't2a.cs.ImposeSubjPredAgr'},
                {'block': 't2a.cs.ImposeAttrAgr'},
                {'block': 't2a.cs.ImposeComplAgr'},
                {'block': 't2a.cs.DropSubjPersProns'},
                {'block': 't2a.cs.AddPrepositions'},
                {'block': 't2a.cs.AddSubconjs'},
                {'block': 't2a.cs.GenerateWordForms', 'args': {'model': 'flect/model-t253-l1_10_00001-alex.pickle.gz'}},
                {'block': 't2a.cs.VocalizePrepos'},
                {'block': 't2a.cs.CapitalizeSentStart'},
                {'block': 'a2w.cs.ConcatenateTokens'},
                {'block': 'a2w.cs.RemoveRepeatedTokens'},
            ],
            'global_args': {'language': 'cs', 'selector': ''},
            'data_dir': as_project_path('applications/TectoTplTest/data/'),
}


class ExpandStops(object):
    tpl = u"[{stop}|n:{case}|gender:{gender},number:{number}]"
    tpl_adj = u"[{stop}|adj:attr]"

    def __init__(self):
        self.stops = defaultdict(list)


    def expand(self):
        scen = Scenario(TECTO_CFG)
        scen.load_blocks()

        for stop in self.stops.keys():
            for gender, case, number in itertools.product(['fem', 'anim', 'inan', 'neut'], [1, 2, 3, 4, 6, 7], ["sg", "pl"]):
                print gender, case, number
                stop_f = self.tpl.format(stop=stop, gender=gender, case=case, number=number)
                stop_out = scen.apply_to(stop_f)
                self.stops[stop].append(stop_out)
                print stop, stop_out

    def expand_morfflex(self):
        morf_dict = defaultdict(set)
        with open('/tmp/morfflex-cz.2013-05-02.utf8.lemmaID_suff-tag-form.tab.csv') as f_in:
            for i, ln in enumerate(f_in):
                t1, x, t2 = ln.strip().lower().decode('utf8').split('\t')
                if t2 in self.stops_words:
                    morf_dict[t2].add(t1)

                #if i > 10000:
                #    break

        for stop in self.stops.keys():
            res = []
            stop_s = stop.split()

            #print stop_s
            #print morf_dict.items()[:10]


            for part in stop_s:
                res.append(morf_dict.get(part, set([part])))

            #print res
            for word in itertools.product(*res):
                stop_out = " ".join(word)
                self.stops[stop].append(stop_out)
                print stop_out


    def save(self, fname):
        with open(fname, "w") as f_out:
            for key, values in self.stops.iteritems():
                f_out.write(";".join(values).encode('utf8'))
                f_out.write("\n")

    def parse_stops(self):
        self.stops_words = set()
        for stop in self.stops.keys():
            stop_s = stop.split()
            self.stops_words.update(set(stop_s))



    @classmethod
    def load_from_file(cls, fname):
        es = ExpandStops()
        with open(fname) as f_in:
            for ln in f_in:
                es.stops[ln.decode('utf8').strip()] = []

        es.parse_stops()

        return es


def main():
    fname = sys.argv[1]
    fname_out = sys.argv[2]
    es = ExpandStops.load_from_file(fname)
    #es.expand()
    es.expand_morfflex()
    es.save(fname_out)



if __name__ == '__main__':
    main()