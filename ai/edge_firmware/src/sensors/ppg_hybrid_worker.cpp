#include "processing/ppg_hybrid_worker.h"
#if defined(ARDUINO_ARCH_ESP32) && ASD_PPG_HYBRID_ENABLED
#include "processing/ppg_rate.h"
#include <Arduino.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <atomic>
#include "processing/ppg_cycle_tracker.h"
#if !ASD_PPG_TRACKER_ENABLED
#error "Firmware uses the selected cycle tracker; baseline is for native tests only"
#endif

namespace asd {
namespace {
struct Input { PpgQuality::Window ir{},red{}; PpgMotionWindow motion{}; uint64_t measuredAt=0; uint32_t generation=0; };
PpgCycleTracker processor;
PpgQuality::Result analyze(const Input& input) {
  const auto tracked=processor.update(input.ir,input.red,input.measuredAt,input.generation,&input.motion);
  PpgQuality::Result r{};
  r.measuredAt=tracked.measuredAt;r.generation=tracked.generation;
  r.bpm=tracked.bpm;r.source=tracked.source;
  r.qualified=tracked.qualified;r.valid=tracked.valid;
  r.trackingMassScore=tracked.massScore;r.trackingEvidence=tracked.evidence;
  r.trackingRawBpm=tracked.rawBpm;
  r.sqi=tracked.sqi;r.irEvidence=tracked.irEvidence;r.redEvidence=tracked.redEvidence;
  r.motionCoverage=tracked.motionCoverage;r.motionOverlap=tracked.motionOverlap;
  r.motionSupported=tracked.motionSupported;r.motionCorrected=tracked.motionCorrected;
  return r;
}
Input staged; // Chỉ producer sensing ghi; task nhận bản copy riêng qua queue.
QueueHandle_t inputQueue=nullptr,outputQueue=nullptr;
TaskHandle_t worker=nullptr;
std::atomic<uint32_t> requests{0},overwritten{0};
std::atomic<bool> selfTestDone{false},selfTestPassed{false};

void task(void*) {
  static Input input{}; // Cửa sổ lớn nằm ở BSS, không chiếm stack task.
  PpgHybridResult output{};
  output.stats.workspaceBytes=sizeof(processor);
  // Self-test nội bộ bằng sóng chuẩn, KHÔNG đưa kết quả này vào outputQueue/MQTT.
  for (size_t i=0;i<400;++i) {
    input.ir[i]=1800*std::sin(double(i)*2*3.14159265358979323846*80/3000);
    input.red[i]=input.ir[i]*.7f;
  }
  const auto start=esp_timer_get_time();
  input.measuredAt=10000;input.generation=0xffffffff;
  const auto first=analyze(input);
  input.measuredAt=11000;
  const auto second=analyze(input);
  output.stats.selfTestUs=static_cast<uint32_t>(esp_timer_get_time()-start);
  output.stats.selfTestPassed=first.qualified && !first.valid && second.valid && std::fabs(second.bpm-80)<2;
  processor.reset();
  selfTestPassed.store(output.stats.selfTestPassed); selfTestDone.store(true);
  output.stats.enabled=output.stats.selfTestPassed;
  output.stats.stackFreeBytes=uxTaskGetStackHighWaterMark(nullptr); // ESP-IDF: bytes.
  xQueueOverwrite(outputQueue,&output); // analysis rỗng, chưa có dữ liệu đo thật.
  for (;;) {
    if (xQueueReceive(inputQueue,&input,portMAX_DELAY)!=pdTRUE) continue;
    if (!output.stats.selfTestPassed) continue;
    const auto started=esp_timer_get_time();
    output.analysis=analyze(input);
    output.stats.trackingMassScore=output.analysis.trackingMassScore;
    output.stats.trackingEvidence=output.analysis.trackingEvidence;
    output.stats.trackingRawBpm=output.analysis.trackingRawBpm;
    output.stats.lastWallUs=static_cast<uint32_t>(esp_timer_get_time()-started);
    output.stats.maxWallUs=std::max(output.stats.maxWallUs,output.stats.lastWallUs);
    ++output.stats.completed;
    if (output.analysis.valid) ++output.stats.accepted;
    output.stats.stackFreeBytes=uxTaskGetStackHighWaterMark(nullptr);
    xQueueOverwrite(outputQueue,&output);
    vTaskDelay(1); // Task priority0, không đợi queue/PUBACK ở vòng sensing.
  }
}
} // namespace
bool ppgHybridSetup() {
  if (worker) return true;
  inputQueue=xQueueCreate(1,sizeof(Input)); outputQueue=xQueueCreate(1,sizeof(PpgHybridResult));
  if (!inputQueue || !outputQueue ||
      xTaskCreatePinnedToCore(task,"asd-ppg-sqi",8192,nullptr,0,&worker,ARDUINO_RUNNING_CORE)!=pdPASS) {
    if (inputQueue) vQueueDelete(inputQueue);
    if (outputQueue) vQueueDelete(outputQueue);
    inputQueue=outputQueue=nullptr; worker=nullptr; return false;
  }
  return true;
}
bool ppgHybridSubmit(const PpgRate& rate,uint64_t measuredAt,uint32_t generation) {
  if (!worker || (selfTestDone.load() && !selfTestPassed.load()) ||
      !rate.copyFilteredWindow(staged.ir,staged.red)) return false;
  rate.copyMotionWindow(staged.motion);
  staged.measuredAt=measuredAt; staged.generation=generation;
  if (uxQueueMessagesWaiting(inputQueue)!=0) ++overwritten;
  ++requests;
  return xQueueOverwrite(inputQueue,&staged)==pdTRUE;
}
bool ppgHybridLatest(PpgHybridResult& output) {
  return outputQueue && xQueuePeek(outputQueue,&output,0)==pdTRUE;
}
PpgHybridStats ppgHybridStats() {
  PpgHybridResult result{};
  if (outputQueue) (void)xQueuePeek(outputQueue,&result,0);
  result.stats.requests=requests.load(); result.stats.overwritten=overwritten.load();
  return result.stats;
}
} // namespace asd
#endif
