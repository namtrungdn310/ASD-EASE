# Hardware Profile

## Current status

Physical hardware is **not verified**. Main MCU is specified as ESP32-S3 Super Mini, but that product name does not guarantee one pinout, flash/PSRAM configuration, USB circuit or power/charging design.

## Must be measured in Phase 00

- Board markings, supplier listing and schematic if available.
- Chip model/revision, CPU frequency, flash size, detected/free PSRAM and heap.
- MAC address and firmware version from `HardwareProfiler`.
- I2C SDA/SCL pins and bus assignment for MAX30102 and MPU6050; current code uses separate buses.
- ADC1-capable GSR GPIO and actual ADC behavior.
- USB behavior, battery architecture, regulator/charger and safe voltage/current limits.

The current `esp32s3_supermini` build environment uses `board = esp32-s3-devkitc-1`, firmware `0.2.0` and a configured 4 MB flash size. These settings do not identify the purchased board or prove its flash/PSRAM capacity. No physical evidence is added by this documentation cleanup.

## Configured values versus physical evidence

| Setting | Current executable source | Verification state |
|---|---|---|
| MAX30102 bus | `Wire`, SDA=8, SCL=9 | Wiring/rate evidence required |
| MPU6050 bus | `Wire1`, SDA=10, SCL=11 | Wiring/rate evidence required |
| GSR ADC | `PIN_GSR_ADC=4` in `board_config.h` | Comment in that header says GPIO1; Tân must confirm actual wiring before the constant is changed |
| Sampling schedules | PPG=100 Hz, IMU=50 Hz, GSR=20 Hz | Configured call rates; effective sample rates, FIFO averaging and losses must be measured |
| Legacy pin/sampling headers | `pins.h` still has unset pins; `sensor_config.h` duplicates sample-rate constants | Pending manual source cleanup; drivers currently include `board_config.h` |
| Hardware profiler | Implementation exists in `src/hardware/HardwareProfiler.cpp` | Current `setup()` does not call it; a profiler measurement requires explicitly invoking the diagnostic path |

The source cleanup will consolidate the shared types and configuration headers. It must not silently replace a GPIO or declare hardware verified from these configured values.

## Sensors

MAX30102 supplies raw red/IR PPG counts, MPU6050 supplies acceleration/gyroscope context, and an analog GSR module supplies ADC counts. No raw GSR count may be described as calibrated conductance without calibration.

Phase 00 remains NOT_STARTED until physical work begins and cannot be DONE without recorded evidence.

