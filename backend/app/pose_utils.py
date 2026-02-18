"""
Pose-based joint angle calculation (from MediaPipe world landmarks).
Elbow logic mirrors the original pose_landmarks notebook.
"""
import math
import numpy as np


def angle_at_joint(proximal, joint, distal):
    """Angle at joint in degrees (proximal–joint–distal). Returns None if invalid."""
    v_pj = [proximal.x - joint.x, proximal.y - joint.y, proximal.z - joint.z]
    v_dj = [distal.x - joint.x, distal.y - joint.y, distal.z - joint.z]
    dot = np.dot(v_pj, v_dj)
    mag_pj = np.linalg.norm(v_pj)
    mag_dj = np.linalg.norm(v_dj)
    if mag_pj * mag_dj == 0:
        return None
    return math.degrees(math.acos(max(-1, min(1, dot / (mag_pj * mag_dj)))))


# MediaPipe pose world landmark indices
# https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST = 11, 13, 15
RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST = 12, 14, 16
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28


def elbow_angles_from_result(pose_result):
    """Left and right elbow angles (degrees). Angle at elbow: shoulder–elbow–wrist."""
    if not pose_result.pose_world_landmarks or len(pose_result.pose_world_landmarks) == 0:
        return None, None
    world = pose_result.pose_world_landmarks[0]
    if len(world) < 17:
        return None, None
    left = angle_at_joint(world[LEFT_SHOULDER], world[LEFT_ELBOW], world[LEFT_WRIST])
    right = angle_at_joint(world[RIGHT_SHOULDER], world[RIGHT_ELBOW], world[RIGHT_WRIST])
    return left, right


def hip_angles_from_result(pose_result):
    """Left and right hip angles (degrees). Angle at hip: shoulder–hip–knee."""
    if not pose_result.pose_world_landmarks or len(pose_result.pose_world_landmarks) == 0:
        return None, None
    world = pose_result.pose_world_landmarks[0]
    if len(world) < 29:
        return None, None
    left = angle_at_joint(world[LEFT_SHOULDER], world[LEFT_HIP], world[LEFT_KNEE])
    right = angle_at_joint(world[RIGHT_SHOULDER], world[RIGHT_HIP], world[RIGHT_KNEE])
    return left, right


def knee_angles_from_result(pose_result):
    """Left and right knee angles (degrees). Angle at knee: hip–knee–ankle."""
    if not pose_result.pose_world_landmarks or len(pose_result.pose_world_landmarks) == 0:
        return None, None
    world = pose_result.pose_world_landmarks[0]
    if len(world) < 29:
        return None, None
    left = angle_at_joint(world[LEFT_HIP], world[LEFT_KNEE], world[LEFT_ANKLE])
    right = angle_at_joint(world[RIGHT_HIP], world[RIGHT_KNEE], world[RIGHT_ANKLE])
    return left, right
