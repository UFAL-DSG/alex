#!/usr/bin/env perl

use strict;
use warnings;
use utf8;
use Treex::Tool::Lexicon::Generation::CS;
use Math::Cartesian::Product;
use autodie;
use Getopt::Long;

my $cases_list = '1,2,4';
GetOptions( 'cases|c=s' => \$cases_list );

if ( @ARGV != 2 ) {
    die("Usage: ./gen_stops.pl [--cases=1,2,4] stops.txt stops.expanded.txt\n");
}

# Lemmatize & tag all stops and pipe the output in here
my $command = "treex -Lcs Read::Sentences from='" . $ARGV[0] . "'"
    . " W2A::CS::Tokenize W2A::CS::TagFeaturama lemmatize=1 W2A::CS::FixMorphoErrors"
    . " Write::AttributeSentences layer=a attributes='form lemma tag' |";

open( my $in, $command );
open( my $out, ">:utf8", $ARGV[1] );
binmode( $in, ":utf8" );

my $generator = Treex::Tool::Lexicon::Generation::CS->new();

# Read each stop and try to inflect it in different cases
while ( my $line = <$in> ) {
    chomp $line;

    my @words = split /\s+/, $line;
    my @cases;

    # try all needed cases
    foreach my $case (split /[, ]/, $cases_list) {

        my @forms;
        my $prevtag = '';

        # try inflecting each word in nominative not following a noun in nominative
        # (only if current case is not nominative)
        foreach my $word (@words) {

            my ( $form, $lemma, $tag ) = split /\|/, $word;

            if ( $tag =~ /^....1/ and $prevtag !~ /^NN..1/ and $case ne '1' ) {

                my $newtag = $tag;
                $newtag =~ s/^(....)1/$1$case/;
                $newtag =~ s/.$/./;

                # -ice: test add both sg. and pl. versions
                if ( $form =~ /ice$/ and $tag =~ /^...S/ ) {
                    $newtag =~ s/^(...)./${1}[SP]/;
                }

                # retrieve the inflection form(s)
                my @newforms = $generator->forms_of_lemma( $lemma, { tag_regex => $newtag } );

                if (@newforms) {
                    # preserve capitalization
                    @newforms = map { substr( $form, 0, 1 ) . substr( $_->get_form(), 1 ) } @newforms;
                }

                # fallback to uninflected (if form not found in the dictionary)
                else {
                    print STDERR "Cannot inflect: $form, $lemma, $tag\n";
                    @newforms = ($form);
                }

                push @forms, \@newforms;
            }
            else {
                push @forms, [$form];
            }
            $prevtag = $tag;
        }

        # merge all variants of the same case (+ avoid repeating)
        cartesian {
            my $forms_str = join( ' ', @_ );
            push @cases, $forms_str if ( !grep( /^$forms_str$/, @cases ) );
        }
        @forms;
    }
    print {$out} join( ";", @cases ), "\n";
}

__END__

=encoding utf8

=head1 NAME

expand_stops.pl -- PID stop inflection using Treex (http://ufal.mff.cuni.cz/treex)

=head1 DESCRIPTION

Inflecting PID stops in all cases using Treex (morphological analyzer,
morphological generator & tagger for Czech).

=head1 USAGE

./gen_stops.pl [--cases=1,2,4] stops.txt stops.expanded.txt

Cases default to 1,2,4 (nominative, genitive, accusative).

=head1 AUTHOR

Ondřej Dušek

=head1 COPYRIGHT AND LICENSE

Copyright © 2013 by Institute of Formal and Applied Linguistics, Charles University in Prague

Distributed under the Apache 2.0 license
