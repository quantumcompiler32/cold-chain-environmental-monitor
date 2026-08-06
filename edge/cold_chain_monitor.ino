/*
  Cold-chain temperature monitor

  Hardware:
    - Arduino UNO R4 WiFi or UNO R4 Minima
    - DHT22 data pin connected to D2
    - DHT22 VCC -> 5V, GND -> GND
    - 10k pull-up resistor between DHT22 DATA and VCC

  Install the "DHT sensor library" by Adafruit before uploading.
  The serial output is CSV-friendly:
    milliseconds,temperature_c,humidity_pct,alarm
*/

#include <DHT.h>

constexpr uint8_t DHT_PIN = 2;
constexpr uint8_t DHT_TYPE = DHT22;
constexpr float MIN_SAFE_C = 2.0;
constexpr float MAX_SAFE_C = 8.0;
constexpr unsigned long SAMPLE_INTERVAL_MS = 2000;

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastSampleMs = 0;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.begin(115200);
  unsigned long startMs = millis();
  while (!Serial && millis() - startMs < 3000) {
    delay(10);
  }

  dht.begin();
  Serial.println("milliseconds,temperature_c,humidity_pct,alarm");
}

void loop() {
  if (millis() - lastSampleMs < SAMPLE_INTERVAL_MS) {
    return;
  }
  lastSampleMs = millis();

  const float humidity = dht.readHumidity();
  const float temperatureC = dht.readTemperature();

  if (isnan(humidity) || isnan(temperatureC)) {
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.print(millis());
    Serial.println(",ERROR,ERROR,SENSOR_ERROR");
    return;
  }

  const bool alarm = temperatureC < MIN_SAFE_C || temperatureC > MAX_SAFE_C;
  digitalWrite(LED_BUILTIN, alarm ? HIGH : LOW);

  Serial.print(millis());
  Serial.print(',');
  Serial.print(temperatureC, 2);
  Serial.print(',');
  Serial.print(humidity, 2);
  Serial.print(',');
  Serial.println(alarm ? "OUT_OF_RANGE" : "OK");
}
