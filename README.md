# Climbing Technique Tracker

Web app that analyzes climbing video with pose estimation: **elbow, hip, and knee angles** per frame, skeleton overlay, time-series chart, and CSV export. Optional **coach chat** (Gemini) to ask questions about your technique after a run.

## Live app

The app is hosted on **Render**. Use the frontend URL from your Render dashboard. Upload a video, choose speed, then **Analyze video**. After processing you get:

- Video with pose overlay and current-frame angles
- Joint angles over time chart and CSV download
- **Coach chat** – a chat panel appears below the chart; you can ask the coach about your joint angles (e.g. “Where are my elbows most bent?”). Requires `GEMINI_API_KEY` on the backend. Chat only appears once a video has been analyzed.

Deployment and env vars (including `GEMINI_API_KEY`, `VITE_API_URL`, `CORS_ORIGINS`) are described in **DEPLOY.md**.

## Run locally

**Backend:** Install deps, optionally [download the pose model](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) into `backend/models/`, then:

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
```

**Frontend:** `cd frontend && npm install && npm run dev` → open http://localhost:5173. Set `VITE_API_URL=http://localhost:8000` if the frontend runs separately.

## API

- **POST /api/analyze-video** – `video` (file), optional `frame_skip` (1–4). Returns per-frame angles (elbow, hip, knee) and landmarks for overlay.
- **POST /api/chat** – `{ "message": "...", "frames": [...] }`. Requires `GEMINI_API_KEY`. Returns `{ "reply": "..." }`.

## Project layout

- **backend/** – FastAPI, MediaPipe pose, Gemini chat.
- **frontend/** – React + Vite: upload, analyze, overlay, chart, CSV, coach chat.

## Backend env (e.g. Render)

- **GEMINI_API_KEY** – Enables coach chat.
- **MAX_ANALYSIS_FRAMES** – Cap frames per run (default `450`). `0` = no cap.
- **PROCESSING_MAX_DIM** – Resize frames before pose (e.g. `320`). `0` = no resize.
