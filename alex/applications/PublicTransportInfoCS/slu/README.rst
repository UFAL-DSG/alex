Building a SLU for the PTIcs domain
===================================

Available data
--------------

At this moment there we have only data which were automatically generated using handcrafted SLU (HDC SLU) on the
transcribed audio. In general, the quality of the annotation is decent. However, manual annotation is needed.

The data can be prepared using the ``prapare_data.py`` script. It assumes that there exist the ``indomain_data`` directory
with links to directories with ``asr_transcribed.xml`` files. Then it uses these files to extract transcriptions
and generate automatic transcriptions using the PTICSHDCSLU parser from the ``hdc_slu.py`` file.

The script generates the following files:

- ``*.trn``: contains manual transcriptions
- ``*.trn.hdc.sem``: contains automatic annotation from transcriptions using handcrafted SLU
- ``*.asr``: contains ASR 1-best results
- ``*.asr.hdc.sem``: contains automatic annotation from 1-best ASR using handcrafted SLU
- ``*.nbl``: contains ASR N-best results
- ``*.nbl.hdc.sem``: contains automatic annotation from n-best ASR using handcrafted SLU


Mapping surface forms to category labels
----------------------------------------

In an utterance:

- there can be multiple surface forms in an utterance
- surface forms can overlap
- a surface form can map to multiple category labels

Then when detecting surface forms / category labels in an utterance:

#. find all existing surface forms / category labels and generate a new utterance with for every found surface form and
   category label (called abstracted), where the original surface form is replaced by its category label

   - instead of testing all surface forms from the CLDB from the longest to the shortest in the utterance, we test
     all the substrings in the utterance from the longest to the shortest

#. for every abstracted utterance
   - replace


Evaluation
----------

Estimating accuracy of the HDC SLU on ASR 1-best hypothesis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the ``train.trn.hdc.sem`` and ``train.asr.hdc.sem``, the following results were obtained:

::

    (2.7)jurcicek@loki:ptics_slu:/ha/home/jurcicek/UFAL-DSG-alex-dev/alex/applications/PublicTransportInfoCS/slu$ ../../../corpustools/semscore.py -i all.trn.hdc.sem all.asr.hdc.sem
    The results are based on 1177 DAs
    --------------------------------------------------------------------------------
                                Dialogue act  Precision     Recall  F-measure
                                       ack()      66.67     100.00      80.00
                                    affirm()      77.78      77.78      77.78
                                       bye()      98.18      72.00      83.08
                               canthearyou()     100.00      73.33      84.62
                      confirm(from_stop="*")     100.00      25.00      40.00
                        confirm(to_stop="*")       0.00       0.00       0.00
                     confirm(trans_type="*")       0.00       0.00       0.00
                  deny(centre_direction="*")       0.00       0.00       0.00
                         deny(from_stop="*")       0.00       0.00       0.00
                                     hello()      80.00     100.00      88.89
                                      help()     100.00      88.89      94.12
                                inform(="*")      30.26      79.73      43.87
                     inform(alternative="*")      96.67      59.18      73.42
                            inform(ampm="*")       0.00       0.00       0.00
                inform(centre_direction="*")     100.00     100.00     100.00
                        inform(date_rel="*")     100.00     100.00     100.00
                       inform(from_stop="*")      91.57      36.71      52.41
                            inform(task="*")     100.00     100.00     100.00
                        inform(time_rel="*")     100.00      56.25      72.00
                         inform(to_stop="*")      93.68      46.35      62.02
                      inform(trans_type="*")       0.00       0.00       0.00
                                    negate()      83.33      45.45      58.82
                                      null()      71.43      11.83      20.30
                                     other()      11.46      88.71      20.30
                                    repeat()      92.31      80.00      85.71
                          request(from_stop)     100.00      52.63      68.97
                      request(num_transfers)     100.00      71.43      83.33
                            request(to_stop)     100.00      36.96      53.97
                                   restart()     100.00      80.00      88.89
                                  thankyou()     100.00      75.47      86.02
    --------------------------------------------------------------------------------
    Total precision:  51.31
    Total recall:     50.52
    Total F-measure:  50.91

If the automatic annotations were correct, we could conclude that the F-measure of the HDC SLU parser on 1-best
results is about 51 %.


Estimating accuracy of the HDC SLU on ASR n-best hypothesis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the ``train.trn.hdc.sem`` and ``train.nbl.hdc.sem``, the following results were obtained:

