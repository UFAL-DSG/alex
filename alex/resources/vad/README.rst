Description of resource files for VAD
=====================================

Please note that to simplify deployment of SDSs, the the VAD is trained to be language independent. That means that VAD
classifies silence (noise, etc.) vs. all sounds in any language.

At this moment, the ``alex/resources/vad/`` has only VAD models build using VOIP audio signal. The created models 
include:

- GMM models
- NN models

More information about the process of creating the VAD models is available in :doc:`alex.tools.vad.README`.

Please note that the NN VAD is much better compared to GMM VAD. Also ``alex/resources/vad/`` stores the models, 
but they should not be checked in the repository anymore. Instead, they should be on the online_update server 
and downloaded from it when they are updated. More on online update is available in
:doc:`alex.applications.ONLINE_RESOURCES_UPDATE`.
