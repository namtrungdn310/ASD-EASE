#pragma once
#include "communication/session_protocol.h"
#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"

// Chụp giá trị và tuổi mẫu trong task sensing; worker mạng chỉ nhận bản copy.
asd::ReadingSnapshot captureTelemetrySnapshot(
    const MAX30102Data& ppg, const MPU6050Data& imu, const GSRData& gsr,
    uint32_t millisNow, uint64_t monotonicNow);

