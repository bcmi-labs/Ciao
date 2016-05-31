/*
Arduino Ciao File Connector: Cpu Usage

Runs commands in Linino OS shell, using Ciao.write to get
the system current date

1) specify the connector to use: "shell".
1) set command to run.
3) insert commands arguments list.

NOTE: be sure to activate and configure shell connector on Linino OS.
http://www.arduino.org/learning/reference/ciao-shell

authors:
created 9 Mag 2016 - sergio tomasello

*/

#include <Ciao.h>

void setup() {

	//init Ciao
	Ciao.begin();
	Serial.begin(9600);
}

void loop() {
	//Run commands in Linino OS to get date
	CiaoData data = Ciao.write("shell","date");

	if(!data.isEmpty()){
		//Get data back
		String usage = data.get(2);
		Serial.println(usage);
	}

	delay(10000);
}
