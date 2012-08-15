#!/bin/bash
# Export hmm models
#
# Parameters:
#  1 - Directory name of model to be exported

rm -f -r export_models
mkdir export_models

# copy the original models
cp ./temp/julius_bigram export_models
cp ./temp/julius_trigram export_models
cp ./temp/julius_dict export_models/julius_dict

cp ./temp/julius_arpa_bigram export_models
cp ./temp/julius_arpa_rev_bigram export_models
cp ./temp/julius_arpa_trigram export_models
cp ./temp/julius_arpa_rev_trigram export_models
