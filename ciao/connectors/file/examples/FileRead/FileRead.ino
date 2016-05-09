/*
Arduino Ciao File Connector: File Overwrite

Open a file, reads its contents and shows it in an LCD Display( 16x2 ).
Before starts create a file and write a line to display into LCD.

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
created 29 Apr 2016 - sergio tomasello

*/

#include <Ciao.h>
#include <LCD_m0.h>

LCD_m0 LCD;

void setup() {
	//init Ciao and LCD
	Ciao.begin();
	LCD.Inizializza_LCD(12,11,5,4,3,2); //D4,D5,D6,D7
}

void loop() {
	//Clear LCD screen
	LCD.Pulisci();
	delay(2000);

	//Read file from lininoOS
	CiaoData data = Ciao.read("file","/root/sample.txt");
	if(!data.isEmpty()){

		//extract data from Ciao
		String message = data.get(2);

		//Print message into LCD Display
		LCD.Scrivi_Testo(message,1);
	}
	//Delay the operations because IO is slow
	delay(2000);
}
