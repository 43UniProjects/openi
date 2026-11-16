"""
OpenI Museum Security — Integrated Cyber Defense Dashboard

A high-tech, single-viewport (no-scroll) tactical security command center:
  • Live AI surveillance stream (dual YOLOv26 inference with suspect & weapon tracking)
  • Physical hardware sensor telemetry (PIR motion, DHT22 climate, MQ-2 smoke, Reed contact, SW-420 piezo)
  • Real-time tactical incident log
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

# Global engine reference for MJPEG endpoint
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
        self._sensor_container: ui.element | None = None

        self._build()

    def _build(self):
        ui.dark_mode().enable()
        ui.colors(primary="#0a0f1d", secondary="#111c33", accent="#06b6d4")

        # Global styles: strict single-viewport, custom scrollbars, futuristic fonts
        ui.add_head_html(
            """
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

                * { box-sizing: border-box; }
                html, body {
                    overflow: hidden !important;
                    height: 100vh !important;
                    width: 100vw !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    background-color: #050811 !important;
                    font-family: 'JetBrains Mono', monospace;
                    user-select: none;
                }
                .nicegui-content {
                    padding: 0 !important;
                    height: 100vh !important;
                    display: flex !important;
                    flex-direction: column !important;
                }
                .font-brand {
                    font-family: 'Chakra Petch', sans-serif;
                }
                /* Custom futuristic scrollbar for incident log */
                ::-webkit-scrollbar {
                    width: 5px;
                }
                ::-webkit-scrollbar-track {
                    background: #090e1a;
                }
                ::-webkit-scrollbar-thumb {
                    background: #1e293b;
                    border-radius: 3px;
                }
                ::-webkit-scrollbar-thumb:hover {
                    background: #0ea5e9;
                }
                .glow-border-cyan {
                    box-shadow: 0 0 15px rgba(6, 182, 212, 0.15);
                }
                .glow-border-red {
                    box-shadow: 0 0 20px rgba(239, 68, 68, 0.35);
                }
            </style>
            """
        )

        # ─── Top Tactical Navigation Bar ────────────────────────
        with ui.header().classes(
            "bg-[#080d1a]/90 backdrop-blur-md text-white items-center justify-between "
            "border-b border-cyan-500/20 px-6 py-2 shadow-2xl h-[52px] z-50"
        ):
            # Creative OpenI Cyber Aperture Logo
            with ui.row().classes("items-center gap-3"):
                ui.html(
                    """
                    <div class="flex items-center gap-2.5">
                        <div class="relative flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-950/40 border border-cyan-400/50 shadow-[0_0_12px_rgba(6,182,212,0.4)]">
                            <svg class="w-5 h-5 text-cyan-400 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="3" fill="currentColor" fill-opacity="0.3"></circle>
                                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"></path>
                                <circle cx="12" cy="12" r="6" stroke-dasharray="2 3"></circle>
                            </svg>
                        </div>
                        <div class="flex flex-col leading-none">
                            <span class="font-brand font-black text-lg tracking-[0.18em] text-white">
                                OPEN<span class="text-cyan-400">I</span>
                            </span>
                            <span class="text-[8px] font-mono tracking-[0.25em] text-cyan-500/70 font-semibold uppercase">
                                AI Tactical Defense
                            </span>
                        </div>
                    </div>
                    """
                )

            # Central Threat Level Indicator
            self._status_container = ui.element("div").classes("flex items-center")
            self._render_status_banner(is_threat=False)

            # System Clock & Live Status
            with ui.row().classes("items-center gap-4"):
                self._clock_label = ui.label("").classes(
                    "text-slate-400 text-xs font-mono tracking-wider"
                )
                ui.html(
                    """
                    <div class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/40 border border-red-500/40">
                        <span class="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                        <span class="text-[10px] font-bold text-red-400 tracking-widest font-mono">LIVE FEED</span>
                    </div>
                    """
                )

        # ─── Main Viewport Body (Zero Scroll) ───────────────────
        with (
            ui.element("div")
            .classes("w-full flex-grow flex flex-col gap-3 p-3 bg-[#050811] overflow-hidden")
            .style("height: calc(100vh - 52px);")
        ):
            # Upper Row: Camera (68%) + Incident Log (32%)
            with ui.element("div").classes("flex gap-3 w-full").style("flex: 7; min-height: 0;"):
                # ── Left: AI Surveillance Monitor ───────────────
                with (
                    ui.element("div")
                    .classes(
                        "flex-[2.8] bg-[#090e1a] border border-slate-800 rounded-xl "
                        "p-3 flex flex-col justify-between shadow-xl relative overflow-hidden"
                    )
                    .style("min-height: 0;")
                ):
                    # Camera Header & Telemetry
                    with ui.row().classes("items-center justify-between w-full mb-1.5 px-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.html(
                                '<span class="inline-block w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>'
                            )
                            ui.label("NEURAL THREAT STREAM").classes(
                                "text-xs font-bold text-slate-200 tracking-wider font-brand"
                            )
                        self._source_label = ui.label(self.engine.source_label).classes(
                            "text-[10px] text-cyan-400/70 font-mono bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40"
                        )

                    # Video Viewport Container
                    with (
                        ui.element("div")
                        .classes(
                            "relative w-full rounded-lg border border-slate-800/90 bg-black flex items-center justify-center overflow-hidden"
                        )
                        .style("flex: 1; min-height: 0;")
                    ):
                        ui.html(
                            """
                            <img src="/video_stream"
                                 style="width: 100%; height: 100%; object-fit: contain;"
                                 alt="Live AI Video Stream" />
                            """
                        )

                    # Telemetry HUD Bar
                    with ui.row().classes(
                        "w-full bg-[#060a14] mt-2 px-4 py-2 rounded-lg border border-slate-800/70 "
                        "justify-between items-center text-center"
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
                                    "text-[9px] text-slate-400 tracking-wider font-semibold"
                                )
                                self._cam_stats[key] = (
                                    ui.label(default)
                                    .classes("text-sm font-bold font-mono tracking-tight")
                                    .style(f"color: {color};")
                                )

                # ── Right: Tactical Incident Stream ─────────────
                with (
                    ui.element("div")
                    .classes(
                        "flex-[1.2] bg-[#090e1a] border border-slate-800 rounded-xl "
                        "p-3 flex flex-col shadow-xl"
                    )
                    .style("min-height: 0;")
                ):
                    with ui.row().classes(
                        "items-center justify-between pb-2 border-b border-slate-800"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.html(
                                '<span class="inline-block w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]"></span>'
                            )
                            ui.label("INCIDENT & THREAT FEED").classes(
                                "text-xs font-bold text-slate-200 tracking-wider font-brand"
                            )
                        ui.label("REALTIME").classes(
                            "text-[9px] text-slate-500 font-mono font-bold"
                        )

                    self._log_element = (
                        ui.log(max_lines=60)
                        .classes(
                            "bg-[#04060c] text-slate-300 p-2.5 mt-2 rounded-lg font-mono text-[11px] "
                            "border border-slate-800/60 leading-relaxed"
                        )
                        .style("flex: 1; min-height: 0; overflow-y: auto;")
                    )

            # ── Lower Row: Physical Hardware Telemetry (32%) ──
            with (
                ui.element("div")
                .classes(
                    "w-full bg-[#090e1a] border border-slate-800 rounded-xl p-3 flex flex-col shadow-xl"
                )
                .style("flex: 3; min-height: 0; overflow: hidden;")
            ):
                with ui.row().classes("items-center justify-between w-full mb-2 px-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.html(
                            '<span class="inline-block w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981]"></span>'
                        )
                        ui.label("PERIMETER & ENVIRONMENTAL TELEMETRY").classes(
                            "text-xs font-bold text-slate-200 tracking-wider font-brand"
                        )
                    ui.label("HARDWARE BUS: ONLINE").classes(
                        "text-[9px] text-emerald-400/80 font-mono font-bold tracking-widest"
                    )

                # Exactly 6 high-contrast, large-readout sensor cards
                self._sensor_container = (
                    ui.element("div")
                    .classes(
                        "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 w-full flex-grow"
                    )
                    .style("overflow: hidden;")
                )

        # Periodic Event Timers
        self._refresh_hardware_sensors()
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
                    <div class="flex items-center gap-2 px-3.5 py-1 rounded-full bg-red-950/80 border border-red-500/70 text-red-400 text-xs font-mono font-bold animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.45)]">
                        <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
                        <span>DEFENSE LEVEL: CRITICAL THREAT DETECTED</span>
                    </div>
                    """
                )
            else:
                ui.html(
                    """
                    <div class="flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 text-xs font-mono font-bold">
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

        # Check threat state change
        is_threat = self.engine.threat_active
        if getattr(self, "_last_threat_state", None) != is_threat:
            self._last_threat_state = is_threat
            self._render_status_banner(is_threat=is_threat)

        # Pull AI engine threat alerts into the log
        pending_alerts = self.engine.get_pending_alerts()
        for alert in pending_alerts:
            if self._log_element:
                self._log_element.push(f"🚨 {alert}")

    # ── Hardware Sensor Display ─────────────────────────────────

    def _refresh_hardware_sensors(self):
        sensors: list[HardwareSensor] = self.sensor_provider.read_all()

        self._sensor_container.clear()
        with self._sensor_container:
            for s in sensors:
                border_color = (
                    "#ef4444"
                    if s.status == SensorStatus.CRITICAL
                    else ("#f59e0b" if s.status == SensorStatus.WARNING else "#1e293b")
                )
                bg_glow = (
                    "rgba(239, 68, 68, 0.1)"
                    if s.status == SensorStatus.CRITICAL
                    else (
                        "rgba(245, 158, 11, 0.08)"
                        if s.status == SensorStatus.WARNING
                        else "#060a14"
                    )
                )

                with (
                    ui.element("div")
                    .classes(
                        "rounded-lg p-2.5 flex flex-col justify-between border transition-all duration-300"
                    )
                    .style(
                        f"background-color: {bg_glow}; "
                        f"border-color: {border_color}; "
                        f"border-left: 4px solid {s.color};"
                    )
                ):
                    # Top Row: Sensor Name + Hardware Model
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(s.name).classes(
                            "text-[11px] font-bold text-slate-200 tracking-tight font-brand"
                        )
                        ui.icon(s.icon, size="xs").style(f"color: {s.color};")

                    # Location / Hardware Tag
                    ui.label(f"{s.hardware_model} • {s.location}").classes(
                        "text-[9px] text-slate-400 font-mono tracking-tighter"
                    )

                    # Prominent Big Sensor Value
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(str(s.value)).classes(
                            "text-xl font-black font-mono tracking-tight"
                        ).style(f"color: {s.color};")
                        if s.unit:
                            ui.label(s.unit).classes("text-xs text-slate-400 font-mono")

                    # Bottom Status Badge
                    status_text = (
                        "CRITICAL"
                        if s.status == SensorStatus.CRITICAL
                        else ("WARNING" if s.status == SensorStatus.WARNING else "NORMAL")
                    )
                    status_class = (
                        "text-red-400 bg-red-950/60 border-red-800"
                        if s.status == SensorStatus.CRITICAL
                        else (
                            "text-amber-400 bg-amber-950/60 border-amber-800"
                            if s.status == SensorStatus.WARNING
                            else "text-emerald-400 bg-emerald-950/40 border-emerald-800"
                        )
                    )

                    with ui.row().classes(
                        "items-center justify-between w-full pt-1 border-t border-slate-800/60"
                    ):
                        ui.label(s.id).classes("text-[9px] text-slate-500 font-mono")
                        ui.label(status_text).classes(
                            f"text-[8px] font-bold font-mono px-1.5 py-0.5 rounded border {status_class}"
                        )

        # Check for critical sensor alerts to push to Incident Log
        for s in sensors:
            if s.status == SensorStatus.CRITICAL:
                ts = datetime.now().strftime("%H:%M:%S")
                if self._log_element:
                    self._log_element.push(
                        f"[{ts}] ⚠️ PERIMETER ALERT: {s.name} ({s.location}) - VALUE: {s.value} {s.unit}"
                    )

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
