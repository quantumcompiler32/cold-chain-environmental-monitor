#include <Arduino.h>
#include <WiFiS3.h>
#include <WiFiFileSystem.h>
#include <WiFiCommands.h>
#include <Modem.h>
#include <Preferences.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>
#include <DHT.h>
#include <RTClib.h>
#include <ArduinoJson.h>
#include <math.h>
#include <string>

#include "AppConfig.h"
#include "Models.h"
#include "DashboardPage.h"

namespace {
WiFiServer webServer(appcfg::HttpPort);
WiFiFileSystem storage;
Preferences preferences;
Adafruit_AHTX0 aht;
Adafruit_BMP280 bmp;
DHT dht(appcfg::DhtDataPin, DHT22);
RTC_DS3231 rtc;

SensorReading reading;
RunConfiguration runConfig;
RuntimeMetrics metrics;

bool setupMode = true;
bool ahtPresent = false;
bool bmpPresent = false;
bool rtcPresent = false;
bool wifiReady = false;
String apPassword;
String deviceSuffix;
String readingsFile;
String eventsFile;
String metadataFile;
uint32_t lastSampleMs = 0;
uint32_t sampleCount = 0;
uint32_t temperatureDisagreementStarted = 0;
uint32_t humidityDisagreementStarted = 0;
float previousDhtTemperature = NAN;
uint32_t unchangedTemperatureStarted = 0;
uint32_t restartAtMs = 0;

struct HttpRequest {
  String method;
  String path;
  String authorization;
  String body;
};

String stateName(MonitorState state) {
  switch (state) {
    case MonitorState::Setup: return "SETUP";
    case MonitorState::Idle: return "IDLE";
    case MonitorState::LoggingNoThreshold: return "LOGGING_NO_THRESHOLD";
    case MonitorState::InRange: return "IN_RANGE";
    case MonitorState::Warning: return "WARNING";
    case MonitorState::PendingExcursion: return "OUTSIDE_RANGE_PENDING";
    case MonitorState::ConfirmedExcursion: return "CONFIRMED_EXCURSION";
    case MonitorState::Recovering: return "RECOVERING";
    case MonitorState::SensorError: return "SENSOR_ERROR";
    case MonitorState::StorageError: return "STORAGE_ERROR";
  }
  return "UNKNOWN";
}

String isoTime(time_t epoch) {
  if (epoch <= 0) return "";
  struct tm timeInfo {};
  gmtime_r(&epoch, &timeInfo);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

time_t currentEpoch() {
  if (rtcPresent && !rtc.lostPower()) return rtc.now().unixtime();
  return static_cast<time_t>(millis() / 1000UL);
}

String sanitize(const String& input) {
  String output;
  for (size_t index = 0; index < input.length(); ++index) {
    const char c = input[index];
    if (isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_') {
      output += c;
    }
  }
  return output.length() ? output.substring(0, 28) : "run";
}

String urlDecode(const String& value) {
  String decoded;
  decoded.reserve(value.length());
  for (size_t index = 0; index < value.length(); ++index) {
    const char c = value[index];
    if (c == '+') {
      decoded += ' ';
    } else if (c == '%' && index + 2 < value.length()) {
      char hex[3] = {value[index + 1], value[index + 2], '\0'};
      decoded += static_cast<char>(strtoul(hex, nullptr, 16));
      index += 2;
    } else {
      decoded += c;
    }
  }
  return decoded;
}

bool hasFormField(const String& body, const String& name) {
  const String needle = name + "=";
  return body.startsWith(needle) || body.indexOf("&" + needle) >= 0;
}

String formField(const String& body, const String& name) {
  const String needle = name + "=";
  int start = body.startsWith(needle) ? 0 : body.indexOf("&" + needle);
  if (start < 0) return "";
  if (start > 0) start++;
  start += needle.length();
  int end = body.indexOf('&', start);
  if (end < 0) end = body.length();
  return urlDecode(body.substring(start, end));
}

String base64Encode(const String& input) {
  static const char table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String output;
  output.reserve(((input.length() + 2) / 3) * 4);
  for (size_t index = 0; index < input.length(); index += 3) {
    const uint32_t a = static_cast<uint8_t>(input[index]);
    const uint32_t b = index + 1 < input.length()
      ? static_cast<uint8_t>(input[index + 1]) : 0;
    const uint32_t c = index + 2 < input.length()
      ? static_cast<uint8_t>(input[index + 2]) : 0;
    const uint32_t triple = (a << 16) | (b << 8) | c;
    output += table[(triple >> 18) & 0x3F];
    output += table[(triple >> 12) & 0x3F];
    output += index + 1 < input.length() ? table[(triple >> 6) & 0x3F] : '=';
    output += index + 2 < input.length() ? table[triple & 0x3F] : '=';
  }
  return output;
}

bool requestAuthenticated(const HttpRequest& request) {
  if (setupMode) return true;
  const String adminPassword = preferences.getString("adminPass", "");
  const String expected = "Basic " +
    base64Encode(String(appcfg::AdminUser) + ":" + adminPassword);
  return adminPassword.length() >= 10 && request.authorization == expected;
}

const char* statusText(int statusCode) {
  switch (statusCode) {
    case 200: return "OK";
    case 302: return "Found";
    case 400: return "Bad Request";
    case 401: return "Unauthorized";
    case 404: return "Not Found";
    case 409: return "Conflict";
    case 413: return "Payload Too Large";
    case 500: return "Internal Server Error";
    case 507: return "Insufficient Storage";
    default: return "Error";
  }
}

void sendHeaders(
  WiFiClient& client,
  int statusCode,
  const char* contentType,
  int32_t contentLength = -1,
  const char* extraHeader = nullptr
) {
  client.print("HTTP/1.1 ");
  client.print(statusCode);
  client.print(" ");
  client.println(statusText(statusCode));
  client.print("Content-Type: ");
  client.println(contentType);
  client.println("Cache-Control: no-store");
  if (contentLength >= 0) {
    client.print("Content-Length: ");
    client.println(contentLength);
  }
  if (extraHeader) client.println(extraHeader);
  client.println("Connection: close");
  client.println();
}

void sendText(
  WiFiClient& client,
  int statusCode,
  const String& body,
  const char* contentType = "text/plain; charset=utf-8",
  const char* extraHeader = nullptr
) {
  sendHeaders(client, statusCode, contentType, body.length(), extraHeader);
  client.print(body);
}

void sendUnauthorized(WiFiClient& client) {
  sendText(
    client,
    401,
    "Administrator sign-in required",
    "text/plain; charset=utf-8",
    "WWW-Authenticate: Basic realm=\"Cold-Chain Monitor\""
  );
}

void sendLargeText(
  WiFiClient& client,
  const char* data,
  size_t length,
  const char* contentType
) {
  sendHeaders(client, 200, contentType, static_cast<int32_t>(length));
  constexpr size_t chunkSize = 512;
  for (size_t offset = 0; offset < length; offset += chunkSize) {
    const size_t count = min(chunkSize, length - offset);
    client.write(reinterpret_cast<const uint8_t*>(data + offset), count);
  }
}

bool readHttpRequest(WiFiClient& client, HttpRequest& request) {
  client.setTimeout(appcfg::HttpClientTimeoutMs);
  String requestLine = client.readStringUntil('\n');
  requestLine.trim();
  if (requestLine.length() == 0) return false;

  const int firstSpace = requestLine.indexOf(' ');
  const int secondSpace = requestLine.indexOf(' ', firstSpace + 1);
  if (firstSpace < 1 || secondSpace < 0) return false;
  request.method = requestLine.substring(0, firstSpace);
  request.path = requestLine.substring(firstSpace + 1, secondSpace);

  int contentLength = 0;
  while (client.connected()) {
    String header = client.readStringUntil('\n');
    header.trim();
    if (header.length() == 0) break;
    if (header.startsWith("Content-Length:")) {
      contentLength = header.substring(15).toInt();
    } else if (header.startsWith("Authorization:")) {
      request.authorization = header.substring(14);
      request.authorization.trim();
    }
  }

  if (contentLength < 0 || contentLength > appcfg::MaximumHttpBodyBytes) {
    sendText(client, 413, "Request body is too large");
    return false;
  }

  request.body.reserve(contentLength);
  const uint32_t started = millis();
  while (
    static_cast<int>(request.body.length()) < contentLength &&
    millis() - started < appcfg::HttpClientTimeoutMs
  ) {
    while (
      client.available() &&
      static_cast<int>(request.body.length()) < contentLength
    ) {
      request.body += static_cast<char>(client.read());
    }
    delay(1);
  }
  return static_cast<int>(request.body.length()) == contentLength;
}

void serviceStatusLed() {
  const uint32_t now = millis();
  bool on = false;
  switch (metrics.state) {
    case MonitorState::ConfirmedExcursion:
    case MonitorState::SensorError:
    case MonitorState::StorageError:
      on = true;
      break;
    case MonitorState::Warning:
    case MonitorState::PendingExcursion:
    case MonitorState::Recovering:
      on = (now / 250UL) % 2 == 0;
      break;
    case MonitorState::Setup:
      on = (now / 800UL) % 2 == 0;
      break;
    default:
      on = false;
      break;
  }
  digitalWrite(appcfg::StatusLedPin, on ? HIGH : LOW);
}

void updateLed() {
  serviceStatusLed();
}

bool writeStored(const String& path, const String& content, int operation) {
  const size_t written = storage.writefile(
    path.c_str(),
    content.c_str(),
    content.length(),
    operation
  );
  if (written != content.length()) {
    metrics.state = MonitorState::StorageError;
    return false;
  }
  metrics.storedBytes += written;
  return true;
}

void appendLine(const String& path, const String& line) {
  const String record = line + "\n";
  writeStored(path, record, WIFI_FILE_APPEND);
}

void streamStoredFile(
  WiFiClient& client,
  const String& path,
  const char* contentType
) {
  sendHeaders(client, 200, contentType);
  int offset = 0;
  constexpr int chunkSize = 768;
  while (client.connected()) {
    std::string result;
    modem.avoid_trim_results();
    const bool ok = modem.write(
      DO_NOT_CHECK_CMD,
      result,
      "%s%d,%d,%s,%d,%d\r\n",
      CMD_WRITE(_FILESYSTEM),
      0,
      WIFI_FILE_READ,
      path.c_str(),
      offset,
      chunkSize
    );
    if (!ok || result.empty()) break;
    client.write(
      reinterpret_cast<const uint8_t*>(result.data()),
      result.size()
    );
    offset += result.size();
    if (static_cast<int>(result.size()) < chunkSize) break;
  }
}

void logEvent(const String& type, const String& note) {
  if (!metrics.runActive) return;
  String safeNote = note;
  safeNote.replace('"', '\'');
  appendLine(
    eventsFile,
    isoTime(currentEpoch()) + ",\"" + type + "\",\"" + safeNote + "\""
  );
  Serial.print("#EVENT,");
  Serial.print(type);
  Serial.print(",");
  Serial.println(safeNote);
}

void saveActiveRun() {
  preferences.putBool("runActive", metrics.runActive);
  preferences.putString("trialId", runConfig.trialId);
  preferences.putString("runToken", metrics.currentRunDirectory);
  preferences.putULong("runStart", metrics.runStartedEpoch);
  preferences.putULong("samples", sampleCount);
  preferences.putULong("stored", metrics.storedBytes);
  preferences.putBool("threshold", runConfig.thresholdEnabled);
  preferences.putFloat("lowerC", runConfig.lowerThresholdC);
  preferences.putFloat("upperC", runConfig.upperThresholdC);
  preferences.putULong("interval", runConfig.sampleIntervalMs);
}

void setRunFileNames(const String& token) {
  readingsFile = "/" + token + "_readings.csv";
  eventsFile = "/" + token + "_events.csv";
  metadataFile = "/" + token + "_metadata.json";
}

void writeMetadata() {
  JsonDocument doc;
  doc["schemaVersion"] = 2;
  doc["firmwareVersion"] = appcfg::FirmwareVersion;
  doc["board"] = "Arduino UNO R4 WiFi";
  doc["storageBackend"] = "UNO R4 WiFi ESP32-S3 file system";
  doc["primarySensor"] = "DHT22";
  doc["trialId"] = runConfig.trialId;
  doc["researcher"] = runConfig.researcher;
  doc["experimentType"] = runConfig.experimentType;
  doc["enclosureType"] = runConfig.enclosureType;
  doc["sensorLocation"] = runConfig.sensorLocation;
  doc["operatingCondition"] = runConfig.operatingCondition;
  doc["notes"] = runConfig.notes;
  doc["thresholdEnabled"] = runConfig.thresholdEnabled;
  doc["lowerThresholdC"] = runConfig.lowerThresholdC;
  doc["upperThresholdC"] = runConfig.upperThresholdC;
  doc["warningMarginC"] = runConfig.warningMarginC;
  doc["sampleIntervalMs"] = runConfig.sampleIntervalMs;
  doc["plannedDurationSeconds"] = runConfig.plannedDurationSeconds;
  doc["excursionPersistenceSeconds"] = runConfig.excursionPersistenceSeconds;
  doc["excursionMinimumSamples"] = runConfig.excursionMinimumSamples;
  doc["recoverySeconds"] = runConfig.recoverySeconds;
  doc["recoveryMinimumSamples"] = runConfig.recoveryMinimumSamples;
  doc["startedAt"] = isoTime(metrics.runStartedEpoch);
  doc["dht22TypicalTemperatureAccuracyC"] = 0.5;
  doc["aht20TypicalTemperatureAccuracyC"] = 0.3;
  doc["temperatureAdvisoryDifferenceC"] =
    appcfg::TemperatureAdvisoryDifferenceC;
  doc["temperatureFaultDifferenceC"] =
    appcfg::TemperatureFaultDifferenceC;
  doc["educationalUseOnly"] = true;
  doc["noSafetyOrDiscardDecision"] = true;
  String output;
  serializeJsonPretty(doc, output);
  writeStored(metadataFile, output, WIFI_FILE_WRITE);
}

bool primaryValid() {
  return reading.dhtValid;
}

void evaluateState() {
  const time_t now = currentEpoch();
  if (!metrics.runActive) {
    metrics.state = setupMode ? MonitorState::Setup : MonitorState::Idle;
    return;
  }
  if (!primaryValid()) {
    metrics.consecutiveMissingSamples++;
    if (
      metrics.consecutiveMissingSamples >=
      appcfg::ConsecutiveMissingSamplesForError
    ) {
      metrics.state = MonitorState::SensorError;
    }
    return;
  }
  metrics.consecutiveMissingSamples = 0;
  metrics.lastValidPrimaryEpoch = now;

  if (
    unchangedTemperatureStarted > 0 &&
    static_cast<uint32_t>(now - unchangedTemperatureStarted) >=
      appcfg::FrozenSensorSeconds
  ) {
    metrics.state = MonitorState::SensorError;
    return;
  }

  const float temperatureDifference = reading.ahtValid && reading.dhtValid
    ? fabsf(
        (reading.ahtTemperatureC - reading.dhtTemperatureC) -
        metrics.baselineTemperatureOffsetC
      )
    : NAN;
  const float humidityDifference = reading.ahtValid && reading.dhtValid
    ? fabsf(
        (reading.ahtHumidityPct - reading.dhtHumidityPct) -
        metrics.baselineHumidityOffsetPct
      )
    : NAN;

  const bool temperatureAdvisory =
    isfinite(temperatureDifference) &&
    temperatureDifference > appcfg::TemperatureAdvisoryDifferenceC;
  const bool temperatureFaultCandidate =
    isfinite(temperatureDifference) &&
    temperatureDifference > appcfg::TemperatureFaultDifferenceC;
  const bool humidityAdvisory =
    isfinite(humidityDifference) &&
    humidityDifference > appcfg::HumidityAdvisoryDifferencePct;
  const bool humidityFaultCandidate =
    isfinite(humidityDifference) &&
    humidityDifference > appcfg::HumidityFaultDifferencePct;

  if (temperatureAdvisory) {
    if (temperatureDisagreementStarted == 0) {
      temperatureDisagreementStarted = now;
    }
  } else {
    temperatureDisagreementStarted = 0;
  }
  if (humidityAdvisory) {
    if (humidityDisagreementStarted == 0) {
      humidityDisagreementStarted = now;
    }
  } else {
    humidityDisagreementStarted = 0;
  }

  const bool disagreementWarning =
    (
      temperatureAdvisory &&
      (now - temperatureDisagreementStarted) >=
        appcfg::TemperatureAdvisoryPersistenceSeconds
    ) ||
    (
      humidityAdvisory &&
      (now - humidityDisagreementStarted) >=
        appcfg::HumidityAdvisoryPersistenceSeconds
    );
  const bool disagreementFault =
    (
      temperatureFaultCandidate &&
      (now - temperatureDisagreementStarted) >=
        appcfg::TemperatureFaultPersistenceSeconds
    ) ||
    (
      humidityFaultCandidate &&
      (now - humidityDisagreementStarted) >=
        appcfg::HumidityFaultPersistenceSeconds
    );

  if (!runConfig.thresholdEnabled) {
    metrics.state = (disagreementWarning || disagreementFault)
      ? MonitorState::Warning
      : MonitorState::LoggingNoThreshold;
    return;
  }

  const float primaryTemperatureC = reading.dhtTemperatureC;
  const bool outside =
    primaryTemperatureC < runConfig.lowerThresholdC ||
    primaryTemperatureC > runConfig.upperThresholdC;
  const bool nearBoundary =
    primaryTemperatureC <=
      runConfig.lowerThresholdC + runConfig.warningMarginC ||
    primaryTemperatureC >=
      runConfig.upperThresholdC - runConfig.warningMarginC;

  if (outside) {
    metrics.consecutiveOutsideSamples++;
    metrics.consecutiveInsideSamples = 0;
    metrics.recoveryStartedEpoch = 0;
    if (metrics.outsideStartedEpoch == 0) {
      metrics.outsideStartedEpoch = now;
    }
    const bool persisted =
      (now - metrics.outsideStartedEpoch) >=
        runConfig.excursionPersistenceSeconds &&
      metrics.consecutiveOutsideSamples >=
        runConfig.excursionMinimumSamples;
    if (
      metrics.state == MonitorState::ConfirmedExcursion ||
      metrics.state == MonitorState::Recovering
    ) {
      metrics.state = MonitorState::ConfirmedExcursion;
    } else if (persisted) {
      metrics.state = MonitorState::ConfirmedExcursion;
      metrics.activeExcursionStartedEpoch = metrics.outsideStartedEpoch;
      metrics.excursionCount++;
      logEvent("EXCURSION_CONFIRMED", "Configured study range exceeded");
    } else {
      metrics.state = MonitorState::PendingExcursion;
    }
  } else {
    metrics.consecutiveOutsideSamples = 0;
    metrics.outsideStartedEpoch = 0;
    if (
      metrics.state == MonitorState::ConfirmedExcursion ||
      metrics.state == MonitorState::Recovering
    ) {
      metrics.state = MonitorState::Recovering;
      metrics.consecutiveInsideSamples++;
      if (metrics.recoveryStartedEpoch == 0) {
        metrics.recoveryStartedEpoch = now;
      }
      if (
        (now - metrics.recoveryStartedEpoch) >= runConfig.recoverySeconds &&
        metrics.consecutiveInsideSamples >= runConfig.recoveryMinimumSamples
      ) {
        logEvent(
          "EXCURSION_RECOVERED",
          "Stable return to configured study range"
        );
        metrics.state = MonitorState::InRange;
        metrics.activeExcursionStartedEpoch = 0;
        metrics.recoveryStartedEpoch = 0;
        metrics.consecutiveInsideSamples = 0;
      }
    } else {
      metrics.state = (nearBoundary || disagreementWarning || disagreementFault)
        ? MonitorState::Warning
        : MonitorState::InRange;
    }
  }
}

void printSerialReading() {
  Serial.print(reading.uptimeMs);
  Serial.print(",");
  Serial.print(reading.sequence);
  Serial.print(",");
  Serial.print(reading.dhtTemperatureC, 3);
  Serial.print(",");
  Serial.print(reading.dhtHumidityPct, 3);
  Serial.print(",");
  Serial.print(reading.bmpTemperatureC, 3);
  Serial.print(",");
  Serial.print(reading.bmpPressureHpa, 3);
  Serial.print(",");
  Serial.print(reading.ahtTemperatureC, 3);
  Serial.print(",");
  Serial.print(reading.ahtHumidityPct, 3);
  Serial.print(",");
  Serial.println(stateName(metrics.state));
}

void readSensors() {
  reading.sequence++;
  reading.uptimeMs = millis();
  reading.epoch = currentEpoch();

  sensors_event_t humidityEvent {};
  sensors_event_t temperatureEvent {};
  if (ahtPresent) {
    aht.getEvent(&humidityEvent, &temperatureEvent);
    reading.ahtTemperatureC = temperatureEvent.temperature;
    reading.ahtHumidityPct = humidityEvent.relative_humidity;
    reading.ahtValid =
      isfinite(reading.ahtTemperatureC) &&
      isfinite(reading.ahtHumidityPct) &&
      reading.ahtTemperatureC >= -40.0F &&
      reading.ahtTemperatureC <= 85.0F &&
      reading.ahtHumidityPct >= 0 &&
      reading.ahtHumidityPct <= 100;
  } else {
    reading.ahtValid = false;
  }

  reading.dhtTemperatureC = dht.readTemperature();
  reading.dhtHumidityPct = dht.readHumidity();
  reading.dhtValid =
    isfinite(reading.dhtTemperatureC) &&
    isfinite(reading.dhtHumidityPct) &&
    reading.dhtTemperatureC >= -40.0F &&
    reading.dhtTemperatureC <= 80.0F &&
    reading.dhtHumidityPct >= 0 &&
    reading.dhtHumidityPct <= 100;

  if (bmpPresent) {
    reading.bmpTemperatureC = bmp.readTemperature();
    reading.bmpPressureHpa = bmp.readPressure() / 100.0F;
    reading.bmpValid =
      isfinite(reading.bmpTemperatureC) &&
      isfinite(reading.bmpPressureHpa) &&
      reading.bmpTemperatureC >= -40.0F &&
      reading.bmpTemperatureC <= 85.0F &&
      reading.bmpPressureHpa >= 300.0F &&
      reading.bmpPressureHpa <= 1100.0F;
  } else {
    reading.bmpValid = false;
  }
  reading.rtcValid = rtcPresent && !rtc.lostPower();

  if (reading.dhtValid && isfinite(previousDhtTemperature)) {
    if (fabsf(reading.dhtTemperatureC - previousDhtTemperature) < 0.001F) {
      if (unchangedTemperatureStarted == 0) {
        unchangedTemperatureStarted = reading.epoch;
      }
    } else {
      unchangedTemperatureStarted = 0;
    }
  }
  if (reading.dhtValid) previousDhtTemperature = reading.dhtTemperatureC;

  evaluateState();
  updateLed();
  printSerialReading();

  if (metrics.runActive) {
    const float tempDifference = reading.ahtValid && reading.dhtValid
      ? fabsf(
          (reading.ahtTemperatureC - reading.dhtTemperatureC) -
          metrics.baselineTemperatureOffsetC
        )
      : NAN;
    const float humidityDifference = reading.ahtValid && reading.dhtValid
      ? fabsf(
          (reading.ahtHumidityPct - reading.dhtHumidityPct) -
          metrics.baselineHumidityOffsetPct
        )
      : NAN;
    String row =
      isoTime(reading.epoch) + "," +
      String(static_cast<unsigned long>(reading.sequence)) + "," +
      String(reading.uptimeMs) + ",";
    row +=
      String(reading.dhtTemperatureC, 3) + "," +
      String(reading.dhtHumidityPct, 3) + "," +
      String(reading.bmpTemperatureC, 3) + "," +
      String(reading.bmpPressureHpa, 3) + "," +
      String(reading.ahtTemperatureC, 3) + "," +
      String(reading.ahtHumidityPct, 3) + ",";
    row +=
      String(reading.dhtValid) + "," +
      String(reading.bmpValid) + "," +
      String(reading.ahtValid) + "," +
      stateName(metrics.state) + "," +
      String(tempDifference, 3) + "," +
      String(humidityDifference, 3);
    appendLine(readingsFile, row);
    sampleCount++;
    if (sampleCount % 30 == 0) saveActiveRun();
    if (
      runConfig.plannedDurationSeconds > 0 &&
      reading.epoch - metrics.runStartedEpoch >=
        runConfig.plannedDurationSeconds
    ) {
      logEvent("PLANNED_DURATION_COMPLETE", "Run stopped automatically");
      metrics.runActive = false;
      metrics.state = MonitorState::Idle;
      saveActiveRun();
    }
  }
}

void startRun(WiFiClient& client, const HttpRequest& request) {
  if (!requestAuthenticated(request)) {
    sendUnauthorized(client);
    return;
  }
  runConfig.trialId = formField(request.body, "trialId");
  runConfig.researcher = formField(request.body, "researcher");
  runConfig.experimentType = formField(request.body, "experimentType");
  runConfig.enclosureType = formField(request.body, "enclosureType");
  runConfig.sensorLocation = formField(request.body, "sensorLocation");
  runConfig.operatingCondition =
    formField(request.body, "operatingCondition");
  runConfig.notes = formField(request.body, "notes");
  runConfig.thresholdEnabled =
    hasFormField(request.body, "thresholdEnabled");
  runConfig.lowerThresholdC =
    formField(request.body, "lowerThresholdC").toFloat();
  runConfig.upperThresholdC =
    formField(request.body, "upperThresholdC").toFloat();
  uint32_t requestedInterval =
    static_cast<uint32_t>(
      max(0L, formField(request.body, "sampleIntervalSeconds").toInt())
    ) * 1000UL;
  runConfig.sampleIntervalMs = constrain(
    requestedInterval,
    appcfg::MinimumSampleIntervalMs,
    appcfg::MaximumSampleIntervalMs
  );
  runConfig.plannedDurationSeconds =
    static_cast<uint32_t>(
      max(0L, formField(request.body, "plannedDurationMinutes").toInt())
    ) * 60UL;
  runConfig.warningMarginC = appcfg::DefaultWarningMarginC;
  runConfig.excursionPersistenceSeconds =
    appcfg::DefaultExcursionPersistenceSeconds;
  runConfig.excursionMinimumSamples =
    appcfg::DefaultExcursionMinimumSamples;
  runConfig.recoverySeconds = appcfg::DefaultRecoverySeconds;
  runConfig.recoveryMinimumSamples =
    appcfg::DefaultRecoveryMinimumSamples;

  if (
    runConfig.trialId.isEmpty() ||
    runConfig.researcher.isEmpty() ||
    (
      runConfig.thresholdEnabled &&
      runConfig.lowerThresholdC >= runConfig.upperThresholdC
    )
  ) {
    sendText(client, 400, "Invalid run configuration");
    return;
  }
  if (metrics.runActive) {
    sendText(client, 409, "A run is already active");
    return;
  }

  const time_t now = currentEpoch();
  metrics = RuntimeMetrics {};
  metrics.runActive = true;
  metrics.runStartedEpoch = now;
  metrics.state = runConfig.thresholdEnabled
    ? MonitorState::InRange
    : MonitorState::LoggingNoThreshold;
  metrics.currentRunDirectory =
    String(static_cast<uint32_t>(now)) + "_" + sanitize(runConfig.trialId);
  setRunFileNames(metrics.currentRunDirectory);
  sampleCount = 0;

  const bool readingsCreated = writeStored(
    readingsFile,
    "timestamp,sequence,uptime_ms,dht22_temp_c,dht22_humidity_pct,"
    "bmp280_temp_c,bmp280_pressure_hpa,aht20_temp_c,aht20_humidity_pct,"
    "dht_valid,bmp_valid,aht_valid,state,temp_difference_c,"
    "humidity_difference_pct\n",
    WIFI_FILE_WRITE
  );
  const bool eventsCreated = writeStored(
    eventsFile,
    "timestamp,event_type,note\n",
    WIFI_FILE_WRITE
  );
  if (!readingsCreated || !eventsCreated) {
    metrics.runActive = false;
    sendText(client, 507, "Unable to create run files");
    return;
  }
  writeMetadata();
  saveActiveRun();
  logEvent("RUN_STARTED", runConfig.experimentType);
  sendText(client, 200, "Run started");
}

void stopRun(WiFiClient& client, const HttpRequest& request) {
  if (!requestAuthenticated(request)) {
    sendUnauthorized(client);
    return;
  }
  if (metrics.runActive) {
    logEvent("RUN_STOPPED", "Stopped from dashboard");
  }
  metrics.runActive = false;
  metrics.state = MonitorState::Idle;
  saveActiveRun();
  sendText(client, 200, "Run stopped");
}

String statusJson() {
  JsonDocument doc;
  doc["setupMode"] = setupMode;
  doc["firmwareVersion"] = appcfg::FirmwareVersion;
  doc["board"] = "Arduino UNO R4 WiFi";
  doc["state"] = stateName(metrics.state);
  JsonObject sensors = doc["sensors"].to<JsonObject>();
  sensors["dht22Present"] = reading.dhtValid;
  sensors["bmp280Present"] = bmpPresent;
  sensors["aht20Present"] = ahtPresent;
  sensors["ds3231Present"] = rtcPresent;
  JsonObject r = doc["reading"].to<JsonObject>();
  r["timestamp"] = isoTime(reading.epoch);
  r["sequence"] = reading.sequence;
  if (reading.dhtValid) {
    r["dhtTemperatureC"] = reading.dhtTemperatureC;
    r["dhtHumidityPct"] = reading.dhtHumidityPct;
  } else {
    r["dhtTemperatureC"] = nullptr;
    r["dhtHumidityPct"] = nullptr;
  }
  if (reading.bmpValid) {
    r["bmpTemperatureC"] = reading.bmpTemperatureC;
    r["bmpPressureHpa"] = reading.bmpPressureHpa;
  } else {
    r["bmpTemperatureC"] = nullptr;
    r["bmpPressureHpa"] = nullptr;
  }
  if (reading.ahtValid) {
    r["ahtTemperatureC"] = reading.ahtTemperatureC;
    r["ahtHumidityPct"] = reading.ahtHumidityPct;
  } else {
    r["ahtTemperatureC"] = nullptr;
    r["ahtHumidityPct"] = nullptr;
  }
  JsonObject quality = doc["quality"].to<JsonObject>();
  const float td = reading.ahtValid && reading.dhtValid
    ? fabsf(
        (reading.ahtTemperatureC - reading.dhtTemperatureC) -
        metrics.baselineTemperatureOffsetC
      )
    : NAN;
  const float hd = reading.ahtValid && reading.dhtValid
    ? fabsf(
        (reading.ahtHumidityPct - reading.dhtHumidityPct) -
        metrics.baselineHumidityOffsetPct
      )
    : NAN;
  if (isfinite(td)) quality["temperatureDifferenceC"] = td;
  else quality["temperatureDifferenceC"] = nullptr;
  if (isfinite(hd)) quality["humidityDifferencePct"] = hd;
  else quality["humidityDifferencePct"] = nullptr;
  if (!reading.dhtValid) {
    quality["message"] = "Primary DHT22 reading unavailable";
  } else if (
    isfinite(td) &&
    td > appcfg::TemperatureFaultDifferenceC
  ) {
    quality["message"] =
      "Temperature disagreement requires investigation";
  } else if (!bmpPresent) {
    quality["message"] =
      "BMP280 not detected; check 3.3 V and SDA/SCL wiring";
  } else if (!ahtPresent) {
    quality["message"] =
      "DHT22/BMP280 mode; AHT20 comparison sensor is optional";
  } else {
    quality["message"] =
      "Readings available; BMP280 temperature is diagnostic only";
  }
  JsonObject run = doc["run"].to<JsonObject>();
  run["active"] = metrics.runActive;
  run["trialId"] = runConfig.trialId;
  run["sampleCount"] = sampleCount;
  run["excursionCount"] = metrics.excursionCount;
  JsonObject storageInfo = doc["storage"].to<JsonObject>();
  storageInfo["backend"] = "UNO R4 WiFi module flash";
  storageInfo["runBytesWritten"] = metrics.storedBytes;
  storageInfo["capacityReported"] = false;
  String response;
  serializeJson(doc, response);
  return response;
}

void configureSecurity(WiFiClient& client, const HttpRequest& request) {
  if (!setupMode) {
    sendText(client, 409, "Already configured");
    return;
  }
  const String newApPassword = formField(request.body, "apPassword");
  const String newAdminPassword = formField(request.body, "adminPassword");
  if (
    newApPassword.length() < 8 ||
    newAdminPassword.length() < 10
  ) {
    sendText(client, 400, "Passwords do not meet minimum length");
    return;
  }
  preferences.putString("apPass", newApPassword);
  preferences.putString("adminPass", newAdminPassword);
  preferences.putBool("configured", true);
  sendText(client, 200, "Saved; the UNO R4 WiFi is restarting");
  restartAtMs = millis() + 1000UL;
}

void recordEvent(WiFiClient& client, const HttpRequest& request) {
  if (!requestAuthenticated(request)) {
    sendUnauthorized(client);
    return;
  }
  if (!metrics.runActive) {
    sendText(client, 409, "No active run");
    return;
  }
  logEvent(
    formField(request.body, "type"),
    formField(request.body, "note")
  );
  sendText(client, 200, "Event recorded");
}

void serveDownload(
  WiFiClient& client,
  const HttpRequest& request,
  const String& path,
  const char* contentType
) {
  if (!requestAuthenticated(request)) {
    sendUnauthorized(client);
    return;
  }
  if (path.isEmpty()) {
    sendText(client, 404, "No run is available");
    return;
  }
  streamStoredFile(client, path, contentType);
}

void routeRequest(WiFiClient& client, const HttpRequest& request) {
  if (request.method == "GET" && request.path == "/") {
    if (!requestAuthenticated(request)) {
      sendUnauthorized(client);
      return;
    }
    sendLargeText(
      client,
      DashboardHtml,
      strlen(DashboardHtml),
      "text/html; charset=utf-8"
    );
  } else if (request.method == "GET" && request.path == "/api/status") {
    if (!requestAuthenticated(request)) {
      sendUnauthorized(client);
      return;
    }
    const String response = statusJson();
    sendText(client, 200, response, "application/json");
  } else if (request.method == "POST" && request.path == "/api/setup") {
    configureSecurity(client, request);
  } else if (
    request.method == "POST" &&
    request.path == "/api/run/start"
  ) {
    startRun(client, request);
  } else if (
    request.method == "POST" &&
    request.path == "/api/run/stop"
  ) {
    stopRun(client, request);
  } else if (
    request.method == "POST" &&
    request.path == "/api/event"
  ) {
    recordEvent(client, request);
  } else if (
    request.method == "GET" &&
    request.path == "/api/download/data"
  ) {
    serveDownload(client, request, readingsFile, "text/csv");
  } else if (
    request.method == "GET" &&
    request.path == "/api/download/events"
  ) {
    serveDownload(client, request, eventsFile, "text/csv");
  } else if (
    request.method == "GET" &&
    request.path == "/api/download/metadata"
  ) {
    serveDownload(client, request, metadataFile, "application/json");
  } else {
    sendText(
      client,
      302,
      "",
      "text/plain",
      "Location: /"
    );
  }
}

void serviceWebServer() {
  if (!wifiReady) return;
  WiFiClient client = webServer.available();
  if (!client) return;
  HttpRequest request;
  if (readHttpRequest(client, request)) {
    routeRequest(client, request);
  }
  delay(2);
  client.stop();
}

void restoreRunIfNeeded() {
  if (!preferences.getBool("runActive", false)) return;
  metrics.runActive = true;
  runConfig.trialId = preferences.getString("trialId", "restored-run");
  runConfig.researcher = "restored after power restart";
  runConfig.experimentType = "restored run";
  runConfig.thresholdEnabled = preferences.getBool("threshold", true);
  runConfig.lowerThresholdC = preferences.getFloat("lowerC", 2.0F);
  runConfig.upperThresholdC = preferences.getFloat("upperC", 8.0F);
  runConfig.sampleIntervalMs =
    preferences.getULong("interval", appcfg::DefaultSampleIntervalMs);
  runConfig.warningMarginC = appcfg::DefaultWarningMarginC;
  runConfig.excursionPersistenceSeconds =
    appcfg::DefaultExcursionPersistenceSeconds;
  runConfig.excursionMinimumSamples =
    appcfg::DefaultExcursionMinimumSamples;
  runConfig.recoverySeconds = appcfg::DefaultRecoverySeconds;
  runConfig.recoveryMinimumSamples =
    appcfg::DefaultRecoveryMinimumSamples;
  metrics.currentRunDirectory =
    preferences.getString("runToken", "restored");
  metrics.runStartedEpoch =
    preferences.getULong("runStart", currentEpoch());
  metrics.storedBytes = preferences.getULong("stored", 0);
  sampleCount = preferences.getULong("samples", 0);
  setRunFileNames(metrics.currentRunDirectory);
  metrics.state = runConfig.thresholdEnabled
    ? MonitorState::InRange
    : MonitorState::LoggingNoThreshold;
  logEvent(
    "POWER_RESTART",
    "Experiment resumed after power restart; verify configuration and clock"
  );
}

void initializeSensors() {
  Wire.begin();
  Wire.setClock(100000);
  ahtPresent = aht.begin(&Wire);
  bmpPresent =
    bmp.begin(0x76, 0x58) ||
    bmp.begin(0x77, 0x58);
  if (bmpPresent) {
    bmp.setSampling(
      Adafruit_BMP280::MODE_NORMAL,
      Adafruit_BMP280::SAMPLING_X2,
      Adafruit_BMP280::SAMPLING_X16,
      Adafruit_BMP280::FILTER_X16,
      Adafruit_BMP280::STANDBY_MS_500
    );
  }
  dht.begin();
  rtcPresent = rtc.begin(&Wire);
  if (rtcPresent && rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
}

void initializeWiFi() {
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("#SYSTEM_ERROR,UNO R4 WiFi radio module not detected");
    metrics.state = MonitorState::SensorError;
    return;
  }

  const String firmwareVersion = WiFi.firmwareVersion();
  if (firmwareVersion < WIFI_FIRMWARE_LATEST_VERSION) {
    Serial.print("#WARNING,Update UNO R4 WiFi connectivity firmware; found ");
    Serial.println(firmwareVersion);
  }

  uint8_t mac[6] = {};
  WiFi.macAddress(mac);
  char suffix[5];
  snprintf(suffix, sizeof(suffix), "%02X%02X", mac[4], mac[5]);
  deviceSuffix = suffix;

  const String ssid =
    String(
      setupMode
        ? appcfg::SetupAccessPointPrefix
        : appcfg::MonitorAccessPointPrefix
    ) + deviceSuffix;
  WiFi.config(IPAddress(192, 168, 4, 1));
  const int status = setupMode
    ? WiFi.beginAP(ssid.c_str())
    : WiFi.beginAP(ssid.c_str(), apPassword.c_str());
  if (status != WL_AP_LISTENING) {
    Serial.println("#SYSTEM_ERROR,Unable to create Wi-Fi access point");
    metrics.state = MonitorState::SensorError;
    return;
  }
  delay(1000);
  webServer.begin();
  wifiReady = true;

  Serial.print("#BOARD,Arduino UNO R4 WiFi\n#FIRMWARE,");
  Serial.println(appcfg::FirmwareVersion);
  Serial.print("#ACCESS_POINT,");
  Serial.println(ssid);
  Serial.print("#DASHBOARD,http://");
  Serial.println(WiFi.localIP());
}
}  // namespace

void setup() {
  Serial.begin(appcfg::SerialBaud);
  const uint32_t waitStart = millis();
  while (!Serial && millis() - waitStart < 3000UL) {
  }

  pinMode(appcfg::StatusLedPin, OUTPUT);
  digitalWrite(appcfg::StatusLedPin, LOW);
  preferences.begin(appcfg::PreferencesNamespace, false);
  setupMode = !preferences.getBool("configured", false);
  apPassword = preferences.getString("apPass", "");

  storage.mount(true);
  initializeSensors();
  dht.begin();
  delay(2000);
  initializeWiFi();
  restoreRunIfNeeded();

  metrics.state = setupMode
    ? MonitorState::Setup
    : (metrics.runActive
      ? (
          runConfig.thresholdEnabled
            ? MonitorState::InRange
            : MonitorState::LoggingNoThreshold
        )
      : MonitorState::Idle);
  updateLed();
  Serial.println(
    "uptime_ms,sequence,dht22_temp_c,dht22_humidity_pct,"
    "bmp280_temp_c,bmp280_pressure_hpa,aht20_temp_c,"
    "aht20_humidity_pct,state"
  );
  lastSampleMs = millis() - appcfg::DefaultSampleIntervalMs;
}

void loop() {
  serviceWebServer();
  serviceStatusLed();

  const uint32_t interval = metrics.runActive
    ? runConfig.sampleIntervalMs
    : appcfg::DefaultSampleIntervalMs;
  if (millis() - lastSampleMs >= interval) {
    lastSampleMs = millis();
    readSensors();
  }

  if (
    restartAtMs > 0 &&
    static_cast<int32_t>(millis() - restartAtMs) >= 0
  ) {
    NVIC_SystemReset();
  }
  delay(2);
}
