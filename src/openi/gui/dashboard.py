from nicegui import ui


class SecurityDashboard:
    def __init__(self):
        # Configure modern dark aesthetic
        ui.colors(primary="#0f172a", secondary="#1e293b", accent="#ef4444")

        with ui.header().classes("bg-secondary text-white border-b border-slate-700"):
            ui.label("OpenI - Museum Security Tracking System").classes("text-2xl font-bold p-4")

        # Main Dashboard Grid
        with ui.row().classes("w-full h-[90vh] p-6 gap-6 bg-primary"):
            # Video Panel: Directly pulls from the MJPEG HTTP stream
            with ui.card().classes(
                "w-[70%] h-full bg-black border border-slate-800 p-0 overflow-hidden shadow-xl"
            ):
                self.video_image = ui.image("/video_stream").classes("w-full h-full object-contain")

            # Sidebar Panel
            with ui.card().classes(
                "flex-grow h-full bg-secondary border border-slate-700 p-6 flex flex-col gap-4 shadow-xl"
            ):
                self.status_label = ui.label("SYSTEM SECURE").classes(
                    "text-green-500 text-3xl font-bold text-center w-full pb-4 border-b border-slate-600"
                )

                ui.label("Incident Logs").classes("text-slate-300 text-lg font-semibold mt-4")

                self.log_box = ui.log(max_lines=50).classes(
                    "w-full flex-grow bg-[#0b1120] text-red-400 p-4 rounded-md font-mono text-sm shadow-inner"
                )

    def trigger_alert(self, message):
        """Updates the UI state dynamically when a threat is detected."""
        self.status_label.set_text("THREAT DETECTED")
        self.status_label.classes(
            replace="text-red-500 text-3xl font-bold text-center w-full pb-4 border-b border-slate-600 animate-pulse"
        )
        self.log_box.push(f"[ALERT] {message}")
