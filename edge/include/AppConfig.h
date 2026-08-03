#pragma once

#include <Arduino.h>

namespace appcfg {
inline constexpr char FirmwareVersion[] = "0.2.0-unor4wifi";
inline constexpr char ProductName[] = "Cold-Chain Environmental Monitor";

// Arduino UNO R4 WiFi. I2C uses the board's SDA/SCL pins (also labeled A4/A5).
inline constexpr uint8_t DhtDataPin = 2;
inline constexpr uint8_t StatusLedPin = LED_BUILTIN;

inline constexpr uint32_t SerialBaud = 115200;
inline constexpr uint32_t DefaultSampleIntervalMs = 10000;
inline constexpr uint32_t LongObservationIntervalMs = 60000;
inline constexpr uint32_t MinimumSampleIntervalMs = 2000;
inline constexpr uint32_t MaximumSampleIntervalMs = 300000;

inline constexpr float DefaultWarningMarginC = 0.5F;
inline constexpr uint32_t DefaultExcursionPersistenceSeconds = 60;
inline constexpr uint16_t DefaultExcursionMinimumSamples = 3;
inline constexpr uint32_t DefaultRecoverySeconds = 300;
inline constexpr uint16_t DefaultRecoveryMinimumSamples = 5;

inline constexpr float TemperatureAdvisoryDifferenceC = 1.0F;
inline constexpr float TemperatureFaultDifferenceC = 2.0F;
inline constexpr uint32_t TemperatureAdvisoryPersistenceSeconds = 60;
inline constexpr uint32_t TemperatureFaultPersistenceSeconds = 300;
inline constexpr float HumidityAdvisoryDifferencePct = 5.0F;
inline constexpr float HumidityFaultDifferencePct = 8.0F;
inline constexpr uint32_t HumidityAdvisoryPersistenceSeconds = 300;
inline constexpr uint32_t HumidityFaultPersistenceSeconds = 600;

inline constexpr uint32_t SensorStaleSeconds = 30;
inline constexpr uint8_t ConsecutiveMissingSamplesForError = 3;
inline constexpr uint32_t FrozenSensorSeconds = 300;

inline constexpr char PreferencesNamespace[] = "ccmonitor";
inline constexpr char SetupAccessPointPrefix[] = "ColdChain-Setup-";
inline constexpr char MonitorAccessPointPrefix[] = "ColdChain-Monitor-";
inline constexpr char AdminUser[] = "admin";
inline constexpr uint16_t HttpPort = 80;
inline constexpr uint16_t MaximumHttpBodyBytes = 2048;
inline constexpr uint16_t HttpClientTimeoutMs = 2000;
}
