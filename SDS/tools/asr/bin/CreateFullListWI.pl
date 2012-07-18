#!/usr/bin/perl

# Using a dictionary, create the full list of all possible
# monophones, left and right biphones, and triphones that
# could be needed in a word internal triphone system.
#
# This replaces using HDMan which doesn't seem to include
# everything that is needed.  Generating all possible
# phones is overkill and maybe is causing trouble?
#
# Also makes sure the sp and sil phones are in there.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <dictionary without sp or sil>\n"; 
    exit(1);
}

my $fullFile;
my @chunks;

($fullFile) = @ARGV;

my $line;
my $i;
my $center;
my $left;
my $right;
my %added;
my $output;

open(IN, $fullFile);
while ($line = <IN>) 
{ 
	$line =~ s/\n//g;
	$line =~ s/\r//g;

	@chunks = split(/\s{1,}/, $line);

	for ($i = 1; $i < scalar @chunks; $i++)
	{
	    $center = $chunks[$i];
	    $left = "";
	    $right = "";

	    # Figure out what phone is to the left or right of this
	    # one (there might not be one).
	    if ($i > 1)
	    {
		$left = $chunks[$i - 1];
	    }

	    if ($i < (scalar @chunks - 1))
	    {
		$right = $chunks[$i + 1];
	    }

	    $output = "";
	    if (length($left) > 0)
	    {
		$output = $output . $left . "-";
	    }

	    $output = $output . $center;

	    if (length($right) > 0)
	    {
		$output = $output . "+" . $right;
	    }

	    # Only print a unique phone once
	    if ($added{$output} != 1)
	    {
		print $output . "\n";
		$added{$output} = 1;
	    }
	}

}
close IN;

if ($added{"sil"} != 1)
{
    print "sil\n";
}

if ($added{"sp"} != 1)
{
    print "sp\n";
}
