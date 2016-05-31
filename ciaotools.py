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
# edited: 5 Apr 2016 by sergio tomasello <sergio@arduino.org>
#
###

import os, logging
import socket, asyncore
import json, time, sys, signal

from threading import Thread
from Queue import Queue
from logging.handlers import RotatingFileHandler
from json.decoder import WHITESPACE

# ASCII code Group Separator but sed as alias/substitution for New Line character
NL_CODE = chr(29) #(non-printable char)
NL = "\n"

# ASCII code for File Separator but sed as alias/substitution for Carriage Return
CR_CODE = chr(28) #(non-printable char)
CR = "\r"

# ASCII code for End of Medium but sed as alias/substitution for Tabs
TAB_CODE = chr(25) #(non-printable char)
TAB = "\t"

# ASCII code for Negative Acknowledgement - Used to separate arguments.
# Usually Ciao write, read and CiaoData have only 3/4 arguments and sometimes
# are not enough. Put all togheter the arguments and separate it with this char code.
ARGS_SEP_CODE = chr(21)


class CiaoThread(Thread, asyncore.dispatcher_with_send):

	# "name" must be specified in __init__ method
	name = "ciaothread"

	#ciao server (default) configuration
	host = "127.0.0.1"
	port = 8900
	write_pending = False
	data_pending = None

	def __init__(self, shd, connector_queue, ciao_queue = None):
		Thread.__init__(self)
		self.daemon = True

		asyncore.dispatcher_with_send.__init__(self)
		self.shd = shd

		self.ciao_queue = ciao_queue
		self.connector_queue = connector_queue

		if "name" in self.shd['conf']:
			self.name = self.shd['conf']['name']
		#print self.shd
		# load Ciao (host, port) configuration if present
		# otherwise it will use default
		if "ciao" in self.shd['conf']:
			if "host" in self.shd['conf']['ciao']:
				self.host = self.shd['conf']['ciao']['host']
			if "port" in self.shd['conf']['ciao']:
				self.port = self.shd['conf']['ciao']['port']

		# setup logger
		self.logger = logging.getLogger(self.name)

		while not self.register():
			# IDEAS: here we could add a max_retry param
			time.sleep(10)

	def run(self):
		try:
			asyncore.loop(0.05)
		except asyncore.ExitNow, e:
		#except Exception, e:
			self.logger.error("Exception asyncore.ExitNow, closing CiaoThread. (%s)" % e)

	def stop(self):
		#self.socket.exit()
		#self.socket.close()
		self.join()

	def exit(self):
		raise asyncore.ExitNow('Connector is quitting!')

	# register function (useful when connector start or reconnect)
	def register(self):
		try:
			self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
			params = { "action" : "register", "name" : self.name }
			self.connect((self.host, self.port))
			self.socket.send(json.dumps(params))
		except Exception, e:
			self.logger.error("Problem connecting to Ciao Core server: %s" % e)
			return False
		else:
			return True

	# function to handle socket close
	def handle_close(self):
		self.logger.debug("Handle CLOSE")
		self.close()
		return

	# function to handle error over socket (and close it if necessary)
	def handle_error(self):
		nil, t, v, tbinfo = asyncore.compact_traceback()

		# sometimes a user repr method will crash.
		try:
			self_repr = repr(self)
		except:
			self_repr = '<__repr__(self) failed for object at %0x>' % id(self)

		self.logger.error('CiaoThread - python exception %s (%s:%s %s)' % (
			self_repr, t, v, tbinfo
		))
		self.logger.debug("Handle ERROR")
		return

	# this function is really helpful to handle multiple json sent at once from core
	def decode_multiple(self, data):
		# force input data into string
		string = str(data)
		self.logger.debug("Decoding data from Core: %s" % string)

		# create decoder to identify json strings
		decoder = json.JSONDecoder()
		idx = WHITESPACE.match(string, 0).end()
		self.logger.debug("Decode WHITESPACE match: %d" % idx)

		ls = len(string)
		result = []
		while idx < ls:
			try:
				obj, end = decoder.raw_decode(string, idx)
				self.logger.debug("JSON object(%d, %d): %s" % (idx, end, obj))
				result.append(obj)
			except ValueError, e:
				self.logger.debug("ValueError exception: %s" % e)

				#to force functione exit
				idx = ls
			else:
				idx = WHITESPACE.match(string, end).end()

		return result

	def handle_read(self):
		self.logger.debug("Handle READ")
		#start = time.time()
		data = self.recv(2048)
		# calling decode_multiple (from ciaoThread) to handle multiple string at once from Core
		for data_decoded in self.decode_multiple(data):
			if "status" in data_decoded:
				if self.write_pending:
					self.shd["requests"][data_decoded["checksum"]] = self.data_pending
					self.data_pending = None
					self.write_pending = False
				else:
					self.logger.warning("result msg but not write_pending: %s" % data)
			else:
				self.connector_queue.put(data_decoded)
				#roundtrip = time.time() - start
				#self.logger.debug("time read: %s" % roundtrip)

	# writable/handle_write are function useful ONLY
	# if the connector offers communication from OUTSIDE WORLD to MCU
	def writable(self):
		if not self.shd["loop"]:
			raise asyncore.ExitNow('Connector is quitting!')
		if not self.ciao_queue.empty() and not self.write_pending:
			return True
		return False

	def handle_write(self):
		#self.logger.debug("Handle WRITE")
		#start = time.time()
		entry = self.ciao_queue.get()

		# we wait a feedback (status + checksum) from ciao
		self.write_pending = True
		self.data_pending = entry
		self.send(json.dumps(entry))
		#roundtrip = time.time() - start
		#self.logger.debug("time write: %s" % roundtrip)

