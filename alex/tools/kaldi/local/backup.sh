#!/bin/sh

# Copyright (c) 2013, Ondrej Platek, Ufal MFF UK <oplatek@ufal.mff.cuni.cz>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License. #


DATE=`date +%F_%T.%N`
name="${EXP_NAME}_${DATE}"
target_dir="Results/$name"

# This is EXAMPLE SCRIPT you are ENCOURAGED TO CHANGE IT!

# Collect the results
local/results.py exp > exp/results.log

mkdir -p "$target_dir"
cp -rf exp  "$target_dir"

echo; echo "DATA successfully copied to $target_dir"; echo

echo "du -hs will tell you the size of stored settings"
du -hs $target_dir
