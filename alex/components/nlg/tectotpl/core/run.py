#!/usr/bin/env python
# coding=utf-8
#
# Classes related to Treex runs
#
from __future__ import unicode_literals
import getopt
import yaml
import sys
from alex.components.nlg.tectotpl.core import ScenarioException
from alex.components.nlg.tectotpl.core.log import log_info
from alex.components.nlg.tectotpl.tool.cluster import Job
import os.path

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Run(object):
    "Main class, used to parse a scenario and run it."

    JOB_NAME_PREFIX = 'treex-'

    def __init__(self, opts=[]):
        """Initialize the main class by parsing the command arguments
        and creating a scenario object."""
        optlist, args = getopt.getopt(opts, 'hj:')
        # no options and no arguments: display usage
        self.help = not optlist and not args
        self.jobs = 0
        for optname, optarg in optlist:
            if optname == '-h':
                self.help = True  # explicit usage display
            elif optname == '-j':
                self.jobs = int(optarg)
        # store options (not needed?)
        self.optlist = optlist
        # parse scenario, if given
        self.scenario = args and Scenario(args.pop(0)) or None
        # store input files
        self.input_files = args

    def run(self):
        "Run according to the options"
        # display help and exit
        if self.help:
            self.print_usage()
            return
        # execute on cluster
        if self.jobs:
            self.run_on_cluster()
            return
        # run the scenario
        self.scenario.load_blocks()
        for file_name in self.input_files:
            self.scenario.apply_to(file_name)

    def run_on_cluster(self):
        # split input files for different jobs
        job_files = [self.input_files[i::self.jobs] for i in xrange(self.jobs)]
        jobs = [Job(name=self.JOB_NAME_PREFIX + self.scenario.name)]
        work_dir = jobs[0].work_dir
        for jobnum in xrange(1, self.jobs):
            jobs.append(Job(name=self.JOB_NAME_PREFIX + self.scenario.name +
                            '-' + str(jobnum).zfill(2), work_dir=work_dir))
        log_info('Creating jobs ...')
        for job, files in zip(jobs, job_files):
            job.header += "from alex.components.nlg.tectotpl.core.run import Run\n"
            args = [self.scenario.file_path] + \
                    [os.path.abspath(file_path) for file_path in files]
            job.code = "run = Run(" + str(args) + ")\nrun.run()\n"
        log_info('Submitting jobs ...')
        for job in jobs:
            job.submit()
        log_info('Waiting for jobs ...')
        for job in jobs:
            job.wait(poll_delay=10)
        log_info('All jobs done.')

    def print_usage(self):
        print """\
        Usage: ./alex.components.nlg.tectotpl.py [-h] [-j jobs] [scenario file1 [file2...]]
        """


class Scenario(object):
    """This represents a scenario, i.e. a sequence of
    blocks to be run on the data"""

    def __init__(self, scenario_file, global_args={}):
        "Initialize (parse YAML scenario from a file)"
        # initialize global arguments
        self.global_args = global_args
        self.file_path = os.path.abspath(scenario_file)
        self.name = os.path.splitext(os.path.basename(scenario_file))[0]
        # parse scenario
        f = open(scenario_file)
        self.scenario_data = yaml.load(f)
        f.close()
        # check whether scenario contains blocks
        if not self.scenario_data:
            raise ScenarioException('No blocks in scenario')

    def load_blocks(self):
        "Load all blocks into memory, finding and creating class objects."
        self.blocks = []
        for block_no, block_data in enumerate(self.scenario_data, start=1):
            # create the block name and import it
            if '.' in block_data["block"]:
                class_subpath, class_name = block_data["block"].rsplit('.', 1)
                class_subpath += '.'
            else:
                class_subpath, class_name = '', block_data["block"]
            class_package = 'alex.components.nlg.tectotpl.block.' + class_subpath + class_name.lower()
            log_info('Loading block ' + str(block_no) + '/' +
                     str(len(self.scenario_data)) + ': ' + class_name)
            exec('import ' + class_package)
            class_obj = getattr(sys.modules[class_package], class_name)
            # create the block object
            args = self.global_args.copy()
            args.update(block_data.get("args", {}))
            self.blocks.append(class_obj(self, args))
            # load models etc.
            self.blocks[-1].load()
        # TODO check whether the first block is a reader

    def apply_to(self, filename):
        "Apply the whole scenario to a file."
        # the first block is supposed to be a reader which creates the document
        log_info('Processing ' + filename)
        log_info('Applying block 1/' + str(len(self.blocks)) + ': ' +
                 self.blocks[0].__class__.__name__)
        doc = self.blocks[0].process_document(filename)
        # apply all other blocks
        for block_no, block in enumerate(self.blocks[1:], start=2):
            log_info('Applying block ' + str(block_no) + '/' +
                     str(len(self.blocks)) + ': ' + block.__class__.__name__)
            block.process_document(doc)
