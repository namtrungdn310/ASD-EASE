#pragma once
// Chép thành network_config.h local (Git bỏ qua), không commit secret.
// Mặc định tắt; chỉ bật sau khi đăng ký đúng DEVICE/ACL/profile ở backend.
#define ASD_NETWORK_ENABLED 0
#define WIFI_SSID "CHANGE_ME"
#define WIFI_PASSWORD "CHANGE_ME"
#define MQTT_DEVICE_ID "ESP32-001"
#define MQTT_BROKER_HOST "192.168.x.x"
#define MQTT_BROKER_PORT 1883
#define MQTT_USERNAME "esp32"
#define MQTT_PASSWORD "CHANGE_ME"
// Chỉ ngoại lệ LAN phát triển riêng. Ngoài LAN riêng dùng TLS + CA/hostname.
#define MQTT_USE_TLS 0
#define ASD_ALLOW_INSECURE_LAN 1
#define MQTT_CA_CERT ""
// Chẩn đoán Serial có thể ảnh hưởng nhịp lấy mẫu; đo cả bật và tắt.
#define ASD_SERIAL_DIAGNOSTICS 1
// Dành raw HTTP ở nhánh7, không dùng làm đường telemetry song song.
#define BACKEND_HOST "192.168.x.x"
#define BACKEND_PORT 8000


