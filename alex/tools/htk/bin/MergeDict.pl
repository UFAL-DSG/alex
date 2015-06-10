#!/usr/bin/perl

# Merges two dictionaries and outputs in alphabetical order.
#
# Copyright 2005 by Keith Vertanen

use strict;

if ( @ARGV < 2 )
{
    print "$0 <dict1> <dict2>\n";
    exit(1);
}

my $dict1;
my $dict2;

($dict1, $dict2) = @ARGV;

open(IN, $dict1);

my $line;
my $pos;
my $rest;
my $word;

my %words;
my $firstChar;
my $newPart;

# Read in the first dictionary.
while ($line = <IN>) 
{
    if (index($line, "#") != 0) 
	{
        $pos = index($line, "\t");
        $word = substr($line, 0, $pos);

        if (length($word) > 0)
        {
            $rest = substr($line, $pos + 1);
            $rest =~ s/[\n\r]//g;
            $rest = lc($rest);
        }

        # We may already have a pronunciation for this word
        # so we'll just add a second line to the output part.
        $newPart = $word . "\t" . $rest . "\n";
        
        # Only add if we don't have something identical for this word.
        if (index($words{$word}, $newPart) == -1)
        {
            $words{$word} = $words{$word} . $word . "\t" . $rest . "\n";
        }
	}
}

close IN;

open(IN, $dict2);

# Read in the second dictionary.
while ($line = <IN>) 
{
    if (index($line, "#") != 0) 
	{
        $pos = index($line, "\t");
        $word = substr($line, 0, $pos);

        if (length($word) > 0)
        {
            $rest = substr($line, $pos + 1);
            $rest =~ s/[\n\r]//g;
            $rest = lc($rest);
        }

        # We may already have a pronunciation for this word
        # so we'll just add a second line to the output part.
        $newPart = $word . "\t" . $rest . "\n";
        
        # Only add if we don't have something identical for this word.
        if (index($words{$word}, $newPart) == -1)
        {
            $words{$word} = $words{$word} . $word . "\t" . $rest . "\n";
        }
	}
}

foreach $word (sort keys %words)
{
    if (length($words{$word}) > 0)
    {
        print $words{$word};
    }
}

close IN;
