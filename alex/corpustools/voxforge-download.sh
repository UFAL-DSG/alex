#!/bin/bash
#set -e

urls=( #"http://www.repository.voxforge1.org/downloads/SpeechCorpus/Trunk/Audio/Main/16kHz_16bit" 
#"http://www.repository.voxforge1.org/downloads/es/Trunk/Audio/Main/16kHz_16bit/" 
#"http://www.repository.voxforge1.org/downloads/fr/Trunk/Audio/Main/16kHz_16bit/" 
"http://www.repository.voxforge1.org/downloads/de/Trunk/Audio/Main/16kHz_16bit/" 
"http://www.repository.voxforge1.org/downloads/pt/Trunk/Audio/Main/16kHz_16bit/" 
"http://www.repository.voxforge1.org/downloads/it/Trunk/Audio/Main/16kHz_16bit/" 
"http://www.repository.voxforge1.org/downloads/Russian/Trunk/Audio/Main/16kHz_16bit/" 
"http://www.repository.voxforge1.org/downloads/Dutch/Trunk/Audio/Main/16kHz_16bit/" 
)
dirs=( 
#"en" "es" "fr" 
"de" "pt" "it" "ru" "nld")


for (( i=0; i<${#urls[@]}; i++ ));
do
  echo $i, ${urls[$i]}, ${dirs[$i]}

  url=${urls[$i]}
  dir=${dirs[$i]}

  mkdir -p "$dir"
  cd "$dir"

  # download and extract all .tgz files
  wget -nv -O- $url | sed -n 's#.*<a href="\(.*\.tgz\)">.*#'$url'/\1#p' | (
    while read f; do
      wget -nv -O- $f | tar xvz
    done
  )

  cd ..
done
