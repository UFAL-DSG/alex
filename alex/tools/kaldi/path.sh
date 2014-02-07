# Needed for "correct" sorting
export LC_ALL=C

if [[ -z "$KALDI_ROOT" ]] ; then
    echo "KALDI_ROOT need to be set"
    exit 1
fi

# adding Kaldi binaries to path
export PATH=$KALDI_ROOT/src/bin:$KALDI_ROOT/tools/openfst/bin:$KALDI_ROOT/tools/irstlm/bin/:$KALDI_ROOT/src/fstbin/:$KALDI_ROOT/src/gmmbin/:$KALDI_ROOT/src/featbin/:$KALDI_ROOT/src/lm/:$KALDI_ROOT/src/sgmmbin/:$KALDI_ROOT/src/sgmm2bin/:$KALDI_ROOT/src/fgmmbin/:$KALDI_ROOT/src/latbin/:$PWD:$PATH

# creating symlinks to scripts which wraps kaldi binaries
symlinks="$KALDI_ROOT/egs/wsj/s5/steps $KALDI_ROOT/egs/wsj/s5/utils"
for syml in $symlinks ; do
    name=`basename $syml`
    if [ ! -e "$name" ] ; then
        ln -f -s "$syml"
        if [ -e $name ] ; then
            echo "Created symlink $syml -> $name"
        else
            echo "Failed to create symlink $syml -> $name"
            exit 1
        fi
    fi
    export PATH="$PWD/$name":$PATH
done

srilm_bin=$KALDI_ROOT/tools/srilm/bin/
if [ ! -e "$srilm_bin" ] ; then
    echo "SRILM is not installed in $KALDI_ROOT/tools."
    echo "May not be able to create LMs!"
fi
srilm_sub_bin=`find "$srilm_bin" -type d`
for d in $srilm_sub_bin ; do
    export PATH=$d:$PATH
done
