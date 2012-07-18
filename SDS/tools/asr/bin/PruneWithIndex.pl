#!/usr/bin/perl

# Prunes files out of a list of *.mfc files that do not
# appear in the WSJ style index file.  This can be used
# to limit training to just the specified set such as
# SI-84.
#
# Copyright 2005 by Keith Vertanen
#

use strict;

if ( @ARGV < 4 )
{
    print "$0 <directory name> <list of mfc files> <WSJ index file> <output file>\n"; 
    exit(1);
}

my $dirName;
my $mfcFile;
my $indexFile;
my $outFile;

($dirName, $mfcFile, $indexFile, $outFile) = @ARGV;

# First read in the valid training files from the index
my $line;
my %filenames;
my $start;
my $end;
my $id;

open(IN, $indexFile);
open(OUT, ">" . $outFile);

my $count;
$count = 0;

while ($line = <IN>) 
{
	$line =~ s/\n//g;
	$line =~ s/\r//g;

	# Ignore comment lines or blank lines
	if ((index($line, "\;") == -1) && (length($line) > 0))
	{
	    # We may pass in a blank dir name if the index file
	    # just lists the filenames.
	    if (length($dirName) > 0)
	    {
		$start = rindex(lc($line), lc($dirName));
	    }
	    else
	    {
		$start = 0;
	    }

	    $end   = rindex($line, ".");
	    
	    if ($end == -1)
	    {
		# Some index files don't have a file extension (WSJ0)
		$end = length($line);
	    }

	    if (($start != -1) && ($end != -1) && ($start < $end))
	    {
		$id = lc(substr($line, $start + length($dirName), $end - $start - length($dirName)));
#		print $id . "\n";

		if ($filenames{$id} == 1)
		{
		    # Index file seems to have some duplicates!
		    print "Duplicate ID of '" . $id . "'\n";
		}

		$filenames{$id} = 1;
		$count++;
	    }
	}
}
close IN;

print "Number in index file: " . $count . "\n";

# Now output just the mfc files that have a matching base name
open(IN, $mfcFile);

while ($line = <IN>)
{
    # If we have a directory name, we use this to match the unique
    # string, otherwise we take what is the right of the last slash.
    if (length($dirName) > 0)
    {
	$start = rindex(lc($line), lc($dirName));
    }
    else
    {
	$start = rindex(lc($line), "/") + 1;
    }

    $end   = rindex($line, ".");

    if (($start != -1) && ($end != -1) && ($start < $end))
    {
	$id = lc(substr($line, $start + length($dirName), $end - $start - length($dirName)));
	print $id . "\n";
	if ($filenames{$id})
	{
	    print OUT $line;
	    $filenames{$id} = 2;
	}
	else
	{
	    print "Not matched: '" . $id . "'\n";
	}
    }
}
close IN;
close OUT;

# Make sure we found everything in the training set we were suppose to
foreach $id (sort keys %filenames)
{
    if ($filenames{$id} < 2)
    {
	print "In index but no mfc file: '" . $id . "'\n";
    }
}
