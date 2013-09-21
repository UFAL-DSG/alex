Approach to bootstraping the domain specific language models
============================================================

::

  **WARNING**: Please note that domain specific language models are build in ./alex/applications/*/lm
  This text explains a simple approach to building a domain specific language models, which can be different for every domain.

These tools serve to build domain specific language models (LMs). While an acoustic model can be build domain independent,
the LMs must be domain specific to ensure high accuracy of ASR when the acoustic models are not built on thousands of
hours of speech data.

In general, building an in-domain LM is easy as long as one has enough of in-domain training data. However, when
the in-domain data is scarce, e.g. when deploying a new dialogue system, this task is difficult and the is need for
some bootstrap solution.

Here we approach the problem of building domain specific language models based on three assumptions. First, we assume that
it is relatively easy to collect/handcraft all domain specific words such as bus/tram/metro stops in the domain, e.g.
from some database. Second, we can use some domain in-dependent data for building general LM. Third, we can include
more and more in-domain data as it becomes available.

Therefore, building of a domain specific LM is based on interpolation of a (potentially) handcrafted list of in-domain
words (zero-gram LM), in-domain data (LM), and a general data (LM).

Data for building general LMs
-----------------------------
For for building general LMs, we use the free W2C – Web to Corpus – Corpora available from the LINDAT project at:
https://ufal-point.mff.cuni.cz/repository/xmlui/handle/11858/00-097C-0000-0022-6133-9

- English: https://ufal-point.mff.cuni.cz/repository/xmlui/bitstream/handle/11858/00-097C-0000-0022-6133-9/eng.txt.gz
- Czech: https://ufal-point.mff.cuni.cz/repository/xmlui/bitstream/handle/11858/00-097C-0000-0022-6133-9/ces.txt.gz

Structure of each domain scripts
-------------------------------
Each of the projects should contain:

#. prepare.sh - builds all necessary files for decoding and exports them to the export_models directory
#. test*.sh - test the models under various conditions using the Julius ASR
#. results.sh - computes the HTK like results

Necessary files for the LM
--------------------------

For each domain the LM package should contain:

#. HTK wordnet bigram language model (wdnet_bigram)
#. ARPA trigram language model (arpa_trigram)
#. Dictionary including all words in the language model (dict) using compatible phone set with the
   language specific acoustic model.

   - E.g. cmu_ext_dict_sp_sil for CamInfo and English

Note that the language models are domain specific. This is different to acoustic modelling since the acoustic models are
intended to be domain independent (to make things easier).


CAMINFO
-------
The caminfo directory is a very specific example.  It uses general acoustic model trained for voip (voip_en) and it
builds and test language model for the CamInfo domain. The language model was developed by someone else. Therefore,
it has to be converted into format suitable for the Julius ASR.


AOTB CS
-------
For more details please see :doc:`alex.applications.AlexOnTheBus.lm.README`.



