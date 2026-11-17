"""
SecurityEngine — Background AI video processing engine.

Coordinates:
  - Dual-model YOLOv26 inference (weapon detection + person tracking)
  - Color-histogram Re-Identification (Re-ID)
  - Multi-frame temporal state tracking
  - MJPEG video frame streaming for NiceGUI
  - Threat event dispatching to the dashboard
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

from openi.ai.detectors import SecurityDetectors, compute_iou, find_primary_carrier
from openi.ai.identifier import Identifier
from openi.core.config import (
    CURRENT_TEST_FOOTAGE,
    FOOTAGE_SRC_TYPE,
    LIVE_FEED_URL,
    PERSON_CONF,
    PERSON_MODEL_PATH,
    REID_THRESHOLD,
    SUSPECT_DIR,
    TEST_VIDEO_PATH,
    WEAPON_CONF,
    WEAPON_KEYWORDS,
    WEAPON_MODEL_PATH,
    WEBCAM_ID,
    SrcType,
)
from openi.core.logger import logger
from openi.tracking.state import SecurityTracker


class SecurityEngine:
    """Manages the real-time AI computer vision pipeline in a background thread."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Telemetry state
        self.fps: float = 0.0
        self.person_count: int = 0
        self.weapon_count: int = 0
        self.suspect_count: int = 0
        self.threat_active: bool = False
        self.source_label: str = "Initializing..."

        # Frame buffer
        self._latest_jpeg: bytes | None = None
        self._alerts: deque[str] = deque(maxlen=50)

        # AI subsystems (initialized in start)
        self.detectors: SecurityDetectors | None = None
        self.reid: Identifier | None = None
        self.tracker: SecurityTracker | None = None

    @property
    def is_running(self) -> bool:
        """Returns True if the worker thread is actively running."""
        return self._running

    def start(self):
        """Initializes AI models and starts video processing thread."""
        if self._running:
            return

        logger.info("Initializing SecurityEngine and loading YOLOv26 models...")
        self.detectors = SecurityDetectors(
            WEAPON_MODEL_PATH,
            PERSON_MODEL_PATH,
            WEAPON_CONF,
            PERSON_CONF,
            WEAPON_KEYWORDS,
        )
        self.reid = Identifier(REID_THRESHOLD)
        self.tracker = SecurityTracker()

        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("SecurityEngine worker thread started successfully.")

    def stop(self):
        """Stops the processing thread safely."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("SecurityEngine stopped.")

    def get_latest_jpeg(self) -> bytes | None:
        """Thread-safe retrieval of the latest processed frame."""
        with self._lock:
            return self._latest_jpeg

    def get_pending_alerts(self) -> list[str]:
        """Pulls and clears pending threat alerts."""
        with self._lock:
            alerts = list(self._alerts)
            self._alerts.clear()
            return alerts

    # ── Internal Video Loop ─────────────────────────────────────

    def _resolve_video_source(self) -> tuple[cv2.VideoCapture | None, str]:
        source = None
        label = "Unknown"

        match FOOTAGE_SRC_TYPE:
            case SrcType.VIDEO:
                path = os.path.join(TEST_VIDEO_PATH, CURRENT_TEST_FOOTAGE)
                label = f"File: {CURRENT_TEST_FOOTAGE}"
                if os.path.isfile(path):
                    source = path
            case SrcType.WEBCAM:
                source = WEBCAM_ID
                label = f"Webcam #{WEBCAM_ID}"
            case SrcType.LIVE:
                source = LIVE_FEED_URL
                label = f"Stream: {LIVE_FEED_URL}"

        if source is None:
            return None, label

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            return None, label
        return cap, label

    def _worker_loop(self):
        cap, label = self._resolve_video_source()
        self.source_label = label

        frame_count = 0
        cached_draw_items = []

        while self._running:
            start_time = time.time()

            # Handle missing or unavailable video source with standby graphic
            if cap is None or not cap.isOpened():
                frame = self._generate_standby_frame(
                    f"Camera Offline / No Feed ({label})",
                    "Add test video to data/test_footages/ or connect webcam.",
                )
                self._update_jpeg(frame)
                time.sleep(0.5)
                # Attempt reconnect every 5 seconds
                if frame_count % 10 == 0:
                    cap, label = self._resolve_video_source()
                    self.source_label = label
                frame_count += 1
                continue

            success, frame = cap.read()
            if not success:
                # Video ended -> loop back to beginning for continuous demo
                if FOOTAGE_SRC_TYPE == SrcType.VIDEO:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    cap.release()
                    cap = None
                    continue

            frame_count += 1
            h, w, _ = frame.shape

            # Run inference on alternate frames for high throughput
            if frame_count % 2 == 0 or frame_count == 1:
                cached_draw_items = []
                raw_weapons = self.detectors.get_weapons(frame)
                raw_persons = self.detectors.get_tracked_persons(frame)

                overlapping_indices = set()
                for i in range(len(raw_persons)):
                    for j in range(i + 1, len(raw_persons)):
                        if compute_iou(raw_persons[i]["coords"], raw_persons[j]["coords"]) > 0.15:
                            overlapping_indices.add(i)
                            overlapping_indices.add(j)

                currently_holding_indices = set()
                for w_item in raw_weapons:
                    carrier_idx = find_primary_carrier(w_item["coords"], raw_persons)
                    if carrier_idx is not None:
                        currently_holding_indices.add(carrier_idx)

                suspects_in_frame = 0

                for idx, p in enumerate(raw_persons):
                    trk_id = p["track_id"]
                    px1, py1, px2, py2 = p["coords"]
                    px1, py1 = max(0, px1), max(0, py1)
                    px2, py2 = min(w, px2), min(h, py2)

                    person_crop = frame[py1:py2, px1:px2]

                    is_holding = idx in currently_holding_indices
                    is_confirmed_armed = self.tracker.update_weapon_strike(trk_id, is_holding)
                    is_prior_suspect = self.tracker.is_prior_suspect(trk_id)

                    matched_reid = False
                    if not is_prior_suspect and not is_confirmed_armed:
                        if self.reid.match(person_crop):
                            matched_reid = self.tracker.update_reid_strike(trk_id, matched=True)
                        else:
                            self.tracker.update_reid_strike(trk_id, matched=False)

                    is_suspect = is_confirmed_armed or is_prior_suspect or matched_reid

                    if is_suspect:
                        suspects_in_frame += 1
                        self.tracker.register_suspect(trk_id)
                        if (
                            is_confirmed_armed
                            and (idx not in overlapping_indices)
                            and person_crop.size > 0
                        ):
                            if self.reid.register_suspect(person_crop):
                                crop_file = os.path.join(
                                    SUSPECT_DIR, f"suspect_{int(time.time() * 1000)}.jpg"
                                )
                                cv2.imwrite(crop_file, person_crop)
                                self._record_alert(f"ARMED SUSPECT #{trk_id} snapshot archived.")

                        cached_draw_items.append(
                            {
                                "coords": (px1, py1, px2, py2),
                                "label": f"SUSPECT #{trk_id}",
                                "color": (0, 0, 255),
                                "thickness": 3,
                            }
                        )
                    else:
                        cached_draw_items.append(
                            {
                                "coords": (px1, py1, px2, py2),
                                "label": f"PERSON #{trk_id}",
                                "color": (0, 255, 0),
                                "thickness": 2,
                            }
                        )

                for w_item in raw_weapons:
                    cached_draw_items.append(
                        {
                            "coords": w_item["coords"],
                            "label": f"{w_item['name'].upper()} {w_item['conf']:.2f}",
                            "color": (0, 0, 255),
                            "thickness": 2,
                        }
                    )

                with self._lock:
                    self.person_count = len(raw_persons)
                    self.weapon_count = len(raw_weapons)
                    self.suspect_count = suspects_in_frame
                    if suspects_in_frame > 0:
                        self.threat_active = True
                        self._alerts.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] THREAT: {suspects_in_frame} Armed Suspect(s) in View!"
                        )
                    else:
                        self.threat_active = False

            # Draw bounding boxes
            for item in cached_draw_items:
                x1, y1, x2, y2 = item["coords"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), item["color"], item["thickness"])
                cv2.putText(
                    frame,
                    item["label"],
                    (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    item["color"],
                    2,
                )

            # Add a subtle, professional corner HUD badge if threat is flagged
            if self.threat_active:
                # Sleek semi-transparent corner indicator (not blocking center view)
                h_img, w_img = frame.shape[:2]
                cv2.rectangle(frame, (w_img - 280, 15), (w_img - 15, 55), (15, 15, 30), -1)
                cv2.rectangle(frame, (w_img - 280, 15), (w_img - 15, 55), (0, 0, 240), 2)
                cv2.putText(
                    frame,
                    "! THREAT DETECTED !",
                    (w_img - 265, 42),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )

            elapsed = time.time() - start_time
            if elapsed > 0:
                self.fps = round(1.0 / elapsed, 1)

            self._update_jpeg(frame)
            time.sleep(max(0.01, 0.033 - elapsed))

        if cap:
            cap.release()

    def _update_jpeg(self, frame: np.ndarray):
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if success:
            with self._lock:
                self._latest_jpeg = encoded.tobytes()

    def _record_alert(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._alerts.append(f"[{timestamp}] {msg}")

    @staticmethod
    def _generate_standby_frame(title: str, subtitle: str) -> np.ndarray:
        """Generates a stylish dark HUD frame when no video source is connected."""
        frame = np.zeros((480, 854, 3), dtype=np.uint8)
        frame[:] = (15, 23, 42)  # Dark slate navy #0f172a

        # Grid lines
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (854, y), (30, 41, 59), 1)
        for x in range(0, 854, 40):
            cv2.line(frame, (x, 0), (x, 480), (30, 41, 59), 1)

        # Center card
        cv2.rectangle(frame, (120, 140), (734, 340), (24, 34, 56), -1)
        cv2.rectangle(frame, (120, 140), (734, 340), (71, 85, 105), 1)

        # Standby text
        cv2.putText(
            frame,
            "OPENI AI VISION FEED",
            (150, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (148, 163, 184),
            2,
        )
        cv2.putText(
            frame,
            title,
            (150, 235),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (239, 68, 68),
            2,
        )
        cv2.putText(
            frame,
            subtitle,
            (150, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (148, 163, 184),
            1,
        )

        # Timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"SYSTEM TIME: {ts}",
            (150, 315),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (100, 116, 139),
            1,
        )

        return frame
