#!/usr/bin/env python
# encoding: utf-8


if __name__ == '__main__':
    import autopath
    from alex.utils.config import online_update

    # Description files
    online_update('resources/asr/voip_en/kaldi/results.log')
    online_update('resources/asr/voip_en/kaldi/experiment_bash_vars.log')
    online_update('resources/asr/voip_en/kaldi/alex_gitlog.log')
    online_update('resources/asr/voip_en/kaldi/alex_gitdiff.log')

    # Models
    online_update('resources/asr/voip_en/kaldi/mfcc.conf')
    online_update('resources/asr/voip_en/kaldi/phones.txt')
    online_update('resources/asr/voip_en/kaldi/silence.csl')
    online_update('resources/asr/voip_en/kaldi/tri2b.mdl')
    online_update('resources/asr/voip_en/kaldi/tri2b.tree')
    online_update('resources/asr/voip_en/kaldi/tri2b.mat')
    online_update('resources/asr/voip_en/kaldi/tri2b_bmmi.mdl')
    online_update('resources/asr/voip_en/kaldi/tri2b_bmmi.tree')
    online_update('resources/asr/voip_en/kaldi/tri2b_bmmi.mat')
