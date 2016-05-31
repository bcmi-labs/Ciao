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
# _andrea[at]arduino[dot]org
# _giuseppe[at]arduino[dot]org
#
#
###

import os, sys, signal, socket
from thread import *
import ciaotools as ciao
import BaseHTTPServer

class HTTPServer(BaseHTTPServer.BaseHTTPRequestHandler):

	def do_GET(self):

		# Response to a GET request
		self.send_response(200)
		self.send_header("Content-type", "text/plain")
		self.end_headers()

		request = self.path[1:]  		# remove "/" from self.path (ex: from /arduino/digital/13/1 to arduino/digital/13/1)
		if '/' in request:
 			service = request[:request.index('/')] # parse the service (ex: arduino )
			if "arduino" in service:
			 	message = request[request.index('/')+1:] # parse the command to MCU (ex: digital/13/1)
				mcu_response = {"data": message}
				ciao_connector.send(mcu_response)
				reply = ""
				try:
					mcu_request = ciao_connector.receive(timeout = restserver_timeout)
					if mcu_request['type'] == "response":
						reply = str(mcu_request['data'][0])
				except:
					reply = "timeout"
				self.wfile.write(reply+'\r\n')
			else:
				self.wfile.write("No such file or directory")
		else:
			self.wfile.write("No such file or directory")

	#override BaseHTTPServer log method
	def log_message(self, format, *args):
		logger.debug("request %s" % format%args )

def restserver_handler(conn, config,logger):

	message = conn.recv(1024)
	reply = ""
	if message != "" :
	 	mcu_response = {"data" : [str(message).rstrip('\r\n')]}
	 	ciao_connector.send(mcu_response)
		mcu_request = ciao_connector.receive(timeout = restserver_timeout)
		if mcu_request['type'] == "response":
		 	reply = str(mcu_request['data'][0])
	conn.send(reply+'\r\n')
	conn.close()

def internal_httpserver_connect()	:

	# socket connection with the lua webserver on port 5555
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			s.bind(('localhost', 5555))
		except socket.error as msg:
			logger.error('Bind failed. Error Code : '+ str(msg[0]) +' Message ' + msg[1])
			sys.exit()
		#Start listening on socket
		logger.info("REST server connector started")
		s.listen(10)
		while True :
		 	conn, addr = s.accept()
		 	start_new_thread(restserver_handler ,(conn, config,logger,))
			#restserver_handler (conn, shd,logger)

	except Exception, e:
		s.close()
		logger.info("Exception while creating REST server: %s" % e)
		#sys.exit(1)

	else:
		s.close()
		logger.info("REST server connector is closing")
		#sys.exit(0)

def httpserver_connect()	:
	httpserver_address = ('', restserver_port)
	httpserver = BaseHTTPServer.HTTPServer(httpserver_address, HTTPServer)
	logger.info("REST server connector started")
	while True:
		try:
			httpserver.handle_request()
		except Exception, e:
			logger.error("Exception while creating REST server: %s" % e)
	httpserver.server_close()

# the absolute path of the connector
working_dir = os.path.dirname(os.path.abspath(__file__)) + os.sep

# LOAD CONFIGURATION

# load configuration object with configuration file restserver.conf.json
config = ciao.load_config(working_dir)
restserver_port = config["params"]["port"] if "port" in config["params"] else 80
restserver_timeout = config["params"]["timeout"] if "timeout" in config["params"] and not config["params"]["timeout"] == 0 else None

# name of the connector
name = config["name"]

# CREATE LOGGER

log_config = config["log"] if "log" in config else None
logger = ciao.get_logger(name, logconf=log_config, logdir=working_dir)

# CALL BASE CONNECTOR

#Call a base connector object to help connection to ciao core
ciao_connector = ciao.BaseConnector(name, logger, async = False)

# start the connector thread
ciao_connector.start()

# Initialize httpserver
if restserver_port is 80:
	internal_httpserver_connect()
else:
	httpserver_connect()
