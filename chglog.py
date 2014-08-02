#!/usr/bin/env python

import datetime
import re
import os
import sys
import argparse
import pwd
import json
import socket
import smtplib


#
# Padd the string x to length n with whitespaces.
def strpad(x, n):
	return x + " " * (n - len(x))

#
# Return the current time as a padded string
def now():
	tmp = datetime.datetime.now()
	now = datetime.datetime(tmp.year, tmp.month, tmp.day, tmp.hour, tmp.minute, tmp.second).isoformat()

	return strpad(now, len(now) + 4)

#
# Get the name of the user
def user():
	return [pwd.getpwuid(os.getuid()).pw_name]

#
# Get the system hostname
def hostname():
	return socket.gethostname()

#
# Load a json config file
def json_load_config(fn):
	# For convenience we allow Python-style comments in the JSON files. These
	# are removed before presenting the string to the json.loads function.
	descr = " ".join(map(lambda x: re.sub(r'#.*$', r'', x), \
			     open(args.config[0], "r").readlines()))
	try:
		return json.loads(descr)
	except ValueError as e:
		sys.stderr.write(" Error: exception thrown while parsing "
		                 "config file: '%s'\n" % str(e))
		sys.exit(1)

#
# Check user permissions
def check_user_perm(config):
	if not "users" in config.keys():
		return False
	
	for user in config["users"]:
		if os.getuid() == pwd.getpwnam(user):
			return True

	return False

#
# Send a mail
def mail(args, config, chglog, msg):
	if not "to" in config.keys():
		return
	if not isinstance(config["to"], list):
		config["to"] = [config["to"]]

	if not "from" in config.keys():
		config["from"] = "root@%s" % hostname()

	if not "subject" in config.keys():
		config["subject"] = "New entry in %s on host %s" % (chglog, hostname())

	if not "server" in config.keys():
		config["server"] = "localhost"

	srv = smtplib.SMTP(config["server"])

	for to in config["to"]:
		srv.sendmail(config["from"], to, """\
From: %s
To: %s
Subject: %s 

%s
""" % (config["from"], to, config["subject"], msg))

	srv.quit()


parser = argparse.ArgumentParser(description = "Add changelog entry")

parser.add_argument("-c", "--config", \
                    type = str, \
                    nargs = 1, \
                    default = ["/etc/chglog.json"],
                    help = "Configuration file")
parser.add_argument("-u", "--user", \
                    type = str, \
                    nargs = 1, \
                    default = user(), \
                    help = "Name of user appearing in the log")
parser.add_argument("message", \
                    type = str, \
                    help = "Message")

args   = parser.parse_args()
config = json_load_config(args)

msg    = now() + strpad("[%s]" % args.user[0], 20) + args.message + "\n"

try:
	if check_user_perm(config):
		raise Exception("user not permitted")

	if not "chglog" in config.keys():
		raise Exception("config: 'chglog' key missing in configuration file")

	with open(config["chglog"], "a") as f:
		for g in [f, sys.stdout]:
			g.write(msg)

		if "mail" in config.keys():
			mail(args, config["mail"], config["chglog"], msg)
except Exception as e:
	sys.stderr.write(" Error: exception thrown while writing changelog: '%s'\n" % str(e))
	sys.exit(1)

