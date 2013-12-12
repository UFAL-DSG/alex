#!/usr/bin/env perl

use strict;
use warnings;
use utf8;
use Treex::Tool::Lexicon::Generation::CS;
use Treex::Tool::Lexicon::CS;
use Math::Cartesian::Product;
use autodie;
use Getopt::Long;
use Treex::Core::Common;
use Treex::Core::Scenario;
use Treex::Core::Document;


my $cases_list = '1,2,4';
GetOptions( 'cases|c=s' => \$cases_list );

if ( @ARGV != 2 ) {
    die("Usage: ./expand_stops.pl [--cases=1,2,4] stops.txt stops.expanded.txt\n");
}

open( my $in, '<:utf8', $ARGV[0] );
open( my $out, ">:utf8", $ARGV[1] );

my $generator = Treex::Tool::Lexicon::Generation::CS->new();
my $scenario_string = "Util::SetGlobal language=cs W2A::CS::Tokenize "
        . "W2A::CS::TagFeaturama lemmatize=1 W2A::CS::FixMorphoErrors";
my $scenario = Treex::Core::Scenario->new( { from_string => $scenario_string } );

log_set_error_level('WARN');

sub analyze_stop {
    my ($source_text) = @_;
    my $document = Treex::Core::Document->new();
    my $bundle   = $document->create_bundle();
    my $zone     = $bundle->create_zone( 'cs', '' );
    $zone->set_sentence($source_text);

    $scenario->apply_to_documents($document);

    my @analysis = ();
    foreach my $bundle ( $document->get_bundles ) {
        my $zone = $bundle->get_zone( 'cs', '' );
        my @tokens = $zone->get_atree()->get_descendants( { ordered => 1 } );
        foreach my $token (@tokens){
            push @analysis, join('|', $token->form, $token->lemma, $token->tag);
        }
    }
    return \@analysis;    
}

# Read each stop and try to inflect it in different cases
my $line_ctr = 0;
while ( my $line = <$in> ) {
    
    chomp $line;
    # skip commented or empty lines
    if ($line =~ /^#/ or $line eq ''){
        next;
    }

    $line_ctr++;
    if ($line_ctr % 10 == 0){
        print STDERR '.';
    }
    my @cases;  # store all inflected form here
    
    # process all possible variant names of the given stop/city
    foreach my $variant (split /\t/, $line){
        
        my @words = @{analyze_stop($variant)};
    
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
                $forms_str =~ s/ ([\.,])/$1/g;  # avoid spaces before comma or period
                push @cases, $forms_str if ( !grep { $_ eq $forms_str } @cases );
            }
            @forms;
        }
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