class BaseConnector:

	def __init__(self, name, logger, async = True):
		# connector name, used also in ciao library (mcu) to indentify the connector, it will be the same
		self.name = name # probabilmente se lo puo caricare direttamente dal file di configurazione.

		# handler to trigger when data from ciao core are available.
		self.__handler = {}

		# it's a queue which stores commands/data/messages directed to the connector, they come from the mcu.
		self.__queue_to_connector = Queue()

		# it's a queue which stores commands/data/messages directed to the ciao core and then to the mcu.
		self.__queue_to_core = Queue()

		# specify if the data from core/mcu will handled synchronously or asynchronously, by default is asynchronous
		self.__async = async

		# conf object which stores data of the configuration file
		#self.__conf = json.loads( open(self.__cwd + name + ".json.conf" ).read())

		# internal socket parameters used between Ciao core and the connectors
		ciao_conf = {
			"host" : "127.0.0.1",
			"port" : 8900
		}
		# logger object for logging
		#self.__logger = ciaotools.get_logger(self.name, logconf=self.__conf, logdir=self.__cwd)
		self.__logger = logger
		self.__shared = {}
		self.__shared["loop"] = True
		self.__shared["conf"] = {}
		self.__shared["requests"] = {}
		self.__shared["conf"]["ciao"] = ciao_conf
		self.__shared["conf"]["name"] = self.name
		#self.__shared["conf"] = self.__conf

	def set_loop_status(self, status):
		if isistance(status, bool):
			self.__shared["loop"] = status

	def start(self):
		self.__forkProcess()

		__ciaoclient = CiaoThread(self.__shared, self.__queue_to_connector, self.__queue_to_core)
		__ciaoclient.start()

		signal.signal(signal.SIGINT, signal.SIG_IGN) #ignore SIGINT(ctrl+c)
		signal.signal(signal.SIGHUP, self.__signal_handler)
		signal.signal(signal.SIGTERM, self.__signal_handler)

		if self.__async:
			while self.__shared["loop"]:
				if not self.__queue_to_connector.empty():
					entry = self.__queue_to_connector.get()
					self.__logger.info("Entry %s" % entry)
					#trigger
					self.__pre_handling(entry)
				# the sleep is really useful to prevent ciao to cap all CPU
				# this could be increased/decreased (keep an eye on CPU usage)
				# time.sleep is MANDATORY to make signal handlers work (they are synchronous in python)
				time.sleep(0.01) ##rendere configurabile

	# creates a forked process and writes its pid number into a file,
	# used by the ciao core to kill the process
	def __forkProcess(self):
		try:
			pid = os.fork()
			if pid > 0:
				# Save child pid to file and exit parent process
				filename = "/var/run/" + self.name + "-ciao.pid"
				runfile = open(filename, "w")
				runfile.write("%d" % pid)
				runfile.close()
				sys.exit(0)

		except OSError, e:
			self.__logger.critical("%s connector fork failed" % self.name)
			sys.exit(1)

	# Who call this method?
	def __signal_handler(self, signum, frame):
		self.__logger.info("SIGNAL CATCHED %d" % signum)
		self.__shared["loop"] = False

	# push data into the core queue. these data will be sent to the core (arduino/mcu)
	def send(self, entry):
		#for index, item in enumerate(entry["data"]):
		#	entry["data"][index] = item.replace(TAB, TAB_CODE).replace(NL, NL_CODE).replace(CR, CR_CODE)
		self.__queue_to_core.put(entry)

	# receive data back from the core (arduino/mcu), in a sync or async way,
	# depends on handler function and asynchronous argument
	def receive(self, handler = None, timeout = None):
		if not handler is None and self.__async :
			self.__handler = handler
		else :
			if timeout is None :
				return self.__queue_to_connector.get()
			else:
				return self.__queue_to_connector.get(block = True, timeout = timeout)

	def __pre_handling(self, entry):
		for index, item in enumerate(entry["data"]):
			entry["data"][index] = item.replace(TAB_CODE, TAB).replace(NL_CODE, NL).replace(CR_CODE, CR)
		self.__handler(entry)

def load_config(cwd):
	for file_entry in os.listdir(cwd):
		if file_entry.endswith(".json.conf"):
			return json.loads(open(cwd+file_entry).read())

def get_logger(logname, logfile = None, logconf = None, logdir = None):
	#logging (default) configuration
	conf = {
		# level can be: debug, info, warning, error, critical
		"level" : "info",
		"format" : "%(asctime)s %(levelname)s %(name)s - %(message)s",
		# max_size is expressed in MB
		"max_size" : 0.1,
		# max_rotate expresses how much time logfile has to be rotated before deletion
		"max_rotate" : 5
	}

	# MAP
	# log levels implemented by logging library
	# to "readable" levels
	DLEVELS = {
		'debug': logging.DEBUG,
		'info': logging.INFO,
		'warning': logging.WARNING,
		'error': logging.ERROR,
		'critical': logging.CRITICAL
	}

	# LOGGER SETUP
	# join user configuration with default configuration
	if logconf:
		conf.update(logconf)

	# if no logfile specified setup the default one
	if not logfile:
		logfile = logname+".log"

	# if user specifies a directory
	if logdir:
		# make sure the logdir param ends with /
		if not logdir.endswith(os.sep):
			logdir = logdir+os.sep
		logfile = logdir+logfile

	logger = logging.getLogger(logname)
	logger.setLevel(DLEVELS.get(conf['level'], logging.NOTSET))

	# create handler for maxsize e logrotation
	handler = RotatingFileHandler(
		logfile,
		maxBytes=conf['max_size']*1024*1024,
		backupCount=conf['max_rotate']
	)

	# setup log format
	formatter = logging.Formatter(conf['format'])
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	return logger
