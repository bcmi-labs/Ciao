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

import os, sys, signal, httplib
import ciaotools as ciao
import BaseHTTPServer

def http_request(url, method, data, chk):

	try:
		#execute http request
		conn = httplib.HTTPConnection(url);
		conn.request(method, data)

		# read http response
		response = conn.getresponse()
		data = response.read()
		conn.close()
		mcu_response = {"checksum": chk, "data" : [str(response.status),str(data)]}

	except Exception,e:
		conn.close()
		mcu_response = {"checksum": chk, "data" : [str("404"),str(e.strerror)]}

	# send response to Mcu
	ciao_connector.send(mcu_response)


def handler(mcu_req):
	if mcu_req['type'] == "result":
		chk = str(mcu_req['checksum'])
		if not chk:
			logger.warning("Missing checksum param, dropping message")

		url = str(mcu_req['data'][0])
		if not url:
			logger.warning("Missing stream param, dropping message")

		data = str(mcu_req['data'][1])
		if not data:
			logger.warning("Missing data param, dropping message")

		if (len(mcu_req['data']) > 2):		#if method isn't specified force it to "GET" method
			method = str(mcu_req['data'][2])
			if not method:
				logger.warning("Missing method param, dropping message")

			logger.debug("Key: %s" % method)
		else:
			method = "GET"

		http_request(url, method, data, chk)

# the absolute path of the connector
working_dir = os.path.dirname(os.path.abspath(__file__)) + os.sep

# LOAD CONFIGURATION

# load configuration object with configuration file rest.conf.json
config = ciao.load_config(working_dir)

# name of the connector
name = config["name"]

# CREATE LOGGER

log_config = config["log"] if "log" in config else None
logger = ciao.get_logger(name, logconf=log_config, logdir=working_dir)

# CALL BASE CONNECTOR

#Call a base connector object to help connection to ciao core
ciao_connector = ciao.BaseConnector(name, logger, async = True)

#register an handler to manage data from core/mcu
ciao_connector.receive(handler)

# start the connector thread
ciao_connector.start()
