#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import subprocess
import time
import urllib
import random

import autopath


from alex.corpustools.wavaskey import load_wavaskey, save_wavaskey


def main():
	utterances = load_wavaskey("all.trn", unicode, limit=100000)

	keys = list(utterances.keys())
	random.seed()
	random.shuffle(keys)

	for k in keys:
	    if '_' in utterances[k]:
	        continue

	    url = 'www.google.cz/#q='+urllib.quote_plus(utterances[k].lower().encode('utf8'))

	    browser = subprocess.Popen(['opera', '-nosession', '-nomail', '-noraise', '-geometry', '500x100+0+0', url])
	    time.sleep(random.randint(10, 200))

	    os.system('kill -9 {pid}'.format(pid=browser.pid))


if __name__ == '__main__':
	main()
