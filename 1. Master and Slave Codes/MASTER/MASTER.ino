// Master_Controller.ino (v3: Variable Speed for Master & Slave)
// This version correctly parses "M:D:S" commands and forwards
// variable speed instructions to the Slave Arduino via I2C.

#include <Wire.h>
#include <AFMotor.h>

#define SLAVE_ADDRESS 8

// Motor Objects
AF_DCMotor motor1(1); AF_DCMotor motor2(2); AF_DCMotor motor3(3); AF_DCMotor motor4(4);

// --- Encoder Pin Definitions ---
#define E1_A 18
#define E1_B 19
#define E2_A 22
#define E2_B 23
#define E3_A 24
#define E3_B 25
#define E4_A 26
#define E4_B 27
#define E5_A 28
#define E5_B 29
#define E6_A 30
#define E6_B 31

// Encoder Counters
volatile long E1_count = 0; volatile long E2_count = 0; volatile long E3_count = 0;
volatile long E4_count = 0; volatile long E5_count = 0; volatile long E6_count = 0;

// State Tracking for Polled Encoders
int E2_last_state; int E3_last_state; int E4_last_state; int E5_last_state; int E6_last_state;

unsigned long last_send_time = 0;
const long SEND_INTERVAL = 100; // ms

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("--- Master w/ Var. Speed & Encoders Initialized ---");
  Wire.begin();

  // Initialize Encoder Pins
  pinMode(E1_A, INPUT_PULLUP); pinMode(E1_B, INPUT_PULLUP);
  pinMode(E2_A, INPUT_PULLUP); pinMode(E2_B, INPUT_PULLUP);
  pinMode(E3_A, INPUT_PULLUP); pinMode(E3_B, INPUT_PULLUP);
  pinMode(E4_A, INPUT_PULLUP); pinMode(E4_B, INPUT_PULLUP);
  pinMode(E5_A, INPUT_PULLUP); pinMode(E5_B, INPUT_PULLUP);
  pinMode(E6_A, INPUT_PULLUP); pinMode(E6_B, INPUT_PULLUP);
  
  attachInterrupt(digitalPinToInterrupt(E1_A), readEncoder1, CHANGE);
  
  E2_last_state = digitalRead(E2_A); E3_last_state = digitalRead(E3_A);
  E4_last_state = digitalRead(E4_A); E5_last_state = digitalRead(E5_A);
  E6_last_state = digitalRead(E6_A);
}

void loop() {
  pollEncoders();
  handleSerialCommands();
  if (millis() - last_send_time > SEND_INTERVAL) {
    sendEncoderData();
    last_send_time = millis();
  }
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    int first_colon = command.indexOf(':');
    int second_colon = command.indexOf(':', first_colon + 1);

    if (first_colon > 0 && second_colon > 0) {
        // Format is "M:D:S", e.g. "1:f:255"
        int motorNum = command.substring(0, first_colon).toInt();
        char direction = command.charAt(first_colon + 1);
        int speed = command.substring(second_colon + 1).toInt();
        speed = constrain(speed, 0, 255);
        
        if (motorNum >= 1 && motorNum <= 4) { // Master Motors
            AF_DCMotor* targetMotor = NULL;
            if (motorNum == 1) targetMotor = &motor1;
            else if (motorNum == 2) targetMotor = &motor2;
            else if (motorNum == 3) targetMotor = &motor3;
            else if (motorNum == 4) targetMotor = &motor4;
            
            targetMotor->setSpeed(speed);
            if(direction == 'f') targetMotor->run(FORWARD);
            else if(direction == 'b') targetMotor->run(BACKWARD);
            else targetMotor->run(RELEASE);
        } else if (motorNum >= 5 && motorNum <= 7) { // Slave Motors
            int motorId = motorNum - 4; // 1 for S1, 2 for S2(M6), 3 for S3
            int directionId = 0;
            if (direction == 'f') directionId = 1;
            else if (direction == 'b') directionId = 2;

            // New 3-byte I2C command: [MotorID, DirectionID, Speed]
            Wire.beginTransmission(SLAVE_ADDRESS);
            Wire.write(motorId);
            Wire.write(directionId);
            Wire.write(speed);
            Wire.endTransmission();
        }
    }
  }
}

void sendEncoderData() {
  Serial.print("E1:"); Serial.print(E1_count);
  Serial.print("|E2:"); Serial.print(E2_count);
  Serial.print("|E3:"); Serial.print(E3_count);
  Serial.print("|E4:"); Serial.print(E4_count);
  Serial.print("|E5:"); Serial.print(E5_count);
  Serial.print("|E6:"); Serial.print(E6_count);
  Serial.println();
}

void readEncoder1() {
  if (digitalRead(E1_A) == digitalRead(E1_B)) E1_count++; else E1_count--;
}

void pollEncoders() {
    int state_E2 = digitalRead(E2_A); if (state_E2 != E2_last_state) { if (digitalRead(E2_B) != state_E2) E2_count++; else E2_count--; E2_last_state = state_E2; }
    int state_E3 = digitalRead(E3_A); if (state_E3 != E3_last_state) { if (digitalRead(E3_B) != state_E3) E3_count++; else E3_count--; E3_last_state = state_E3; }
    int state_E4 = digitalRead(E4_A); if (state_E4 != E4_last_state) { if (digitalRead(E4_B) != state_E4) E4_count++; else E4_count--; E4_last_state = state_E4; }
    int state_E5 = digitalRead(E5_A); if (state_E5 != E5_last_state) { if (digitalRead(E5_B) != state_E5) E5_count++; else E5_count--; E5_last_state = state_E5; }
    int state_E6 = digitalRead(E6_A); if (state_E6 != E6_last_state) { if (digitalRead(E6_B) != state_E6) E6_count++; else E6_count--; E6_last_state = state_E6; }
}
