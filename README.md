# Climbing Technique Tracker

Full-stack web app to analyze **elbow angles** from:

1. **Video** – upload a recording; pose estimation (MediaPipe) runs on each frame and returns left/right elbow angles over time.
2. **IMU** – upload two quaternion CSVs from sensors (e.g. upper arm + forearm); angles are computed from relative rotation.

## Quick start

### 1. Pose model (required for video analysis)

Download the MediaPipe pose landmarker model once:

```bash
cd backend
python scripts/download_model.py
```

Or place your own `pose_landmarker_full.task` (or `pose_landmarker_lite.task`) in `backend/models/` or the project root. You can also set:

```bash
export POSE_LANDMARKER_MODEL=/path/to/pose_landmarker_full.task
```

### 2. Backend (Python)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Use “Video analysis” to drop a video and run analysis, or “IMU (quaternion)” to upload two tab-delimited quaternion CSVs.

## API

- **POST /api/analyze-video** – body: `video` (file). Returns `{ "frames": [...], "total_frames": N }` with `frame_index`, `time_s`, `left_elbow_deg`, `right_elbow_deg` per frame.
- **POST /api/analyze-imu** – body: `sensor1`, `sensor2` (files). Returns `{ "angles": [ { "angle_deg", "timestamp" }, ... ] }`.

## Project layout

- **backend/** – FastAPI app, MediaPipe video processing, quaternion→angle logic.
- **frontend/** – React + Vite UI: upload, run analysis, view chart and download CSV.
- **pose_landmarks copy.ipynb** – original live webcam + pose pipeline (reference).
- **quaternion_analyses.ipynb** – was in repo for IMU/quaternion logic (now reflected in `backend/app/imu_utils.py`).

## CSV format (IMU)

Tab-delimited, first 3 rows skipped. Columns: timestamp, w, x, y, z (quaternion). Same format as the original Qsense/Quaternion_*.csv files.
