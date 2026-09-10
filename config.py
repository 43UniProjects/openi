import os

# System Directories
SUSPECT_DIR = "suspects"
os.makedirs(SUSPECT_DIR, exist_ok=True)

# Neural Network Paths
WEAPON_MODEL_PATH = 'best_openvino_model/'
PERSON_MODEL_PATH = 'yolov8n_openvino_model/'

# Mathematical Thresholds
WEAPON_CONF = 0.60
PERSON_CONF = 0.45
REID_THRESHOLD = 0.75

# Supported Classes
WEAPON_KEYWORDS = [
    'gun', 'pistol', 'rifle', 'handgun', 'shotgun', 'weapon',
    'firearm', 'machine gun', 'knife', 'sword', 'blade'
]
