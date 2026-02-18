"""
Process an uploaded video with MediaPipe Pose Landmarker (VIDEO mode)
and return per-frame elbow angles.
"""
import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from app.pose_utils import elbow_angles_from_result, hip_angles_from_result, knee_angles_from_result

# Optional: download default model if not present
DEFAULT_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)


def get_model_path():
    path = os.environ.get(
        "POSE_LANDMARKER_MODEL",
        os.path.join(os.path.dirname(__file__), "..", "models", "pose_landmarker_lite.task"),
    )
    if os.path.isfile(path):
        return path
    # Fallback: same folder as original project (e.g. pose_landmarker_full.task)
    parent = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for name in ("pose_landmarker_full.task", "pose_landmarker_lite.task"):
        candidate = os.path.join(parent, name)
        if os.path.isfile(candidate):
            return candidate
    return path


# On slow servers (e.g. Render free tier), cap how many frames we process so the request finishes.
# ~450 processed frames ≈ 15 sec of video at 30fps with frame_skip=2. Set to 0 to disable.
MAX_PROCESSED_FRAMES = int(os.environ.get("MAX_ANALYSIS_FRAMES", "450"))

# Resize frames so longest side is this many pixels before pose detection. Smaller = faster, less accurate.
# e.g. 320 or 480. Set to 0 to disable (full resolution).
PROCESSING_MAX_DIM = int(os.environ.get("PROCESSING_MAX_DIM", "0"))


def analyze_video(video_path: str, progress_callback=None, frame_skip: int = 1):
    """
    Run pose landmarker on video and return list of per-frame results.
    frame_skip: process every Nth frame (1=all, 2=every 2nd, etc.) for faster analysis.
    Stops after MAX_PROCESSED_FRAMES (when set) so hosted servers don't run forever.
    """
    BaseOptions = mp_tasks.BaseOptions
    PoseLandmarker = vision.PoseLandmarker
    PoseLandmarkerOptions = vision.PoseLandmarkerOptions
    VisionRunningMode = vision.RunningMode

    model_path = get_model_path()
    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Pose landmarker model not found at {model_path}. "
            "Set POSE_LANDMARKER_MODEL or place pose_landmarker_lite.task / pose_landmarker_full.task in backend/models/ or project root."
        )

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(
            "Could not open video. MP4 (H.264) is most reliable. "
            "Try converting .mov to MP4 with QuickTime (File → Export) or HandBrake."
        )
    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        cap.release()
        raise ValueError(
            "Could not read any frames from the video. Try converting to MP4 (H.264)."
        )
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    results_list = []

    frame_skip = max(1, int(frame_skip))
    with PoseLandmarker.create_from_options(options) as landmarker:
        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_index % frame_skip != 0:
                frame_index += 1
                if progress_callback and total_frames > 0:
                    progress_callback(frame_index, total_frames)
                continue
            time_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if PROCESSING_MAX_DIM > 0:
                h, w = img.shape[:2]
                if max(h, w) > PROCESSING_MAX_DIM:
                    scale = PROCESSING_MAX_DIM / max(h, w)
                    new_w, new_h = int(w * scale), int(h * scale)
                    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
            detection_result = landmarker.detect_for_video(mp_image, time_ms)
            left_elb, right_elb = elbow_angles_from_result(detection_result)
            left_hip, right_hip = hip_angles_from_result(detection_result)
            left_knee, right_knee = knee_angles_from_result(detection_result)
            # Serialize normalized image landmarks (x,y in [0,1]) for overlay drawing
            landmarks = []
            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                for lm in detection_result.pose_landmarks[0]:
                    landmarks.append({"x": round(lm.x, 5), "y": round(lm.y, 5), "z": round(lm.z, 5)})
            results_list.append({
                "frame_index": frame_index,
                "time_ms": time_ms,
                "time_s": round(time_ms / 1000.0, 3),
                "left_elbow_deg": round(left_elb, 2) if left_elb is not None else None,
                "right_elbow_deg": round(right_elb, 2) if right_elb is not None else None,
                "left_hip_deg": round(left_hip, 2) if left_hip is not None else None,
                "right_hip_deg": round(right_hip, 2) if right_hip is not None else None,
                "left_knee_deg": round(left_knee, 2) if left_knee is not None else None,
                "right_knee_deg": round(right_knee, 2) if right_knee is not None else None,
                "landmarks": landmarks,
            })
            frame_index += 1
            if progress_callback and total_frames > 0:
                progress_callback(frame_index, total_frames)
            if MAX_PROCESSED_FRAMES > 0 and len(results_list) >= MAX_PROCESSED_FRAMES:
                cap.release()
                return results_list, True

    cap.release()
    return results_list, False
