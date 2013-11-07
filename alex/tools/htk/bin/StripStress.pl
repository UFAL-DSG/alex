#!/usr/bin/perl

# Strips any stress marking in a CMU format dictionary.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <file>\n"; 
    exit(1);
}

my $listFile;

($listFile) = @ARGV;

open(IN, $listFile);

my $line;
my $pos;
my $rest;

while ($line = <IN>) 
{
	$pos = index($line, " ");
	printf substr($line, 0, $pos) . "\t";

	$rest = substr($line, $pos + 1);
	$rest =~ s/[0123456789]//g;
	$rest = lc($rest);

	printf $rest;
}

close IN;
