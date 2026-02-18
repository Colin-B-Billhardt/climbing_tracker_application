# Climbing Technique Tracker

Full-stack web app to analyze **elbow angles** from video: upload a recording, and pose estimation (MediaPipe) runs on each frame and returns left/right elbow angles over time, with a skeleton overlay and chart.

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

Open **http://localhost:5173**. Drop a video and run analysis to get elbow angles, pose overlay, and a chart.

## API

- **POST /api/analyze-video** – body: `video` (file), optional `frame_skip` (1–4). Returns `{ "frames": [...], "total_frames": N, "truncated": bool }` with per-frame `time_s`, `left_elbow_deg`, `right_elbow_deg`, and `landmarks` for overlay.

## Project layout

- **backend/** – FastAPI app, MediaPipe video processing.
- **frontend/** – React + Vite UI: upload, run analysis, pose overlay, chart, CSV download.
- **pose_landmarks copy.ipynb** – original live webcam + pose pipeline (reference).

## Faster processing (hosted / long videos)

- **Frontend:** Use the **Speed** dropdown: “Every 3rd frame” or “Every 4th frame” to process fewer frames (faster, slightly less smooth overlay).
- **Backend env (e.g. on Render):**
  - **MAX_ANALYSIS_FRAMES** – Cap processed frames so requests finish (default `450` ≈ 15–30s of video). Set to `0` to disable.
  - **PROCESSING_MAX_DIM** – Resize each frame so the longest side is this many pixels before pose detection (e.g. `320` or `480`). Smaller = faster, slightly less accurate. Default `0` (no resize).

## Possible future features

- **Summary stats** – e.g. mean/min/max elbow angle per arm, time in range.
- **Knee / hip angles** – same pipeline, different landmarks.
- **File size limit** – reject very large uploads with a clear message.
- **Progress indicator** – “Processing frame 120 / 450” during analysis.
- **Compare two videos** – overlay two angle curves (e.g. before/after).
- **Export overlay video** – server or client renders the skeleton onto the video and returns an MP4.
