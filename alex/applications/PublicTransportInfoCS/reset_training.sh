#!/bin/bash

cd data
cat .gitignore | xargs echo rm

cd ../lm
cat .gitignore | xargs echo rm

cd ../hclg
cat .gitignore | xargs echo rm

cd ../slu
cat .gitignore | xargs echo rm
