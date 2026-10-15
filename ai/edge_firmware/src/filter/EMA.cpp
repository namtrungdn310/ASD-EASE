#include "EMA.h"
#include <cmath>

EMA::EMA(float alpha)
    : alpha_(alpha < 0.001f ? 0.001f : (alpha > 1.0f ? 1.0f : alpha)),
      value_(0.0f), initialized_(false) {}

EMA::EMA(float alpha, float initialValue)
    : alpha_(alpha < 0.001f ? 0.001f : (alpha > 1.0f ? 1.0f : alpha)),
      value_(initialValue), initialized_(true) {}

void EMA::setAlpha(float alpha) {
  if (alpha < 0.001f)
    alpha = 0.001f;
  if (alpha > 1.0f)
    alpha = 1.0f;
  alpha_ = alpha;
}

float EMA::getAlpha() const { return alpha_; }

float EMA::update(float input) {

  if (isnan(input) || isinf(input)) {
    return value_;
  }

  // Khởi tạo trơn tru ở mẫu đo đầu tiên: tránh kéo tụt tín hiệu từ 0.0
  if (!initialized_) {
    value_ = input;
    initialized_ = true;
    return value_;
  }

  value_ = alpha_ * input + (1.0f - alpha_) * value_;
  return value_;
}

float EMA::getValue() const { return value_; }

bool EMA::isInitialized() const { return initialized_; }

void EMA::reset() {
  value_ = 0.0f;
  initialized_ = false;
}

void EMA::reset(float initialValue) {
  value_ = initialValue;
  initialized_ = true;
}
