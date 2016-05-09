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
# Copyright 2016 Arduino Srl (http://www.arduino.org/)
#
# authors:
# 	created 5 May 2016 - sergio tomasello <sergio@arduino.org>
#
###

import ciaotools as ciao
import os, subprocess

# DEFINE CONNECTOR HANDLERS AND FUNCTIONS

def run_command(command, arguments, chk):
	"""
	Run a command in the Linino Shell and get back the value to the MCU

	Parameters:
		- command: the command to be executed
		- arguments: array of arguments to pass at the command
	"""
	#create a response for the microcontroller
	mcu_response = { "checksum" : chk }
	try:
		# arguments array
		if command:
			#get arguments
			args = get_arguments(command, arguments, array=False)

			# run command
			process = subprocess.Popen(args, cwd = shell_cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

			# get output or error
			output, error = process.communicate()
			process.wait()

			# get the exit code
			exitcode = process.returncode

			if output :
				mcu_response["data"] = [str(exitcode), output.strip()]
				logger.debug("Shell OUTPUT for command '%s %s' is: %s" %(command, arguments, output))
			elif error :
				mcu_response["data"] = [str(exitcode), error.strip()]
				logger.warning("Shell ERROR for command '%s %s' is: %s" %(command, arguments, output))
			else :
				mcu_response["data"] = [str(exitcode), ""]
		else:
			logger.debug("Empty command passed to connector: ignored!")
			mcu_response["data"] = [str(-1), "Empty command passed to connector: ignored!"]

	except Exception, e:
		logger.error(e)
		mcu_response["data"] = [str(-1), "Error during command execution"]

	# cut data at allowed max size
	mcu_response["data"][1] = mcu_response["data"][1][:shell_rms]

	# send mcu response object back to the mcu
	ciao_connector.send(mcu_response)

def get_arguments(cmd, arguments, array=False):
	if array:
		#push the command into 'args' array
		args = [cmd]
		# split arguments by ciao separator char to obtain each single arguments
		for arg in arguments.split(ciao.ARGS_SEP_CODE):
			if arg.strip():
				args.append(arg)
			else:
				logger.debug("Empty arguments passed to connector: ignored!")
		return args
	else :
		return [cmd + " " + arguments.replace(ciao.ARGS_SEP_CODE, " ")]

def handler(mcu_req):
	if mcu_req["type"] == "result":
		#mcu_req["data"][0] # command
		#mcu_req["data"][1] # arguments
		if len(mcu_req) == 2:
			logger.debug(mcu_req["data"])
			logger.debug("2")
			args = mcu_req["data"][1]
		else:
			logger.debug("1")
			args = ""

		run_command(mcu_req["data"][0], args, mcu_req["checksum"])

# the absolute path of the connector
working_dir = os.path.dirname(os.path.abspath(__file__)) + os.sep

# LOAD CONFIGURATION

# load configuration object with configuration file smtp.conf.json
config = ciao.load_config(working_dir)

# load parameters
shell_cwd = config["params"]["working_directory"] if "working_directory" in config["params"] else "/root"
shell_rms = config["params"]["read_max_size"] if "read_max_size" in config["params"] else 1024

# name of the connector
name = config["name"]

# CREATE LOGGER

log_config = config["log"] if "log" in config else None
logger = ciao.get_logger(name, logconf=log_config, logdir=working_dir)

# CALL BASE CONNECTOR

#Call a base connector object to help connection to ciao core
ciao_connector = ciao.BaseConnector(name, logger, config["ciao"], async=True)

#register an handler to manage data from core/mcu
ciao_connector.receive(handler)

# start the connector thread
ciao_connector.start()
