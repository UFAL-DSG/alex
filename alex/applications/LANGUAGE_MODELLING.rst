Approach to bootstraping the domain specific language models
============================================================

::

  **WARNING**: Please note that domain specific language models are build in ./alex/applications/*/lm
  This text explains a simple approach to building a domain specific language models, which can be different for every
  domain.

While an acoustic model can be build domain independent, the language models (LMs) must be domain specific to ensure
high accuracy of the ASR.

In general, building an in-domain LM is easy as long as one has enough of in-domain training data. However, when
the in-domain data is scarce, e.g. when deploying a new dialogue system, this task is difficult and there is a need for
some bootstrap solution.

The approach described here builds on:

#. some bootstrap text - probably handcrafted, which captures the main aspects of the domain
#. LM classes - which clusters words into classes, this can be derived from some domain ontology. For example, all food
   types belong to the FOOD class and all public transport stops stops belong to the STOP class
#. in-domain data - collected using some prototype or final system
#. general out-of-domain data - for example Wikipedia - from which is selected a subset of data, similar to our
   in-domain data

Then a simple process of building a domain specific language model can described as follows:

#. Append bootstrap text to the text extracted from the indomain data.
#. Build a class based language model using the data generated in the previous step and the classes derived from
   the domain ontology.
#. Score the general (domain independent) data using the LM build in the previous step.
#. Select some sentences with the lowest perplexity given the class based language model.
#. Append the selected sentences to the training data generated in the 1. step.
#. Re-build the class based language model.
#. Generate dictionaries.


Data for building general LMs
-----------------------------
To get free general out-of-domain text data, we use the free W2C – Web to Corpus – Corpora available from the
LINDAT project at: https://ufal-point.mff.cuni.cz/repository/xmlui/handle/11858/00-097C-0000-0022-6133-9

- English: https://ufal-point.mff.cuni.cz/repository/xmlui/bitstream/handle/11858/00-097C-0000-0022-6133-9/eng.txt.gz
- Czech: https://ufal-point.mff.cuni.cz/repository/xmlui/bitstream/handle/11858/00-097C-0000-0022-6133-9/ces.txt.gz

Structure of each domain scripts
-------------------------------
Each of the projects should contain:

#. build.py - builds the final LMs, and computes perplexity of final LMs

Necessary files for the LM
--------------------------

For each domain the LM package should contain:

#. ARPA trigram language model (``final.tg.arpa``)
#. ARPA bigram language model (``final.bg.arpa``)
#. HTK wordnet bigram language model (``final.bg.wdnet``)
#. List of all words in the language model (``final.vocab``)
#. Dictionary including all words in the language model using compatible phone set with the
   language specific acoustic model (``final.dict`` - without pauses and ``final.dict.sp_sil`` with short and long pauses)

CamInfoRest
-------
For more details please see :doc:`alex.applications.CamInfoRest.lm.README`.

PTIcs
-------
For more details please see :doc:`alex.applications.AlexOnTheBus.lm.README`.



