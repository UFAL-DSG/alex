#!/usr/bin/perl
####################################################################
###
### script name : ProcessJuliusOutput.pl
### version: 0.1
### created by: Ken MacLean
### mail: contact@voxforge.org
### Date: 2006.09.12
### Command: perl ./ProcessJuliusOutput.pl
###
### Copyright (C) 2006 Ken MacLean
###
### This program is free software; you can redistribute it and/or
### modify it under the terms of the GNU General Public License
### as published by the Free Software Foundation; either version 2
### of the License, or (at your option) any later version.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
####################################################################

use strict;
my ($line, $label, $filein, $fileout, %seen);
my (@line_array, $line_array);
if (@ARGV != 2) {
  print "usage: $0 filein fileout\n\n";
  exit (0);
}
# read in command line arguments
($filein, $fileout) = @ARGV;

open (FILEIN,"$filein") || die ("Unable to open $filein for reading");
open (FILEOUT,">$fileout") || die ("Unable to open $fileout for writing");

print (FILEOUT "#!MLF!#\n");
while ($line = <FILEIN>) {
  chomp ($line);
  if ($line =~ /input speechfile: /) {
    $line =~ s/input speechfile: //;
    $line =~ s/\.wav/\.rec/;
    $line =~ s/wav\///;
    print (FILEOUT "\"*\/$line\"\n");
  } elsif ($line =~ /input MFCC file: /) {
    $line =~ s/input MFCC file: //;
    $line =~ s/\.mfc/\.rec/;

    my $pos = rindex($line, "/");
    $line = substr($line, $pos+1);
    $line =~ s/mfcc\///;
    print (FILEOUT "\"$line\"\n");
  }
  elsif ($line =~ /sentence1: /) {
    $line =~ s/[^\ ]*sentence1: //;
    $line =~ s/<s> //;
    $line =~ s/ <\/s>//;
    $line =~ s/^\s+//;
    $line =~ s/\s+$//;

    @line_array=split(/\s+/, $line);
    foreach $line_array (@line_array) {
      print (FILEOUT "$line_array\n");
    }
    print (FILEOUT "\.\n");
  }
}
close(FILEIN);
close(FILEOUT);
