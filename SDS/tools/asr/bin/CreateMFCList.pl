#!/usr/bin/perl

# Takes a list of files with a given extension and produces a file 
# that has this as the first column and a second column with a 
# different extension.
#
# This can be used to create the audio file/mfc file list used 
# when initially coding the speech data.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 1 )
{
    print "$0 <list file> [audio file extension] [output extension] [output extension2]\n"; 
    exit(1);
}

my $listFile;
my $ext;
my $outExt;
my $outExt2;

($listFile, $ext, $outExt, $outExt2) = @ARGV;

if (length($ext) <= 0)
{
    $ext = "wav";
}

if (length($outExt) <= 0)
{
    $outExt = "mfc";
}

open(IN, $listFile);

my $line;
my $pos;
my $lowerline;

while ($line = <IN>) 
{
  $line =~ s/\n//g;
  $lowerline = lc($line);

  $pos = index($lowerline, lc($ext));
  printf $line . " ";

  $line = substr($line, 0, $pos) . $outExt;
  printf $line;

  if (length($outExt2) > 0)
  {
      print " ";
      $line = substr($line, 0, $pos) . $outExt2;
      printf $line;
  }
  
  printf "\n";
}


close IN;
