#!/usr/bin/env python

import time
import sys

fmt = "%Y-%m-%d"
if len(sys.argv) > 1 and "-f" == sys.argv[1]:
	fmt += "T%H%M%SZ%z"

sys.stdout.write(time.strftime(fmt, time.localtime()) + "\n")
sys.exit(0)

