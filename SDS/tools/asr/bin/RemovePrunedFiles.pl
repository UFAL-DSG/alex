#!/usr/bin/perl

# Checks that every file in the script file is actually in the MLF file.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 2 )
{
    print "$0 <MLF file> <original script file> [output not in]\n"; 
    exit(1);
}

my $MLFFile;
my $scriptFile;
my $posStart;
my $posEnd;
my $line;
my %files;
my $filename;
my $invert;

($MLFFile, $scriptFile, $invert) = @ARGV;

# Read in all the filename lines from the MLF
open(IN, $MLFFile);
while ($line = <IN>) 
{
    $line =~ s/\n//g;
  
  
    $posStart = index($line, "\/");

    if ($posStart > 0)
    {
  $posEnd = index($line, ".lab");
  if ($posEnd == -1)
  {
      $posEnd = index($line, ".rec");
  }

# print $line."\n";
  if ($posEnd > 0)
  {
      $filename = substr($line, $posStart + 1, $posEnd - $posStart - 1);      
      $files{$filename} = 1;
#     print "#" . $filename . "\n";
  }
    }

}
close IN;

open(IN, $scriptFile);
while ($line = <IN>) 
{
    $line =~ s/\n//g;

    $posStart = index($line, "\/");

    if ($posStart >= 0)
    {
  $posEnd = rindex($line, ".mfc");

#        print $line."\n";
  if ($posEnd > 0)
  {
      $filename = substr($line, $posStart + 1, $posEnd - $posStart - 1);

#     print "@" . $filename . "\n";
      
      if ($invert) 
      {
    
    if (!$files{$filename})
    {
        print $line . "\n";
    }
      }
      else
      {
    if ($files{$filename})
    {
        print $line . "\n";
    }
    else
    {
#       print "not found: $filename on $line\n";
    }
      }
  }
    } 
}
close IN;

