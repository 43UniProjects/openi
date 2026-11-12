"""
OpenI — Museum Security Tracking System
Main Entry Point

Initializes the background AI Vision Engine (dual YOLOv26 inference, Re-ID,
temporal state tracking) and launches the integrated real-time web dashboard.
"""

import sys

from openi.ai.engine import SecurityEngine
from openi.core.logger import logger
from openi.gui.dashboard import launch_dashboard


def main():
    logger.info("Starting OpenI Integrated Museum Security System...")
    engine = SecurityEngine()

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
