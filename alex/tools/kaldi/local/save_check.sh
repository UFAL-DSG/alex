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

LOCAL=$1
MFCC=$2
EXP=$3

# make sure that the directories exists
mkdir -p "$LOCAL"
mkdir -p "$MFCC"
mkdir -p "$EXP"

# Save the variables set up 
(set -o posix ; set ) > $EXP/bash_vars.log
git log -1 > $EXP/git_log_state.log
git diff > $EXP/git_diff_state.log
