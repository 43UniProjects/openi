import os
from pathlib import Path

from dotenv import load_dotenv

from .types import SrcType

load_dotenv()  # loads variables from .env into the process environment

# Resolve absolute paths based on the new nested location
# This file is in src/museum_security/core/, so the project root is 3 levels up
ROOT_DIR = Path(__file__).resolve().parents[3]

# System Directories
SUSPECT_DIR = os.path.join(ROOT_DIR, "data", "saved_suspects")
os.makedirs(SUSPECT_DIR, exist_ok=True)

FOOTAGE_SRC_TYPE: SrcType = SrcType.VIDEO

TEST_VIDEO_PATH = os.path.join(ROOT_DIR, "data", "test_footages")

CURRENT_TEST_FOOTAGE = os.getenv(
    "CURRENT_TEST_FOOTAGE", "test.mp4"
)  # keep test videos at data\test_footages\ directory
WEBCAM_ID = int(os.getenv("WEBCAM_ID", "0"))
LIVE_FEED_URL = os.getenv("LIVE_FEED_URL", "")

# Neural Network Paths (Compiled for Intel OpenVINO CPU Optimization)
WEAPON_MODEL_PATH = os.path.join(ROOT_DIR, "models", "best_openvino_model")
PERSON_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8n_openvino_model")

# Mathematical Thresholds
WEAPON_CONF = 0.60
PERSON_CONF = 0.45
REID_THRESHOLD = 0.75

# Supported Classes
WEAPON_KEYWORDS = [
    "gun",
    "pistol",
    "rifle",
    "handgun",
    "shotgun",
    "weapon",
    "firearm",
    "machine gun",
    "knife",
    "sword",
    "blade",
]
