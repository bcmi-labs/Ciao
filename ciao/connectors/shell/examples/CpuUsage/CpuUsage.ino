/*
Arduino Ciao File Connector: Cpu Usage

Runs commands in Linino OS shell, using Ciao.write to get
the CPU usage every one minute, by reading /proc/stat system file

http://stackoverflow.com/questions/9229333/how-to-get-overall-cpu-usage-e-g-57-on-linux

1) specify the connector to use: "shell".
1) set command to run.
3) insert commands arguments list.

NOTE: be sure to activate and configure shell connector on Linino OS.
http://www.arduino.org/learning/reference/ciao-shell

authors:
created 9 Mag 2016 - sergio tomasello

*/

#include <Ciao.h>
#define ARGS_SEP_CODE String(char(21))

String ShellCommand = "grep";
String ShellArguments = "'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'";

void setup() {

	//init Ciao
	Ciao.begin();
	Serial.begin(9600);
}

void loop() {
	//Run commands in Linino OS to get the CPU Usage
	CiaoData data = Ciao.write("shell",ShellCommand, ShellArguments);

	if(!data.isEmpty()){
		//Get data back
		String usage = data.get(2);
		Serial.println(usage);
	}

	delay(10000);
}
