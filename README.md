```markdown
# OpenI — Contributor Setup & Run Guide

![Python Version](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&logoColor=white)
![Task Runner](https://img.shields.io/badge/task_runner-just-black)
![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

This guide covers how to configure, build, and run the OpenI codebase locally based on your machine's available hardware (CPU-only vs. dedicated NVIDIA GPU).

---

## 📋 Prerequisites

Ensure the following tools are installed on your machine before starting:

- **Python:** `>= 3.10`
- **Git:** Installed and added to your system `PATH`
- **`just` (Command Runner):**
  - **Windows:** `winget install Casey.Just`
  - **macOS / Linux:** `brew install just`
- **NVIDIA GPU *(Optional)*:** CUDA Toolkit `11.8+` (only required if running GPU-accelerated inference)

---

## 📂 Key Directories

```text
OpenI/
├── data/
│   ├── test_footages/      # Place local test videos here
│   └── saved_suspects/     # Auto-generated output directory for captures
├── models/
│   ├── *.pt                # Base YOLO model weights
│   └── *_openvino_model/   # Generated OpenVINO model exports
├── src/
│   └── openi/
│       ├── ai/             # Detection and identification
│       ├── core/           # Configuration, logging, and shared types
│       ├── gui/            # Dashboard and application routing
│       ├── iot/            # Sensor integrations
│       ├── tracking/       # Tracking state management
│       ├── __main__.py     # Module entry point
│       └── main.py         # Application entry point
├── tests/                  # Automated tests
├── example.env             # Template for local environment variables
├── justfile                # Task runner commands
├── pyproject.toml          # Dependencies and linter config
├── .pre-commit-config.yaml # Git hook configuration
└── README.md               # Project documentation
```

---

## 🚀 Installation & Hardware Setup

### 1. Clone the Repository

```bash
git clone <your-github-repo-url>
cd openi

```

### 2. Place Base Model Weights

Ensure both base YOLO weights are inside the `models/` directory before running the application:

* `models/yolov26n.pt`
* `models/weapon.pt`

### 3. Set Up According to Your Hardware

Follow **Option A** if you are running on a standard laptop/desktop CPU, or **Option B** if you have a dedicated NVIDIA GPU.

#### Option A: CPU-Only Setup (OpenVINO)

1. **Create the environment and install CPU dependencies:**
```bash
just setup

```


2. **Activate the virtual environment:**
* **Windows:** `.\.venv\Scripts\activate`
* **macOS / Linux:** `source .venv/bin/activate`


3. **Compile the `.pt` models to OpenVINO format:**
```bash
yolo export model=models/yolov26n.pt format=openvino imgsz=416
yolo export model=models/weapon.pt format=openvino imgsz=416

```


4. **Verify `src/openi/core/config.py`:** Ensure `PERSON_MODEL_PATH` and `WEAPON_MODEL_PATH` point to the generated `models/yolov26n_openvino_model` and `models/weapon_openvino_model` folders.

#### Option B: Dedicated NVIDIA GPU Setup (CUDA)

1. **Create the environment and install GPU dependencies:**
```bash
just setup-gpu

```


2. **Verify `src/openi/core/config.py`:** Ensure `PERSON_MODEL_PATH` and `WEAPON_MODEL_PATH` point directly to the raw PyTorch files (`models/yolov26n.pt` and `models/weapon.pt`).

---

## ⚙️ Environment Configuration

1. Duplicate `example.env` in the project root and rename it to `.env`:
```dotenv
FOOTAGE_SRC_TYPE=video
CURRENT_TEST_FOOTAGE=
WEBCAM_ID=0
LIVE_FEED_URL=

```


2. Configure the variables based on the input source you want to test:

| Variable | Accepted Values | Usage |
| --- | --- | --- |
| `FOOTAGE_SRC_TYPE` | `video`, `webcam`, `live` | Selects which video input mode to use on startup. |
| `CURRENT_TEST_FOOTAGE` | Filename (e.g., `knife.MOV`) | Used when `FOOTAGE_SRC_TYPE=video`. File must be inside `data/test_footages/`. |
| `WEBCAM_ID` | Integer (default `0`) | Used when `FOOTAGE_SRC_TYPE=webcam`. Selects the local camera index. |
| `LIVE_FEED_URL` | Stream URL (e.g., `rtsp://...`) | Used when `FOOTAGE_SRC_TYPE=live`. Leave empty for local video or webcam. |

> **Note:** Never commit your `.env` file to Git.

### Optional Tuning (`src/openi/core/config.py`)

If you need to adjust detection sensitivity during testing, modify these values in `src/openi/core/config.py`:

| Parameter | Default | Description |
| --- | --- | --- |
| `WEAPON_CONF` | `0.60` | Minimum confidence score (`0.0`–`1.0`) to flag a weapon. |
| `PERSON_CONF` | `0.45` | Minimum confidence score (`0.0`–`1.0`) to track a person. |
| `REID_THRESHOLD` | `0.75` | Color-matching threshold (`0.0`–`1.0`) for re-identifying returning individuals. |
| `WEAPON_KEYWORDS` | `['gun', 'knife', ...]` | Active class names the weapon detector will flag. |

---

## 💻 Running & Managing the Project

All daily commands are handled through `just` (no manual `.venv` activation required):

| Command | Action |
| --- | --- |
| `just` | List all available commands. |
| `just run` | Start the OpenI system and web dashboard. |
| `just format` | Format code and run Ruff linting checks. |
| `just clean` | Delete the `.venv` and temporary cache files for a fresh start. |

*(Alternatively, with `.venv` activated, you can run `openi` or `python -m openi` directly).*

---

## 🤝 Contribution Rules

Git hooks via `pre-commit` are automatically installed during `just setup` and will block commits that violate these rules:

1. **No Direct Commits to Main:** Create a branch (`feature/your-feature` or `fix/your-fix`) and open a Pull Request. Direct commits to `main` or `master` are blocked.
2. **Conventional Commits:** Commit messages must follow the `type: description` format (e.g., `feat: add RTSP retry logic`, `fix: resolve tracker path issue`).
3. **5 MB File Size Limit:** Any file `>= 5 MB` (such as `.pt` weights or test videos) will be rejected by Git hooks. Keep models and videos local or in external storage.
4. **Format Before Committing:** Code must pass Ruff linting and formatting checks. Always run `just format` before staging your changes.

---

## 👥 Maintainers & License

* **Janindu Malshan** ([@imjanindu](https://github.com/imjanindu))
* **Malith Banuka** ([@malithbanuka](https://www.google.com/search?q=https://github.com/malithbanuka))

Licensed under the **MIT License**. See `LICENSE` for details.

```

```
