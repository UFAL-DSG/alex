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
- ``*.trn.hdc.sem``: contains automatic annotation
- ``*.asr``: contains ASR 1-best results
- ``*.asr.hdc.sem``: contains automatic annotation
- ``*.nbl``: contains ASR N-best results


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

Estimating accuracy of the HDC SLU on ASR data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the ``train.trn.hdc.sem`` and ``train.asr.hdc.sem``, the following results were obtained:

::

    The results are based on 880 DAs.
    --------------------------------------------------------------------------------
                           Dialogue act item  Precision     Recall    F-score
                                    affirm()      75.00      75.00      75.00
                                       bye()      98.08      75.00      85.00
                      confirm(from_stop="*")     100.00      11.11      20.00
                        confirm(to_stop="*")     100.00       9.09      16.67
                                     hello()      75.00      33.33      46.15
                                inform(="*")      29.55      81.25      43.33
                     inform(alternative="*")     100.00      68.42      81.25
                     inform(from_centre="*")        nan       0.00        nan
                       inform(from_stop="*")      86.89      38.13      53.00
                            inform(time="*")     100.00      56.52      72.22
                       inform(to_centre="*")     100.00     100.00     100.00
                         inform(to_stop="*")      93.90      61.11      74.04
                                    negate()      83.33      55.56      66.67
                                      null()      71.43      16.39      26.67
                                     other()      23.99      87.25      37.63
                                    repeat()     100.00      84.62      91.67
                                   reqalts()     100.00      64.10      78.12
                          request(from_stop)     100.00      42.86      60.00
                      request(num_transfers)     100.00      70.59      82.76
                            request(to_stop)     100.00      42.22      59.37
                                   restart()     100.00     100.00     100.00
                                  thankyou()     100.00      78.00      87.64
    --------------------------------------------------------------------------------

                macro   micro
    --------------------------------------------------------------------------------
    Precision:  54.84   56.02
    Recall:     54.87   55.41
    F-score:    54.85   55.71

If the automatic annotations was correct, then we could conclude that the F-measure of the HDC SLU parser on 1-best
result is about 55 %.

::
    **NOTE** that HDC SLU is far from being perfect. Mostly because the CLDB cannot detect all slot values in the
    input text.