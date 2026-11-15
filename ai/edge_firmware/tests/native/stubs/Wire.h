#pragma once
#include "Arduino.h"
#include <array>
#include <deque>
#include <vector>
#include <cstdint>
#include <cstddef>

struct TwoWire {
  std::array<uint8_t, 256> registers{};
  std::deque<uint8_t> fifo, rx;
  std::vector<uint8_t> tx;
  bool imu = false;
  bool emulateNoRolloverStall = false;
  int failedRegister = -1, corruptRegister = -1, failedWriteRegister = -1;
  unsigned transactions = 0;
  bool ppgResetStuck = false;
  uint32_t failureDelayMs = 0; // Chỉ test: mô phỏng timeout từng giao dịch.
  int shortReadRegister = -1, readValueRegister = -1;
  size_t shortReadLimit = 0;
  uint8_t readValue = 0;
  bool failPpgProbe = false;
  uint8_t cursor = 0, ppgRead = 0, ppgWrite = 0;
  size_t maximumRead = 0;
  explicit TwoWire(bool isImu = false) : imu(isImu) { registers[0x75] = 0x68; registers[0xff]=0x15; }
  void beginTransmission(uint8_t) { tx.clear(); }
  void write(uint8_t value) { tx.push_back(value); }
  int endTransmission(bool = true) {
    ++transactions;
    if (tx.empty()) return 0;
    cursor = tx[0];
    if (cursor == failedRegister || (!imu && cursor==0xff && failPpgProbe) ||
        (tx.size()>=2 && cursor==failedWriteRegister)) { fakeNowMs+=failureDelayMs; return 4; }
    if (tx.size() >= 2) {
      if (cursor != corruptRegister) registers[cursor] = tx[1];
      if (!imu && cursor==0x09 && (tx[1]&0x40)) {
        fifo.clear(); ppgRead=ppgWrite=0;
        registers[0x09]=ppgResetStuck ? 0x40 : 0;
      }
      if(!imu && cursor==0x04)ppgWrite=tx[1];
      if(!imu && cursor==0x06){ppgRead=tx[1];if(tx[1]==0)fifo.clear();}
      if (imu && cursor == 0x6a && (tx[1] & 4)) fifo.clear();
    }
    return 0;
  }
  size_t requestFrom(uint8_t, size_t length) {
    rx.clear();
    if (length > maximumRead) maximumRead = length;
    if (cursor == failedRegister) return 0;
    if (cursor == shortReadRegister) length = length < shortReadLimit ? length : shortReadLimit;
    const bool fromFifo = cursor == (imu ? 0x74 : 0x07);
    if (fromFifo) {
      const size_t received = fifo.size() < length ? fifo.size() : length;
      for (size_t i = 0; i < received; ++i) { rx.push_back(fifo.front()); fifo.pop_front(); }
      if (!imu) ppgRead = (ppgRead + received / 6) % 32;
      if (!imu && received >= 6) registers[0x05] = 0;
      return received;
    }
    for (size_t i = 0; i < length; ++i) {
      const uint8_t reg = cursor + i;
      uint8_t value = registers[reg];
      if (reg == readValueRegister) value = readValue;
      if (imu && (reg == 0x72 || reg == 0x73))
        value = reg == 0x72 ? uint8_t(fifo.size() >> 8) : uint8_t(fifo.size());
      if (!imu && reg == 0x04) value = ppgWrite;
      if (!imu && reg == 0x06) value = ppgRead;
      rx.push_back(value);
      if (reg == (imu ? 0x3a : 0x00)) registers[reg] = 0;
    }
    return length;
  }
  int available() const { return static_cast<int>(rx.size()); }
  int read() { if (rx.empty()) return -1; const int value = rx.front(); rx.pop_front(); return value; }
  void pushPpg(uint32_t red, uint32_t ir) {
    if(registers[0x09]&0x80)return;
    if (emulateNoRolloverStall && (registers[0x08] & 0x10) == 0) {
      registers[0x05] = 1; return;
    }
    for (uint32_t value : {red, ir}) {
      fifo.push_back((value >> 16) & 0xff); fifo.push_back((value >> 8) & 0xff); fifo.push_back(value & 0xff);
    }
    ppgWrite = (ppgWrite + 1) % 32;
  }
  void pushImu(int16_t ax = 0, int16_t ay = 0, int16_t az = -16384,
               int16_t gx = 131, int16_t gy = -262, int16_t gz = 0) {
    for (int16_t value : {ax, ay, az, int16_t(0), gx, gy, gz}) {
      fifo.push_back((uint16_t(value) >> 8) & 0xff); fifo.push_back(value & 0xff);
    }
  }
};
inline TwoWire Wire;
inline TwoWire Wire1(true);
