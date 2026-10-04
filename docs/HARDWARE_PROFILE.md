# Hardware Profile

## Current status

Physical hardware is **not verified**. Main MCU is specified as ESP32-S3 Super Mini, but that product name does not guarantee one pinout, flash/PSRAM configuration, USB circuit or power/charging design.

## Must be measured in Phase 00

- Board markings, supplier listing and schematic if available.
- Chip model/revision, CPU frequency, flash size, detected/free PSRAM and heap.
- MAC address and firmware version from `HardwareProfiler`.
- I2C SDA/SCL pins shared by MAX30102 and MPU6050.
- ADC1-capable GSR GPIO and actual ADC behavior.
- USB behavior, battery architecture, regulator/charger and safe voltage/current limits.

`board = esp32-s3-devkitc-1` is a temporary conservative compile profile only; it does not identify the purchased board. The initial firmware does not require PSRAM. GPIO values remain `PIN_UNVERIFIED` until bench evidence exists.

## Sensors

MAX30102 supplies raw red/IR PPG counts, MPU6050 supplies acceleration/gyroscope context, and an analog GSR module supplies ADC counts. No raw GSR count may be described as calibrated conductance without calibration.

Phase 00 remains NOT_STARTED until physical work begins and cannot be DONE without recorded evidence.

