#include <Arduino.h>
#include <Esp.h>
#include <WiFi.h>
#include "HardwareProfiler.h"
#include "board_config.h"

void HardwareProfiler::printToSerial() {
  Serial.printf("chip_model=%s\n", ESP.getChipModel());
  Serial.printf("chip_revision=%d\n", ESP.getChipRevision());
  Serial.printf("cpu_mhz=%u\n", ESP.getCpuFreqMHz());
  Serial.printf("flash_bytes=%u\n", ESP.getFlashChipSize());
  Serial.printf("psram_detected=%s\n", psramFound() ? "true" : "false");
  Serial.printf("psram_bytes=%u\n", ESP.getPsramSize());
  Serial.printf("free_heap_bytes=%u\n", ESP.getFreeHeap());
  Serial.printf("free_psram_bytes=%u\n", ESP.getFreePsram());
  Serial.printf("mac=%s\n", WiFi.macAddress().c_str());
  Serial.printf("firmware_version=%s\n", ASD_FIRMWARE_VERSION);
}
