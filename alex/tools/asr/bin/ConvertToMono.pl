#!/usr/bin/perl
#
# Converts a triphone MLF file back to a monophone one.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <triphone MLF>\n"; 
    exit(1);
}

my $fullFile;

($fullFile) = @ARGV;

my $line;
my $start;
my $end;
my @chunks;

open(IN, $fullFile);
while ($line = <IN>) 
{
	$line =~ s/\n//g;
	$line =~ s/\r//g;

	@chunks = split(/\s{1,}/, $line);

	if (scalar @chunks >= 3)
	{
	    $line = $chunks[2];
	}

	if ($line !~ /\"/)
	{
	    $start = index($line, "-");
	    $end   = index($line, "+");

	    if ($start < 0)
	    {
		$start = 0;
	    }
	    else
	    {
		$start++;
	    }
	    
	    if ($end < 0)
	    {
		$end = length($line) - 1;
	    }
	    else
	    {
		$end--;
	    }
	    
	    print substr($line, $start, $end - $start + 1) . "\n";
	}
	else
	{
	    print $line . "\n";
	}

}
close IN;
