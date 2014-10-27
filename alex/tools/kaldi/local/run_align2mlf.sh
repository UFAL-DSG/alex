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

lattice-align-phones --replace-output-symbols=true final.mdl ark:decode/lat.1 ark:phone_aligned100.lats
lattice-1best ark:phone_aligned100.lats ark:- | nbest-to-ctm ark:- 1.ctm
# If you use the --write-lengths=true option to ali-to-phones, you can get
# the information you want, but it's not in ctm format
phones-to-prons

Wrong scheme
 lattice-align-phones final.mdl ark:lat.1 ark,t:phone_aligned.lat
 lattice-1best ark:phone_aligned.lat ark:-| nbest-to-ctm ark:- 1.ctm

echo << EOF
Dans suggestions:
The program lattice-align-phones is not what you want here.  What the
program does is to modify the lattice so the arcs coincide with the phones,
i.e. each arc spans exactly one phone.  But it doesn't care about moving
around the labels on the lattice arcs, which as far as it is concerned
could be words.  The program nbest-to-ctm looks at those labels (which
would normally be words) and these haven't been aligned correctly by
lattice-align-phones.
The way to fix this is either to replace lattice-align-phones with
lattice-align-words, or to replace it with lattice-to-phone-lattice, and
then pipe into lattice-align-words.  The program lattice-to-phone-lattice
actually throws away the labels on the lattice, keeping only the
alignments, and replaces them with the phone labels derived from the
alignments.  In your case it should basically be a no-op as your lattice is
already a phone lattice, but it will shift the labels around in such a way
that lattice-align-words will have an easier time.
By the way, in this pipeline you can move lattice-1best to the beginning
which will make the whole thing more efficient (and will probably remove
the need for the lattice-to-phone-lattice stage).  Be careful that
lattice-1best takes an --acoustic-scale option, and this is important
EOF


echo << EOF
The way to go according Dan
word alignment
lattice-to-1best | lattice-align-words | nbest-to-ctm
To get the phone-level segmentation:
lattice-to-1best | lattice-align-phones --replace-output-symbols=true | nbest-to-ctm

steps/get_train_ctm.sh
EOF


Interesting tools
get-post-on-ali
lattice-align-words-lexicon



exit 0
