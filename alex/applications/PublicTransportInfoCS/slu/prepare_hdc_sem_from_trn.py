#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

from alex.utils.config import as_project_path

from alex.components.asr.utterance import Utterance, UtteranceNBList


def hdc_slu(fn_input, constructor, fn_output):
    """
    Use for transcription a HDC SLU model.

    :param fn_model:
    :param fn_input:
    :param constructor:
    :param fn_reference:
    :return:
    """
    print "="*120
    print "HDC SLU: ", fn_input, fn_output
    print "-"*120

    from alex.components.slu.base import CategoryLabelDatabase
    from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
    from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU
    from alex.corpustools.wavaskey import load_wavaskey, save_wavaskey
    from alex.corpustools.semscore import score

    cldb = CategoryLabelDatabase('../data/database.py')
    preprocessing = PTICSSLUPreprocessing(cldb)
    hdc_slu = PTICSHDCSLU(preprocessing, cfg = {'SLU': {PTICSHDCSLU: {'utt2da': as_project_path("applications/PublicTransportInfoCS/data/utt2da_dict.txt")}}})

    test_utterances = load_wavaskey(fn_input, constructor, limit=1000000)

    parsed_das = {}
    for utt_key, utt in sorted(test_utterances.iteritems()):
        if isinstance(utt, Utterance):
            obs = {'utt': utt}
        elif isinstance(utt, UtteranceNBList):
            obs = {'utt_nbl': utt}
        else:
            raise BaseException('Unsupported observation type')

        print '-' * 120
        print "Observation:"
        print utt_key, " ==> "
        print unicode(utt)

        da_confnet = hdc_slu.parse(obs, verbose=False)

        print "Conf net:"
        print unicode(da_confnet)

        da_confnet.prune()
        dah = da_confnet.get_best_da_hyp()

        print "1 best: "
        print unicode(dah)

        parsed_das[utt_key] = dah.da

        if 'CL_' in str(dah.da):
            print '*' * 120
            print utt
            print dah.da
            hdc_slu.parse(obs, verbose=True)

    save_wavaskey(fn_output, parsed_das, trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))


if __name__ == "__main__":
    hdc_slu('./all.trn',    Utterance, './all.trn.hdc.sem')
    hdc_slu('./train.trn',  Utterance, './train.trn.hdc.sem')
    hdc_slu('./dev.trn',    Utterance, './dev.trn.hdc.sem')
    hdc_slu('./test.trn',   Utterance, './test.trn.hdc.sem')
    hdc_slu('./uniq.trn',   Utterance, './uniq.trn.hdc.sem')

