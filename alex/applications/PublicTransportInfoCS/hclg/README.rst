Utils for building decoding graph HCLG
======================================

Summary
-------
The ``build_hclg.sh`` script formats language model (LM) and acoustic model (AM) 
into files (e.g. HCLG) formated for Kaldi decoders.


The scripts extracts phone lists and sets from lexicon given 
the acoustic model (AM), the phonetic decision tree (tree) and the phonetic dictionary(lexicon).

The script silently supposes the same phone lists 
are generated from lexicon as the these used for training AM.
If they are not the same, the script crashes.

The use case. 
Run the script with trained AM on full phonetic set for given language,
pass the script also the tree used for tying the phonetic set and
also give the script your LM and corresponding lexicon.
The lexicon and the LM should also cover the full phonetic set for given language.


Dependencies
------------
The build_hclg.sh script requires the scripts listed belofw from ``$KALDI_ROOT/egs/wsj/s5/utils``. 
The "utils scripts transitevely uses scripts from ``$KALDI_ROOT/egs/wsj/s5/steps``.
The dependency is solved in ``path.sh`` script which create corresponding symlinks
and adds Kaldi binaries to your system path.

You just needed to set up ``KALDI_ROOT`` root variable and provide correct arguments.
Try to run

Needed scripts from ``utils`` symlinked directory.
* gen_topo.pl 
* add_lex_disambig.pl
* apply_map.pl
* eps2disambig.pl
* find_arpa_oovs.pl
* gen_topo.pl
* make_lexicon_fst.pl
* remove_oovs.pl
* s2eps.pl
* sym2int.pl
* validate_dict_dir.pl
* validate_lang.pl
* parse_options.sh


Scripts from the list use Kaldi binaries,
so you need Kaldi compiled on your system.
The script ``path.sh`` adds Kaldi binaries to the ``PATH``
and also creates symlinks to ``utils`` and ``steps`` directories,
where the helper scripts are located.
You only need to set up ``$KALDI_ROOT`` variable.
