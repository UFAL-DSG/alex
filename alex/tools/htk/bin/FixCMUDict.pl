#!/usr/bin/perl

# Prepares a HTK style dictionary based on the original
# from CMU.  Does the following:
#    Strips any stress marking in a CMU format dictionary.
#    Makes the phones lowercase.
#    Eliminates the (#) notation for words with multiple pronunciations.
#    Eliminates comment lines.
#    Sorts alphabetically by words.
#    Escapes leading non-alphanumeric characters with '\'.
#    Makes sure there aren't identical pronunciations of the same word.
#    Changes erroneous "e" phone to "eh".
#
# Can optionally add a string to the end of each pronunciation (like sp).
#
# Copyright 2005 by Keith Vertanen

use strict;

if ( @ARGV < 1 )
{
    print "$0 <file> [add to end]\n"; 
    exit(1);
}

my $listFile;
my $addToEnd;

($listFile, $addToEnd) = @ARGV;

open(IN, $listFile);

my $line;
my $pos;
my $rest;
my $word;

my %words;
my $firstChar;
my $newPart;

while ($line = <IN>) 
{
  if (index($line, "#") != 0 and index($line, ";") != 0) 
  {
    $pos = index($line, " ");
    $word = substr($line, 0, $pos);
    $word =~ s/\([123456789]\)//g;

    $firstChar = substr($line, 0, 1);
    
		# See if we need to escape this word.
    if (($firstChar !~ /[A-Z|a-z|0-9|\s]/) && (length($line) > 0))
    {
      $word = "\\" . $word;
      # print "blah " . $word . "\n";
    }

    if (length($word) > 0)
    {
      $rest = substr($line, $pos + 1);
      $rest =~ s/[0123456789]//g;
      $rest =~ s/[\n\r]//g;
      $rest = lc($rest);
      $rest =~ s/^\s+//;
      $rest =~ s/\s+$//;

			# Convert the 'e' phone to 'eh'.
      $rest =~ s/\s(e\s)/ eh /g;

      if (length($addToEnd) > 0)
      {
        $rest = $rest . " " . $addToEnd;
      }
        
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
