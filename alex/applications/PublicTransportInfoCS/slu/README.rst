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

dict[category_label][category_value][surface_form]



Evaluation
----------

Estimating accuracy of the HDC SLU on ASR 1-best hypothesis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the ``train.trn.hdc.sem`` and ``train.asr.hdc.sem``, the following results were obtained:

::

    (2.7)jurcicek@loki:ptics_slu:~/UFAL-DSG-alex-dev/alex/applications/PublicTransportInfoCS/slu$ ./semscore.py -i train.trn.hdc.sem train.asr.hdc.sem

    The results are based on 941 DAs
    --------------------------------------------------------------------------------
                                Dialogue act  Precision     Recall  F-measure
                                    affirm()      75.00      75.00      75.00
                                       bye()      98.08      73.91      84.30
                      confirm(from_stop="*")       0.00       0.00       0.00
                        confirm(to_stop="*")     100.00       9.09      16.67
                                     hello()      71.43      27.78      40.00
                                      help()       0.00       0.00       0.00
                                inform(="*")      33.33      83.05      47.57
                     inform(alternative="*")     100.00      63.64      77.78
                     inform(from_centre="*")       0.00       0.00       0.00
                       inform(from_stop="*")      70.21      41.77      52.38
                            inform(time="*")     100.00      56.52      72.22
                       inform(to_centre="*")     100.00     100.00     100.00
                         inform(to_stop="*")      89.53      58.78      70.97
                                    negate()      83.33      55.56      66.67
                                      null()      74.55      18.81      30.04
                                     other()      21.30      83.33      33.93
                                    repeat()     100.00      84.62      91.67
                                   reqalts()     100.00      65.00      78.79
                          request(from_stop)     100.00      42.86      60.00
                      request(num_transfers)     100.00      70.59      82.76
                            request(to_stop)     100.00      42.22      59.38
                                   restart()     100.00     100.00     100.00
                                  thankyou()     100.00      78.43      87.91
    --------------------------------------------------------------------------------
    Total precision:  53.29
    Total recall:     53.07
    Total F-measure:  53.18



If the automatic annotations was correct, then we could conclude that the F-measure of the HDC SLU parser on 1-best
result is about 53 %.

::
    **NOTE** that HDC SLU is far from being perfect. Mostly because the CLDB cannot detect all slot values in the
    input text.



Estimating accuracy of the HDC SLU on ASR n-best hypothesis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the ``train.trn.hdc.sem`` and ``train.nbl.hdc.sem``, the following results were obtained:

::

    (2.7)jurcicek@loki:ptics_slu:~/UFAL-DSG-alex-dev/alex/applications/PublicTransportInfoCS/slu$ ./semscore.py -i train.trn.hdc.sem train.nbl.hdc.sem

    The results are based on 941 DAs
    --------------------------------------------------------------------------------
                                Dialogue act  Precision     Recall  F-measure
                                    affirm()      85.71      75.00      80.00
                                       bye()      98.04      72.46      83.33
                      confirm(from_stop="*")       0.00       0.00       0.00
                        confirm(to_stop="*")     100.00       9.09      16.67
                                     hello()      71.43      27.78      40.00
                                      help()       0.00       0.00       0.00
                                inform(="*")      32.39      77.97      45.77
                     inform(alternative="*")     100.00      59.09      74.29
                     inform(from_centre="*")       0.00       0.00       0.00
                       inform(from_stop="*")      72.09      39.24      50.82
                            inform(time="*")     100.00      17.39      29.63
                       inform(to_centre="*")     100.00     100.00     100.00
                         inform(to_stop="*")      89.02      55.73      68.54
                                    negate()      83.33      55.56      66.67
                                      null()      66.67      19.27      29.89
                                     other()      20.09      83.33      32.38
                                    repeat()     100.00      84.62      91.67
                                   reqalts()     100.00      62.50      76.92
                          request(from_stop)     100.00      34.29      51.06
                      request(num_transfers)     100.00      70.59      82.76
                            request(to_stop)     100.00      35.56      52.46
                                   restart()     100.00     100.00     100.00
                                  thankyou()     100.00      78.43      87.91
    --------------------------------------------------------------------------------
    Total precision:  50.62
    Total recall:     50.41
    Total F-measure:  50.51

This is confusing as it looks like that the decoding from n-best lists gives worse results when compared to decoding from
1-best ASR hypothesis.