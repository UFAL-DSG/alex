#!/usr/bin/perl

# Duplicates each line, creating two columns of the same thing.
# Can be used to create a fake dictionary with each word being
# a phone.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <file>\n"; 
    exit(1);
}

my $fullFile;

($fullFile) = @ARGV;

my $line;
open(IN, $fullFile);
while ($line = <IN>) 
{
	$line =~ s/\n//g;
	$line =~ s/\r//g;

	print $line . "\t" . $line . "\n";
}
close IN;
