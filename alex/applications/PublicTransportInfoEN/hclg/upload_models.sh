#!/bin/sh
scp ./models/mfcc.conf ./models/tri2b_bmmi.mdl ./models/tri2b_bmmi.mat ./models/HCLG_tri2b_bmmi.fst ./models/INFO_HCLG.txt ./models/silence.csl ./models/words.txt vystadial.ms.mff.cuni.cz:/var/www/download/alex/applications/PublicTransportInfoEN/hclg/models
scp -r ./models/phones vystadial.ms.mff.cuni.cz:/var/www/download/alex/applications/PublicTransportInfoEN/hclg/models
