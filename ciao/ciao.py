#!/usr/bin/python -u
###
# This file is part of Arduino Ciao
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright 2015 Arduino Srl (http://www.arduino.org/)
#
# authors:
# _giuseppe[at]arduino[dot]org
#
# edited 06 Apr 2016 by sergio@arduino.org
# edited 18 Apr 2016 by andrea@arduino.org
#
###

import io, os
#import sys,
import signal, re
import logging, json
from threading import Thread
import time
#import atexit

import settings
from utils import *
from ciaoconnector import CiaoConnector
import ciaoserver, ciaomcu

#function to handle OS signals
def signal_handler(signum, frame):
	global logger
	global keepcycling
	logger.info("Received signal %d" % signum)
	keepcycling = False

def __kill_connectors():
	#stopping connectors (managed)
	for name, connector in shd.items():
		logger.info("Sending stop signal to %s" % name)
		connector.stop()

#opening logfile
logger = get_logger("ciao")

#loading configuration for connectors
settings.load_connectors(logger)

#check if connectors have been actually loaded
if not "connectors" in settings.conf or len(settings.conf["connectors"]) == 0:
	logger.critical("No connector enabled, exiting.")
	sys.exit(1)

#creating shared dictionary
shd = {}

#get the board model from cpuinfo
board_model = get_board_model()

#kill previous connectors
kill_connectors_by_pids()

#start ciaoserver thread (to interact with connectors)
server = Thread(name="server", target=ciaoserver.init, args=(settings.conf,shd,))
server.daemon = True
server.start()

mcu = None

if board_model == "ARDUINO YUN":
	logger.debug("Ciao MCU Connection starting via standard output")
	mcu = ciaomcu.StdIO(settings, logger)
	mcu.start()
	logger.info("Ciao MCU Connection started via standard output")

elif board_model == "ARDUINO TIAN":
	logger.debug("Ciao MCU Connection starting via serial")
	baud = settings.conf["tian"]["baud"]
	port = settings.conf["tian"]["port"]
	mcu = ciaomcu.Serial(port, baud, logger)
	mcu.start()
	logger.info("Ciao MCU Connection started via serial")

#we start MANAGED connectors after ciaoserver (so they can register properly)
core_version = settings.conf["core"]

for connector, connector_conf in settings.conf['connectors'].items():
	#core_version = settings.conf["core"]
	required_version = connector_conf['core'] if "core" in connector_conf else ">=0.0.0"

	if not ( check_version(required_version, core_version) ):
		logger.error("Required version of Ciao Core [%s] for the connector %s is not compatible with the working Core version [%s]" %(required_version, connector, core_version ))
	else:
		shd[connector] = CiaoConnector(connector, connector_conf, mcu)
		# connector must start after it has been added to shd,
		# it can register only if listed in shd
		shd[connector].start()
		#__attach_connector(connector)

'''
def __attach_connector(connector_name):
	connector_conf = settings.conf['connectors'][connector_name]
	required_version = connector_conf['core'] if "core" in connector_conf else ">=0.0.0"

	if not ( check_version(required_version, core_version) ):
		logger.error("Required version of Ciao Core [%s] for the connector %s is not compatible with the working Core version [%s]" %(required_version, connector, core_version ))
	else:
		shd[connector_name] = CiaoConnector(connector_name, connector_conf, mcu)
		shd[connector_name].start()
'''

#TODO: maybe we can start another thread to control Ciao Core status
#logger.warning(shd)
#variable to "mantain control" over while loop
keepcycling = True

#adding signals management
signal.signal(signal.SIGINT, signal_handler) #ctrl+c
signal.signal(signal.SIGHUP, signal_handler) #SIGHUP - 1
signal.signal(signal.SIGTERM, signal_handler) #SIGTERM - 15

# Before start reading from micro controller, flushes data and cleans the buffer.
# Usually mcu starts to write into buffer before ciao begins to read.
mcu.flush()

while keepcycling:
	try:
		cmd = clean_command(mcu.read())
	except KeyboardInterrupt, e:
		logger.warning("SIGINT received")
	except IOError, e:
		logger.warning("Interrupted system call: %s" %e)
	else:
		if cmd:
			logger.debug("command: %s" % cmd)
			connector, action = is_valid_command(cmd)
			if connector == False:
				if cmd != "run-ciao":
					logger.warning("unknow command: %s" % cmd)
					mcu.write(-1, "unknown_command")
				# else : in this case ciao.py received run-ciao and it must discard the commands
			elif connector == "ciao": #internal commands
				params = cmd.split(";",2)
				if len(params) != 3:
					mcu.write(-1, "unknown_command")
					continue
				if action == "r" and params[2] == "status": #read status
					mcu.write(1, "running")
				elif action == "w" and params[2] == "quit": #stop ciao
					mcu.write(1, "done")
					keepcycling = False
					__kill_connectors()
			elif not connector in settings.conf['connectors']:
				logger.warning("unknown connector: %s" % cmd)
				mcu.write(-1, "unknown_connector")
			elif not connector in shd:
				logger.warning("connector not runnable: %s" % cmd)
				mcu.write(-1, "connector_not_runnable")
			else:
				shd[connector].run(action, cmd)
				'''
				if not connector in shd:
					__attach_connector(connector)
					mcu.write(0, "no_connector")
				else:
					shd[connector].run(action, cmd)
				'''


		# the sleep is really useful to prevent ciao to "cap" all CPU
		# this could be increased/decreased (keep an eye on CPU usage)
		time.sleep(0.01)

logger.info("Exiting")
sys.exit(0)
