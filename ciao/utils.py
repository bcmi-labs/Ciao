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
###

import os, sys, time, logging
import tty #, termios
import re, array
import socket
import hashlib
import logging
from logging.handlers import RotatingFileHandler

import settings

# setup logger
def get_logger(logname):

	logger = logging.getLogger(logname)
	logger.setLevel(settings.conf['log']['level'])

	# create handler for maxsize e logrotation
	handler = RotatingFileHandler(
		settings.conf['log']['file'],
		maxBytes=settings.conf['log']['maxSize'],
		backupCount=settings.conf['log']['maxRotate']
	)

	# setup log format
	formatter = logging.Formatter(settings.conf['log']['format'])
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	return logger

#COMMAND FUNCTIONS
def clean_command(command):
	return command.rstrip()

def is_valid_command(command):
	#a valid command must contain at least two fields: connector and action
	elements = command.split(";", 2)
	if len(elements) >= 2 and elements[1] in settings.actions_map:
		return elements[:2]
	return False, False

#SERIALIZATION FUNCTIONS
# serialize passed dict/list, atm it works only for one level object not nested ones
def serialize(data):
	s = array.array("B")
	entries = []
	if isinstance(data, list):
		for e in data:
			entries.append(escape(e))
	elif isinstance(data, dict):
		for k, v in data.items():
			entries.append(settings.keyvalue_separator.join([escape(k), escape(v)]))
	else:
		entries.append(escape(data))
	s.fromstring(settings.entry_separator.join(entries))
	return s

# unserialize passed dict/list, atm it works only for one level object not nested ones
def unserialize(source, from_array = True):
	#create a clone of original array or a new one from a string
	if from_array:
		data = array.array("B", source)
	else:
		data = array.array("B")
		for c in source:
			data.append(ord(c))

	#identifying data type
	try:
		index = data.index(ord(settings.keyvalue_separator))
		result = {}
	except ValueError, e:
		try:
			index = data.index(ord(settings.entry_separator))
			result = []
		except ValueError, e:
			result = []

	#converting bytearray into object
	addr, size = data.buffer_info()
	count = 0
	if isinstance(result, dict):
		params = ["",""]
		param_index = 0
		while count < size:
			pick = data.pop(0)
			count +=1
			if pick == ord(settings.keyvalue_separator):
				param_index = 1
				params[param_index] = ""
			elif pick == ord(settings.entry_separator):
				result[escape(params[0], False)] = escape(params[1], False)
				param_index = 0
				params = ["", ""]
			else:
				params[param_index] += chr(pick)
		if params[0] != "":
			result[escape(params[0], False)] = escape(params[1], False)
	else:
		entry = ""
		while count < size:
			pick = data.pop(0)
			count +=1
			if pick == ord(settings.entry_separator):
				result.append(escape(entry, False))
				entry = ""
			else:
				entry += chr(pick)
		result.append(escape(entry, False))
	return result

# escape/unescape string for serialization procedure
def escape(s, encode = True):
	if encode:
		return s.encode('unicode-escape')
	else:
		return s.decode('unicode-escape')

# calculate (unique)? checksum from a string
def get_checksum(msg, is_unique = True):
	if not is_unique:
		msg = str(time.time()) + msg
	return hashlib.md5(msg.encode('unicode-escape')).hexdigest()

# get the board name/model
def get_board_model():
	import subprocess
	return subprocess.check_output(['awk','''/machine/ {print $3,$4}''','/proc/cpuinfo']).strip('\n').upper()

# check version

def check_version(core_req_ver_num, core_ver_num):
	global logger
	operator = re.sub("[0-9.]", "", core_req_ver_num) #get operators
	core_req_ver_num = re.sub("[^0-9.]", "", core_req_ver_num) #get numbers
	#core_ver_num > core_req_ver_num => 1
	#core_ver_num = core_req_ver_num => 0
	#core_ver_num < core_req_ver_num => -1
	comp = __compare(core_ver_num, core_req_ver_num)
	#logger.info("VERSION CORE REQUIRED: %s - OPERATOR: %s - VERSION CORE CURRENT %s" % (core_req_ver_num, operator, core_ver_num))

	if operator == "=":
		if comp == 0:
			return True
		else:
			return False
	elif operator == ">":
		if comp == 1:
			return True
		else:
			return False
	elif operator == "<":
		if comp == -1:
			return True
		else:
			return False
	elif operator == ">=":
		if comp >= 0:
			return True
		else:
			return False
	elif operator == "<=":
		if comp <= 0:
			return True
		else:
			return False

def __compare(v1, v2):
	def normalize(v):
		return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
	return cmp(normalize(v1), normalize(v2))

def kill_connectors_by_pids():
	import fnmatch
	for ciaofile in os.listdir('/var/run/'):
		if fnmatch.fnmatch(ciaofile, '*ciao.pid'):
			cf = open('/var/run/'+ciaofile, "r")
			pid = cf.readline()
			os.system("kill -9 " + pid)
			os.remove(cf.name)
