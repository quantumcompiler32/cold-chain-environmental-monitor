#!/usr/bin/env python3
"""List serial ports and stream UNO R4 WiFi diagnostic output."""

from __future__ import annotations

import argparse
import sys
import time

import serial
from serial.tools import list_ports


def choose_port(explicit: str | None) -> str:
    if explicit:
        return explicit
    ports = list(list_ports.comports())
    likely = [p for p in ports if any(token in (p.description or "").lower() for token in ("usb", "uart", "serial", "jtag"))]
    candidates = likely or ports
    if not candidates:
        raise RuntimeError("No serial ports found")
    for index, port in enumerate(candidates, start=1):
        print(f"{index}. {port.device} — {port.description}")
    selection = int(input("Select port: "))
    return candidates[selection - 1].device


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    port = choose_port(args.port)
    print(f"Opening {port} at {args.baud}. Press Ctrl+C to stop.")
    with serial.Serial(port, args.baud, timeout=1) as connection:
        time.sleep(1)
        while True:
            line = connection.readline().decode("utf-8", errors="replace").rstrip()
            if line:
                print(line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
