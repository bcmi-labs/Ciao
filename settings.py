import re

debug = False

allowed_actions = {
	"r": { "params": 3, "map": "read"},				#requires 3 params - connector;action;data(optional)
	"w": { "params": 3, "map": "write"},			#requires 3 params - connector;action;data
	"wr": { "params": 4, "map": "writeresponse"}	#requires 4 params - connector;action;reference;data
}

#configuration dictionary (will be read from file)
"""
#TODO here we have to:
	- load bridge_config
	- scan SOMEDIR_CONF for connector configuration (bridge-side)
"""
conf = {
	"backlog" : 5, #this value must match number of enabled connectors (we could len(connectors))
	"srvhost" : "localhost",
	"srvport" : 8900,
	"logfile" : "bridge.log",
	"connectors" : {
		"xmpp" : {
			"implements" : {
				"read" : "with_message",
				"write" : "with_queue",
				"writeresponse" : "with_queue"
			}
		}
	}
}

#serialization settings
entry_separator = chr(30)	#ASCII code for GroupSeparator
keyvalue_separator = chr(31)	#ASCII code for UnitSeparator