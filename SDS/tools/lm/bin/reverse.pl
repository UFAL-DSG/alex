#!/usr/bin/perl
while(<>) {
          print join(' ', reverse(split(/[ \t\n]+/))) . "\n";
}
