#!/bin/bash

logname=logs/`date +"%y-%m-%d-%H_%M_%S"`_$$.log
mem=8  # gigabytes


if [ -z "$EMAIL" ] ; then
    notify=""
else
    echo notifying with email
    notify="-m abe -M $EMAIL"
fi

mkdir -p `dirname $logname`
touch $logname

qsub $notify -hard \
  -l mem_free=${mem}g,h_vmem=`expr $mem + $mem`g,act_mem_free=${mem}g \
  -V -cwd -j y -o $logname $@

tail -f $logname