::

    (2.7)jurcicek@loki:ptics_slu:/ha/home/jurcicek/UFAL-DSG-alex-dev/alex/applications/PublicTransportInfoCS/slu$ ../../../corpustools/semscore.py -i all.trn.hdc.sem all.nbl.hdc.sem
    The results are based on 1177 DAs
    --------------------------------------------------------------------------------
                                Dialogue act  Precision     Recall  F-measure
                                       ack()      66.67     100.00      80.00
                                    affirm()      87.50      77.78      82.35
                                       bye()      98.15      70.67      82.17
                               canthearyou()     100.00      60.00      75.00
                      confirm(from_stop="*")     100.00      25.00      40.00
                        confirm(to_stop="*")       0.00       0.00       0.00
                     confirm(trans_type="*")       0.00       0.00       0.00
                  deny(centre_direction="*")       0.00       0.00       0.00
                         deny(from_stop="*")       0.00       0.00       0.00
                                     hello()      80.00     100.00      88.89
                                      help()     100.00      88.89      94.12
                                inform(="*")      29.63      75.68      42.59
                     inform(alternative="*")      97.56      54.42      69.87
                            inform(ampm="*")       0.00       0.00       0.00
                inform(centre_direction="*")     100.00      50.00      66.67
                        inform(date_rel="*")     100.00     100.00     100.00
                       inform(from_stop="*")      92.41      35.27      51.05
                            inform(task="*")     100.00     100.00     100.00
                        inform(time_rel="*")     100.00      34.38      51.16
                         inform(to_stop="*")      93.33      43.75      59.57
                      inform(trans_type="*")       0.00       0.00       0.00
                                    negate()      83.33      45.45      58.82
                                      null()      55.56      11.83      19.51
                                     other()      10.74      88.71      19.16
                                    repeat()      92.31      80.00      85.71
                          request(from_stop)     100.00      44.74      61.82
                      request(num_transfers)     100.00      71.43      83.33
                            request(to_stop)     100.00      32.61      49.18
                                   restart()     100.00      80.00      88.89
                                  thankyou()     100.00      75.47      86.02
    --------------------------------------------------------------------------------
    Total precision:  48.53
    Total recall:     47.78
    Total F-measure:  48.15

This is confusing as it looks like that the decoding from n-best lists gives worse results when compared to decoding from
1-best ASR hypothesis.

Evaluation of TRN model
~~~~~~~~~~~~~~~~~~~~~~~

The TRN model is trained on transcriptions and evaluated on both transcriptions and the ASR output from dev and test data.

::

    DEV and TEST data size is about 120 utterances.

    TRN model on TRN DEV data

    Total precision:  90.40
    Total recall:     89.68
    Total F-measure:  90.04

    TRN model on TRN TEST data

    Total precision:  91.41
    Total recall:     92.13
    Total F-measure:  91.76

    TRN model on ASR DEV data

    Total precision:  44.54
    Total recall:     42.06
    Total F-measure:  43.27

    TRN model on ASR TEST data

    Total precision:  48.33
    Total recall:     45.67
    Total F-measure:  46.96

One can see that the performance of the TRN model on TRN dev and test data is **NOT** 100 % perfect. This is probably due to
the mismatch between the train, dev, and test data sets. Once more training data will be available, we can expect better
results.



Evaluation of ASR model
~~~~~~~~~~~~~~~~~~~~~~~

The ASR model is trained on transcriptions and evaluated on both transcriptions and the ASR output from dev and test data.

::

    ASR model on TRN DEV data

    Total precision:  81.75
    Total recall:     81.75
    Total F-measure:  81.75

    ASR model on TRN TEST data

    Total precision:  77.60
    Total recall:     76.38
    Total F-measure:  76.98

    ASR model on ASR DEV data

    Total precision:  59.68
    Total recall:     58.73
    Total F-measure:  59.20

    ASR model on ASR TEST data

    Total precision:  59.68
    Total recall:     58.27
    Total F-measure:  58.96

On can see that the ASR model scores worse on the TRN DEV and TRN TEST data when compared to the TRN model. This is
expected result. The good thing is that the **ASR model scores significantly better** on the ASR DEV and ASR TEST data when
compared to *the TRN model*. Even more, the the **ASR model scores significantly better** on the ASR DEV and ASR TEST data when
compared to *the HDC SLU model* when evaluated on the ASR data. The improvement is about 8 % increase in F-measure absolute.

This shows that SLU trained on the ASR data sets can be beneficial.

Evaluation of NBL model
~~~~~~~~~~~~~~~~~~~~~~~

The NBL model is trained on transcriptions and evaluated on both transcriptions and the NBL output from dev and test data.

::

    NBL model on TRN DEV data

    NBL model on TRN TEST data

    NBL model on ASR DEV data


    NBL model on ASR TEST data

TODO: The experiments