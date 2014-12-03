#!/bin/env python

import os
import sys
import re
import string
import argparse
import hashlib


parser = argparse.ArgumentParser(description = "Sanitize file names in a directory")

parser.add_argument("--md5sum" , help = "Rename files to <md5sum of file>", action = "store_true")
parser.add_argument("directory", help = "Directory to scan")

args = parser.parse_args()

for f in os.listdir(args.directory):
	if os.path.isdir("/".join([args.directory, f])):
		continue

	g = None
	if args.md5sum:
		tmp = hashlib.md5()
		tmp.update(open("/".join([args.directory, f])).read())
		g = tmp.hexdigest()
	else:
		g = filter(lambda x: x in string.printable, f.replace(' ', '_'))

	assert(g)
	if f != g:
		os.rename("/".join([args.directory, f]), "/".join([args.directory, g]))

