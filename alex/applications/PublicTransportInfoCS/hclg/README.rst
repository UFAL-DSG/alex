Utils for building decoding graph HCLG
======================================

Summary
-------
The build_hclg.sh script requires following scripts from ``$KALDI_ROOT/egs/wsj/s5/utils``: 
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
