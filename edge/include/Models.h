#pragma once

#include <Arduino.h>

struct SensorReading {
  uint64_t sequence = 0;
  uint32_t uptimeMs = 0;
  time_t epoch = 0;
  float ahtTemperatureC = NAN;
  float ahtHumidityPct = NAN;
  float dhtTemperatureC = NAN;
  float dhtHumidityPct = NAN;
  float bmpTemperatureC = NAN;
  float bmpPressureHpa = NAN;
  bool ahtValid = false;
  bool dhtValid = false;
  bool bmpValid = false;
  bool rtcValid = false;
};

enum class MonitorState : uint8_t {
  Setup,
  Idle,
  LoggingNoThreshold,
  InRange,
  Warning,
  PendingExcursion,
  ConfirmedExcursion,
  Recovering,
  SensorError,
  StorageError
};

struct RunConfiguration {
  String trialId;
  String researcher;
  String experimentType;
  String enclosureType;
  String sensorLocation;
  String operatingCondition;
  String notes;
  bool thresholdEnabled = false;
  float lowerThresholdC = 2.0F;
  float upperThresholdC = 8.0F;
  float warningMarginC = 0.5F;
  uint32_t sampleIntervalMs = 10000;
  uint32_t plannedDurationSeconds = 0;
  uint32_t excursionPersistenceSeconds = 60;
  uint16_t excursionMinimumSamples = 3;
  uint32_t recoverySeconds = 300;
  uint16_t recoveryMinimumSamples = 5;
};

struct RuntimeMetrics {
  bool runActive = false;
  MonitorState state = MonitorState::Idle;
  uint32_t runStartedEpoch = 0;
  uint32_t outsideStartedEpoch = 0;
  uint32_t recoveryStartedEpoch = 0;
  uint16_t consecutiveOutsideSamples = 0;
  uint16_t consecutiveInsideSamples = 0;
  uint8_t consecutiveMissingSamples = 0;
  uint32_t excursionCount = 0;
  uint32_t activeExcursionStartedEpoch = 0;
  float baselineTemperatureOffsetC = 0.0F;
  float baselineHumidityOffsetPct = 0.0F;
  uint32_t lastValidPrimaryEpoch = 0;
  uint32_t lastSampleEpoch = 0;
  String currentRunDirectory;
  uint32_t storedBytes = 0;
};
