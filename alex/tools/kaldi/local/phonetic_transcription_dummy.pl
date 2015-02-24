#!/usr/bin/perl

use strict;
use warnings;
use utf8;
use Encode;

# $ PhoneticTranscriptionCS.pl [inputFile inputFile2 ...] outputFile
#
# Converts Czech text in CAPITALS in utf8 to Czech phonetic alphabet in
# utf8. All input files will be concatenated into the output file. If no
# input files are specified, reads from STDIN.
#
# If you want the script to operate in another encoding, set the EV_encoding
# environment variable to the desired encoding.
#
# This is a rewrite of "vyslov" shell-script by Nino Peterek and Jan Oldrich Kruza, which was using tools
# written by Pavel Ircing. These are copy-pasted including comments into this
# script.

my $enc = 'utf8';

my $out_fn = pop @ARGV;
if ($out_fn) {
    close STDOUT;
    open STDOUT, '>', $out_fn or die "Couldn't open '$out_fn': $!";
}

my %seen = ();
while (<>) {
    for (decode($enc, $_)) {
#        if (/[^\w\s]/) {
#            chomp;
#            print encode($enc, $_), (' ' x 7), "sp\n";
#            next
#        }
        chomp;
        $_ = uc($_);

        print encode($enc, $_);
        print(' ' x 7);

        $_ = lc($_);
        $_ = join(" ", split(//, $_));

        print encode($enc, $_);
        print "\n";
    }
}

