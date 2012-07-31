#!/bin/bash
# Export hmm models
#
# Parameters:
#  1 - Directory name of model to be exported

rm -f -r export_models
mkdir export_models

# copy the original models
cp julius_bigram export_models
cp julius_trigram export_models
cp julius_dict export_models/julius_dict

