import os
import uuid
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.video_analyzer import analyze_video
from app.imu_utils import analyze_imu_csv


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "uploads"), exist_ok=True)
    yield
    # optional: cleanup uploads on shutdown


app = FastAPI(title="Climbing Tracker API", lifespan=lifespan)

_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
_cors_env = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_env:
    _origins.extend(origin.strip() for origin in _cors_env.split(",") if origin.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Climbing Tracker API", "docs": "/docs"}


@app.post("/api/analyze-video")
async def analyze_video_endpoint(video: UploadFile = File(...)):
    """Upload a video file; returns per-frame elbow angles (left/right) from pose estimation."""
    ct = (video.content_type or "").strip().lower()
    allowed = ct.startswith("video/") or ct == "application/octet-stream"
    if video.filename:
        ext = (video.filename or "").lower().split(".")[-1]
        if ext in ("mov", "mp4", "webm", "m4v", "avi"):
            allowed = True
    if not allowed:
        raise HTTPException(400, "File must be a video (e.g. .mov, .mp4).")

    suffix = os.path.splitext(video.filename or "")[-1] or ".mp4"
    path = os.path.join(
        os.path.dirname(__file__), "..", "uploads", f"{uuid.uuid4().hex}{suffix}"
    )
    try:
        async with aiofiles.open(path, "wb") as f:
            while chunk := await video.read(1024 * 1024):
                await f.write(chunk)
        frames = analyze_video(path)
        return JSONResponse(content={"frames": frames, "total_frames": len(frames)})
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        err = str(e)
        if "video" in err.lower() or "open" in err.lower() or "decode" in err.lower():
            raise HTTPException(
                400,
                "Could not read this video. MP4 (H.264) works best. Try converting your .mov in QuickTime (File → Export) or with HandBrake.",
            )
        raise HTTPException(500, err)
    finally:
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.post("/api/analyze-imu")
async def analyze_imu_endpoint(
    sensor1: UploadFile = File(..., description="Reference segment quaternion CSV (e.g. upper arm)"),
    sensor2: UploadFile = File(..., description="Segment quaternion CSV (e.g. forearm)"),
):
    """Upload two quaternion CSVs (tab-delimited, with timestamp, w, x, y, z). Returns angle time series."""
    try:
        c1 = await sensor1.read()
        c2 = await sensor2.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read files: {e}")
    angles = analyze_imu_csv(c1, c2)
    if not angles:
        raise HTTPException(400, "Could not parse quaternion data; check CSV format (tab-delimited, skip first 3 rows).")
    return JSONResponse(content={"angles": angles})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
