# OpenI - Museum Security Tracking System

![Python Version](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.14%2B-EE4C2C.svg?logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5.0%2B-5C3EE8.svg?logo=opencv&logoColor=white)
![YOLOv8](https://img.shields.io/badge/AI_Model-YOLOv8-00FFFF.svg?logo=ultralytics&logoColor=black)
![Task Runner](https://img.shields.io/badge/task_runner-just-black)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

An AI-driven museum security system that provides real-time threat detection, suspect tracking, and automated incident reporting. OpenI utilizes a dual-model YOLOv8 architecture to track individuals and detect weapons simultaneously, engineered to run efficiently on standard CPUs (via Intel OpenVINO) with full native support for NVIDIA GPUs.

---

## 📂 Project Structure

```text
OpenI/
├── data/                  # Local storage for datasets, test footages, and captured suspects
├── models/                # YOLOv8 weights (Native PyTorch .pt / OpenVINO compiled)
├── src/
│   └── openi/             # Main application package
│       ├── ai/            # Detection models and Re-ID (HSV histogram) logic
│       ├── core/          # Centralized configuration (config.py) and ANSI loggers
│       ├── gui/           # User interface and display components
│       ├── iot/           # Hardware integrations and network communications
│       ├── tracking/      # SecurityTracker state management buffers
│       ├── __main__.py    # Entry point for 'python -m openi' execution
│       └── main.py        # Main execution loop
├── .pre-commit-config.yaml# Git hook configurations (Ruff, file limits, commit standards)
├── justfile               # Cross-platform command runner definitions
├── pyproject.toml         # Modern Python packaging and dependency specifications
└── README.md              # Project documentation

```

---

## ✨ Features / Highlights

* **Dual-Model Architecture:** Runs a standard COCO model for multi-object person tracking alongside a custom-trained model strictly for weapon detection.
* **Hardware Flexibility:** Supports OpenVINO graph compilation for rapid CPU inference and native PyTorch for high-speed NVIDIA GPU processing.
* **Custom Re-Identification (Re-ID) Engine:** Computes a 3D HSV (Hue, Saturation, Value) color histogram of a person's upper torso to recognize suspects who leave and re-enter the camera frame.
* **Temporal Stability Buffers:** Requires multi-frame mathematical confirmation to eliminate single-frame visual glitches and false positives completely.
* **Automated Evidence Archiving:** Automatically crops and saves high-resolution snapshots of verified suspects to a local `/suspects` directory.
* **Modern Developer Experience:** Fully containerized virtual environment handling, strict code formatting via Ruff, and cross-platform task execution via `just`.

---

## 📋 Prerequisites / Requirements

* **Python:** `>= 3.10`
* **Task Runner:** [`just`](https://github.com/casey/just?utm_source=gemini) installed globally (e.g., `winget install just` on Windows, or `brew install just` on macOS/Linux).
* **Git:** Installed and available in your system PATH.
* *(Optional)* **NVIDIA GPU:** CUDA Toolkit 11.8+ for hardware-accelerated PyTorch inference.

---

## 🚀 Installation

This project utilizes `just` to automate virtual environment creation, dependency installation, and Git hook configuration across Windows, macOS, and Linux.

### 1. Clone the Repository

```bash
git clone <your-github-repo-url>
cd OpenI

```

### 2. Automated Setup via Just

Run the setup command to automatically initialize the `.venv`, upgrade pip, install the `openi` package in editable mode with `[dev]` dependencies, and attach Git hooks:

* **Option A: CPU-Only:**
```bash
just setup

```

* **Option B: Dedicated NVIDIA GPU:**
```bash
just setup-gpu

```

### 3. Hardware-Specific Model Setup

Depending on your machine, you must configure the AI models inside `src/openi/core/config.py`.

* **Option A: CPU-Only (OpenVINO):**
Compile the PyTorch weights to OpenVINO format for maximum CPU speed:
```bash
yolo export model=models/yolov8n.pt format=openvino imgsz=640
yolo export model=models/best.pt format=openvino imgsz=640

```


* **Option B: Dedicated NVIDIA GPU (CUDA):**
Ensure your `config.py` targets the raw `.pt` PyTorch weights directly.

---

## 💻 Usage

OpenI includes a command-line task runner to simplify daily development.

To view all available commands, simply type:

```bash
just

```

### Running the Application

You do not need to manually activate the virtual environment. Simply execute:

```bash
just run

```

*Alternatively, because the project is packaged via `pyproject.toml`, you can activate your `.venv` and run the app globally by typing `openi`, or via `python -m openi` from the `src` directory.*

### Code Maintenance

To automatically format the codebase and run linting checks:

```bash
just format

```

To completely wipe the virtual environment and start fresh:

```bash
just clean

```

---
## ⚙️ Configuration

All system parameters, mathematical thresholds, and environment paths are centralized in `src/openi/core/config.py`.

### Architectural Simplifications
Recent workflow automation and architectural updates have significantly simplified the configuration process:
* **Automated Absolute Pathing:** `ROOT_DIR` is now dynamically calculated using `pathlib.Path`. The system automatically resolves its own location regardless of where the terminal is opened, completely eliminating "file not found" errors caused by relative paths.
* **Streamlined Model Loading:** The system has been reverted to utilize standard PyTorch `.pt` weights natively. Developers no longer need to run complex `yolo export` commands to compile OpenVINO graphs before running the application.
* **Enum Type Safety:** Camera sources are now strongly typed using the `SrcType` enum, preventing runtime crashes caused by string typos when switching between local files and live cameras.
* **Auto-Initialization:** Required directories (like `data/saved_suspects`) are automatically verified and created on startup if they do not exist.

### Key Environment Variables
Modify these variables in `config.py` to adjust how the system operates:

**Video Source Settings:**
* `FOOTAGE_SRC_TYPE`: Controls the active input stream. Accepts `SrcType` enums (e.g., `SrcType.VIDEO`, `SrcType.WEBCAM`, `SrcType.LIVE_STREAM`).
* `CURRENT_TEST_FOOTAGE`: The filename of the local video to analyze (e.g., `"knife.MOV"`). Reads from the `data/test_footages/` directory.
* `WEBCAM_ID`: The hardware index of the local camera (default is `0`).
* `LIVE_FEED_URL`: Network stream URL for IP cameras (e.g., `"rtsp://..."`).

**Model Configuration:**
* `WEAPON_MODEL_PATH` / `PERSON_MODEL_PATH`: Absolute paths to the YOLOv8 weights. Automatically resolved to the `models/` directory.

**Mathematical Thresholds:**
* `WEAPON_CONF`: Minimum confidence score required to confirm a weapon detection (Default: `0.60`).
* `PERSON_CONF`: Minimum confidence score required to detect and track a person (Default: `0.45`).
* `REID_THRESHOLD`: The matching threshold (0.0 to 1.0) for the HSV 3D color histogram. A higher number requires a stricter color match to re-identify a suspect who left the camera frame (Default: `0.75`).
* `WEAPON_KEYWORDS`: List of allowed class names the threat detection model will actively flag (e.g., `'gun'`, `'knife'`, `'machine gun'`).

---

## 🤝 Contributing

We welcome contributions! To maintain code quality, OpenI strictly enforces workflow rules via `.pre-commit-config.yaml`.

### Workflow Guidelines

1. **Fork and Branch:** Create a feature branch (`feature/your-feature`) or bugfix branch (`fix/issue-description`).
2. **Branch Protection:** **Direct commits to the `main` or `master` branches are strictly prohibited.** You must submit a Pull Request.
3. **Commit Standards:** We enforce [Conventional Commits](https://www.conventionalcommits.org/?utm_source=gemini). Your commit messages must follow the `type: description` format (e.g., `feat: add RTSP stream support`, `fix: resolve GUI crash`).
4. **File Size Limits:** Git hooks will automatically reject any commits containing files `>= 5MB` to prevent bloating the repository with large `.pt` weights or video files. Use Git LFS or external storage for these.
5. **Linting & Formatting:** Ruff is integrated into the pre-commit pipeline. Any code that violates PEP8 standards or line-length limits will automatically block the commit. Run `just format` before committing.

---

## 👨‍💻 Developer Information

This software was engineered as the IoT project for the Digital Control Systems module, a core component of the Bachelor of Honors in Information and Communication Technology (BICT) degree program at the University of Sri Jayewardenepura.

* **Janindu Malshan** ([@imjanindu](https://github.com/imjanindu?utm_source=gemini)) - Lead System Architect & AI Developer
* **Malith Banuka** ([@malithbanuka](https://www.google.com/search?q=https://github.com/malithbanuka&utm_source=gemini)) - DevOps & Workflow Automation Engineer

*Engineered with a focus on modularity, real-time performance, and scalable computer vision design.*

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for full details.
