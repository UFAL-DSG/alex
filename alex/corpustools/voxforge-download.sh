#!/bin/sh

url=http://www.repository.voxforge1.org/downloads/SpeechCorpus/Trunk/Audio/Main/16kHz_16bit
dir="$1"

if [ $# -eq 0 ]; then
  echo No output directory supplied
  exit 1
fi

mkdir -p "$dir"
cd "$dir"

# download and extract all .tgz files
wget -nv -O- $url | sed -n 's#.*<a href="\(.*\.tgz\)">.*#'$url'/\1#p' | (
  while read f; do
    wget -nv -O- $f | tar xvz
  done
)
