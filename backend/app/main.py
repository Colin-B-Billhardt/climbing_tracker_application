import json
import os
import threading
import uuid
from contextlib import asynccontextmanager
from queue import Queue

import aiofiles
from fastapi import FastAPI, File, Form, Query, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.video_analyzer import analyze_video


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
    "https://climbing-tracker-frontend.onrender.com",
    "http://climbing-tracker-frontend.onrender.com",
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


def _stream_analysis(path: str, skip: int):
    """Generator that yields NDJSON progress and final result."""
    q = Queue()

    def progress_cb(frame_index: int, total_frames: int):
        q.put(("progress", frame_index, total_frames))

    def run():
        try:
            frames, truncated = analyze_video(path, progress_callback=progress_cb, frame_skip=skip)
            q.put(("done", frames, truncated))
        except Exception as e:
            q.put(("error", str(e)))

    t = threading.Thread(target=run)
    t.start()
    total = None
    try:
        while True:
            msg = q.get()
            if msg[0] == "progress":
                _, frame_index, total_frames = msg
                if total is None:
                    total = total_frames
                    yield json.dumps({"event": "start", "total_frames": total}) + "\n"
                yield json.dumps({"event": "progress", "frame_index": frame_index, "total_frames": total_frames}) + "\n"
            elif msg[0] == "done":
                _, frames, truncated = msg
                yield json.dumps({
                    "event": "done",
                    "frames": frames,
                    "total_frames": len(frames),
                    "truncated": truncated,
                }) + "\n"
                break
            elif msg[0] == "error":
                yield json.dumps({"event": "error", "message": msg[1]}) + "\n"
                break
    finally:
        t.join()
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.post("/api/analyze-video")
async def analyze_video_endpoint(
    video: UploadFile = File(...),
    frame_skip: str | None = Form(default=None),
    stream: str | None = Query(None, description="Set to 1 for NDJSON progress stream"),
):
    """Upload a video file; returns per-frame elbow angles. Add ?stream=1 for progress updates (NDJSON)."""
    ct = (video.content_type or "").strip().lower()
    allowed = ct.startswith("video/") or ct == "application/octet-stream"
    if video.filename:
        ext = (video.filename or "").lower().split(".")[-1]
        if ext in ("mov", "mp4", "webm", "m4v", "avi"):
            allowed = True
    if not allowed:
        raise HTTPException(400, "File must be a video (e.g. .mov, .mp4).")
    skip = 1
    if frame_skip is not None:
        try:
            skip = max(1, min(4, int(frame_skip)))
        except ValueError:
            pass

    suffix = os.path.splitext(video.filename or "")[-1] or ".mp4"
    path = os.path.join(
        os.path.dirname(__file__), "..", "uploads", f"{uuid.uuid4().hex}{suffix}"
    )
    try:
        async with aiofiles.open(path, "wb") as f:
            while chunk := await video.read(1024 * 1024):
                await f.write(chunk)
        if stream == "1":
            return StreamingResponse(
                _stream_analysis(path, skip),
                media_type="application/x-ndjson",
            )
        frames, truncated = analyze_video(path, frame_skip=skip)
        return JSONResponse(content={
            "frames": frames,
            "total_frames": len(frames),
            "truncated": truncated,
        })
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
        if stream != "1" and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
