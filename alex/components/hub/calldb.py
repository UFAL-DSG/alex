#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pylint: disable-msg=E1101

import fcntl
import time
import cPickle as pickle

class CallDB(object):
    """Implements logging of all interesting call stats.
    It can be used for customization of the SDS, e.g. for novice or expert users.
    """
    def __init__(self, cfg, file_name, period = 24*60*60):
        self.cfg = cfg
        self.db_fname = file_name
        self.period = period

    def read_database(self):
        db = dict()
        try:
            self.f = open(self.db_fname, 'r+')
            fcntl.lockf(self.f, fcntl.LOCK_EX)
            db = pickle.load(self.f)
        except (IOError, EOFError):
            pass

        try:
            fcntl.lockf(self.f, fcntl.LOCK_UN)
            self.f.close()
        except AttributeError:
            pass

        if 'calls_from_start_end_length' not in db:
            db['calls_from_start_end_length'] = dict()

        return db

    def open_database(self):
        db = dict()
        try:
            self.f = open(self.db_fname, 'r+')
            fcntl.lockf(self.f, fcntl.LOCK_EX)
            db = pickle.load(self.f)
        except (IOError, AttributeError):
            # the DB file does not exist
            self.f = open(self.db_fname, 'w+')
            fcntl.lockf(self.f, fcntl.LOCK_EX)

        if 'calls_from_start_end_length' not in db:
            db['calls_from_start_end_length'] = dict()

        return db

    def close_database(self, db):
        try:
            self.f.seek(0)
            self.f.truncate(0)
            pickle.dump(db, self.f)
            fcntl.lockf(self.f, fcntl.LOCK_UN)
            self.f.close()
        except AttributeError:
            pass

    def release_database(self):
        try:
            fcntl.lockf(self.f, fcntl.LOCK_UN)
            self.f.close()
        except AttributeError:
            pass

    def log(self):
        db = self.read_database()

        for remote_uri in db['calls_from_start_end_length']:
            num_all_calls, total_time, last_period_num_calls, last_period_total_time = self.get_uri_stats(remote_uri)

            m = []
            m.append('')
            m.append('=' * 120)
            m.append('Remote SIP URI: %s' % remote_uri)
            m.append('-' * 120)
            m.append('Total calls:                  %d' % num_all_calls)
            m.append('Total time (min):             %0.1f' % (total_time/60.0, ))
            m.append('Last period total calls:      %d' % last_period_num_calls)
            m.append('Last period total time (min): %0.1f' % (last_period_total_time/60.0, ))
            m.append('-' * 120)

            m.append('-' * 120)
            m.append('')
            self.cfg['Logging']['system_logger'].info('\n'.join(m))


    def get_uri_stats(self, remote_uri):
        db = self.read_database()

        num_all_calls = 0
        total_time = 0
        last_period_num_calls = 0
        last_period_total_time = 0

        try:
            for s, e, l in db['calls_from_start_end_length'][remote_uri]:
                if l > 0:
                    num_all_calls += 1
                    total_time += l

                    # do counts for last period hours
                    if s > time.time() - self.period:
                        last_period_num_calls += 1
                        last_period_total_time += l
        except:
            pass


        return num_all_calls, total_time, last_period_num_calls, last_period_total_time

    def track_confirmed_call(self, remote_uri):
        db = self.open_database()
        try:
            db['calls_from_start_end_length'][remote_uri].append([time.time(), 0, 0])
        except:
            db['calls_from_start_end_length'][remote_uri] = [[time.time(), 0, 0], ]

        self.close_database(db)

    def track_disconnected_call(self, remote_uri):
        db = self.open_database()

        try:
            s, e, l = db['calls_from_start_end_length'][remote_uri][-1]

            if e == 0 and l == 0:
                # there is a record about last confirmed but not disconnected call
                db['calls_from_start_end_length'][remote_uri][-1] = [s, time.time(), time.time() - s]
        except KeyError:
            # disconnecting call which was not confirmed for URI calling for the first time
            pass

        self.close_database(db)
