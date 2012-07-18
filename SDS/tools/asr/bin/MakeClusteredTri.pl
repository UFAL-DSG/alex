#!/usr/bin/perl

# Creates a HHEd script that will try and cluster each
# of the states in a triphone system.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if (@ARGV < 3)
{
    print "$0 <HHEd command> <threshold> <monophone list> [number output states] [first output state]\n"; 
    exit(1);
}

my $command;
my $threshold;
my $monoFile;
my $line;
my $numStates;
my @outStates;
my $offset;
my $i;

($command, $threshold, $monoFile, $numStates, $offset) = @ARGV;

# Set default values for last two parameters
if (@ARGV == 3)
{
    $numStates = 3;
}
if (@ARGV < 5)
{
    $offset = 2;
}

open(IN, $monoFile);
while ($line = <IN>) 
{
  $line =~ s/\n|\r//g;

  if (length($line) > 0)
  {
      for ($i = 0; $i < $numStates; $i++)
      {
    $outStates[$i] = $outStates[$i] . "$command $threshold \"ST_" . $line . "_" . ($i + $offset) . "_\" {($line,*-$line\+*,$line\+*,*-$line).state[" . ($i + $offset) . "]}\n"
      }
      
  }
}
close IN;

# Now actually output the commands for each set of states
for ($i = 0; $i < $numStates; $i++)
{
    print $outStates[$i];
}


