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

import os, logging, json

#basepath to look for conf/connectors/whatelse
basepath = os.path.dirname(os.path.abspath(__file__)) + os.sep

#configuration dictionary
conf = {
	"core" : "0.1.0",
	"server": {
		"host" : "localhost",
		"port" : 8900
	},
	# path starting with slash will be handled like absolute ones
	"paths": {
		"conf" : "conf/",
		"connectors" : "connectors/"
	},
	"log": {
		"file" : "ciao.log",
		"level" : "debug",
		"format" : "%(asctime)s %(levelname)s %(name)s - %(message)s",
		"maxSize" : 0.1 , # maxSize is expressed in MBytes
		"maxRotate" : 5 # maxRotate expresses how much time logfile has to be rotated before deletion
	},
	"tian": {
		"baud" : 4000000,
		"port" : "/dev/ttySAMD"
	}
}

#map of actions accepted from Ciao Library (MCU-side)
actions_map = {
	"r": "read", #usually requires 2/3 params - connector;action;data(optional)
	"w": "write", #usuallyrequires 3 params - connector;action;data
	"wr": "writeresponse" #usually requires 4 params - connector;action;reference;data
}

#this is the number of default params the MCU will pass to Ciao
base_params = {
	"read" : 2, # connector_name + action
	"write" : 2, # connector_name + action
	"writeresponse" : 3, # connector_name + action + checksum
}

#serialization settings
# ASCII code for GroupSeparator (non-printable char)
entry_separator = chr(30)
# ASCII code for UnitSeparator (non-printable char)
keyvalue_separator = chr(31)

#enable/disable fake.stdin - FOR TESTING PURPOSE
# atm this params has to be set to True only
# if you want to use a file as stdin instead of the real one
use_fakestdin = False

#DO NOT CHANGE ANYTHING BELOW (UNLESS YOU ARE KNOW EXACTLY WHAT YOU'RE DOING)

#adjust some settings about paths
if not conf['paths']['conf'].startswith(os.sep): #relative path
	conf['paths']['conf'] = basepath + conf['paths']['conf']
if not conf['paths']['conf'].endswith(os.sep):
	conf['paths']['conf'] += os.sep
if not conf['log']['file'].startswith(os.sep): #relative path
	conf['log']['file'] = basepath + conf['log']['file']

#adjust settings about logging
DLEVELS = {
	'debug': logging.DEBUG,
	'info': logging.INFO,
	'warning': logging.WARNING,
	'error': logging.ERROR,
	'critical': logging.CRITICAL
}
conf['log']['level'] = DLEVELS.get(conf['log']['level'], logging.NOTSET)
conf['log']['maxSize'] *= 1024*1024 #it's expressed in MBytes but we need bytes

def load_connectors(logger):
	global conf

	conf_path = conf['paths']['conf']
	#loading configuration for connectors
	try:
		conf_list = os.listdir(conf_path)
	except Exception, e:
		logger.debug("Problem opening conf folder: %s" % e)
		return
	else:
		conf['connectors'] = {}
		for conf_file in conf_list:
			if conf_file.endswith("ciao.json.conf"):
				try:
					conf_json = open(conf_path + conf_file).read()
					conf_plain = json.loads(conf_json)
					if 'name' in conf_plain:
						connector_name = conf_plain['name']
					else:
						logger.debug("Missing connector name in configuration file(%s)" % conf_file)
						connector_name = conf_file[:-len(".ciao.json.conf")]
					if "enabled" in conf_plain and conf_plain['enabled']:
						conf['connectors'][connector_name] = conf_plain
						logger.debug("Loaded configuration for %s connector" % connector_name)
					else:
						logger.debug("Ignoring %s configuration: connector not enabled" % connector_name)
				except Exception, e:
					logger.debug("Problem loading configuration file (%s): %s" % (conf_file, e))
		conf['backlog'] = len(conf['connectors'])

def init():
	global conf
	if not conf['paths']['conf'].startswith(os.sep): #relative path
		global basepath
		conf['paths']['conf'] = basepath + conf['paths']['conf']
