"""
OpenI Museum Security — Tactical Cyber Defense Command Center

A robust, 100% single-screen (zero-scroll) dashboard layout:
  • Header: OpenI Cyber-Aperture logo, Defense Level banner, System Clock, Live feed tag
  • Upper Area: AI Vision Stream (YOLOv26) with Telemetry HUD + Tactical Incident Stream
  • Bottom Area: 6 Physical Hardware Sensors with prominent, crisp values & status
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi.responses import StreamingResponse
from nicegui import app, ui

from openi.ai.engine import SecurityEngine
from openi.core.logger import logger
from openi.iot.sensors import HardwareSensor, MockSensorProvider, SensorStatus

REFRESH_INTERVAL = 2.0

# Global engine reference for the MJPEG endpoint
_GLOBAL_ENGINE: SecurityEngine | None = None


@app.get("/video_stream")
async def video_stream():
    """High-efficiency MJPEG stream for AI camera viewport."""

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
    logger.info("Dashboard shutdown. Stopping AI engine...")
    if _GLOBAL_ENGINE is not None:
        _GLOBAL_ENGINE.stop()


class SecurityDashboard:
    """Tactical Cyber Defense Command Dashboard for OpenI."""

    def __init__(self, engine: SecurityEngine | None = None):
        global _GLOBAL_ENGINE

        if engine is None:
            engine = SecurityEngine()
            engine.start()

        self.engine = engine
        _GLOBAL_ENGINE = self.engine

        self.sensor_provider = MockSensorProvider()

        # Dynamic UI bindings
        self._cam_stats: dict[str, ui.label] = {}
        self._status_container: ui.element | None = None
        self._clock_label: ui.label | None = None
        self._log_element: ui.log | None = None
        self._bus_status_label: ui.label | None = None
        self._prev_sensor_status: dict[str, SensorStatus] = {}

        # Static card bindings to guarantee zero flicker / instant display
        self._sensor_ui: dict[str, dict] = {}

        self._build()

    def _build(self):
        ui.dark_mode().enable()

        # Global layout styling — lock strictly to 100vh with no scrollbars
        ui.add_head_html(
            """
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

                * { box-sizing: border-box; }
                html, body {
                    overflow: hidden !important;
                    height: 100vh !important;
                    width: 100vw !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    background-color: #040711 !important;
                    font-family: 'JetBrains Mono', monospace;
                    user-select: none;
                }
                .q-header { display: none !important; }
                .q-page-container { padding: 0 !important; }
                .nicegui-content {
                    padding: 0 !important;
                    margin: 0 !important;
                    height: 100vh !important;
                    width: 100vw !important;
                    overflow: hidden !important;
                }
                .font-brand {
                    font-family: 'Chakra Petch', sans-serif;
                }
                ::-webkit-scrollbar {
                    width: 4px;
                }
                ::-webkit-scrollbar-track {
                    background: #070b16;
                }
                ::-webkit-scrollbar-thumb {
                    background: #1e293b;
                    border-radius: 2px;
                }
            </style>
            """
        )

        # ─── Master Single-Screen Layout Container ──────────────
        with ui.element("div").classes(
            "w-screen h-screen flex flex-col bg-[#040711] p-2 gap-2 overflow-hidden"
        ):
            # ── 1. Top Tactical Navigation Bar (Fixed 44px) ─────
            with ui.element("div").classes(
                "w-full h-[44px] bg-[#080d1a] border border-cyan-500/20 rounded-lg px-4 "
                "flex items-center justify-between shadow-lg shrink-0"
            ):
                # Creative OpenI Cyber Aperture Logo
                ui.html(
                    """
                    <div class="flex items-center gap-2.5">
                        <div class="relative flex items-center justify-center w-7 h-7 rounded bg-cyan-950/60 border border-cyan-400/50 shadow-[0_0_10px_rgba(6,182,212,0.4)]">
                            <svg class="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="3" fill="currentColor" fill-opacity="0.4"></circle>
                                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"></path>
                            </svg>
                        </div>
                        <div class="flex flex-col leading-none">
                            <span class="font-brand font-black text-base tracking-[0.18em] text-white">
                                OPEN<span class="text-cyan-400">I</span>
                            </span>
                            <span class="text-[7.5px] font-mono tracking-[0.22em] text-cyan-400/70 uppercase">
                                Autonomous Defense
                            </span>
                        </div>
                    </div>
                    """
                )

                # Central Threat Level Indicator
                self._status_container = ui.element("div").classes("flex items-center")
                self._render_status_banner(is_threat=False)

                # System Clock & Live Status Tag
                with ui.row().classes("items-center gap-3"):
                    self._clock_label = ui.label("").classes(
                        "text-slate-400 text-xs font-mono tracking-wider"
                    )
                    ui.html(
                        """
                        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-red-950/40 border border-red-500/40">
                            <span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span>
                            <span class="text-[9px] font-bold text-red-400 tracking-wider font-mono">LIVE FEED</span>
                        </div>
                        """
                    )

            # ── 2. Middle Row: Video (70%) + Incident Log (30%) ──
            # Takes 100% of the remaining vertical space dynamically
            with ui.element("div").classes("w-full flex gap-2 flex-1 min-h-0 overflow-hidden"):
                # ── Left: AI Surveillance Monitor ───────────────
                with ui.element("div").classes(
                    "flex-[2.8] bg-[#080d1a] border border-slate-800 rounded-lg p-2 "
                    "flex flex-col shadow-xl min-h-0 overflow-hidden"
                ):
                    # Monitor Header
                    with ui.row().classes("items-center justify-between w-full mb-1 shrink-0 px-1"):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.html(
                                '<span class="inline-block w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]"></span>'
                            )
                            ui.label("AI THREAT DETECTION FEED").classes(
                                "text-[11px] font-bold text-slate-200 tracking-wider font-brand"
                            )
                        self._source_label = ui.label(self.engine.source_label).classes(
                            "text-[9px] text-cyan-400/80 font-mono bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40"
                        )

                    # Video Viewport (Absolute Containment - Zero layout pushing)
                    with ui.element("div").classes(
                        "relative w-full flex-1 min-h-0 rounded border border-slate-800/80 bg-black overflow-hidden flex items-center justify-center"
                    ):
                        ui.html(
                            """
                            <img src="/video_stream"
                                 style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain;"
                                 alt="Live AI Video Stream" />
                            """
                        )

                    # Telemetry HUD Bar (Compact bottom bar)
                    with ui.row().classes(
                        "w-full bg-[#050811] mt-1.5 px-3 py-1 rounded border border-slate-800/80 "
                        "justify-between items-center text-center shrink-0"
                    ):
                        hud_metrics = [
                            ("fps", "INFERENCE FPS", "0.0", "#38bdf8"),
                            ("persons", "TRACKED PERSONS", "0", "#10b981"),
                            ("weapons", "WEAPONS FLAGGED", "0", "#f59e0b"),
                            ("suspects", "ARMED SUSPECTS", "0", "#ef4444"),
                        ]
                        for key, label, default, color in hud_metrics:
                            with ui.column().classes("gap-0 items-center"):
                                ui.label(label).classes(
                                    "text-[8.5px] text-slate-400 tracking-wider font-semibold"
                                )
                                self._cam_stats[key] = (
                                    ui.label(default)
                                    .classes("text-xs font-bold font-mono")
                                    .style(f"color: {color};")
                                )

                # ── Right: Tactical Incident Stream ─────────────
                with ui.element("div").classes(
                    "flex-[1.2] bg-[#080d1a] border border-slate-800 rounded-lg p-2 "
                    "flex flex-col shadow-xl min-h-0 overflow-hidden"
                ):
                    with ui.row().classes(
                        "items-center justify-between pb-1 border-b border-slate-800 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.html(
                                '<span class="inline-block w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_#f59e0b]"></span>'
                            )
                            ui.label("INCIDENT & THREAT FEED").classes(
                                "text-[11px] font-bold text-slate-200 tracking-wider font-brand"
                            )
                        ui.label("REALTIME").classes(
                            "text-[8.5px] text-slate-500 font-mono font-bold"
                        )

                    self._log_element = ui.log(max_lines=60).classes(
                        "bg-[#04060c] text-slate-300 p-2 mt-1 rounded font-mono text-[10px] "
                        "border border-slate-800/60 leading-relaxed flex-1 min-h-0 overflow-y-auto"
                    )

            # ── 3. Bottom Row: 6 Hardware Telemetry Cards (Fixed 130px) ──
            # Locked height guaranteed to never get pushed off-screen
            with ui.element("div").classes(
                "w-full h-[130px] min-h-[130px] max-h-[130px] bg-[#080d1a] border border-slate-800 "
                "rounded-lg p-2 flex flex-col shadow-xl shrink-0 overflow-hidden"
            ):
                with ui.row().classes("items-center justify-between w-full mb-1 shrink-0 px-1"):
                    with ui.row().classes("items-center gap-1.5"):
                        ui.html(
                            '<span class="inline-block w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#06b6d4]"></span>'
                        )
                        ui.label("PHYSICAL EXHIBIT & PERIMETER SENSORS (ESP32 BUS)").classes(
                            "text-[11px] font-bold text-slate-200 tracking-wider font-brand"
                        )
                    self._bus_status_label = ui.label("ESP32 BUS: INITIALIZING").classes(
                        "text-[8.5px] text-cyan-400/90 font-mono font-bold tracking-widest"
                    )

                # Pre-build 6 stable cards with permanent DOM handles
                with ui.element("div").classes(
                    "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 w-full flex-1 overflow-hidden"
                ):
                    initial_sensors = self.sensor_provider.read_all()
                    for s in initial_sensors:
                        card_box = (
                            ui.element("div")
                            .classes(
                                "rounded px-2.5 py-1.5 flex flex-col justify-between border bg-[#040711]"
                            )
                            .style(f"border-color: #1e293b; border-left: 3.5px solid {s.color};")
                        )
                        with card_box:
                            # Header
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label(s.name).classes(
                                    "text-[10px] font-bold text-slate-200 font-brand truncate"
                                )
                                ui.icon(s.icon, size="xs").style(f"color: {s.color};")

                            # Subtitle / Model
                            ui.label(f"{s.hardware_model} • {s.location}").classes(
                                "text-[8px] text-slate-400 font-mono truncate"
                            )

                            # Big Value Readout
                            with ui.row().classes("items-baseline gap-1 my-0.5"):
                                val_lbl = (
                                    ui.label(str(s.value))
                                    .classes("text-lg font-black font-mono")
                                    .style(f"color: {s.color};")
                                )
                                unit_lbl = ui.label(s.unit).classes(
                                    "text-[10px] text-slate-400 font-mono"
                                )

                            # Bottom status badge
                            with ui.row().classes(
                                "items-center justify-between w-full pt-0.5 border-t border-slate-800/60"
                            ):
                                ui.label(s.id).classes("text-[8px] text-slate-500 font-mono")
                                status_lbl = ui.label("NORMAL").classes(
                                    "text-[7.5px] font-bold font-mono px-1 py-0.5 rounded border text-emerald-400 bg-emerald-950/40 border-emerald-800"
                                )

                        self._sensor_ui[s.id] = {
                            "val": val_lbl,
                            "unit": unit_lbl,
                            "status": status_lbl,
                            "card": card_box,
                            "color": s.color,
                        }
                        self._prev_sensor_status[s.id] = s.status

        # Periodic Event Timers
        ui.timer(REFRESH_INTERVAL, self._refresh_hardware_sensors)
        ui.timer(0.4, self._sync_engine_telemetry)
        ui.timer(1.0, self._update_clock)

    # ── Status Banner Renderer ──────────────────────────────────

    def _render_status_banner(self, is_threat: bool):
        self._status_container.clear()
        with self._status_container:
            if is_threat:
                ui.html(
                    """
                    <div class="flex items-center gap-2 px-3 py-0.5 rounded-full bg-red-950/80 border border-red-500/70 text-red-400 text-xs font-mono font-bold animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.45)]">
                        <span class="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                        <span>DEFENSE LEVEL: CRITICAL THREAT DETECTED</span>
                    </div>
                    """
                )
            else:
                ui.html(
                    """
                    <div class="flex items-center gap-2 px-3 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 text-xs font-mono font-bold">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span>DEFENSE LEVEL: NOMINAL & SECURE</span>
                    </div>
                    """
                )

    # ── Engine Telemetry Sync ───────────────────────────────────

    def _sync_engine_telemetry(self):
        self._cam_stats["fps"].set_text(f"{self.engine.fps:.1f}")
        self._cam_stats["persons"].set_text(str(self.engine.person_count))
        self._cam_stats["weapons"].set_text(str(self.engine.weapon_count))
        self._cam_stats["suspects"].set_text(str(self.engine.suspect_count))

        # Check threat state change from AI vision
        is_ai_threat = self.engine.threat_active
        self.sensor_provider.set_external_threat(is_ai_threat)

        # Overall defense threat combines AI vision threats + physical perimeter breaches
        summary = self.sensor_provider.get_summary()
        overall_threat = is_ai_threat or summary.get("has_critical", False)

        if getattr(self, "_last_threat_state", None) != overall_threat:
            self._last_threat_state = overall_threat
            self._render_status_banner(is_threat=overall_threat)

        # Pull AI engine threat alerts into the log
        pending_alerts = self.engine.get_pending_alerts()
        for alert in pending_alerts:
            if self._log_element:
                self._log_element.push(f"🚨 {alert}")

    # ── Hardware Sensor Display (Zero DOM Re-creation) ──────────

    def _refresh_hardware_sensors(self):
        sensors: list[HardwareSensor] = self.sensor_provider.read_all()

        # Update ESP32 bus status text
        if self._bus_status_label:
            if getattr(self.sensor_provider, "_is_hardware_connected", False):
                port_name = getattr(self.sensor_provider, "_hardware_port_name", "COM")
                self._bus_status_label.set_text(f"ESP32 BUS: ONLINE ({port_name})")
                self._bus_status_label.classes(
                    replace="text-[8.5px] text-emerald-400 font-mono font-bold tracking-widest"
                )
            else:
                self._bus_status_label.set_text("ESP32 BUS: ACTIVE (DEMO SIMULATION)")
                self._bus_status_label.classes(
                    replace="text-[8.5px] text-cyan-400/90 font-mono font-bold tracking-widest"
                )

        for s in sensors:
            if s.id in self._sensor_ui:
                ui_entry = self._sensor_ui[s.id]
                ui_entry["val"].set_text(str(s.value))
                ui_entry["val"].style(f"color: {s.color};")
                ui_entry["unit"].set_text(s.unit)

                # Status text and class
                status_text = (
                    "CRITICAL"
                    if s.status == SensorStatus.CRITICAL
                    else ("WARNING" if s.status == SensorStatus.WARNING else "NORMAL")
                )
                ui_entry["status"].set_text(status_text)

                if s.status == SensorStatus.CRITICAL:
                    ui_entry["status"].classes(
                        replace="text-[7.5px] font-bold font-mono px-1 py-0.5 rounded border text-red-400 bg-red-950/60 border-red-800"
                    )
                    ui_entry["card"].style(
                        f"border-color: #ef4444; border-left: 3.5px solid {s.color}; background-color: rgba(239, 68, 68, 0.1);"
                    )
                elif s.status == SensorStatus.WARNING:
                    ui_entry["status"].classes(
                        replace="text-[7.5px] font-bold font-mono px-1 py-0.5 rounded border text-amber-400 bg-amber-950/60 border-amber-800"
                    )
                    ui_entry["card"].style(
                        f"border-color: #f59e0b; border-left: 3.5px solid {s.color}; background-color: rgba(245, 158, 11, 0.08);"
                    )
                else:
                    ui_entry["status"].classes(
                        replace="text-[7.5px] font-bold font-mono px-1 py-0.5 rounded border text-emerald-400 bg-emerald-950/40 border-emerald-800"
                    )
                    ui_entry["card"].style(
                        f"border-color: #1e293b; border-left: 3.5px solid {s.color}; background-color: #040711;"
                    )

                # Edge-triggered incident feed logging (avoid repetitive spam)
                prev_status = self._prev_sensor_status.get(s.id, SensorStatus.NORMAL)
                if s.status != prev_status:
                    ts = datetime.now().strftime("%H:%M:%S")
                    if s.status == SensorStatus.CRITICAL and self._log_element:
                        self._log_element.push(
                            f"[{ts}] ⚠️ PERIMETER BREACH: {s.name} ({s.location}) — Status: {s.value} {s.unit}"
                        )
                    elif (
                        prev_status == SensorStatus.CRITICAL
                        and s.status == SensorStatus.NORMAL
                        and self._log_element
                    ):
                        self._log_element.push(
                            f"[{ts}] 🛡️ ZONE SECURED: {s.name} returned to Nominal state."
                        )
                    self._prev_sensor_status[s.id] = s.status

    def _update_clock(self):
        self._clock_label.set_text(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))


def launch_dashboard(
    engine: SecurityEngine | None = None,
    *,
    host: str = "0.0.0.0",
    port: int = 8080,
):
    """Launches the OpenI Security Command Dashboard."""

    @ui.page("/")
    def index():
        SecurityDashboard(engine=engine)

    ui.run(
        title="OpenI — AI Security & Defense Command",
        host=host,
        port=port,
        favicon="👁️",
        dark=True,
        reload=False,
        timeout_graceful_shutdown=0.5,
    )


if __name__ == "__main__":
    launch_dashboard()
