Do not distribute the caminfo* files!

RULES
--------------------------

For each domain the package should contain:

1) HTK wordnet bigram language model (wdnet_bigram)
2) ARPA trigram language model (arpa_trigram)
3) Dictionary including all words in the language model (dict) using compatible phone set with the language specific acoustic model.
   - E.g. cmu_ext_dict_sp_sil for CamInfo and English 

Note that the language models are domain specific. This is different to acoustic modelling since the acoustic models are intented to be domain independent (to make things easier).
In general, the acoustic models should also be domain specific or at least adapted but this is going to be left for future.
