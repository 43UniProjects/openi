# Museum Security Tracking System

A real-time, highly optimized computer vision pipeline designed for museum security environments. This system utilizes a dual-model YOLOv8 architecture to track individuals and detect weapons simultaneously. It is engineered to run efficiently on standard CPUs using Intel OpenVINO compilation, with full support for NVIDIA GPUs via CUDA.

## 🚀 Features & Current Progress

This repository currently includes a fully modular, object-oriented pipeline with the following active features:

* **Dual-Model Architecture:** Runs a standard COCO model for multi-object person tracking alongside a custom-trained model strictly for weapon detection.
* **Hardware Flexibility:** Supports OpenVINO graph compilation for rapid CPU inference and native PyTorch for high-speed NVIDIA GPU processing.
* **Custom Re-Identification (Re-ID) Engine:** Computes a 3D HSV (Hue, Saturation, Value) color histogram of a person's upper torso. This allows the system to recognize a suspect who leaves the camera frame and returns later with a concealed weapon.
* **Temporal Stability Buffers:** Requires multi-frame mathematical confirmation to eliminate single-frame visual glitches and false positives completely.
* **Automated Evidence Archiving:** Automatically crops and saves high-resolution snapshots of verified suspects to a local `/suspects` directory.

## 🗺️ Development Roadmap (To-Do)

The underlying architecture is modularized to support the following upcoming features:

* **Artifact Theft Detection:** Monitor stationary museum artifacts and flag suspects who remove objects from their designated podiums.
* **Restricted Area Geofencing:** Define mathematical coordinate boundaries to instantly flag individuals trespassing in unauthorized zones.
* **Unified Suspect Tracking:** Expand the Re-ID engine to track thieves and trespassers alongside armed individuals.
* **Live Camera Integration:** Transition the input source from pre-recorded video files to real-time CCTV or webcam streams via OpenCV.

## ⚙️ Local Setup Instructions

Follow these steps to deploy and run this security system on your local machine. 

### 1. Prerequisites
Ensure you have Python 3.8 or higher installed on your system. 

### 2. Clone the Repository
Open your terminal and clone this project:
```bash
git clone <your-github-repo-url>
cd museum-security-project
```

### 3. Create a Virtual Environment
It is highly recommended to isolate your project dependencies to prevent conflicts with other Python projects.

**For Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**For macOS and Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Hardware-Specific Setup

Choose the setup path that matches your computer's hardware.

**Option A: CPU-Only Setup (Intel/AMD)**
This method uses OpenVINO to maximize CPU performance.
1. Install the required computer vision libraries via the requirements file:
   ```bash
   pip install -r requirements.txt
   ```
2. Compile the raw PyTorch weights into OpenVINO models:
   ```bash
   yolo export model=yolov8n.pt format=openvino imgsz=640
   yolo export model=best.pt format=openvino imgsz=640
   ```
3. Ensure your `config.py` file points to the compiled folders:
   ```python
   WEAPON_MODEL_PATH = 'best_openvino_model/'
   PERSON_MODEL_PATH = 'yolov8n_openvino_model/'
   ```

**Option B: Dedicated NVIDIA GPU Setup (CUDA)**
This method uses your graphics card for maximum processing speed.
1. Install the CUDA-enabled version of PyTorch first, then install the remaining project requirements:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   pip install -r requirements.txt
   ```
2. Open your `config.py` file and update the paths to use the raw PyTorch weights directly:
   ```python
   WEAPON_MODEL_PATH = 'best.pt'
   PERSON_MODEL_PATH = 'yolov8n.pt'
   ```

### 5. Execute the Pipeline
Before running the system, open `main.py` and update the `video_path` variable to point to your own local video file, or set it to `0` to use your live webcam. Also you can use RTSP stream URL (for an IP security camera) as well:
```python
video_path = "your_video_file.mp4" # Or set to 0 for a live camera feed
```
Then, execute the application:
```bash
python main.py
```

---

## 👨‍💻 Developer Information

This software was engineered as the IoT project for the Digital Control Systems module. It is a core component of the Bachelor of Honors in Information and Communication Technology (BICT) degree program at the University of Sri Jayewardenepura.

* **Developer 1:** [Janindu Malshan](https://github.com/imjanindu)
* **Role:** Lead System Architect & Developer

*Engineered with a focus on modularity, real-time performance, and scalable computer vision design.*