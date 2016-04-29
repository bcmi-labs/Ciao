/*
Arduino Ciao File Connector: File Overwrite

Open a file in write mode, overwriting it,
and write into digital value of the specified pin

NOTE: be sure to activate and configure file connector on Linino OS.
http://labs.arduino.org/Ciao

How to specify file:
- relative path: the base path is the 'root' parameters specified in the configuration file
- absolute path

File access mode:
- Ciao.read: file is open in read mode.
- Ciao.write: you can specify the access mode ("a" append, "w" write) in the last (optional) arguments.
	by default the access mode is specified in the configuration file


authors:
created 28 Apr 2016 - sergio tomasello

*/

#include <Ciao.h>

int buttonPin = 5;
int pressed = 0;

void setup() {
	//init Ciao
	Ciao.begin();
	pinMode(buttonPin, INPUT);
}

void loop() {
	//Read digital input
	pressed = digitalRead(buttonPin);

	//Write value into a file in root folder. Root folder is specified into the connector
	//configuration file: /usr/lib/python2.7/ciao/connectors/file/file.json.conf
	//Else you can specify the absolute path for the file, eg: /tmp/my-file.log
	Ciao.write("file","button.txt", (String)pressed, "w");

	//Delay the operations because IO is slow
	delay(1000);
}
