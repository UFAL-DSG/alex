
# Creates a list of all combinations of monophones,
# left and right biphones, and triphones.  This
# assume sp is context free, sil is context independent,
# and all others are context dependent.
#
# Copyright 2005 by Keith Vertanen

use strict;

if ( @ARGV < 1 )
{
    print "$0 <monophone list without sp> \n"; 
    exit(1);
}

my $listFile;
my @mono;

($listFile) = @ARGV;

my $line;
open(IN, $listFile);

my $monoCount = 0;

# Output all monophones including sp
while($line = <IN>)
{
    $line =~ s/[\n\r]//g;		

    if (length($line) > 0)
    {
	$mono[$monoCount] = $line;	
	$monoCount++;
	print $line . "\n";
    }
}
close(IN);
print "sp\n";

# Now all possible left biphones
my $i;
my $j;

for ($i = 0; $i < $monoCount; $i++)
{
    for ($j = 0; $j < $monoCount; $j++)
    {
	if ($mono[$j] !~ /sil/)
	{
	    print $mono[$i] . "-" . $mono[$j] . "\n";
	}
    }
}

# Right biphones
for ($i = 0; $i < $monoCount; $i++)
{
    for ($j = 0; $j < $monoCount; $j++)
    {
	if ($mono[$i] !~ /sil/)
	{
	    print $mono[$i] . "+" . $mono[$j] . "\n";
	}
    }
}

# Triphones
my $k;

for ($i = 0; $i < $monoCount; $i++)
{
    for ($j = 0; $j < $monoCount; $j++)
    {
	if ($mono[$j] !~ /sil/)
	{
	    for ($k = 0; $k < $monoCount; $k++)
	    {
		print $mono[$i] . "-" . $mono[$j] . "+" . $mono[$k] . "\n";	
	    }
	}
    }
}








