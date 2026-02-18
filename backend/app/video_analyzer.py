"""
Process an uploaded video with MediaPipe Pose Landmarker (VIDEO mode)
and return per-frame elbow angles.
"""
import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from app.pose_utils import elbow_angles_from_result

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


def analyze_video(video_path: str, progress_callback=None):
    """
    Run pose landmarker on video and return list of:
    { "frame_index": int, "time_ms": int, "time_s": float, "left_elbow_deg": float | null, "right_elbow_deg": float | null }
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

    with PoseLandmarker.create_from_options(options) as landmarker:
        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            time_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            detection_result = landmarker.detect_for_video(mp_image, time_ms)
            left_deg, right_deg = elbow_angles_from_result(detection_result)
            # Serialize normalized image landmarks (x,y in [0,1]) for overlay drawing
            landmarks = []
            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                for lm in detection_result.pose_landmarks[0]:
                    landmarks.append({"x": round(lm.x, 5), "y": round(lm.y, 5), "z": round(lm.z, 5)})
            results_list.append({
                "frame_index": frame_index,
                "time_ms": time_ms,
                "time_s": round(time_ms / 1000.0, 3),
                "left_elbow_deg": round(left_deg, 2) if left_deg is not None else None,
                "right_elbow_deg": round(right_deg, 2) if right_deg is not None else None,
                "landmarks": landmarks,
            })
            frame_index += 1
            if progress_callback and total_frames > 0:
                progress_callback(frame_index, total_frames)

    cap.release()
    return results_list
