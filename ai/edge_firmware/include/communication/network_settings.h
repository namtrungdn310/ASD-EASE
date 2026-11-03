#pragma once
#if !defined(ASD_NETWORK_BUILD_CHECK) && __has_include("network_config.h")
#include "network_config.h"
#endif
#ifdef ASD_NETWORK_BUILD_CHECK
#define WIFI_SSID "BUILD_ONLY"
#define WIFI_PASSWORD "BUILD_ONLY_NOT_SECRET"
#define MQTT_BROKER_HOST "build-check.invalid"
#define MQTT_USERNAME "build-check"
#define MQTT_PASSWORD "BUILD_ONLY_NOT_SECRET"
#define MQTT_USE_TLS 0
#define ASD_ALLOW_INSECURE_LAN 1
#endif
#ifndef ASD_NETWORK_ENABLED
#define ASD_NETWORK_ENABLED 0
#endif
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef MQTT_BROKER_HOST
#define MQTT_BROKER_HOST ""
#endif
#ifndef MQTT_BROKER_PORT
#define MQTT_BROKER_PORT 8883
#endif
#ifndef MQTT_USERNAME
#define MQTT_USERNAME ""
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif
#ifndef MQTT_DEVICE_ID
#define MQTT_DEVICE_ID "ASD-ESP32S3-SUPERMINI"
#endif
#ifndef MQTT_USE_TLS
#define MQTT_USE_TLS 1
#endif
#ifndef MQTT_CA_CERT
#define MQTT_CA_CERT ""
#endif
#ifndef ASD_ALLOW_INSECURE_LAN
#define ASD_ALLOW_INSECURE_LAN 0
#endif
#ifndef ASD_SERIAL_DIAGNOSTICS
#define ASD_SERIAL_DIAGNOSTICS 1
#endif
