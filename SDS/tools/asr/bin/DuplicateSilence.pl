#!/usr/bin/perl

# Duplicates the sil model and renames it sp.  
#
# This version creates a sil model that has three states
# just like sil.  We will tie each of the states but
# allow sp to skip completely with a transition from state
# 1 to 5.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <hmmdef file>\n"; 
    exit(1);
}

my $protoFile;

($protoFile) = @ARGV;

open(IN, $protoFile);

# First read in the body of the HMM from the prototype file
my $line;
my $inSil = 0;
my $silStateBody = "";

while ($line = <IN>) 
{
    if (index($line, "\"sil\"") > 0)
    {
	$inSil = 1;
    }
    elsif ($inSil)
    {
	$silStateBody = $silStateBody . $line;
	
	if (index($line, "ENDHMM") > 0)
	{
	    $inSil = 0;
	}
    }

    printf $line;	
}
close IN;

printf "~h \"sp\"\n";
printf $silStateBody . "\n";



