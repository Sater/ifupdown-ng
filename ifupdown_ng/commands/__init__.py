"""
ifupdown_ng.commands.__init__  -  Core command-line argument handling
Copyright (C) 2012-2013  Kyle Moffett <kyle@moffetthome.net>

This program is free software; you can redistribute it and/or modify it
under the terms of version 2 of the GNU General Public License, as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with this program; otherwise you can obtain it here:
  http://www.gnu.org/licenses/gpl-2.0.txt
"""

## Futureproofing boilerplate
from __future__ import absolute_import

import argparse
import logging
import os.path
import sys

from ifupdown_ng.autogen.version import VERSION
from ifupdown_ng import logfilter


## This is a namespace used to hold all the parsed command-line arguments
ARGS = argparse.Namespace()


## This simple metaclass maintains a database of all command handler classes
## and provides a main() classmethod that can be used to pick one at runtime.
class CommandHandlerType(type):
	_known_commands = dict()
	_max_command_len = 0

	def __new__(mcs, name, bases, namespace):
		cls = type.__new__(mcs, name, bases, namespace)
		for command in cls.COMMANDS:
			assert command not in mcs._known_commands
			mcs._known_commands[command] = cls
			if len(command) > mcs._max_command_len:
				mcs._max_command_len = len(command)
		return cls

	@classmethod
	def print_usage_error(mcs, command):
		sys.stderr.write('Unknown command: %s\n' % command)
		sys.stderr.write('This application contains code for multiple commands:\n')
		for cmd, desc in sorted(mcs._known_commands.iteritems()):
			sys.stderr.write('  %-*s  -  %s\n' %
				(mcs._max_command_len, cmd, desc))

		sys.stderr.write('''
To select the appropriate command, you may either run this binary via a
symlink or copy such that its name is one of the above commands, or you may
run it via another name that is not in the list and ensure that the very
first argument is one of the above commands.
''')

	@classmethod
	def main(mcs, argv=None):
		## Make a copy of whatever argument list we got
		if argv is None:
			argv = sys.argv
		argv = list(argv)

		## First check to see what command we were called by
		script_path = argv.pop(0)
		command = os.path.basename(script_path)

		## If that's not a known command, then hopefully the user
		## specified one of "ifup", "ifdown", etc as the first
		## argument.
		if not command in mcs._known_commands:
			if argv and argv[0] in mcs._known_commands:
				command = argv.pop(0)
			else:
				mcs.print_usage_error(command)
				sys.exit(2)

		## Now let's actually run that command handler
		cmdh = mcs._known_commands[command](command)
		return cmdh.main(argv)


## Pull out the "main" function to the module so it may be easily imported
main = CommandHandlerType.main


class CommandHandler(object):
	__metaclass__ = CommandHandlerType

	APP_VERSION_COPYRIGHT = (
"""ifupdown-ng version %s
Copyright(C) 2012  Kyle Moffett <kyle@moffetthome.net>

This program is free software; you can redistribute it and/or modify it
under the terms of version 2 of the GNU General Public License, as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with this program; otherwise you can obtain it here:
  http://www.gnu.org/licenses/gpl-2.0.txt
"""
	) % VERSION

	COMMANDS = tuple()

	_LOG_LEVELS = frozenset((
		'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
	))

	def __init__(self, command, **kwargs):
		self.logger = None

		## Create the argument parser
		self.argp = argparse.ArgumentParser(prog=command,
				description=self.COMMANDS[command],
				**kwargs)
		self.command = command

		## Keep track of how many total errors/warnings occur
		self.log_total = logfilter.LogCount()

		## Add common global options
		self.argp.add_argument('-V', '--version', action='version',
			version=self.APP_VERSION_COPYRIGHT,
			help='Display the version and copyright')

		self.argp.add_argument('--log-level',
			choices=self._LOG_LEVELS, default='INFO',
			help='Control which messages are displayed')

	def main(self, argv):
		## Before doing anything that might generate log messages,
		## set up the default global stderr logging handler.
		logging.basicConfig(format='%(levelname)s: %(message)s')
		self.logger = logging.getLogger()
		self.logger.addFilter(self.log_total)

		## Begin redirecting python warnings into the logging system
		logging.captureWarnings(True)

		## Perform argument parsing
		self.argp.parse_args(argv, namespace=ARGS)

		## Set up the global log-level
		self.logger.setLevel(getattr(logging, ARGS.log_level))

		## Now actually execute the command
		return self.execute() or 0

	def execute(self):
		## Must be implemented by a subclass
		raise NotImplementedError()
