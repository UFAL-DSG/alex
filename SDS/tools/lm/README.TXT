Here we build domain specific languiage models.

The caminfo directory is a very specific example.  It uses general acoustic model trained for voip (voip_en) and it builds and test language model
for the CamInfo domain. The language model was developed by someone else. Therefore, it has to be converted into format suitable for the Julius ASR.


Each of the projects should contain:
1) prepare.sh - builds all necessary files for decoding and exports them to the export_models directory
2) test*.sh - test the models under various conditions using the Julius ASR
3) results.sh - computes the HTK like results

