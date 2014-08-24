#!/usr/bin/env python

import sys
import os
import syslog
import subprocess
import re
import time
import datetime
import threading
import signal
import select


# The name "white ice" is a homage to the black ice in W. Gibson's "Burning Chrome"
# short story. Black ice is a countermeasure that kills intrusiors. White ice is thus
# the opposite and a rather harmless and simple intrusion countermeasure.
PROGNAME  = "white-ice"
DEBUG     = False
SSHD_LOG  = "/var/log/secure"
MAX_FAILS = 3

#
# Record of a client
class Client():
	def __init__(self, ip):
		self.ip        = ip
		self.fails     = 0
		self.blocked   = False
		self.rulenum   = -1
		self.blockedat = None

	#
	# Handle a failed login attempt.
	def handle_failure(self):
		global DEBUG
		global MAX_FAILS

		if not DEBUG and self.blocked:
			syslog.syslog(syslog.LOG_WARNING, "Client %s should already be blocked" % self.ip)

		self.fails += 1
		if self.fails > MAX_FAILS:
			self.block()

	#
	# Handle a successfull login.
	def handle_success(self):
		if not DEBUG and self.blocked:
			syslog.syslog(syslog.LOG_WARNING, "Client %s should have been blocked." % self.ip)

		self.fails = 0

	#
	# Block a client at the firewall. Drop all incoming packages. Note that this
	# not only affects traffic direct at port 22 but any connection from the blocked
	# client.
	def block(self):
		if self.blocked:
			return

		ret = iptables_input_block(self.ip)

		if 0 == ret:
			syslog.syslog(syslog.LOG_INFO, "Succesfully blocked %s.\n" % self.ip)
		else:
			syslog.syslog(syslog.LOG_ERR, "Failed to block %s (exit code %d)\n" % (self.ip, ret))
			return

		ret, self.rulenum = iptables_input_rulenum(ip)
		if self.rulenum < 1:
			syslog.syslog(syslog.LOG_WARNING, "Failed to receive rule number for %s.\n" % self.ip)

		self.blocked   = True
		self.blockedat = datetime.datetime.now()

	#
	# Unblock a client. Calling unblock() on a client that has not been block()'ed before is
	# a failure.
	# NOTE: Unblocking is currently not implemented and not properly tested!
	def unblock(self):
		if not self.blocked:
			syslog.syslog(syslog.LOG_ERR, "%s is not blocked. Cannot unblock.\n")
			return

		if self.rulenum < 1:
			syslog.syslog(syslog.LOG_ERR, "Invalid rule number for %s. Cannot unblock.\n" % self.ip)
			return

		ret = iptables_input_unblock(self.rulenum)
		if 0 == ret:
			syslog.syslog(syslog.LOG_INFO, "Succesfully unblocked %s.\n" % self.ip)
		else:
			syslog.syslog(syslog.LOG_ERR, "Failed to unblock %s (exit code %d)\n" % (self.ip, ret))
			return

		self.blocked   = False
		self.blockedat = None
		self.rulenum   = -1

#
# Block all traffic from an IP.
def ipbtables_input_block(ip):
	cmd  = ["iptables", "-I", "INPUT", "1", "-j", "DROP", "-s", self.ip]
	p    = subprocess.Popen(cmd, \
	                        stdout = subprocess.PIPE, \
	                        stderr = subprocess.PIPE)
	o, e = p.communicate()
	ret  = p.wait()

	return ret

#
# Get the rule number by matching the IP.
def iptables_input_rulenum(ip):
	rulenum = -1

	cmd  = ["iptables", "-vnL", "INPUT", "--line-numbers"]
	p    = subprocess.Popen(cmd, \
	                        stdout = subprocess.PIPE, \
	                        stderr = subprocess.PIPE)
	o, e = p.communicate()
	ret  = p.wait()

	if 0 == ret:
		for line in [x for x in map(lambda z: z.strip(), o.split("\n")) if len(x) > 0]:
			cols = [x for x in map(lambda z: z.strip(), line.split()) if len(x) > 0]
			if ip == cols[8]:
				rulenum = int(cols[0])
				break

	return ret, rulenum

#
# Remove an input rule.
def iptables_input_unblock(rulenum):
	if -1 == rulenum:
		return 1

	cmd  = ["iptables", "-D", "INPUT", "d" % rulenum]
	p    = subprocess.Popen(cmd, \
	                        stdout = subprocess.PIPE, \
	                        stderr = subprocess.PIPE)
	o, e = p.communicate()
	ret  = p.wait()

	return ret

#
# Follow the content of the logfile
def spawn_tail_on_log():
	if DEBUG:
		# For debugging it can be helpful to cat the full logfile and retrace the steps
		return subprocess.Popen(["cat", SSHD_LOG], stdout = subprocess.PIPE)
	else:
		# Use -F option to make sure we can handle log rotation
		return subprocess.Popen(["tail", "-n0", "-F", SSHD_LOG], stdout = subprocess.PIPE)

#
# Process a single line from the log
def process_line(line):
	if '' == line:
		return

	# Regular expressions and corresponding client actions
	handlers = [
		[r'.*sshd.*Failed password.*from ([0-9\.]+) port.*'   , lambda z: z.handle_failure()],
		[r'.*sshd.*Accepted password.*from ([0-9\.]+) port.*' , lambda z: z.handle_success()],
		[r'.*sshd.*Accepted publickey.*from ([0-9\.]+) port.*', lambda z: z.handle_success()]
	]

	for regexp, handler in handlers:
		match = re.match(regexp, line)
		if match:
			ip = match.group(1)

			if not ip in clients.keys():
				clients[ip] = Client(ip)

			handler(clients[ip])

def main():
	global QUIT

	try:
		# Mapping from IPv4 addresses to clients
		clients = {}

		tail = spawn_tail_on_log()
		while 1:
			ready, _, _ = select.select([tail.stdout], [], [], 1)
			
			if 1 == QUIT:
				break
			if 1 == len(ready):
				process_line(tail.stdout.readline())

	finally:
		tail.terminate()
		tail.wait()

#
# daemonize
if not DEBUG:
	os.umask(0)
	pid = os.fork()
	if 0 != pid:
		sys.exit(0)
	
	os.chdir("/")
	os.setsid()
	
	sys.stdin  = open(os.devnull, "w")
	sys.stderr = open(os.devnull, "w")
	sys.stderr = open(os.devnull, "w")

QUIT = 0

def handlesig(signum, frame):
	global QUIT
	QUIT = 1

signal.signal(signal.SIGQUIT, handlesig)
signal.signal(signal.SIGINT , handlesig)
signal.signal(signal.SIGTERM, handlesig)


syslog.openlog(PROGNAME, 0, syslog.LOG_AUTH)
main()

