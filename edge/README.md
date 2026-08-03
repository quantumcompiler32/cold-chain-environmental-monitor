# Experimental UNO R4 WiFi edge prototype

This folder contains an untested Arduino edge prototype for the vaccine
cold-chain environmental-monitoring project. It documents the project's
possible hardware direction and is not part of the currently verified
MQTT/PostgreSQL demonstration.

## Current status

The firmware was not successfully tested or uploaded during the project work.
Build, board behavior, sensor readings, Wi-Fi behavior, authentication,
storage, and long-running reliability still need hardware validation. Treat all
features below as possibilities represented in the source, not verified claims.

The firmware targets the **Arduino UNO R4 WiFi**. The UNO R4 Minima is not
supported by this firmware because it depends on the UNO R4 WiFi connectivity
module and `WiFiS3`.

## Possible capabilities in the source

- Private local Wi-Fi setup and monitoring access at `http://192.168.4.1`.
- DHT22 primary temperature and humidity readings.
- BMP280 diagnostic temperature and pressure readings.
- Optional AHT20 comparison readings and sensor-disagreement checks.
- Optional DS3231 timestamps and power-restart recovery.
- Configurable 2-8 °C study range or no-threshold observation mode.
- Warning, pending excursion, confirmed excursion, recovery, sensor-error, and
  storage-error states.
- Persistent run settings and run files on the UNO R4 WiFi connectivity module.
- CSV, event-log, and metadata downloads from the embedded dashboard.
- USB serial output at 115200 baud.
- Manual event recording for door changes, cooling interruptions, sensor moves,
  reference readings, and other observed events.
- Planned run duration, run metadata, and a basic embedded temperature chart.

## Hardware and wiring

Expected core hardware:

- Arduino UNO R4 WiFi
- DHT22 three-pin module on digital pin D2
- BMP280 on the I2C SDA/SCL pins
- Data-capable USB-C cable

Optional hardware includes an AHT20 or AHT20/BMP280 module and a DS3231 RTC.
Read the wiring information before applying power; the BMP280 module described
by the project uses 3.3 V.

## Build and upload attempt

The project uses PlatformIO and its configuration is in `platformio.ini`.
From this directory, a future hardware test can use:

```bash
pio run
pio run --target upload
pio device monitor --baud 115200
```

These commands describe the intended workflow; they are not evidence that the
current firmware builds, uploads, or operates correctly on the available board.

## Important limitations and future work

- Complete a real PlatformIO build and upload on an UNO R4 WiFi.
- Confirm each sensor's wiring, I2C address, voltage requirements, and reading quality.
- Verify first-boot setup, local Wi-Fi access, authentication, and restart recovery.
- Validate flash-storage limits and download preservation for completed runs.
- Test excursion and recovery state transitions with controlled temperature experiments.
- Decide how edge events should map into the backend MQTT event contract.
- Add a tested transport path from the edge device to the backend pipeline.
- Validate calibration, placement, uncertainty, and deployment protocol before using measurements operationally.

This prototype is not a certified medical device, compliance instrument,
potency estimator, or vaccine use/discard system.
