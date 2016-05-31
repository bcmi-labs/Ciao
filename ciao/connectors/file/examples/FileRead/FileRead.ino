/*
Arduino Ciao File Connector: File Overwrite

Open a file, reads its contents and shows it via serial .
Before starts create a file and write a line to display or
Move the attached file (sample.txt) into /root/ directory of your LininoOS.

NOTE: be sure to activate and configure file connector on Linino OS.
http://www.arduino.org/learning/reference/ciao-file

How to specify file:
- relative path: the base path is the 'root' parameters specified in the configuration file
- absolute path

File access mode:
- Ciao.read: file is open in read mode.
- Ciao.write: you can specify the access mode ("a" append, "w" write) in the last (optional) arguments.
	by default the access mode is specified in the configuration file

authors:
created 29 Apr 2016 - sergio tomasello

*/

#include <Ciao.h>

void setup() {
	//init Ciao and LCD
	Ciao.begin();
	Serial.begin(9600);
}

void loop() {
	delay(2000);

	//Read file from lininoOS
	CiaoData data = Ciao.read("file","/root/sample.txt");
	if(!data.isEmpty()){

		//extract data from Ciao
		String message = data.get(2);

		//Print message via serial
		Serial.println(message);
	}
	//Delay the operations because IO is slow
	delay(2000);
}
