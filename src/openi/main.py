"""
OpenI — Museum Security Tracking System
Main Entry Point

Initializes the background AI Vision Engine (dual YOLOv26 inference, Re-ID,
temporal state tracking) and launches the integrated real-time web dashboard.
Includes robust OS-level termination handlers for Windows console environments.
"""

from __future__ import annotations

import ctypes
import os
import signal
import sys

from openi.ai.engine import SecurityEngine
from openi.core.logger import logger
from openi.gui.dashboard import launch_dashboard

# Retain global reference so garbage collection doesn't collect the Windows callback
_WIN_HANDLER = None


def setup_ctrl_c_handler(engine: SecurityEngine):
    """Installs native OS console handlers to ensure instant, clean Ctrl+C exits on Windows."""
    global _WIN_HANDLER

    def cleanup_and_exit():
        logger.info("Shutdown signal received (Ctrl+C). Terminating OpenI safely...")
        try:
            engine.stop()
        except Exception:
            pass
        os._exit(0)

    # Windows native console control handler
    if sys.platform == "win32":
        try:
            HANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

            def win_handler(ctrl_type: int) -> bool:
                # 0 = CTRL_C_EVENT, 1 = CTRL_BREAK_EVENT, 2 = CTRL_CLOSE_EVENT
                if ctrl_type in (0, 1, 2):
                    cleanup_and_exit()
                    return True
                return False

            _WIN_HANDLER = HANDLER_ROUTINE(win_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_WIN_HANDLER, True)
        except Exception as e:
            logger.debug(f"Could not register Windows console handler: {e}")

    # Standard Python signal handlers
    def signal_handler(sig, frame):
        cleanup_and_exit()

    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, signal_handler)
    except Exception:
        pass


def main():
    logger.info("Starting OpenI Integrated Museum Security System...")
    engine = SecurityEngine()
    setup_ctrl_c_handler(engine)

    try:
        engine.start()
        logger.info("AI Vision Engine online. Launching GUI Dashboard...")
        launch_dashboard(engine=engine)
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user.")
    except Exception as e:
        logger.error(f"Unexpected fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Stopping AI Vision Engine...")
        engine.stop()
        logger.info("OpenI System safely terminated.")


if __name__ == "__main__":
    main()
