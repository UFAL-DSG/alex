
Running SLU on collected transcriptions
=======================================

To run SLU on collected transcriptions and obtain more accurate interpretation
(to be used for the NLG CrowdFlower task), you need to perform these steps:

1. Extract texts from the `asr_transcribed.xml` files in the call log directories:

   ``./extract_texts.py call_log_dir > extracted.tsv``


2. Reparse using SLU for the given language:

   ``./reparse_<en|cs>.py extracted.tsv > reparsed.tsv``


3. (Optionally) filter out just abstracted versions of the interpretations:

   ``./abstract.sh reparsed.tsv abstract.tsv``

   These can then be analyzed/sorted etc. and/or fed to the `generate_reply_tasks.py` script for
   the NLG CrowdFlower task.


More information can be found in documentation strings in the respective script files.
