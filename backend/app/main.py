import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import asynccontextmanager
from queue import Queue

_CHAT_EXECUTOR = ThreadPoolExecutor(max_workers=2)
GEMINI_REQUEST_TIMEOUT = int(os.environ.get("GEMINI_REQUEST_TIMEOUT", "45"))

import aiofiles
from fastapi import Body, FastAPI, File, Form, Query, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.video_analyzer import analyze_video


def _angle_summary_for_llm(frames: list, max_rows: int = 50) -> str:
    """Build a compact text summary of frame angles for the LLM context."""
    if not frames:
        return "No frame data available."
    step = max(1, len(frames) // max_rows) if len(frames) > max_rows else 1
    sampled = [f for i, f in enumerate(frames) if i % step == 0]
    lines = ["frame_index\ttime_s\tL_elbow\tR_elbow\tL_hip\tR_hip\tL_knee\tR_knee"]
    for f in sampled:
        le = f.get("left_elbow_deg")
        re = f.get("right_elbow_deg")
        lh = f.get("left_hip_deg")
        rh = f.get("right_hip_deg")
        lk = f.get("left_knee_deg")
        rk = f.get("right_knee_deg")
        parts = [
            str(f.get("frame_index", "")),
            str(f.get("time_s", "")),
            f"{le:.1f}" if le is not None else "-",
            f"{re:.1f}" if re is not None else "-",
            f"{lh:.1f}" if lh is not None else "-",
            f"{rh:.1f}" if rh is not None else "-",
            f"{lk:.1f}" if lk is not None else "-",
            f"{rk:.1f}" if rk is not None else "-",
        ]
        lines.append("\t".join(parts))
    return "\n".join(lines) + f"\n(Total frames: {len(frames)}, shown: {len(sampled)})"


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


@app.post("/api/chat")
async def chat(
    body: dict = Body(...),
):
    """Send a message with the current analysis (joint angles) as context. Requires GEMINI_API_KEY."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            503,
            "Chat is not configured. Set GEMINI_API_KEY on the server.",
        )
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "message is required")
    frames = body.get("frames") or []
    angle_summary = _angle_summary_for_llm(frames)

    system = (
        "You are a helpful climbing technique coach. The user has analyzed a climbing video with pose estimation. "
        "Below is joint angle data (elbow, hip, knee in degrees) per frame (L/R = left/right). "
        "Answer based on this data when relevant; keep replies concise and actionable."
    )
    user_block = f"Joint angle data (tab-separated):\n{angle_summary}\n\nUser question: {message}"

    try:
        try:
            from google import genai
        except ImportError:
            raise HTTPException(
                503,
                "Chat requires the google-genai package. Install with: pip install google-genai",
            ) from None
        client = genai.Client(api_key=api_key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite").strip() or "gemini-2.0-flash-lite"
        config = genai.types.GenerateContentConfig(system_instruction=[system])
        timeout_sec = max(15, min(120, GEMINI_REQUEST_TIMEOUT))

        def _call_gemini():
            return client.models.generate_content(
                model=model,
                contents=user_block,
                config=config,
            )

        last_err = None
        for attempt in range(2):
            try:
                future = _CHAT_EXECUTOR.submit(_call_gemini)
                response = future.result(timeout=timeout_sec)
                text = getattr(response, "text", None)
                if text is None and hasattr(response, "candidates") and response.candidates:
                    parts = getattr(response.candidates[0].content, "parts", [])
                    text = (parts[0].text if parts else None) or ""
                return {"reply": (text or "").strip() or "No reply generated."}
            except FuturesTimeoutError:
                last_err = Exception("Request timed out")
                raise HTTPException(
                    504,
                    f"Coach request took too long (>{timeout_sec}s). Try again or use a shorter clip.",
                )
            except Exception as e:
                last_err = e
                err = str(e)
                if "429" not in err and "RESOURCE_EXHAUSTED" not in err and "quota" not in err.lower():
                    raise
                if attempt >= 1:
                    raise
                delay = 15
                match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err, re.I)
                if match:
                    delay = max(5, min(45, int(float(match.group(1)) + 1)))
                time.sleep(delay)
        raise last_err
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        if "API_KEY" in err or "api_key" in err or "403" in err or "FORBIDDEN" in err:
            raise HTTPException(
                503,
                "Gemini API key was rejected. Check that the key is valid at https://aistudio.google.com/apikey and that GEMINI_API_KEY on the server has no extra spaces.",
            )
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            raise HTTPException(
                429,
                "Gemini rate limit reached. Wait a minute or try again later. See https://ai.google.dev/gemini-api/docs/rate-limits",
            )
        raise HTTPException(502, f"Gemini request failed: {err}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
