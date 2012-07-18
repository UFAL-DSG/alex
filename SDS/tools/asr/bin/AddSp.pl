#!/usr/bin/perl

# Add a sp to the end of everything in a dictionary
# Can optionally also produce a second variant for
# every word that use sil instead of sp at the end.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <dictionary> [add sil variant]\n"; 
    exit(1);
}

my $fullFile;
my $addSil;

($fullFile, $addSil) = @ARGV;

my $line;
open(IN, $fullFile);
while ($line = <IN>) 
{
    $line =~ s/\n//g;
    $line =~ s/\r//g;

    # Make sure the line has some content
    if ($line =~ /\w/)
    {
	if (index($line, "sil") > 0)
	{
	    print $line . "\n";
	}
	else
	{
	    print $line . " sp\n";
	    
	    # See if we are suppose to add a sil variant as well
	    if ($addSil)
	    {
		print $line . " sil\n";
	    }
	}
    }
}
close IN;
