"""
OpenI Museum Security — Integrated NiceGUI Dashboard

Combines:
  • Live AI Security Camera stream (dual YOLOv26 inference with suspect tracking)
  • Real-time IoT sensor network (DHT22 temp/humidity, PIR motion, door reed, smoke, vibration)
  • Threat detection incident log
  • Telemetry data table and trend charts
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime

from fastapi.responses import StreamingResponse
from nicegui import app, ui

from openi.ai.engine import SecurityEngine
from openi.core.logger import logger
from openi.iot.sensors import MockSensorProvider, SensorStatus

# ── Constants ───────────────────────────────────────────────────
REFRESH_INTERVAL = 2.0  # seconds between sensor updates

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

# Global engine reference for the FastAPI video endpoint
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
    """Builds and orchestrates the integrated OpenI Security Dashboard."""

    def __init__(self, engine: SecurityEngine | None = None):
        global _GLOBAL_ENGINE

        if engine is None:
            engine = SecurityEngine()
            engine.start()

        self.engine = engine
        _GLOBAL_ENGINE = self.engine

        self.sensor_provider = MockSensorProvider()
        self.history: dict[str, deque[float]] = {}

        # UI Element handles
        self._stat_labels: dict[str, ui.label] = {}
        self._cam_stats: dict[str, ui.label] = {}
        self._status_banner: ui.label | None = None
        self._status_badge: ui.badge | None = None
        self._log_element: ui.log | None = None
        self._table: ui.table | None = None

        self._build()

    # ── Layout Builder ──────────────────────────────────────────

    def _build(self):
        ui.dark_mode().enable()
        ui.colors(primary="#0f172a", secondary="#1e293b", accent="#ef4444")

        # ─── Top Navigation Header ──────────────────────────────
        with ui.header().classes(
            "bg-[#0f172a] text-white items-center justify-between "
            "border-b border-slate-700 px-6 py-3 shadow-lg"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("security", size="md").classes("text-red-500")
                ui.label("OpenI").classes("text-2xl font-black tracking-tight")
                ui.label("Museum Security & Threat Intelligence").classes(
                    "text-sm text-slate-400 ml-2 hidden sm:block"
                )

            with ui.row().classes("items-center gap-4"):
                self._status_banner = ui.label("SYSTEM SECURE").classes(
                    "text-xs font-bold px-3 py-1 rounded bg-green-950 text-green-400 border border-green-800"
                )
                self._clock_label = ui.label("").classes("text-slate-400 text-sm font-mono")
                self._status_badge = ui.badge("LIVE", color="red").classes("animate-pulse")

        # ─── Main Content Container ─────────────────────────────
        with ui.column().classes("w-full max-w-[1700px] mx-auto px-4 py-6 gap-6"):
            # Row 1: High-Level Telemetry Cards
            self._build_metric_cards()

            # Row 2: AI Video Surveillance + Live Threat Log
            with ui.row().classes("w-full gap-6 flex-wrap lg:flex-nowrap items-stretch"):
                # Left: Live AI Camera Feed
                with ui.card().classes(
                    "flex-[3] bg-[#1e293b] border border-slate-700 rounded-xl "
                    "p-4 shadow-xl flex flex-col gap-3"
                ):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("videocam", size="sm").classes("text-red-400")
                            ui.label("AI Video Stream (YOLOv26 Threat Detection)").classes(
                                "text-lg font-bold text-white"
                            )
                        self._source_label = ui.label(self.engine.source_label).classes(
                            "text-xs text-slate-400 font-mono"
                        )

                    # Video display viewport
                    ui.html(
                        '<div class="relative w-full overflow-hidden rounded-lg border border-slate-800 bg-black aspect-video flex items-center justify-center">'
                        '  <img src="/video_stream" class="w-full h-full object-contain" alt="Security Camera" />'
                        "</div>"
                    )

                    # Video Feed HUD Metrics
                    with ui.row().classes(
                        "w-full bg-[#0f172a] p-3 rounded-lg border border-slate-800 "
                        "justify-around text-center"
                    ):
                        hud_items = [
                            ("fps", "Inference FPS", "0.0", "speed"),
                            ("persons", "Tracked Persons", "0", "group"),
                            ("weapons", "Weapons Detected", "0", "gavel"),
                            ("suspects", "Flagged Suspects", "0", "warning"),
                        ]
                        for key, label, default, icon in hud_items:
                            with ui.row().classes("items-center gap-2"):
                                ui.icon(icon, size="xs").classes("text-slate-400")
                                with ui.column().classes("gap-0 items-start"):
                                    ui.label(label).classes("text-[10px] text-slate-400 uppercase")
                                    self._cam_stats[key] = ui.label(default).classes(
                                        "text-sm font-bold text-white font-mono"
                                    )

                # Right: Threat & Incident Log
                with ui.card().classes(
                    "flex-[1.4] min-w-[340px] bg-[#1e293b] border border-slate-700 "
                    "rounded-xl p-4 shadow-xl flex flex-col"
                ):
                    with ui.row().classes("items-center gap-2 pb-2 border-b border-slate-700"):
                        ui.icon("crisis_alert", size="sm").classes("text-red-400")
                        ui.label("Threat & Incident Log").classes("text-lg font-bold text-white")

                    self._log_element = ui.log(max_lines=60).classes(
                        "flex-grow bg-[#0b1120] text-red-400 p-3 mt-3 "
                        "rounded-lg font-mono text-xs shadow-inner h-[380px]"
                    )

            # Row 3: IoT Sensor Network
            with ui.card().classes(
                "w-full bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl p-4"
            ):
                with ui.row().classes("items-center justify-between w-full mb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("sensors", size="sm").classes("text-cyan-400")
                        ui.label("Museum IoT Sensor Network").classes(
                            "text-lg font-bold text-white"
                        )
                    ui.label("Auto-refreshing every 2s").classes("text-xs text-slate-400")

                self._sensor_grid_container = ui.element("div").classes(
                    "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 pt-2"
                )

            # Row 4: Sensor History Charts
            with ui.card().classes(
                "w-full bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl p-4"
            ):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("show_chart", size="sm").classes("text-purple-400")
                    ui.label("Environmental & Structural Telemetry (Past 30 Samples)").classes(
                        "text-lg font-bold text-white"
                    )
                self._chart_area = ui.element("div").classes(
                    "grid grid-cols-1 md:grid-cols-2 gap-4 pt-2"
                )

            # Row 5: Detailed Data Table
            with ui.card().classes(
                "w-full bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl p-4"
            ):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("table_chart", size="sm").classes("text-blue-400")
                    ui.label("Detailed Sensor Telemetry Table").classes(
                        "text-lg font-bold text-white"
                    )
                self._build_data_table()

        # Timers
        self._refresh()
        ui.timer(REFRESH_INTERVAL, self._refresh)
        ui.timer(0.5, self._sync_engine_telemetry)
        ui.timer(1.0, self._update_clock)

    # ── Sub-component Builders ──────────────────────────────────

    def _build_metric_cards(self):
        stat_defs = [
            ("total_sensors", "Monitored Sensors", "sensors", "#3b82f6", "developer_board"),
            ("normal", "Optimal State", "0", "#22c55e", "check_circle"),
            ("warning", "Warnings / Motion", "0", "#f59e0b", "motion_photos_on"),
            ("critical", "Active Hazards", "0", "#ef4444", "gpp_bad"),
        ]
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for key, title, default, color, icon in stat_defs:
                with ui.card().classes(
                    "flex-1 min-w-[200px] bg-[#1e293b] border border-slate-700 "
                    "rounded-xl p-4 shadow-lg hover:border-slate-500 transition-colors"
                ):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.column().classes("gap-1"):
                            ui.label(title).classes(
                                "text-xs text-slate-400 uppercase tracking-wider"
                            )
                            self._stat_labels[key] = (
                                ui.label(default)
                                .classes("text-3xl font-black")
                                .style(f"color: {color}")
                            )
                        ui.icon(icon, size="lg").classes("opacity-30").style(f"color: {color}")

    def _build_data_table(self):
        columns = [
            {"name": "id", "label": "Sensor ID", "field": "id", "align": "left", "sortable": True},
            {"name": "type", "label": "Type", "field": "type", "align": "left", "sortable": True},
            {"name": "zone", "label": "Zone", "field": "zone", "align": "left", "sortable": True},
            {
                "name": "value",
                "label": "Value",
                "field": "value",
                "align": "right",
                "sortable": True,
            },
            {"name": "unit", "label": "Unit", "field": "unit", "align": "left"},
            {
                "name": "status",
                "label": "Status",
                "field": "status",
                "align": "center",
                "sortable": True,
            },
        ]
        self._table = (
            ui.table(columns=columns, rows=[], row_key="id", pagination={"rowsPerPage": 10})
            .classes("w-full")
            .props("flat bordered dense dark")
        )

    # ── Telemetry Refresh Loop ──────────────────────────────────

    def _sync_engine_telemetry(self):
        """High-frequency sync with the background AI video engine."""
        self._cam_stats["fps"].set_text(f"{self.engine.fps:.1f}")
        self._cam_stats["persons"].set_text(str(self.engine.person_count))
        self._cam_stats["weapons"].set_text(str(self.engine.weapon_count))
        self._cam_stats["suspects"].set_text(str(self.engine.suspect_count))

        # Update threat status banner
        if self.engine.threat_active:
            self._status_banner.set_text("CRITICAL THREAT FLAGGED")
            self._status_banner.classes(
                replace="text-xs font-bold px-3 py-1 rounded bg-red-950 text-red-400 border border-red-700 animate-pulse"
            )
        else:
            self._status_banner.set_text("SYSTEM SECURE")
            self._status_banner.classes(
                replace="text-xs font-bold px-3 py-1 rounded bg-green-950 text-green-400 border border-green-800"
            )

        # Pull AI alerts into incident log
        pending_alerts = self.engine.get_pending_alerts()
        for alert in pending_alerts:
            if self._log_element:
                self._log_element.push(alert)

    def _refresh(self):
        """Refreshes IoT sensor data and telemetry visualizers."""
        summary = self.sensor_provider.get_summary()
        readings = summary["readings"]

        # Update metric cards
        for key in ("total_sensors", "normal", "warning", "critical"):
            if key in self._stat_labels:
                self._stat_labels[key].set_text(str(summary[key]))

        # Rebuild sensor cards
        self._sensor_grid_container.clear()
        with self._sensor_grid_container:
            for r in readings:
                icon = SENSOR_ICONS.get(r.sensor_type, "device_thermostat")
                color = COLORS[r.status]
                status_icon = STATUS_ICONS[r.status]

                with (
                    ui.card()
                    .classes(
                        "bg-[#0f172a] border border-slate-700 rounded-lg p-3 "
                        "hover:border-slate-500 transition-colors"
                    )
                    .style(f"border-left: 3px solid {color}")
                ):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.icon(icon, size="xs").style(f"color: {color}")
                            ui.label(r.sensor_id).classes("text-xs font-bold text-white")
                        ui.icon(status_icon, size="xs").style(f"color: {color}")
                    ui.label(r.zone).classes("text-[10px] text-slate-500 mt-1")
                    with ui.row().classes("items-baseline gap-1 mt-1"):
                        ui.label(str(r.value)).classes("text-lg font-black text-white")
                        ui.label(r.unit).classes("text-[10px] text-slate-400")

        # Update table
        self._table.rows = [
            {
                "id": r.sensor_id,
                "type": r.sensor_type,
                "zone": r.zone,
                "value": r.value,
                "unit": r.unit,
                "status": r.status.value.upper(),
            }
            for r in readings
        ]
        self._table.update()

        # Check for IoT critical events
        for r in readings:
            if r.status == SensorStatus.CRITICAL:
                ts = datetime.now().strftime("%H:%M:%S")
                msg = f"[{ts}] HAZARD: {r.sensor_type} @ {r.zone}: {r.value} {r.unit}"
                if self._log_element:
                    self._log_element.push(msg)

        # Track history for trend charts
        for r in readings:
            if r.sensor_type in ("Temperature", "Humidity", "Smoke", "Vibration"):
                if r.sensor_id not in self.history:
                    self.history[r.sensor_id] = deque(maxlen=30)
                self.history[r.sensor_id].append(r.value)

        # Re-render trend charts
        self._render_charts()

    def _render_charts(self):
        self._chart_area.clear()
        with self._chart_area:
            chart_groups: dict[str, dict[str, list[float]]] = {}
            for sid, values in self.history.items():
                stype = sid.split("-")[0]
                chart_groups.setdefault(stype, {})[sid] = list(values)

            type_labels = {
                "TEMP": ("Temperature Trends", "°C"),
                "HUM": ("Humidity Trends", "%RH"),
                "SMOKE": ("Smoke Particulate Trends", "ppm"),
                "VIB": ("Exhibit Vibration Trends", "g"),
            }
            palette = ["#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4"]

            for stype, sensors_data in chart_groups.items():
                label, unit = type_labels.get(stype, (stype, ""))
                echart_series = []
                for i, (sid, vals) in enumerate(sensors_data.items()):
                    echart_series.append(
                        {
                            "name": sid,
                            "type": "line",
                            "smooth": True,
                            "symbol": "none",
                            "data": vals,
                            "lineStyle": {"width": 2},
                            "itemStyle": {"color": palette[i % len(palette)]},
                        }
                    )

                chart_options = {
                    "backgroundColor": "#0f172a",
                    "title": {
                        "text": label,
                        "textStyle": {"color": "#94a3b8", "fontSize": 13},
                        "left": "center",
                    },
                    "tooltip": {"trigger": "axis"},
                    "legend": {
                        "bottom": 0,
                        "textStyle": {"color": "#94a3b8", "fontSize": 10},
                    },
                    "grid": {"left": "12%", "right": "5%", "top": "18%", "bottom": "18%"},
                    "xAxis": {
                        "type": "category",
                        "show": False,
                        "data": list(range(max(len(v) for v in sensors_data.values()))),
                    },
                    "yAxis": {
                        "type": "value",
                        "name": unit,
                        "nameTextStyle": {"color": "#64748b"},
                        "axisLabel": {"color": "#64748b"},
                        "splitLine": {"lineStyle": {"color": "#1e293b"}},
                    },
                    "series": echart_series,
                }
                ui.echart(chart_options).classes("w-full rounded-lg").style("height: 220px")

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
        title="OpenI — Museum Security & AI Telemetry",
        host=host,
        port=port,
        favicon="🔒",
        dark=True,
        reload=False,
    )


if __name__ == "__main__":
    launch_dashboard()
