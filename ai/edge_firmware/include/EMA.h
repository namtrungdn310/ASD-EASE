#pragma once
#include <Arduino.h>

/**
 * =============================================================================
 * EMA (Exponential Moving Average) Filter
 * Bộ lọc thông thấp làm mịn tín hiệu theo phương pháp trung bình động hàm mũ
 * =============================================================================
 *
 * Công thức:
 *   y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
 *
 * Ý nghĩa của hệ số làm mượt alpha (0 < alpha <= 1.0):
 *   - alpha càng nhỏ (gần 0): Lọc càng mạnh, triệt tiêu nhiễu cao tần tốt,
 *                             nhưng đáp ứng chậm hơn (tăng độ trễ pha).
 *   - alpha càng lớn (gần 1): Lọc nhẹ hơn, đáp ứng nhanh tức thời theo tín hiệu.
 *   - alpha = 1.0: Không lọc (y[n] = x[n]).
 *
 * Tính năng nổi bật:
 *   - Khởi tạo mượt tự động (Auto-initialization): Mẫu hợp lệ đầu tiên được gán
 *     trực tiếp làm giá trị gốc, tránh hiện tượng trũng tín hiệu từ 0 (cold start).
 *   - Bảo vệ chống lỗi NaN / Infinity khi đọc lỗi cảm biến.
 *   - Hỗ trợ functor operator() và cast sang float trực tiếp.
 */

class EMA {
 public:
  /**
   * @brief Khởi tạo bộ lọc EMA với hệ số làm mượt alpha.
   * @param alpha Hệ số làm mượt (mặc định 0.2f, dải hợp lệ 0.001f - 1.0f).
   */
  explicit EMA(float alpha = 0.2f);

  /**
   * @brief Khởi tạo bộ lọc EMA với hệ số alpha và giá trị ban đầu xác định trước.
   * @param alpha Hệ số làm mượt.
   * @param initialValue Giá trị khởi tạo sẵn sàng ngay từ đầu.
   */
  EMA(float alpha, float initialValue);

  /**
   * @brief Cài đặt hệ số làm mượt alpha mới (được tự động giới hạn 0.001f đến 1.0f).
   */
  void setAlpha(float alpha);

  /**
   * @brief Lấy hệ số làm mượt alpha hiện tại.
   */
  float getAlpha() const;

  /**
   * @brief Cập nhật một mẫu đo mới vào bộ lọc và trả về giá trị đã lọc mượt.
   * @param input Mẫu dữ liệu đầu vào.
   * @return float Giá trị sau lọc.
   */
  float update(float input);

  /**
   * @brief Bí danh tương thích cho hàm update().
   */
  inline float filter(float input) { return update(input); }

  /**
   * @brief Functor operator cho phép gọi ngắn gọn: float smoothVal = myFilter(rawVal);
   */
  inline float operator()(float input) { return update(input); }

  /**
   * @brief Lấy giá trị đã lọc hiện tại mà không đẩy mẫu mới vào.
   */
  float getValue() const;

  /**
   * @brief Tự động chuyển đổi sang float khi đọc.
   */
  inline operator float() const { return getValue(); }

  /**
   * @brief Kiểm tra xem bộ lọc đã tiếp nhận mẫu đầu tiên chưa.
   */
  bool isInitialized() const;

  /**
   * @brief Đặt lại bộ lọc về trạng thái chưa khởi tạo (mẫu tiếp theo sẽ làm mốc gốc).
   */
  void reset();

  /**
   * @brief Đặt lại bộ lọc với một giá trị khởi đầu cụ thể.
   */
  void reset(float initialValue);

 private:
  float alpha_       = 0.2f;
  float value_       = 0.0f;
  bool  initialized_ = false;
};

// Bí danh tên lớp tương thích
using EMAFilter = EMA;
