#!/usr/bin/perl

# Takes a list of files with a given extension and produces a file 
# that has this as the first column and a second column with a 
# different extension.
#
# This can be used to create the audio file/mfc file list used 
# when initially coding the speech data.
#
# Copyright 2005 by Keith Vertanen

use strict;

if ( @ARGV < 1 )
{
    print "$0 <list file> [audio file extension] [output extension] [output extension2]\n"; 
    exit(1);
}

# Process arguments.
my ($listFile, $ext, $outExt, $outExt2);
($listFile, $ext, $outExt, $outExt2) = @ARGV;

if (length($ext) <= 0)
{
    $ext = "wav";
}

if (length($outExt) <= 0)
{
    $outExt = "mfc";
}

# Transform the file.
my ($line, $pos, $basename);

open(IN, $listFile);
while ($line = <IN>) 
{
	# Analyze the line into the basename and extension.
	$line =~ s/\n//g;  # XXX Why the 'g' flag?
	$pos = index(lc(line), lc($ext));
	$basename = substr($line, 0, $pos)

	# Print the required fields.
	print $line . " " . $basename . $outExt;
	print " " . $basename . $outExt2 if length($outExt2);
	print "\n";
}


close IN;
