
# Converts a word list into a dictionary by looking up the words
# in a provided other superset dictionary.
#
# It should output every variant that was in the dictionary.
#
# Outputs !!UNKNOWN!! for any words we couldn't find in the superset
# dictionary
#
# Optionally can add sentence start and end symbols to top.
#
# Copyright 2005 by Keith Vertanen

use strict;

if ( @ARGV < 3 )
{
    print "$0 <word list> <dictionary> <output file> [sentence start] [sentence end]\n";
    exit(1);
}

my $listFile;
my $dictFile;
my $outFile;
my $sentStart;
my $sentEnd;

($listFile, $dictFile, $outFile, $sentStart, $sentEnd) = @ARGV;

my $line;
my @chunks;
my %words;
my $phones;
my $word;
my $i;

# Read in the dictionary
open(IN, $dictFile);
open(OUT, ">". $outFile);

# See if we need to put sentence start/end symbols at the top
if ($sentStart)
{
    print OUT $sentStart . " [] sil\n";
}
if ($sentEnd)
{
    print OUT $sentEnd . " [] sil\n";
}


while($line = <IN>)
{
    $line =~ s/\n//g;
    $line =~ s/\r//g;

    @chunks = split(/\s{1,}/, $line);

    $word = $chunks[0];

    $phones = "";
    for ($i = 1; $i < scalar @chunks; $i++)
    {
        $phones = $phones . $chunks[$i];
        if (($i + 1) < scalar @chunks)
        {
            $phones = $phones . " ";
        }
    }

    #print "word = '" . $word . "', phones = '" . $phones . "'\n";

    # We store in the hash all the lines corresponding to this word
    $words{$word} = $words{$word} . $word . "\t" . $phones . "\n";
}
close(IN);

open(IN, $listFile);
while($line = <IN>)
{
#    $line =~ s/[\n\s]//g;

    $line =~ s/\n//g;
    $line =~ s/\r//g;

    @chunks = split(/\s{1,}/, $line);

    $word = $chunks[0];

    # Escape any leading apostrophes
    if (index($word, "'") == 0)
    {
        $word = "\\" . $word;
    }

    if ($words{$word})
    {
        print OUT $words{$word};
    }
    else
    {
        print "Unknown word: " . $line . "\n";
        print OUT $line . "\t!!UNKNOWN!!\n";
    }
}
close(IN);
close(OUT);
