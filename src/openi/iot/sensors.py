"""
Mock IoT sensor data provider for the OpenI Museum Security System.

Simulates real-time readings from museum-grade sensors:
  - Temperature & Humidity (DHT22 style)
  - PIR Motion Sensors (per-zone)
  - Door/Window Contact Sensors (magnetic reed)
  - Smoke / Gas Detectors
  - Vibration Sensors (artifact display cases)

All values fluctuate realistically around configurable baselines.
When the system connects to real hardware (ESP32 / Raspberry Pi),
swap this module for the actual MQTT or serial reader.
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum


class SensorStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class ZoneID(str, Enum):
    MAIN_HALL = "Main Hall"
    GALLERY_A = "Gallery A"
    GALLERY_B = "Gallery B"
    ENTRANCE = "Entrance"
    STORAGE = "Storage Room"
    CORRIDOR = "Corridor"


@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    zone: str
    value: float
    unit: str
    status: SensorStatus
    timestamp: float = field(default_factory=time.time)


class MockSensorProvider:
    """Generates realistic fluctuating sensor data for the dashboard."""

    def __init__(self):
        self._baselines = {
            "temperature": 22.5,  # °C — ideal museum climate
            "humidity": 45.0,  # %RH
            "vibration": 0.02,  # g (acceleration)
        }
        self._motion_zones = {z: False for z in ZoneID}
        self._door_zones = {
            ZoneID.ENTRANCE: True,  # open during hours
            ZoneID.STORAGE: False,  # should stay closed
            ZoneID.MAIN_HALL: True,
        }
        self._smoke_level = 0.0  # ppm
        self._tick = 0

    # ── Public API ──────────────────────────────────────────────

    def read_all(self) -> list[SensorReading]:
        """Return a snapshot of every sensor in the museum."""
        self._tick += 1
        readings: list[SensorReading] = []

        # Temperature sensors (one per zone)
        for zone in ZoneID:
            temp = self._jitter(self._baselines["temperature"], sigma=0.4)
            readings.append(
                SensorReading(
                    sensor_id=f"TEMP-{zone.name[:3]}",
                    sensor_type="Temperature",
                    zone=zone.value,
                    value=round(temp, 1),
                    unit="°C",
                    status=self._threshold(temp, low=18, high=26, crit_high=30),
                )
            )

        # Humidity sensors (one per zone)
        for zone in ZoneID:
            hum = self._jitter(self._baselines["humidity"], sigma=2.0)
            readings.append(
                SensorReading(
                    sensor_id=f"HUM-{zone.name[:3]}",
                    sensor_type="Humidity",
                    zone=zone.value,
                    value=round(hum, 1),
                    unit="%RH",
                    status=self._threshold(hum, low=30, high=60, crit_high=70),
                )
            )

        # PIR motion sensors
        for zone in ZoneID:
            # ~15 % chance of motion each tick
            motion = random.random() < 0.15
            self._motion_zones[zone] = motion
            readings.append(
                SensorReading(
                    sensor_id=f"PIR-{zone.name[:3]}",
                    sensor_type="Motion",
                    zone=zone.value,
                    value=1.0 if motion else 0.0,
                    unit="detected" if motion else "clear",
                    status=SensorStatus.WARNING if motion else SensorStatus.NORMAL,
                )
            )

        # Door contact sensors
        for zone, default_open in self._door_zones.items():
            # Small chance the door state flips
            if random.random() < 0.05:
                self._door_zones[zone] = not self._door_zones[zone]
            is_open = self._door_zones[zone]
            # Storage door open is critical
            is_critical = zone == ZoneID.STORAGE and is_open
            readings.append(
                SensorReading(
                    sensor_id=f"DOOR-{zone.name[:3]}",
                    sensor_type="Door Contact",
                    zone=zone.value,
                    value=1.0 if is_open else 0.0,
                    unit="OPEN" if is_open else "CLOSED",
                    status=(SensorStatus.CRITICAL if is_critical else SensorStatus.NORMAL),
                )
            )

        # Smoke detector (building-wide)
        self._smoke_level = max(0, self._jitter(self._smoke_level, sigma=0.3))
        # Very rare spike to simulate false alarm
        if random.random() < 0.01:
            self._smoke_level = random.uniform(5, 15)
        readings.append(
            SensorReading(
                sensor_id="SMOKE-BLD",
                sensor_type="Smoke",
                zone="Building-Wide",
                value=round(self._smoke_level, 2),
                unit="ppm",
                status=self._threshold(self._smoke_level, low=-1, high=5, crit_high=10),
            )
        )

        # Vibration sensors on display cases
        for zone in [ZoneID.MAIN_HALL, ZoneID.GALLERY_A, ZoneID.GALLERY_B]:
            vib = abs(self._jitter(self._baselines["vibration"], sigma=0.01))
            readings.append(
                SensorReading(
                    sensor_id=f"VIB-{zone.name[:3]}",
                    sensor_type="Vibration",
                    zone=zone.value,
                    value=round(vib, 4),
                    unit="g",
                    status=self._threshold(vib, low=-1, high=0.08, crit_high=0.15),
                )
            )

        return readings

    def get_summary(self) -> dict:
        """Return aggregate counts for quick dashboard cards."""
        readings = self.read_all()
        total = len(readings)
        normal = sum(1 for r in readings if r.status == SensorStatus.NORMAL)
        warning = sum(1 for r in readings if r.status == SensorStatus.WARNING)
        critical = sum(1 for r in readings if r.status == SensorStatus.CRITICAL)
        motion_zones = [z.value for z, m in self._motion_zones.items() if m]
        return {
            "total_sensors": total,
            "normal": normal,
            "warning": warning,
            "critical": critical,
            "motion_zones": motion_zones,
            "readings": readings,
        }

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _jitter(base: float, sigma: float = 1.0) -> float:
        return base + random.gauss(0, sigma)

    @staticmethod
    def _threshold(
        value: float,
        low: float,
        high: float,
        crit_high: float,
    ) -> SensorStatus:
        if value >= crit_high:
            return SensorStatus.CRITICAL
        if value >= high or value <= low:
            return SensorStatus.WARNING
        return SensorStatus.NORMAL
