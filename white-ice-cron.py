#!/usr/bin/env python

import sys
import os
import subprocess
import re
import syslog

#
# Check whether a process with name matching 'name' and cmdline argument matching
# regexp is alive
def process_lives(name, regexp):
	try:
		for p in sorted([x for x in os.listdir("/proc") if re.match('[0-9]+', x)]):
			try:
				if not re.match(r'.*%s$' % name, os.path.realpath("/proc/%s/exe" % p)):
					continue

				cmdline = [x for x in file("/proc/%s/cmdline" % p, "r").read().split('\0') if len(x) > 0]

				if re.match(regexp, cmdline[1]):
					return 0, 1
			except:
				continue

		return 0, 0
	except:
		return 1,0

def main():
	ret, runs = process_lives("python", r'.*([/]*)white-ice$')

	if ret:
		syslog.syslog(syslog.LOG_ERR, "white-ice-cron failed.")

	if ret or runs:
		return ret

	syslog.syslog(syslog.LOG_INFO, "white-ice not running. Starting it.")

	ret = os.execv("/root/bin/white-ice", ["white-ice"])
	sys.exit(ret)


syslog.openlog("white-ice-cron", syslog.LOG_PID, syslog.LOG_USER)
main()

