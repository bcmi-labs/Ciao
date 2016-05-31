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
# created: 18 Apr 2016 by sergio tomasello <sergio@arduino.org>
#
###

import abc
import serial, time, utils, os
import sys, atexit, termios, io

class CiaoMcu(object):
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def start(self):
		""" Connect to MCU"""
		return

	@abc.abstractmethod
	def stop(self):
		""" Disconnect from MCU"""
		return

	@abc.abstractmethod
	def read(self):
		""" Read a line from MCU"""
		return

	@abc.abstractmethod
	def write(self, status, message, data):
		""" Gets value and create a message to write to the MCU """
		return

	@abc.abstractmethod
	def flush(self):
		""" Flushes data from the buffer """
		return

class StdIO(CiaoMcu):

	def __init__(self, settings, logger):
		self.__handler = None
		self.__settings = settings;
		self.__logger = logger;

	def start(self):
		#return input.read()
		if self.__settings.use_fakestdin:
			print "Starting Ciao in DEBUG MODE"
			#logger.debug("Starting Ciao in DEBUG MODE")
			self.__handler = io.open(settings.basepath + "fake.stdin", "r+b")
		else:
			#disable echo on terminal
			self.__enable_echo(sys.stdin, False)

			#allow terminal echo to be enabled back when ciao exits
			atexit.register(self.__enable_echo, sys.stdin.fileno(), True)
			self.__handler = io.open(sys.stdin.fileno(), "rb")
			#self.__flush_terminal(sys.stdin)
			self.flush()

	def stop(self):
		return

	def read(self):
		return self.__handler.readline()

	def write(self, status, message, data = None):
		output = [ str(status), str(message) ]
		if not data is None:
			data = utils.serialize(data)
			output.append(data.tostring())
		#4 (ASCII) means end trasmit (like newline but via a non-printable char)
		os.write(sys.stdout.fileno(), ";".join(output)+ chr(4))

	# enable/disable echo on tty
	def __enable_echo(self, fd, enabled):
		(iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(fd)
		if enabled:
			lflag |= termios.ECHO
		else:
			lflag &= ~termios.ECHO
		new_attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
		termios.tcsetattr(fd, termios.TCSANOW, new_attr)

	def flush(self):
		termios.tcflush(sys.stdin, termios.TCIOFLUSH)
		sys.stdout.flush()

	# flush stdin before starting service
	# it prevents answering to requests sent before Ciao Core is really up and running
	#def __flush_terminal(self, fd):
	#	termios.tcflush(fd, termios.TCIOFLUSH)

class Serial(CiaoMcu):

	def __init__(self, baseport, baudrate, logger):
		self.__serial = None
		#self.__conn_status = False
		self.__port = None
		self.__baseport = baseport
		self.__baudrate = baudrate
		self.__logger = logger

	def __connect(self):
		try :
			#self.__conn_status = False
			#if not self.__serial is None:
			#	self.__serial.close()
			#	time.sleep(30)

			if not os.path.exists(self.__baseport):
				self.__logger.error(self.__baseport + " not found. Maybe there are problems. Exiting Ciao.")
				exit(1)

			self.__logger.debug("Connecting to " + self.__baseport + " at " + str(self.__baudrate) + " baud")
			self.__serial = serial.Serial(self.__baseport, self.__baudrate, timeout = 0)
			#self.__conn_status = True

		except Exception, e:
			raise ValueError(e)

	def flush(self):
		if not self.__serial is None:
			self.__serial.flush()
			self.__serial.flushInput()
			self.__serial.flushOutput()

	def __kill_ciao(self):
		self.__serial.close()
		utils.kill_connectors_by_pids()
		os.system(' kill -9 `/usr/bin/pgrep -f "python -u ciao.py"` ')

	def start(self):
		self.__connect()

	def stop(self):
		#self.__conn_status = False
		self.__serial.close()

	def read(self):
		#if self.__conn_status:
		try:
			return self.__serial.readline()
		except Exception, e:
			self.__logger.warning("Problems when reading from MCU, trying reconnection...")
			#self.__connect()
			self.__kill_ciao()

	def write(self, status, message, data = None):
		#if self.__conn_status:
		try:
			output = [ str(status), str(message) ]
			if not data is None:
				data = utils.serialize(data)
				output.append(data.tostring())
			send = ";".join(output)+ chr(4)
			for i in send:
				self.__serial.write(i)
		except Exception, e:
			self.__logger.warning("Problems when writing to MCU, trying reconnection...")
			self.__kill_ciao()
			#self.__connect()
