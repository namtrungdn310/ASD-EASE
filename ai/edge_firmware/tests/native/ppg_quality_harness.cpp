#include "processing/ppg_quality.h"
#include <iomanip>
#include <iostream>

int main() {
  static asd::PpgQuality quality;
  asd::PpgQuality::Window ir{},red{};
  uint64_t measured; uint32_t generation;
  std::cout<<std::setprecision(17);
  while (std::cin>>measured>>generation) {
    for (auto& x:ir) if (!(std::cin>>x)) return 2;
    for (auto& x:red) if (!(std::cin>>x)) return 2;
    const auto r=quality.update(ir,red,measured,generation);
    std::cout<<measured<<' '<<r.qualified<<' '<<r.valid<<' '<<r.bpm<<' '<<unsigned(r.source);
    for (const auto* f:{&r.ir,&r.red})
      std::cout<<' '<<f->usable<<' '<<unsigned(f->reason)<<' '<<f->qualifies()<<' '<<f->bpm
               <<' '<<f->recentBpm<<' '<<f->amplitude<<' '<<f->rrCv<<' '<<f->templateMedian
               <<' '<<f->templateP20<<' '<<f->spectralFraction<<' '<<f->peakAge<<' '<<f->peaks;
    std::cout<<'\n';
  }
}
