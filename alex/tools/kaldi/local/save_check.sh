#!/bin/bash
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


if [ ! -d "$DATA_ROOT" ]; then
  echo "You need to set \"DATA_ROOT\" variable in your configs to point to the directory to host data"
  exit 1
fi

# make sure that the directories exists
mkdir -p "$MFCC_DIR"
mkdir -p "exp"
mkdir -p "data"

# Copy the current settings to exp directory
cp -r conf exp
cp cmd.sh path.sh exp/conf
git log -1 > exp/conf/git_log_state.log
git diff > exp/conf/git_diff_state.log
