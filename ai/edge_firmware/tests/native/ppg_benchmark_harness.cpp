// Chỉ dùng benchmark trên laptop. Không biên dịch vào firmware.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include "processing/sensor_math.h"
// Truy cập chính bộ lọc của production để mọi ứng viên dùng cùng tiền xử lý.
// Macro chỉ tồn tại trong translation unit benchmark, không sửa header sản phẩm.
#define private public
#include "processing/ppg_rate.h"
#undef private
#include "processing/ppg_contact.h"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main() {
  asd::PpgRate current;
  asd::PpgRate::Filter irFilter{}, redFilter{};
  asd::PpgContact contact(10000,6000,1000);
  std::string line;
  uint64_t previous = 0;
  unsigned segment = 0;
  bool initialized = false, hasPrevious = false;
  float irDc = 0, redDc = 0;
  std::cout << std::setprecision(9);
  while (std::getline(std::cin,line)) {
    std::replace(line.begin(),line.end(),',',' ');
    std::istringstream input(line);
    uint64_t time; uint32_t red, ir;
    if (!(input >> time >> red >> ir)) continue;
    const auto gate = contact.update(ir,time);
    if (gate.restart || (hasPrevious && (time <= previous || time-previous > 40))) {
      current.reset(); irFilter = {}; redFilter = {}; initialized = false; ++segment;
    }
    previous = time; hasPrevious = true;
    float a = NAN, b = NAN;
    if (gate.usable) {
      if (!initialized) { irDc = float(ir); redDc = float(red); initialized = true; }
      a = irFilter.apply(float(ir)-irDc); b = redFilter.apply(float(red)-redDc);
      (void)current.update(ir,red,time);
    }
    const auto& estimate = current.estimate();
    std::cout << time << ',' << estimate.valid << ',' << estimate.bpm << ','
              << a << ',' << b << ',' << gate.usable << ',' << segment << '\n';
  }
}
