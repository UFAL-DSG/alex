#!/bin/bash

if [ -z "$EMAIL" ] ; then
    notify=""
else
    notify="-m abe -M $EMAIL"
fi

mkdir -p logs
logname=logs/`date +"%y-%m-%d-%H_%M_%S"`_$$.log
touch $logname
qsub $notify -cwd -j y -o $logname ./train_voip_cs.sh
tail -f $logname
