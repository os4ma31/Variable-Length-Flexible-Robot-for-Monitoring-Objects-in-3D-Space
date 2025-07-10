// Slave_Controller.ino (v2: Variable Speed)
// This version receives a 3-byte I2C command from the master
// to control its motors with variable speed.

#include <Wire.h>
#include <AFMotor.h>


#define SLAVE_ADDRESS 8


// Slave motor objects
AF_DCMotor motorS1(1); // S1 on M1 Port
AF_DCMotor motorS2(2); // S2 on M2 Port (Corresponds to M6)
AF_DCMotor motorS3(3); // S3 on M3 Port

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("--- Slave Controller w/ Var. Speed Initialized ---");

  Wire.begin(SLAVE_ADDRESS);
  Wire.onReceive(receiveEvent); // Register event handler
}

void loop() {
  // All action happens in the I2C event
  delay(100);
}

// This function is called automatically whenever the Master sends data.
void receiveEvent(int byteCount) {
  // We expect 3 bytes: [MotorID, DirectionID, Speed]
  if (byteCount == 3) {
    byte motorId = Wire.read();
    byte directionId = Wire.read();
    byte speed = Wire.read();

    AF_DCMotor* targetMotor = NULL;

    if (motorId == 1) targetMotor = &motorS1;
    else if (motorId == 2) targetMotor = &motorS2;
    else if (motorId == 3) targetMotor = &motorS3;
    else return; // Unknown motor

    targetMotor->setSpeed(speed);

    if (directionId == 1) targetMotor->run(FORWARD);      // Forward
    else if (directionId == 2) targetMotor->run(BACKWARD); // Backward
    else targetMotor->run(RELEASE);                       // Stop
  } else {
    // If we receive a different number of bytes, clear the buffer
    while(Wire.available()) {
      Wire.read();
    }
  }
}
