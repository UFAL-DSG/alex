#!/bin/bash

[ -f path.sh ] && . ./path.sh # source the path.
. utils/parse_options.sh || exit 1;


if [ $# -ne 2 ] ; then
    echo "Usage: $0 <exp-ali-directory> <MLF-dir>";
    exit 1;
fi

ali_dir="$1"
mlf_dir="$2"

echo -e "\nTODO convert\n"
mkdir -p "$mlf_dir"


exit 0
