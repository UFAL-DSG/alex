#!/usr/bin/perl

# Only outputs a source file every so many lines.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 2 )
{
    print "$0 <file> <interval> [inital stride]\n"; 
    exit(1);
}

my $fullFile;
my $interval;
my $i;
my $stride;

$i = 0;
($fullFile, $interval, $stride) = @ARGV;

my $line;
open(IN, $fullFile);
while ($line = <IN>) 
{
	$line =~ s/\n//g;
	$line =~ s/\r//g;

	if (($i + $stride) % $interval == 0)
	{
	    print $line . "\n";
	}

	$i++;
}
close IN;
