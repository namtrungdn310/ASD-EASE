#pragma once
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <cstdlib>
using std::isnan;
using std::isinf;
#define F(value) value
constexpr int INPUT = 0;
constexpr int ADC_11db = 3;
inline uint64_t fakeNowMs = 1000;
inline uint32_t fakeRawAdc = 1800;
inline uint32_t millis() { return static_cast<uint32_t>(fakeNowMs); }
inline void delay(uint32_t duration) { fakeNowMs += duration; }
inline void analogReadResolution(int) {}
inline void analogSetPinAttenuation(int, int) {}
inline void pinMode(int, int) {}
inline uint32_t analogRead(int) { return fakeRawAdc; }
struct FakeSerial {
  template<typename... Args> void printf(const char*, Args...) {}
  template<typename T> void print(T) {}
  template<typename T> void println(T) {}
  void println() {}
};
inline FakeSerial Serial;
