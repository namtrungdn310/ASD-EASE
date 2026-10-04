#include <Arduino.h>
#include "HardwareProfiler.h"
#include "pins.h"

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("ASD Edge AI firmware scaffold — hardware not verified");
  HardwareProfiler::printToSerial();
  if (PIN_I2C_SDA == PIN_UNVERIFIED || PIN_I2C_SCL == PIN_UNVERIFIED || PIN_GSR_ADC == PIN_UNVERIFIED) {
    Serial.println("Sensors unavailable: GPIO mapping awaits physical verification.");
  }
}

void loop() { delay(1000); }

