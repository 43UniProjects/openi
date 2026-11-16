"""
OpenI Museum Security — Integrated NiceGUI Dashboard

A single-viewport (no-scroll) security command center combining:
  • Live AI camera feed with YOLOv26 threat detection
  • Key IoT sensor readings (temperature, humidity, smoke, motion, door)
  • Real-time incident log
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi.responses import StreamingResponse
from nicegui import app, ui

from openi.ai.engine import SecurityEngine
from openi.core.logger import logger
from openi.iot.sensors import MockSensorProvider, SensorStatus

# ── Constants ───────────────────────────────────────────────────
REFRESH_INTERVAL = 2.0

COLORS = {
    SensorStatus.NORMAL: "#22c55e",
    SensorStatus.WARNING: "#f59e0b",
    SensorStatus.CRITICAL: "#ef4444",
    SensorStatus.OFFLINE: "#64748b",
}

STATUS_ICONS = {
    SensorStatus.NORMAL: "check_circle",
    SensorStatus.WARNING: "warning",
    SensorStatus.CRITICAL: "error",
    SensorStatus.OFFLINE: "cloud_off",
}

SENSOR_ICONS = {
    "Temperature": "thermostat",
    "Humidity": "water_drop",
    "Motion": "directions_walk",
    "Door Contact": "door_front",
    "Smoke": "local_fire_department",
    "Vibration": "vibration",
}

# Global engine reference for MJPEG endpoint
_GLOBAL_ENGINE: SecurityEngine | None = None


@app.get("/video_stream")
async def video_stream():
    """MJPEG streaming endpoint for the AI camera feed."""

    async def frame_generator():
        try:
            while _GLOBAL_ENGINE is not None and _GLOBAL_ENGINE.is_running:
                jpeg = _GLOBAL_ENGINE.get_latest_jpeg()
                if jpeg is not None:
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                await asyncio.sleep(0.033)
        except (asyncio.CancelledError, GeneratorExit):
            pass

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.on_shutdown
def handle_app_shutdown():
    """Ensures AI worker threads are cleanly terminated on server exit."""
    logger.info("NiceGUI shutdown signal received. Stopping background engine...")
    if _GLOBAL_ENGINE is not None:
        _GLOBAL_ENGINE.stop()


class SecurityDashboard:
    """Single-viewport security command center dashboard."""

    def __init__(self, engine: SecurityEngine | None = None):
        global _GLOBAL_ENGINE

        if engine is None:
            engine = SecurityEngine()
            engine.start()

        self.engine = engine
        _GLOBAL_ENGINE = self.engine

        self.sensor_provider = MockSensorProvider()

        # UI element handles
        self._cam_stats: dict[str, ui.label] = {}
        self._status_banner: ui.label | None = None
        self._clock_label: ui.label | None = None
        self._log_element: ui.log | None = None
        self._sensor_container: ui.element | None = None

        self._build()

    def _build(self):
        ui.dark_mode().enable()
        ui.colors(primary="#0f172a", secondary="#1e293b", accent="#ef4444")

        # Prevent page scroll — full viewport layout
        ui.add_head_html(
            "<style>"
            "html, body { overflow: hidden !important; height: 100vh !important; }"
            ".nicegui-content { padding: 0 !important; }"
            "</style>"
        )

        # ─── Header Bar ────────────────────────────────────────
        with ui.header().classes(
            "bg-[#0f172a] text-white items-center justify-between "
            "border-b border-slate-700 px-6 py-2 shadow-lg h-[48px]"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("security", size="sm").classes("text-red-500")
                ui.label("OpenI").classes("text-xl font-black tracking-tight")
                ui.label("Security Command Center").classes(
                    "text-xs text-slate-400 ml-1 hidden sm:block"
                )

            with ui.row().classes("items-center gap-3"):
                self._status_banner = ui.label("SYSTEM SECURE").classes(
                    "text-[10px] font-bold px-2 py-0.5 rounded "
                    "bg-green-950 text-green-400 border border-green-800"
                )
                self._clock_label = ui.label("").classes("text-slate-400 text-xs font-mono")
                ui.badge("LIVE", color="red").classes("animate-pulse text-[10px]")

        # ─── Main Body — fills remaining viewport height ───────
        with (
            ui.element("div")
            .classes("w-full bg-[#0f172a] flex flex-col")
            .style("height: calc(100vh - 48px); overflow: hidden; padding: 12px;")
        ):
            # ── Top Row: Camera Feed + Log ──────────────────────
            with ui.element("div").classes("flex gap-3 w-full").style("flex: 3; min-height: 0;"):
                # Left: AI Camera Panel
                with (
                    ui.card()
                    .classes(
                        "bg-[#1e293b] border border-slate-700 rounded-lg "
                        "p-3 shadow-lg flex flex-col gap-2 flex-[3]"
                    )
                    .style("min-height: 0;")
                ):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("videocam", size="xs").classes("text-red-400")
                            ui.label("AI Camera Feed").classes("text-sm font-bold text-white")
                        self._source_label = ui.label(self.engine.source_label).classes(
                            "text-[10px] text-slate-400 font-mono"
                        )

                    # Video viewport — flexible height
                    ui.html(
                        '<div style="flex: 1; min-height: 0;" '
                        'class="relative w-full overflow-hidden rounded-md border border-slate-800 bg-black flex items-center justify-center">'
                        '  <img src="/video_stream" style="width: 100%; height: 100%; object-fit: contain;" alt="Feed" />'
                        "</div>"
                    ).style("flex: 1; min-height: 0;")

                    # HUD stats bar
                    with ui.row().classes(
                        "w-full bg-[#0f172a] px-3 py-1.5 rounded border border-slate-800 "
                        "justify-around text-center"
                    ):
                        hud_items = [
                            ("fps", "FPS", "0.0", "speed"),
                            ("persons", "Persons", "0", "group"),
                            ("weapons", "Weapons", "0", "gavel"),
                            ("suspects", "Suspects", "0", "warning"),
                        ]
                        for key, label, default, icon in hud_items:
                            with ui.row().classes("items-center gap-1"):
                                ui.icon(icon, size="xs").classes("text-slate-500")
                                ui.label(label).classes("text-[10px] text-slate-400 uppercase")
                                self._cam_stats[key] = ui.label(default).classes(
                                    "text-xs font-bold text-white font-mono"
                                )

                # Right: Incident Log
                with (
                    ui.card()
                    .classes(
                        "bg-[#1e293b] border border-slate-700 rounded-lg "
                        "p-3 shadow-lg flex flex-col flex-[1.2]"
                    )
                    .style("min-height: 0;")
                ):
                    with ui.row().classes("items-center gap-2 pb-2 border-b border-slate-700"):
                        ui.icon("crisis_alert", size="xs").classes("text-red-400")
                        ui.label("Incident Log").classes("text-sm font-bold text-white")

                    self._log_element = (
                        ui.log(max_lines=50)
                        .classes(
                            "bg-[#0b1120] text-red-400 p-2 mt-2 "
                            "rounded font-mono text-[11px] shadow-inner"
                        )
                        .style("flex: 1; min-height: 0; overflow-y: auto;")
                    )

            # Spacer
            ui.element("div").style("height: 12px; flex-shrink: 0;")

            # ── Bottom Row: Sensor Readings ─────────────────────
            with (
                ui.card()
                .classes("w-full bg-[#1e293b] border border-slate-700 rounded-lg p-3 shadow-lg")
                .style("flex: 1; min-height: 0; overflow: hidden;")
            ):
                with ui.row().classes("items-center justify-between w-full mb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("sensors", size="xs").classes("text-cyan-400")
                        ui.label("IoT Sensor Network").classes("text-sm font-bold text-white")
                    ui.label("Mock Data — Auto-refreshing").classes("text-[10px] text-slate-400")

                self._sensor_container = (
                    ui.element("div")
                    .classes("grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2")
                    .style("overflow: hidden;")
                )

        # Timers
        self._refresh_sensors()
        ui.timer(REFRESH_INTERVAL, self._refresh_sensors)
        ui.timer(0.5, self._sync_engine)
        ui.timer(1.0, self._update_clock)

    # ── Engine Sync ─────────────────────────────────────────────

    def _sync_engine(self):
        """Syncs AI camera telemetry into the HUD."""
        self._cam_stats["fps"].set_text(f"{self.engine.fps:.1f}")
        self._cam_stats["persons"].set_text(str(self.engine.person_count))
        self._cam_stats["weapons"].set_text(str(self.engine.weapon_count))
        self._cam_stats["suspects"].set_text(str(self.engine.suspect_count))

        # Status banner
        if self.engine.threat_active:
            self._status_banner.set_text("THREAT DETECTED")
            self._status_banner.classes(
                replace="text-[10px] font-bold px-2 py-0.5 rounded "
                "bg-red-950 text-red-400 border border-red-700 animate-pulse"
            )
        else:
            self._status_banner.set_text("SYSTEM SECURE")
            self._status_banner.classes(
                replace="text-[10px] font-bold px-2 py-0.5 rounded "
                "bg-green-950 text-green-400 border border-green-800"
            )

        # AI alerts → log
        for alert in self.engine.get_pending_alerts():
            if self._log_element:
                self._log_element.push(alert)

    # ── Sensor Refresh ──────────────────────────────────────────

    def _refresh_sensors(self):
        """Refreshes IoT sensor compact cards."""
        summary = self.sensor_provider.get_summary()
        readings = summary["readings"]

        self._sensor_container.clear()
        with self._sensor_container:
            for r in readings:
                icon = SENSOR_ICONS.get(r.sensor_type, "device_thermostat")
                color = COLORS[r.status]
                status_icon = STATUS_ICONS[r.status]

                with (
                    ui.card()
                    .classes(
                        "bg-[#0f172a] border border-slate-700 rounded p-2 "
                        "hover:border-slate-500 transition-colors"
                    )
                    .style(f"border-left: 3px solid {color}")
                    .props("flat")
                ):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.icon(icon, size="xs").style(f"color: {color}")
                        ui.icon(status_icon, size="xs").style(f"color: {color}")
                    ui.label(r.sensor_id).classes("text-[10px] font-bold text-white mt-0.5")
                    ui.label(r.zone).classes("text-[9px] text-slate-500")
                    with ui.row().classes("items-baseline gap-0.5 mt-0.5"):
                        ui.label(str(r.value)).classes("text-sm font-black text-white")
                        ui.label(r.unit).classes("text-[9px] text-slate-400")

        # Critical alerts → log
        for r in readings:
            if r.status == SensorStatus.CRITICAL:
                ts = datetime.now().strftime("%H:%M:%S")
                if self._log_element:
                    self._log_element.push(
                        f"[{ts}] HAZARD: {r.sensor_type} @ {r.zone}: {r.value} {r.unit}"
                    )

    def _update_clock(self):
        self._clock_label.set_text(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))


def launch_dashboard(
    engine: SecurityEngine | None = None,
    *,
    host: str = "0.0.0.0",
    port: int = 8080,
):
    """Entry point to launch the integrated OpenI Security Dashboard."""

    @ui.page("/")
    def index():
        SecurityDashboard(engine=engine)

    ui.run(
        title="OpenI — Museum Security",
        host=host,
        port=port,
        favicon="🔒",
        dark=True,
        reload=False,
        timeout_graceful_shutdown=0.5,
    )


if __name__ == "__main__":
    launch_dashboard()
