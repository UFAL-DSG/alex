#!/usr/bin/perl

# Processes a bunch of file with numbers in columns through a
# template script file.  The template contains !COL1, !COL2, etc
# to indicate where to put the values from the list of numbers
# file.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 2 )
{
    print "$0 <list of numbers> <template script> [limit to]\n";
    exit(1);
}

my $listFile;
my $templateFile;
my $limit;

($listFile, $templateFile, $limit) = @ARGV;

my @template;
my $templateSize = 0;
my $line;
my $i = 0;
my $command = "";
my $pos = 0;

open(IN, $templateFile);
while($line = <IN>)
{
  $template[$templateSize] = $line;
  $templateSize++;
}
close IN;

open(IN, $listFile);

my $count = 0;
my $j;
my @cols;

while ($line = <IN>)
{
  if (($limit ne "") && ($count >= $limit))
  {
    last;
  }

  $line =~ s/\n//g;
  @cols = split(/\s{1,}/, $line);

  for ($i = 0; $i < $templateSize; $i++)
  {
    $command = $template[$i];

    for ($j = 1; $j <= scalar @cols; $j++)
    {
      $command =~ s/!COL$j/$cols[$j - 1]/g;
    }

    system $command;
  }

  $count++;

}

close IN;
