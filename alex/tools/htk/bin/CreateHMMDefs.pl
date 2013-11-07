#!/usr/bin/perl

# Create the hmmdefs file by duplicating a prototype HMM model for
# each phone in a list.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 2 )
{
    print "$0 <prototype HMM> <monophone list>\n"; 
    exit(1);
}

my $protoFile;
my $monoFile;

($protoFile, $monoFile) = @ARGV;

open(IN, $protoFile);

# First read in the body of the HMM from the prototype file
my $line;
my $pos;
my $body;
my $inBody = 0;

while ($line = <IN>) 
{
    if (index($line, "BEGINHMM") > 0)
    {
	$inBody = 1;
    }

    if ($inBody)
    {
	$body = $body . $line;
    }
}
close IN;

open(IN, $monoFile);
while ($line = <IN>)
{
    $line =~ s/\n//g;
    $line =~ s/\r//g;

    printf "~h \"" . $line . "\"\n";
    printf $body;
}
close IN;
