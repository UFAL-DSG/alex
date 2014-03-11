#!/bin/bash

cd data
cat .gitignore | xargs echo rm

cd ../lm
cat .gitignore | xargs echo rm

cd ../hclg
cat .gitignore | xargs echo rm

cd ../slu
cat .gitignore | xargs echo rm

curdate=`date +%Y%d%m-%H%M%S`
for file in training-log* SLU-* Goog-* qsubmit.* scores-*; do
    mv $file old.$curdate.$file
done
