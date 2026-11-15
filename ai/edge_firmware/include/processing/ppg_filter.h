#pragma once
#include <cmath>
#include "processing/sensor_math.h"
namespace asd {
class PpgBandpass {
 public:
    float x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    float hx1 = 0, hx2 = 0, hy1 = 0, hy2 = 0;
    float raw1 = 0, raw2 = 0, noisePower = 0;
    float apply(float x) {
      // Với nhiễu trắng độc lập: Var(x[n]-2x[n-1]+x[n-2])=6*Var(noise).
      // Đây chỉ là proxy nhiễu; nhịp nhanh/chuyển động cũng có thể làm tăng nó.
      const float difference = x - 2*raw1 + raw2;
      noisePower = difference*difference/6;
      raw2 = raw1; raw1 = x;
      static const auto c = lowPass(4, 50);
      static const float k = std::tan(3.14159265358979323846f*.5f/50);
      static const float norm = 1/(1+1.4142135623730951f*k+k*k);
      static const float a1 = 2*(k*k-1)*norm, a2 = (1-1.4142135623730951f*k+k*k)*norm;
      const float hp = norm*(x-2*hx1+hx2) - a1*hy1 - a2*hy2;
      hx2 = hx1; hx1 = x; hy2 = hy1; hy1 = hp;
      const float y = c.b0*hp + c.b1*x1 + c.b2*x2 - c.a1*y1 - c.a2*y2;
      x2 = x1; x1 = hp; y2 = y1; y1 = y; return y;
    }
  };
}
