#!/bin/bash
# "queue.pl" uses qsub.  The options to it are
# options to qsub.  If you have GridEngine installed,
# change this to a queue you have access to.
# Otherwise, use "run.pl", which will run jobs locally
# (make sure your --num-jobs options are no more than
# the number of cpus on your machine.

# export train_cmd="queue.pl -q all.q@a*.clsp.jhu.edu"
# export decode_cmd="queue.pl -q all.q@a*.clsp.jhu.edu"

# # UFAL settings
#mem=2
#  TODO # export train_cmd="queue.pl -hard -l mem_free=${mem}g -l h_vmem=`expr $mem + $mem`g -l act_mem_free=${mem}g"
export train_cmd="queue.pl -V -l mem_free=2G,h_vmem=4G"
#mem=3
#  TODO # export decode_cmd="queue.pl -hard -l mem_free=${mem}g -l h_vmem=`expr $mem + $mem`g -l act_mem_free=${mem}g"
export decode_cmd="queue.pl -V -l mem_free=4G,h_vmem=8G"
export njobs=100


# This is a command to run the code on a CUDA enabled machine at UFAL. We do not have CUDA machines at the cluster.
# You must run the training from a CUDA enabled manchine!
export gpu_cmd=run.pl
export gpu_nj=16

# The number of parallel jobs to be started for some parts of the recipe
# Make sure you have enough resources(CPUs and RAM) to accomodate this number of jobs
#export train_cmd=run.pl
#export decode_cmd=run.pl
#export njobs=6
