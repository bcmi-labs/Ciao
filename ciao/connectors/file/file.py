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
# 	created 28 Apr 2016 - sergio tomasello <sergio@arduino.org>
#
###

import ciaotools, os

# DEFINE CONNECTOR HANDLERS AND FUNCTIONS
write_modes = ["a","w"]

def write_file(file_path, data, mod):
	"""
	Writes a line (which comes from arduino) into a file in the linino os filesystem

	Parameters:
		- mod: file access mode (a: append, w: (over)write)
		- file_path: the path of the file to write into
		- data: the line to write into the file
	"""
	f = get_file(mod, file_path)
	f.write(data + file_eol)
	f.close()

def read_file(file_path, chk):
	"""
	Read the specified file contents and send back to arduino

	Parameters:
		- file_path: the path of the file to read
		- chk: checksum code used by the ciao core to bind the request with the response
	"""
	f = get_file("r", file_path)
	if int(os.path.getsize(f.name)) <= file_rms:
		lines = f.read()

		f.close()
		mcu_res = {
			"checksum" : chk,
			"data" : [file_path, lines]
		}
		ciao_connector.send(mcu_res)

def get_file(mod, file_path):
	'''
	Opens the specified file, in the specified access mod.
	Checks if the specified file path is an relative path or absolute.
	'''
	try:

		#if specified file starts with '.'
		#if specified file starts with "/" means of an absolute path, if not it's a relative path
		if file_path.startswith(".") or  not file_path.startswith(os.sep):
			file_path = os.path.normpath(file_root + os.sep + file_path.lstrip("."))

		#if specified file starts with "/" means of an absolute path, if not it's a relative path
		#if not file_path.startswith(os.sep):
		#	file_path = file_root + os.sep + file_path

		#if the absolute path doesn't exist, create it
		path_name = os.path.dirname(file_path)
		if not os.path.exists(path_name):
			os.makedirs(path_name)

		#if the file in the absolute path doesn't exist, create it
		if not os.path.exists(file_path):
			os.mknod(file_path)

		logger.debug("Specified file: %s"  %file_path)

		if mod in write_modes or mod == 'r':
			f = open(file_path, mod)
			logger.debug("Opened file %s in %s mode:" %(file_path , mod))
			return f

	except Exception, e:
		logger.error(e)

def handler(mcu_req):
	if mcu_req["type"] == "out":
		#entry["data"][0] # file path
		#entry["data"][1] # file content
		#entry["data"][2] # access mode (optional, default 'w')

		# if access mode is not specified, set default write access mode by configuration file
		if len(mcu_req["data"]) <= 2:
			mcu_req["data"].append( file_wam )

		logger.debug(mcu_req)

		write_file(mcu_req["data"][0], mcu_req["data"][1], mcu_req["data"][2])

	elif mcu_req["type"] == "result":
		#entry["data"][0] # file path
		read_file(mcu_req["data"][0], str(mcu_req['checksum']))

# the absolute path of the connector
working_dir = os.path.dirname(os.path.abspath(__file__)) + os.sep

# LOAD CONFIGURATION

# load configuration object with configuration file smtp.conf.json
config = ciaotools.load_config(working_dir)

# load parameters
file_root = config["params"]["root"] if "root" in config["params"] else "/root"
file_eol = config["params"]["eol"] if "eol" in config["params"] else "\n"
file_rl = config["params"]["read_line"] if "read_line" in config["params"] else False
file_rms = config["params"]["read_max_size"] if "read_max_size" in config["params"] else 2048
file_wam = config["params"]["default_write_access_mode"] if "default_write_access_mode" in config["params"] else "w"

# name of the connector
name = config["name"]

# CREATE LOGGER

log_config = config["log"] if "log" in config else None
logger = ciaotools.get_logger(name, logconf=log_config, logdir=working_dir)

# CALL BASE CONNECTOR

#Call a base connector object to help connection to ciao core
ciao_connector = ciaotools.BaseConnector(name, logger, config["ciao"],async=True)

#register an handler to manage data from core/mcu
ciao_connector.receive(handler)

# start the connector thread
ciao_connector.start()
