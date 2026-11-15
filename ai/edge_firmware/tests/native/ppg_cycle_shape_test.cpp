#include "processing/ppg_cycle_shape.h"
#include <cstdlib>
#include <iostream>
#include <limits>

namespace {
void check(bool ok,const char* message) {
  if(!ok) {std::cerr<<"FAIL: "<<message<<'\n';std::exit(1);}
}
std::array<float,400> wave(float bpm,float amplitude=100,float dc=0,float harmonic=.25f) {
  std::array<float,400> values{};
  for(size_t i=0;i<values.size();++i) {
    const float phase=float(i)*2*3.14159265358979323846f*bpm/3000;
    values[i]=dc+amplitude*(std::sin(phase)+harmonic*std::sin(2*phase+.3f));
  }
  return values;
}
}

int main() {
  asd::PpgCycleShape shape;unsigned cases=0;
  for(size_t length:{size_t(200),size_t(400)}) for(unsigned bpm=40;bpm<=200;bpm+=10) {
    const auto values=wave(float(bpm));
    check(shape.evaluate(values.data(),length,float(bpm))>.95f,"clean repeated cycles lost across HR range");
    ++cases;
  }
  {
    const auto low=wave(40,100,0,1.3f);
    check(shape.evaluate(low.data(),200,40)>.95f,"real low HR with strong harmonic rejected");++cases;
  }
  {
    const auto small=wave(80,4),large=wave(80,400,170000);
    check(std::fabs(shape.evaluate(small.data(),400,80)-shape.evaluate(large.data(),400,80))<.005f,
          "shape quality depended on DC or amplitude");++cases;
  }
  {
    const auto values=wave(80,100,0,0);
    check(shape.evaluate(values.data(),400,80)>shape.evaluate(values.data(),400,115)+.5f,
          "incoherent candidate scored like the real period");++cases;
  }
  {
    std::array<float,400> flat{};
    check(shape.evaluate(flat.data(),400,80)==0,"flat window acquired shape evidence");++cases;
    flat.fill(std::numeric_limits<float>::quiet_NaN());
    check(shape.evaluate(flat.data(),400,80)==0,"nonfinite window acquired shape evidence");++cases;
  }
  {
    const auto values=wave(80);
    for(float bpm:{0.f,-1.f,29.f,211.f,std::numeric_limits<float>::infinity()}) {
      check(shape.evaluate(values.data(),400,bpm)==0,"invalid candidate rate accepted");++cases;
    }
    check(shape.evaluate(nullptr,400,80)==0,"null pointer accepted");++cases;
    check(shape.evaluate(values.data(),199,80)==0,"unexpected window length accepted");++cases;
  }
  std::cout<<"PASS: "<<cases<<" cycle shape cases; workspace="<<sizeof(shape)<<" bytes\n";
}
