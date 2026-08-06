# Edge hardware

This folder contains the sensor-side reference material for the vaccine
cold-chain demonstration. The verified conference flow runs the deterministic
event generator in `backend/`; the Arduino hardware path is optional and is
not required to run PostgreSQL, MQTT, the dashboard bridge, or the frontend.

## Hardware covered

- Arduino UNO R4 WiFi: the intended Wi-Fi-capable board.
- Arduino UNO R4 Minima: reference hardware without the Wi-Fi module.
- DHT22: temperature/humidity sensor reference.
- BMP280 and AHT20: I2C comparison-sensor reference material.

`images/` contains the available board, sensor, wiring, and prototype
reference images. No Arduino sketch or firmware source is currently present
in this checkout; the Arduino path is documented as planned hardware work in
the research report. The deterministic backend generator remains the
reproducible conference-demo input.

## Hardware notes

The planned wiring uses DHT22 for air temperature/relative humidity and
BMP280 for a secondary temperature/pressure channel. The UNO R4 WiFi and UNO
R4 Minima are reference boards; firmware, pin choices, calibration,
power requirements, Wi-Fi behavior, and upload procedure must be validated on
the physical board before use. No sensor program is allowed to be treated as
a calibrated vaccine data logger.
