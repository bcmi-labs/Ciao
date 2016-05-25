/*
Arduino Ciao File Connector: Board Model

Runs commands in Linino OS shell, using Ciao.write to get
board model, using awk command

1) specify connector name: "shell".
1) set command to run.
3) insert commands arguments list.

NOTE: be sure to activate and configure shell connector on Linino OS.
http://www.arduino.org/learning/reference/ciao-shell

authors:
created 6 Mag 2016 - sergio tomasello

*/

#include <Ciao.h>
#define ARGS_SEP_CODE String(char(21))

String ArduinoBoard = "";

void setup() {

	//init Ciao
	Ciao.begin();
	Serial.begin(9600);
}

void loop() {

	if(ArduinoBoard == ""){
		//Run commands in Linino OS to get the board model
		CiaoData data = Ciao.write("shell","awk","'/machine/ {print $4}' /proc/cpuinfo");
		if(!data.isEmpty()){
			//extract data back
			ArduinoBoard = data.get(2);
			Serial.println(ArduinoBoard);
		}

	}
}
