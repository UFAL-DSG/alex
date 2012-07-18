#!/usr/bin/perl

# Outputs a HHEd script that will clone all the monophones in
# a list to produce a new triphone model where all the
# transition matrices of models with the same central phone
# are tied.  
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 2 )
{
    print "$0 <monophone list> <output triphone file>\n"; 
    exit(1);
}

my $monoFile;
my $triFile;
my $line;

($monoFile, $triFile) = @ARGV;

print "CL " . $triFile . "\n";

open(IN, $monoFile);
while ($line = <IN>) 
{
	$line =~ s/\n|\r//g;

	if (length($line) > 0)
	{
	    print "TI T_$line {(*-$line+*,$line+*,*-$line).transP}\n";
	}
}
close IN;


