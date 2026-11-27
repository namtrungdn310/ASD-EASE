#pragma once

// ============================================================================
// AUTO-GENERATED EDGE AI (TinyML) MODEL PARAMETERS FOR ESP32-S3
// Architecture: Ultra-Lightweight Algebraic Folded Logistic Regression
// Dataset: WESAD (3,040 windows, 15 subjects LOSO Acc: 90.69%, Stress F1: 84.66%)
// Footprint: 148 bytes Flash (.rodata) | 0 bytes dynamic RAM | 0 floating divisions
// Hardware Target: ESP32-S3 Xtensa LX7 dual-core MCU (FPU Hardware Accelerated)
// ============================================================================

#define MODEL_VERSION "wesad_lr_v1_folded"
constexpr int MODEL_FEATURE_COUNT = 36;
constexpr float MODEL_FOLDED_BIAS = 135.10469055f;
constexpr float MODEL_DECISION_THRESHOLD = 0.50f;
constexpr float MODEL_LOGIT_THRESHOLD = 0.0f; // log(0.5 / (1.0 - 0.5)) == 0.0f

static const char* const MODEL_FEATURE_NAMES[MODEL_FEATURE_COUNT] = {
    "eda_mean",
    "eda_std",
    "eda_min",
    "eda_max",
    "eda_ptp",
    "eda_slope",
    "eda_tonic_mean",
    "eda_tonic_std",
    "eda_phasic_mean",
    "eda_phasic_max",
    "eda_phasic_std",
    "eda_phasic_auc",
    "eda_scr_count",
    "eda_scr_amp_mean",
    "acc_norm_mean",
    "acc_norm_std",
    "acc_norm_min",
    "acc_norm_max",
    "acc_norm_ptp",
    "acc_norm_energy",
    "acc_motion_intensity",
    "acc_x_mean",
    "acc_x_std",
    "acc_y_mean",
    "acc_y_std",
    "acc_z_mean",
    "acc_z_std",
    "hr_valid_count",
    "hr_valid_ratio",
    "hr_is_valid",
    "hr_mean",
    "hr_std",
    "hr_min",
    "hr_max",
    "hr_ptp",
    "hr_slope"
};

// Folded weights: w'_i = w_i / scale_i (Pre-scaled offline, 0 runtime divisions)
static const float MODEL_FOLDED_WEIGHTS[MODEL_FEATURE_COUNT] = {
    -1.87245607f,  // [ 0] eda_mean
    12.37061596f,  // [ 1] eda_std
    1.66261816f,  // [ 2] eda_min
    1.20618033f,  // [ 3] eda_max
    -2.84707928f,  // [ 4] eda_ptp
    -32.86193848f,  // [ 5] eda_slope
    -1.92278457f,  // [ 6] eda_tonic_mean
    -6.98689604f,  // [ 7] eda_tonic_std
    90.19071960f,  // [ 8] eda_phasic_mean
    -3.34212494f,  // [ 9] eda_phasic_max
    -12.70367908f,  // [10] eda_phasic_std
    1.50317943f,  // [11] eda_phasic_auc
    0.29021454f,  // [12] eda_scr_count
    1.62497544f,  // [13] eda_scr_amp_mean
    -33.04841614f,  // [14] acc_norm_mean
    8.63633919f,  // [15] acc_norm_std
    -0.03988277f,  // [16] acc_norm_min
    -0.01501017f,  // [17] acc_norm_max
    -0.00318890f,  // [18] acc_norm_ptp
    1.90597332f,  // [19] acc_norm_energy
    -14.25956249f,  // [20] acc_motion_intensity
    0.02984070f,  // [21] acc_x_mean
    -2.08743525f,  // [22] acc_x_std
    -0.08086965f,  // [23] acc_y_mean
    -0.34435534f,  // [24] acc_y_std
    -0.13158508f,  // [25] acc_z_mean
    -1.41733277f,  // [26] acc_z_std
    -0.06445987f,  // [27] hr_valid_count
    -3.86759233f,  // [28] hr_valid_ratio
    -3.43071699f,  // [29] hr_is_valid
    0.06273786f,  // [30] hr_mean
    -0.02976624f,  // [31] hr_std
    0.06084893f,  // [32] hr_min
    0.06539094f,  // [33] hr_max
    0.03764416f,  // [34] hr_ptp
    -0.27592441f  // [35] hr_slope
};

#include <math.h>

/**
 * @brief Tính giá trị logit z = b' + sum(w'_i * x_i) bằng phép nhân cộng FPU phần cứng.
 * Tận dụng pipeline của ESP32-S3, tối ưu tốc độ và không dùng heap.
 */
inline float edge_compute_logit(const float* raw_features) {
    if (!raw_features) return -100.0f;
    float z = MODEL_FOLDED_BIAS;
    #pragma GCC unroll 4
    for (int i = 0; i < MODEL_FEATURE_COUNT; ++i) {
        z += MODEL_FOLDED_WEIGHTS[i] * raw_features[i];
    }
    return z;
}

/**
 * @brief Suy luận nhanh quyết định Stress/Bình thường (Real-time decision).
 * Khử hoàn toàn hàm expf(-z), chạy trong 1 chu kỳ so sánh FPU (z >= 0.0f).
 * Thích hợp gọi trực tiếp trong ngắt hoặc loop điều khiển rung/còi (latency < 1us).
 */
inline bool edge_predict_stress_fast(const float* raw_features) {
    return edge_compute_logit(raw_features) >= MODEL_LOGIT_THRESHOLD;
}

/**
 * @brief Tính xác suất Stress [0.0f, 1.0f] qua Sigmoid khi cần hiển thị giao diện hoặc telemetry MQTT.
 */
inline float edge_predict_stress_probability(const float* raw_features) {
    float z = edge_compute_logit(raw_features);
    if (isnan(z)) return 0.0f;
    if (z > 16.0f) return 1.0f;
    if (z < -16.0f) return 0.0f;
    return 1.0f / (1.0f + expf(-z));
}

/**
 * @brief Hàm tương thích chuẩn với ngưỡng tùy chọn (default = 0.50f).
 */
inline bool edge_predict_stress(const float* raw_features, float threshold = MODEL_DECISION_THRESHOLD) {
    if (threshold == 0.50f) {
        return edge_predict_stress_fast(raw_features);
    }
    return edge_predict_stress_probability(raw_features) >= threshold;
}
