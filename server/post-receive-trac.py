#!/usr/bin/env python

# This should work:
#
#    Changed blah and foo to do this or that. Re #10 and #12, and qa #12.
#

import re
import sys
from datetime import datetime

from trac.env import open_environment
from trac.ticket.notification import TicketNotifyEmail
from trac.ticket import Ticket
from trac.ticket.web_ui import TicketModule
from trac.util.datefmt import utc
from trac.versioncontrol.api import NoSuchChangeset

project = sys.argv[1]
refname = sys.argv[2]
describe = sys.argv[3]
describe_tags = sys.argv[4]
rev = sys.argv[5]
author = sys.argv[6]
message = sys.argv[7]

def refs(ticket):
	pass

def qa(ticket):
	if ticket['phase'] == 'Final Fixing':
		ticket['phase'] = 'Final QA'
	else:
		ticket['phase'] = 'Initial QA'
	ticket['owner'] = ''
	ticket['status'] = 'new'

commands = { 're': refs, 'refs': refs, 'qa': qa }
commandPattern = re.compile(r'(?P<action>[A-Za-z]*).?(?P<ticket>#[0-9]+(?:(?:[, &]*|[ ]?and[ ]?)#[0-9]+)*)')
ticketPattern = re.compile(r'#([0-9]*)')
authorPattern = re.compile(r'<(.+)@')
tickets = {}

env = open_environment(project)
for command, ticketList in commandPattern.findall(message):
	if commands.has_key(command.lower()):
		for ticketId in ticketPattern.findall(ticketList):
			tickets.setdefault(ticketId, []).append(commands[command.lower()])

for ticketId, commands in tickets.iteritems():
	db = env.get_db_cnx()

	ticket = Ticket(env, int(ticketId), db)
	for command in commands:
		command(ticket)

	# determine sequence number...
	cnum = 0
	tm = TicketModule(env)
	for change in tm.grouped_changelog_entries(ticket, db):
		c_cnum = change.get('cnum', None)
		if c_cnum and int(c_cnum) > cnum:
			cnum = int(c_cnum)

	username = authorPattern.findall(author)[0]
	now = datetime.now(utc)
	message = "(On {0!s} [changeset:{1!s} {2!s}]) {3!s}".format(refname, rev, describe_tags, message)
	ticket['branch'] = refname
	ticket.save_changes(username, message, now, db, cnum+1)
	db.commit()

	tn = TicketNotifyEmail(env)
	tn.notify(ticket, newticket=0, modtime=now)

