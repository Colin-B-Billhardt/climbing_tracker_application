"""
Pose-based elbow angle calculation (from MediaPipe world landmarks).
Mirrors logic from the original pose_landmarks notebook.
"""
import math
import numpy as np


def calculate_elbow_angle(shoulder_landmark, elbow_landmark, wrist_landmark):
    """Angle at elbow (degrees) from shoulder–elbow–wrist world landmarks."""
    vector_s_e = [
        shoulder_landmark.x - elbow_landmark.x,
        shoulder_landmark.y - elbow_landmark.y,
        shoulder_landmark.z - elbow_landmark.z,
    ]
    vector_w_e = [
        wrist_landmark.x - elbow_landmark.x,
        wrist_landmark.y - elbow_landmark.y,
        wrist_landmark.z - elbow_landmark.z,
    ]
    dot_product = np.dot(vector_s_e, vector_w_e)
    magnitude_s_e = np.linalg.norm(vector_s_e)
    magnitude_w_e = np.linalg.norm(vector_w_e)
    if magnitude_s_e * magnitude_w_e == 0:
        return None
    angle = math.degrees(
        math.acos(max(-1, min(1, dot_product / (magnitude_s_e * magnitude_w_e))))
    )
    return angle


# MediaPipe pose world landmark indices
# https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST = 11, 13, 15
RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST = 12, 14, 16


def elbow_angles_from_result(pose_result):
    """
    From a PoseLandmarkerResult, compute left and right elbow angles (degrees).
    pose_result has .pose_world_landmarks: list of lists of normalized landmarks.
    Returns (left_angle, right_angle); either can be None if not detected.
    """
    if not pose_result.pose_world_landmarks or len(pose_result.pose_world_landmarks) == 0:
        return None, None
    world = pose_result.pose_world_landmarks[0]
    if len(world) < 17:
        return None, None
    left = calculate_elbow_angle(
        world[LEFT_SHOULDER], world[LEFT_ELBOW], world[LEFT_WRIST]
    )
    right = calculate_elbow_angle(
        world[RIGHT_SHOULDER], world[RIGHT_ELBOW], world[RIGHT_WRIST]
    )
    return left, right
