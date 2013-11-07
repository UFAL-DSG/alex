#!/usr/bin/perl

# Replaces one pattern with another in a text file
#
# Copyright 2004 by Keith Vertanen
#

use strict;

if ( @ARGV < 3 )
{
    print "$0 <file> <find> <replace>\n";
    exit(1);
}

my $dictFile;
my $find;
my $replace;

($dictFile, $find, $replace) = @ARGV;

open(IN, $dictFile);

my $line;

while ($line = <IN>)
{
  $line =~ s/$find/$replace/g;
  printf $line;
}

close IN;
