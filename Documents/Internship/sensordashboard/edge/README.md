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

`images/` contains the available board, sensor, wiring, and architecture
reference images. `tools/serial_diagnostics.py` lists serial ports and streams
diagnostic output from a connected board at 115200 baud.

## Serial diagnostic setup

From the project root, install the optional serial dependency and run:

```bash
python3 -m pip install pyserial
python3 edge/tools/serial_diagnostics.py --port /dev/cu.usbmodemXXXX
```

The serial tool does not publish MQTT events. Hardware firmware, pin choices,
sensor calibration, power requirements, Wi-Fi behavior, and upload procedure
must be validated on the physical board before being used as a production
source. The deterministic backend generator remains the reproducible demo
input.
