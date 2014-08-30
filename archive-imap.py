#!/usr/bin/env python2

import imaplib
import re
import time
import datetime
import os
import sys
import argparse
import getpass
import hashlib


now = datetime.datetime.now()

parser = argparse.ArgumentParser(description = "Download e-mails from IMAP server for archiving.")

parser.add_argument("-H", "--host"  , nargs = 1, required = True)
parser.add_argument("-u", "--user"  , nargs = 1, required = True)
parser.add_argument("-p", "--passwd", nargs = 1)
parser.add_argument("-i", "--inbox" , nargs = 1, required = True)
parser.add_argument("-T", "--trash" , nargs = 1, required = True)
parser.add_argument("-o", "--outdir", nargs = 1, required = True)
parser.add_argument("--older-than"  , nargs = 1, required = True, type = int)

args = parser.parse_args()
args = vars(args)

if not os.path.isdir(args["outdir"][0]):
	raise Exception("Directory '%s' does not exist." % args["outdir"][0])

if "passwd" in args.keys():
	pwd = args["passwd"][0]
else:
	pwd = getpass.getpass()

ctx = imaplib.IMAP4_SSL(args["host"][0])

ok, _ = ctx.login(args["user"][0], pwd)
if "OK" != ok:
	raise Exception("IMAP login failed.")

ok, _ = ctx.select(args["inbox"][0])
if "OK" != ok:
	raise Exception("Accessing inbox '%s' failed." % args["inbox"][0])

IDX_DATE      = 0
IDX_TIMESTAMP = 1
IDX_UID       = 2
IDX_HEADER    = 3

messages = {}

ok, data = ctx.uid("search", None, "ALL")
if "OK" != ok:
	raise Exception("search failed.")

for uid in data[0].split():
	ok, h = ctx.uid("fetch", uid, '(BODY.PEEK[HEADER])')
	if "OK" != ok:
		raise Exception("fetch failed.")

	header = {}
	tmp = [x for x in map(lambda x: x.strip(), h[0][1].split('\r\n')) if x]
	i   = 0
	while i < len(tmp):
		assert(re.search(r'([^ ]+):( .*|$)', tmp[i]))
		line = tmp[i]
		i += 1
		while i < len(tmp) and not re.search(r'([^ ]+):( .*|$)', tmp[i]):
			line += tmp[i]
			i += 1

		x = re.search(r'([^ ]+):(.*)', line)
		header[x.group(1).lower().strip()] = x.group(2).strip()

	tmp = re.search(r'[^ ]+, (.*)', header["date"])
	if tmp:
		date = tmp.group(1)
	else:
		date = header["date"]

	tmp  = date.split()
	
	# FIXME We need a more generic way to handle this
	if   3 == len(tmp[3].split(":")):
		fmt = "%d %b %Y %H:%M:%S"
	elif 2 == len(tmp[3].split(":")):
		fmt = "%d %b %Y %H:%M"
	
	date = datetime.datetime.strptime(" ".join(tmp[0:4]), fmt)
	
	if len(tmp) > 4:
		# FIXME We need a more generic way to handle this
		if "EDT" == tmp[4]:
			date = date + datetime.timedelta(hours = -4)
		else:
			date = date + datetime.timedelta(hours = int(tmp[4][0:3]))

	if header["message-id"] in messages.keys():
		messages[header["message-id"]].append([date, date, uid, header])
	else:
		messages[header["message-id"]] = [[date, date, uid, header]]

# Update the timestamp of messages in a thread to ensure that we do
# not delete messages in threads that are relevant
for _, msglist in messages.iteritems():
	for msg in msglist:
		if not "in-reply-to" in msg[IDX_HEADER]:
			continue
		
		k = msg[IDX_HEADER]["in-reply-to"]
	
		if not k in messages.keys():
			continue
	
		for x in messages[k]:
			if msg[IDX_DATE] > x[IDX_DATE]:
				x[IDX_DATE] = msg[IDX_DATE]

timediff = int(args["older_than"][0])
purged   = 0

for _, msglist in messages.iteritems():
	for msg in msglist:
		if (timediff < 0) or ((now - msg[IDX_TIMESTAMP]) > datetime.timedelta(days = timediff)):
	 		ok, w = ctx.uid("fetch", msg[IDX_UID], '(BODY[])')
	 		if "OK" != ok:
	 			raise Exception("Fetching the body failed.")

			tmp = hashlib.md5()
			tmp.update(w[0][1])
			d = tmp.hexdigest()

			f = args["outdir"][0] + "/" + d + ".eml"
			if os.path.isfile(f):
				if w[0][1] != open(f).read():
					raise Exception("File '%s' exists but content differs." % f)
			
			open(f, "w").write(w[0][1])

			ok, w = ctx.uid("copy", msg[IDX_UID], args["trash"][0])
			if "OK" != ok:
				raise Exception("Copy to trash '%s' failed." % args["trash"][0])

			ok, _ = ctx.uid("store", msg[IDX_UID], "+FLAGS", "(\\Deleted)")
			if "OK" != ok:
				raise Exception("Delete failed.")

			try:
				print(msg[IDX_HEADER]["subject"])
			except:
				print("-")

			purged += 1

if purged > 0:
	ok, _ = ctx.expunge()
	if "OK" != ok:
		raise Exception("Expunge failed.")

	print("Purged %d emails from '%s'." % (purged, args["inbox"][0]))

ok, _ = ctx.close()
if "OK" != ok:
	raise Exception("Close failed.")

ctx.logout()

