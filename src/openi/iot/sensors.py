"""
Mock IoT sensor data provider for the OpenI Museum Security System.

Simulates real hardware sensors connected via microcontrollers (e.g., ESP32 / Arduino):
  1. PIR Motion Sensor (HC-SR501) — Perimeter & zone motion
  2. Climate Temperature (DHT22) — Gallery climate control
  3. Climate Humidity (DHT22) — Gallery relative humidity
  4. Gas & Smoke Detector (MQ-2) — Smoke / hazardous fumes detection
  5. Magnetic Door Contact (Reed Switch) — Vault / restricted door breach
  6. Piezo Vibration Sensor (SW-420) — Exhibit glass & display case impact
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum


class SensorStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HardwareSensor:
    id: str
    name: str
    hardware_model: str
    location: str
    value: float | str
    unit: str
    status: SensorStatus
    icon: str
    color: str
    updated_at: float = field(default_factory=time.time)


class MockSensorProvider:
    """Simulates realistic micro-fluctuations for physical IoT hardware."""

    def __init__(self):
        self._temp = 22.4
        self._hum = 46.5
        self._smoke = 0.08
        self._vibration = 0.012
        self._door_open = False
        self._motion_detected = False
        self._tick = 0

    def read_all(self) -> list[HardwareSensor]:
        """Returns snapshot of the 6 primary physical IoT sensors."""
        self._tick += 1

        # 1. PIR Motion Sensor
        # ~10% probability of motion
        if random.random() < 0.12:
            self._motion_detected = not self._motion_detected
        pir_status = SensorStatus.WARNING if self._motion_detected else SensorStatus.NORMAL

        # 2. Temperature (DHT22)
        self._temp = round(self._temp + random.gauss(0, 0.15), 1)
        self._temp = max(18.0, min(32.0, self._temp))
        temp_status = (
            SensorStatus.CRITICAL
            if self._temp > 29
            else (SensorStatus.WARNING if self._temp > 26 else SensorStatus.NORMAL)
        )

        # 3. Humidity (DHT22)
        self._hum = round(self._hum + random.gauss(0, 0.3), 1)
        self._hum = max(30.0, min(75.0, self._hum))
        hum_status = (
            SensorStatus.WARNING if self._hum > 60 or self._hum < 35 else SensorStatus.NORMAL
        )

        # 4. MQ-2 Smoke Detector
        self._smoke = max(0.01, round(self._smoke + random.gauss(0, 0.04), 2))
        smoke_status = (
            SensorStatus.CRITICAL
            if self._smoke > 3.0
            else (SensorStatus.WARNING if self._smoke > 1.2 else SensorStatus.NORMAL)
        )

        # 5. Door Reed Switch
        if random.random() < 0.03:
            self._door_open = not self._door_open
        door_status = SensorStatus.CRITICAL if self._door_open else SensorStatus.NORMAL

        # 6. Piezo Vibration
        self._vibration = max(0.001, round(abs(random.gauss(0.015, 0.006)), 3))
        vib_status = (
            SensorStatus.CRITICAL
            if self._vibration > 0.08
            else (SensorStatus.WARNING if self._vibration > 0.04 else SensorStatus.NORMAL)
        )

        return [
            HardwareSensor(
                id="PIR-01",
                name="Perimeter Motion",
                hardware_model="HC-SR501",
                location="Main Gallery",
                value="ACTIVE" if self._motion_detected else "CLEAR",
                unit="",
                status=pir_status,
                icon="radar",
                color="#f59e0b" if self._motion_detected else "#10b981",
            ),
            HardwareSensor(
                id="DHT-T1",
                name="Ambient Temp",
                hardware_model="DHT22",
                location="Artifact Hall",
                value=f"{self._temp}",
                unit="°C",
                status=temp_status,
                icon="device_thermostat",
                color="#38bdf8",
            ),
            HardwareSensor(
                id="DHT-H1",
                name="Humidity",
                hardware_model="DHT22",
                location="Vault Room",
                value=f"{self._hum}",
                unit="%",
                status=hum_status,
                icon="water_drop",
                color="#818cf8",
            ),
            HardwareSensor(
                id="MQ2-01",
                name="Smoke / Gas",
                hardware_model="MQ-2",
                location="Central Hall",
                value=f"{self._smoke}",
                unit="ppm",
                status=smoke_status,
                icon="air",
                color="#ef4444" if smoke_status == SensorStatus.CRITICAL else "#22c55e",
            ),
            HardwareSensor(
                id="REED-01",
                name="Vault Door",
                hardware_model="Reed Switch",
                location="Restricted Vault",
                value="BREACHED" if self._door_open else "LOCKED",
                unit="",
                status=door_status,
                icon="lock_open" if self._door_open else "lock",
                color="#ef4444" if self._door_open else "#10b981",
            ),
            HardwareSensor(
                id="VIB-01",
                name="Case Vibration",
                hardware_model="SW-420 Piezo",
                location="Display #04",
                value=f"{self._vibration}",
                unit="g",
                status=vib_status,
                icon="vibration",
                color="#a855f7",
            ),
        ]

    def get_summary(self) -> dict:
        sensors = self.read_all()
        return {
            "sensors": sensors,
            "has_critical": any(s.status == SensorStatus.CRITICAL for s in sensors),
            "has_warning": any(s.status == SensorStatus.WARNING for s in sensors),
        }
