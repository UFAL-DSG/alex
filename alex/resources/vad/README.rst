Description of resource files for VAD
=====================================

Please note that to simplified deployment of SDS the the VAD is trained to be language independent. That means that VAD
classifies silence vs. all sounds in any language.

At this moment, the ``alex/resources/vad/ has only VAD models build using VOIP audio signal. The created models include:

- GMM models
- NN models

More information about the process of creating the VAD models is available in :doc:`alex.tools.vad.README`.
