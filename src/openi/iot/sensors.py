"""
OpenI Museum Security — IoT Sensor Telemetry Provider.

Supports both:
  1. Real ESP32 Hardware via USB Serial (pyserial reading JSON packets)
  2. High-fidelity Physical Simulation of the exact OpenI project hardware kit:
     • Load Cell (5kg Aluminum Block) + HX711 Amplifier Module
     • Laser Diode Emitter (KY-008) + Laser Receiver (GL5528 LDR)
     • Ambient Optical Sensor (GL5528 Photocell Divider)
     • Active Buzzer (3.3V/5V driven by 2N2222 NPN Transistor)
     • Tri-Color Alert LEDs (5mm Red / Green / Blue with 220Ω limiters)
     • ESP32 Development Board (38-pin NodeMCU-32S Master Controller)
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from openi.core.logger import logger

try:
    import serial
    import serial.tools.list_ports

    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


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


class OpenISensorProvider:
    """Unified IoT provider supporting real ESP32 serial communication & simulation."""

    def __init__(self, port: str | None = None, baud: int = 115200):
        self._port = port or os.getenv("ESP32_PORT")
        self._baud = baud

        # Real serial state
        self._ser: serial.Serial | None = None
        self._serial_running = False
        self._serial_thread: threading.Thread | None = None
        self._latest_hardware_json: dict | None = None
        self._lock = threading.Lock()
        self._is_hardware_connected = False
        self._hardware_port_name = "SIMULATED"

        # Simulation state (matched to 5kg Load Cell, KY-008 laser, etc.)
        self._baseline_weight = 854.2  # grams (relic on pedestal)
        self._current_weight = 854.2
        self._laser_breach = False
        self._ambient_adc = 3120
        self._external_threat = False
        self._sim_tick = 0
        self._breach_countdown = 0

        # Attempt auto-detection or connection to physical ESP32
        self._init_serial()

    # ── Serial Subsystem ────────────────────────────────────────

    def _init_serial(self):
        """Attempts to discover and connect to an ESP32 board over USB COM port."""
        if not PYSERIAL_AVAILABLE:
            return

        target_port = self._port
        if not target_port:
            # Auto-detect common USB UART chips (CH340, CP210x, Silicon Labs)
            try:
                available = list(serial.tools.list_ports.comports())
                for p in available:
                    desc = (p.description or "").lower()
                    hwid = (p.hwid or "").lower()
                    if any(
                        k in desc or k in hwid for k in ["cp210", "ch340", "usb-serial", "uart"]
                    ):
                        target_port = p.device
                        break
            except Exception as e:
                logger.debug(f"Port scanning skipped: {e}")

        if target_port:
            try:
                self._ser = serial.Serial(target_port, self._baud, timeout=1.0)
                self._is_hardware_connected = True
                self._hardware_port_name = target_port
                self._serial_running = True
                self._serial_thread = threading.Thread(target=self._serial_worker, daemon=True)
                self._serial_thread.start()
                logger.info(f"Connected to ESP32 hardware on {target_port} @ {self._baud} baud")
            except Exception as e:
                logger.info(
                    f"ESP32 not detected on {target_port} ({e}). Running in realistic simulation mode."
                )
                self._is_hardware_connected = False
                self._hardware_port_name = "SIMULATED"

    def _serial_worker(self):
        """Continuously reads incoming JSON lines from physical ESP32."""
        while self._serial_running and self._ser:
            try:
                if self._ser.in_waiting > 0:
                    raw_bytes = self._ser.readline()
                    line = raw_bytes.decode("utf-8", errors="ignore").strip()
                    if line.startswith("{") and line.endswith("}"):
                        parsed = json.loads(line)
                        with self._lock:
                            self._latest_hardware_json = parsed
                            self._is_hardware_connected = True
            except Exception:
                time.sleep(0.05)

    def set_external_threat(self, threat_active: bool):
        """Notifies sensor provider of AI vision threat state (armed suspect / weapon)."""
        self._external_threat = threat_active

    # ── Telemetry Reader ────────────────────────────────────────

    def read_all(self) -> list[HardwareSensor]:
        """Returns instantaneous snapshot of the 6 core OpenI hardware sensors."""
        with self._lock:
            hw_data = self._latest_hardware_json if self._is_hardware_connected else None

        if hw_data:
            return self._build_from_hardware(hw_data)
        return self._build_from_simulation()

    def _build_from_hardware(self, data: dict) -> list[HardwareSensor]:
        """Parses real telemetry from ESP32 ArduinoJson packet."""
        lc = data.get("loadcell", {})
        laser = data.get("laser", {})
        alert_active = data.get("alert_active", False) or self._external_threat

        weight_g = lc.get("weight_g", 0.0)
        weight_alert = lc.get("alert", False)
        beam_ok = laser.get("beam_ok", True)
        ldr_raw = laser.get("ldr_raw", 0)

        lc_status = SensorStatus.CRITICAL if weight_alert else SensorStatus.NORMAL
        laser_status = SensorStatus.CRITICAL if not beam_ok else SensorStatus.NORMAL
        buzzer_status = SensorStatus.CRITICAL if alert_active else SensorStatus.NORMAL
        led_status = SensorStatus.CRITICAL if alert_active else SensorStatus.NORMAL

        return [
            HardwareSensor(
                id="LC-5KG",
                name="Artifact Weight",
                hardware_model="Load Cell 5kg + HX711",
                location="Exhibit Pedestal",
                value=f"{weight_g:.1f}",
                unit="g",
                status=lc_status,
                icon="scale",
                color="#ef4444" if weight_alert else "#38bdf8",
            ),
            HardwareSensor(
                id="LSR-01",
                name="Laser Tripwire",
                hardware_model="KY-008 Laser + LDR",
                location="Perimeter Beam",
                value="BREACH!" if not beam_ok else "SECURED",
                unit="",
                status=laser_status,
                icon="crisis_alert",
                color="#ef4444" if not beam_ok else "#10b981",
            ),
            HardwareSensor(
                id="LDR-01",
                name="Optical Light Bus",
                hardware_model="GL5528 Photocell",
                location="Pedestal Ambient",
                value=f"{ldr_raw}",
                unit="ADC",
                status=SensorStatus.NORMAL,
                icon="light_mode",
                color="#f59e0b",
            ),
            HardwareSensor(
                id="BUZ-01",
                name="Acoustic Siren",
                hardware_model="Active Buzzer + 2N2222",
                location="Pedestal Alarm",
                value="ALARM (85dB)" if alert_active else "STANDBY",
                unit="",
                status=buzzer_status,
                icon="volume_up",
                color="#ef4444" if alert_active else "#a855f7",
            ),
            HardwareSensor(
                id="LED-01",
                name="Defense Strobe",
                hardware_model="5mm RGB LED Array",
                location="Pedestal Beacon",
                value="RED STROBE" if alert_active else "GREEN OK",
                unit="",
                status=led_status,
                icon="flare",
                color="#ef4444" if alert_active else "#22c55e",
            ),
            HardwareSensor(
                id="ESP-32",
                name="Controller Node",
                hardware_model="ESP32 NodeMCU-32S",
                location=f"USB ({self._hardware_port_name})",
                value="HARDWARE ONLINE",
                unit="",
                status=SensorStatus.NORMAL,
                icon="memory",
                color="#06b6d4",
            ),
        ]

    def _build_from_simulation(self) -> list[HardwareSensor]:
        """Generates realistic telemetry for testing when ESP32 is not yet connected."""
        self._sim_tick += 1

        # Periodic simulated events (e.g. occasional brief perimeter beam breach)
        if self._breach_countdown > 0:
            self._breach_countdown -= 1
            if self._breach_countdown == 0:
                self._laser_breach = False
        elif random.random() < 0.04:  # ~4% chance to simulate a beam cross
            self._laser_breach = True
            self._breach_countdown = 2  # lasts ~4 seconds

        # Load Cell weight micro-fluctuation (±0.15g natural strain gauge noise)
        self._current_weight = round(self._baseline_weight + random.gauss(0, 0.15), 1)

        # Ambient optical noise
        self._ambient_adc = int(3120 + random.gauss(0, 15))

        # Combined alert state
        is_breach = self._laser_breach
        is_alert = is_breach or self._external_threat

        laser_status = SensorStatus.CRITICAL if is_breach else SensorStatus.NORMAL
        buzzer_status = SensorStatus.CRITICAL if is_alert else SensorStatus.NORMAL
        led_status = (
            SensorStatus.CRITICAL
            if is_alert
            else (SensorStatus.WARNING if is_breach else SensorStatus.NORMAL)
        )

        return [
            HardwareSensor(
                id="LC-5KG",
                name="Artifact Weight",
                hardware_model="Load Cell 5kg + HX711",
                location="Exhibit Pedestal",
                value=f"{self._current_weight:.1f}",
                unit="g",
                status=SensorStatus.NORMAL,
                icon="scale",
                color="#38bdf8",
            ),
            HardwareSensor(
                id="LSR-01",
                name="Laser Tripwire",
                hardware_model="KY-008 Laser + LDR",
                location="Perimeter Beam",
                value="BREACH!" if is_breach else "SECURED",
                unit="",
                status=laser_status,
                icon="crisis_alert",
                color="#ef4444" if is_breach else "#10b981",
            ),
            HardwareSensor(
                id="LDR-01",
                name="Optical Light Bus",
                hardware_model="GL5528 Photocell",
                location="Pedestal Ambient",
                value=f"{self._ambient_adc}",
                unit="ADC",
                status=SensorStatus.NORMAL,
                icon="light_mode",
                color="#f59e0b",
            ),
            HardwareSensor(
                id="BUZ-01",
                name="Acoustic Siren",
                hardware_model="Active Buzzer + 2N2222",
                location="Pedestal Alarm",
                value="ALARM (85dB)" if is_alert else "STANDBY",
                unit="",
                status=buzzer_status,
                icon="volume_up",
                color="#ef4444" if is_alert else "#a855f7",
            ),
            HardwareSensor(
                id="LED-01",
                name="Defense Strobe",
                hardware_model="5mm RGB LED Array",
                location="Pedestal Beacon",
                value="RED STROBE" if is_alert else "GREEN OK",
                unit="",
                status=led_status,
                icon="flare",
                color="#ef4444" if is_alert else "#22c55e",
            ),
            HardwareSensor(
                id="ESP-32",
                name="Controller Node",
                hardware_model="ESP32 NodeMCU-32S",
                location="Bridge Node",
                value="ONLINE (115.2k)",
                unit="",
                status=SensorStatus.NORMAL,
                icon="memory",
                color="#06b6d4",
            ),
        ]

    def get_summary(self) -> dict:
        sensors = self.read_all()
        return {
            "sensors": sensors,
            "has_critical": any(s.status == SensorStatus.CRITICAL for s in sensors),
            "has_warning": any(s.status == SensorStatus.WARNING for s in sensors),
        }


# Backward-compatible alias for existing imports
MockSensorProvider = OpenISensorProvider
