"""
OpenI Museum Security — NiceGUI Dashboard

A modern, dark-themed web dashboard that presents:
  • Real-time IoT sensor cards (temp, humidity, motion, door, smoke, vibration)
  • System status overview with aggregate counts
  • Live-updating sensor data table
  • Incident / alert log feed
  • Sensor history sparkline charts

Launch with:  python -m openi.gui.dashboard
Or integrate via:  from openi.gui.dashboard import launch_dashboard
"""

from __future__ import annotations

from collections import deque
from datetime import datetime

from nicegui import ui

from openi.iot.sensors import MockSensorProvider, SensorStatus

# ── Constants ───────────────────────────────────────────────────
REFRESH_INTERVAL = 2.0  # seconds between sensor polls

# Color palette
COLORS = {
    SensorStatus.NORMAL: "#22c55e",  # green-500
    SensorStatus.WARNING: "#f59e0b",  # amber-500
    SensorStatus.CRITICAL: "#ef4444",  # red-500
    SensorStatus.OFFLINE: "#64748b",  # slate-500
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


class SecurityDashboard:
    """Builds and manages the full NiceGUI dashboard."""

    def __init__(self):
        self.provider = MockSensorProvider()
        self.alert_log: deque[str] = deque(maxlen=100)
        self.history: dict[str, deque[float]] = {}  # sensor_id -> last 30 values

        # UI element references (populated in build())
        self._stat_labels: dict[str, ui.label] = {}
        self._sensor_cards: dict[str, dict] = {}
        self._log_element: ui.log | None = None
        self._table_rows: ui.table | None = None
        self._chart_containers: dict[str, ui.element] = {}

        self._build()

    # ── Layout ──────────────────────────────────────────────────

    def _build(self):
        # Apply dark theme globally
        ui.dark_mode().enable()
        ui.colors(primary="#0f172a", secondary="#1e293b", accent="#ef4444")

        # ─── Header ────────────────────────────────────────────
        with ui.header().classes(
            "bg-[#0f172a] text-white items-center justify-between "
            "border-b border-slate-700 px-6 py-3 shadow-lg"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("security", size="md").classes("text-red-500")
                ui.label("OpenI").classes("text-2xl font-black tracking-tight")
                ui.label("Museum Security Dashboard").classes(
                    "text-sm text-slate-400 ml-2 hidden sm:block"
                )
            with ui.row().classes("items-center gap-4"):
                self._clock_label = ui.label("").classes("text-slate-400 text-sm font-mono")
                ui.badge("LIVE", color="red").classes("animate-pulse")

        # ─── Main Content ──────────────────────────────────────
        with ui.column().classes("w-full max-w-[1600px] mx-auto px-4 py-6 gap-6"):
            # Row 1: Status Summary Cards
            self._build_summary_row()

            # Row 2: Sensor Grid + Alert Log
            with ui.row().classes("w-full gap-6 flex-wrap lg:flex-nowrap"):
                # Sensor cards grid (left, wider)
                with ui.card().classes(
                    "flex-[3] bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl"
                ):
                    ui.label("IoT Sensor Network").classes("text-lg font-bold text-white px-4 pt-4")
                    ui.label("Real-time readings from museum sensors").classes(
                        "text-xs text-slate-400 px-4 pb-2"
                    )
                    self._sensor_grid_container = ui.element("div").classes(
                        "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4"
                    )

                # Alert log (right, narrower)
                with ui.card().classes(
                    "flex-[1.2] min-w-[300px] bg-[#1e293b] border border-slate-700 "
                    "rounded-xl shadow-xl flex flex-col"
                ):
                    with ui.row().classes("items-center gap-2 px-4 pt-4 pb-2"):
                        ui.icon("notifications_active", size="sm").classes("text-red-400")
                        ui.label("Incident Log").classes("text-lg font-bold text-white")
                    self._log_element = ui.log(max_lines=50).classes(
                        "flex-grow bg-[#0b1120] text-red-400 p-3 m-3 mt-0 "
                        "rounded-lg font-mono text-xs shadow-inner"
                    )

            # Row 3: Sensor data table
            with ui.card().classes(
                "w-full bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl"
            ):
                ui.label("Sensor Data Table").classes("text-lg font-bold text-white px-4 pt-4 pb-2")
                self._build_data_table()

            # Row 4: History charts
            with ui.card().classes(
                "w-full bg-[#1e293b] border border-slate-700 rounded-xl shadow-xl"
            ):
                ui.label("Sensor History (Last 30 Readings)").classes(
                    "text-lg font-bold text-white px-4 pt-4 pb-2"
                )
                self._chart_area = ui.element("div").classes(
                    "grid grid-cols-1 md:grid-cols-2 gap-4 p-4"
                )

        # Initial data fetch & start the timer
        self._refresh()
        ui.timer(REFRESH_INTERVAL, self._refresh)
        ui.timer(1.0, self._update_clock)

    # ── Summary row ─────────────────────────────────────────────

    def _build_summary_row(self):
        stat_defs = [
            ("total_sensors", "Total Sensors", "sensors", "#3b82f6", "monitor_heart"),
            ("normal", "Normal", "0", "#22c55e", "check_circle"),
            ("warning", "Warnings", "0", "#f59e0b", "warning"),
            ("critical", "Critical", "0", "#ef4444", "error"),
        ]
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for key, title, default, color, icon in stat_defs:
                with ui.card().classes(
                    "flex-1 min-w-[200px] bg-[#1e293b] border border-slate-700 "
                    "rounded-xl p-5 shadow-lg hover:shadow-2xl transition-shadow"
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

    # ── Data table ──────────────────────────────────────────────

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

    # ── Refresh logic ───────────────────────────────────────────

    def _refresh(self):
        summary = self.provider.get_summary()
        readings = summary["readings"]

        # Update stat cards
        for key in ("total_sensors", "normal", "warning", "critical"):
            if key in self._stat_labels:
                self._stat_labels[key].set_text(str(summary[key]))

        # Rebuild sensor mini-cards
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
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(icon, size="xs").style(f"color: {color}")
                            ui.label(r.sensor_id).classes("text-xs font-bold text-white")
                        ui.icon(status_icon, size="xs").style(f"color: {color}")
                    ui.label(r.zone).classes("text-[10px] text-slate-500 mt-1")
                    with ui.row().classes("items-baseline gap-1 mt-1"):
                        ui.label(str(r.value)).classes("text-xl font-black text-white")
                        ui.label(r.unit).classes("text-xs text-slate-400")

        # Update data table
        table_rows = [
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
        self._table.rows = table_rows
        self._table.update()

        # Alerts
        for r in readings:
            if r.status == SensorStatus.CRITICAL:
                msg = (
                    f"[{datetime.now().strftime('%H:%M:%S')}] CRITICAL — "
                    f"{r.sensor_type} @ {r.zone}: {r.value} {r.unit}"
                )
                if self._log_element:
                    self._log_element.push(msg)
            elif r.status == SensorStatus.WARNING and r.sensor_type == "Motion":
                msg = (
                    f"[{datetime.now().strftime('%H:%M:%S')}] MOTION — "
                    f"{r.zone}: Movement detected"
                )
                if self._log_element:
                    self._log_element.push(msg)

        # History tracking for charts
        tracked_sensors = [
            r
            for r in readings
            if r.sensor_type in ("Temperature", "Humidity", "Smoke", "Vibration")
        ]
        for r in tracked_sensors:
            if r.sensor_id not in self.history:
                self.history[r.sensor_id] = deque(maxlen=30)
            self.history[r.sensor_id].append(r.value)

        # Rebuild history charts
        self._chart_area.clear()
        with self._chart_area:
            chart_groups = {}
            for sid, values in self.history.items():
                stype = sid.split("-")[0]  # TEMP, HUM, SMOKE, VIB
                chart_groups.setdefault(stype, {})[sid] = list(values)

            type_labels = {
                "TEMP": ("Temperature History", "°C", "#ef4444"),
                "HUM": ("Humidity History", "%RH", "#3b82f6"),
                "SMOKE": ("Smoke Level History", "ppm", "#f59e0b"),
                "VIB": ("Vibration History", "g", "#a855f7"),
            }

            palette = ["#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4"]

            for stype, sensors_data in chart_groups.items():
                label, unit, color = type_labels.get(stype, (stype, "", "#22c55e"))
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
                    "grid": {
                        "left": "12%",
                        "right": "5%",
                        "top": "18%",
                        "bottom": "18%",
                    },
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
                ui.echart(chart_options).classes("w-full rounded-lg").style("height: 240px")

    def _update_clock(self):
        self._clock_label.set_text(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))


def launch_dashboard(*, host: str = "0.0.0.0", port: int = 8080):
    """Entry point to launch the dashboard as a standalone web app."""

    @ui.page("/")
    def index():
        SecurityDashboard()

    ui.run(
        title="OpenI — Museum Security",
        host=host,
        port=port,
        favicon="🔒",
        dark=True,
        reload=False,
    )


if __name__ == "__main__":
    launch_dashboard()
