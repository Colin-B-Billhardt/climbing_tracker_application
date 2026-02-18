"""
IMU quaternion to elbow angle conversion (from quaternion_analyses notebook).
Expects tab-delimited CSV with columns like: timestamp, w, x, y, z.
"""
import csv
import io
import numpy as np


def multiply_quaternions(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def parse_quaternion_csv(content: bytes, delimiter="\t", skip_rows=3):
    """Parse CSV bytes into list of [timestamp, w, x, y, z] rows (numeric)."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    data = []
    for row in rows[skip_rows:]:
        if len(row) < 5:
            continue
        try:
            ts = row[0].strip()
            w, x, y, z = float(row[1]), float(row[2]), float(row[3]), float(row[4])
            data.append([ts, w, x, y, z])
        except (ValueError, IndexError):
            continue
    return data


def quaternion_to_angle(sensor_array_1, sensor_array_2, angle_offset=-180):
    """
    Relative angle between two sensors (e.g. upper arm vs lower arm).
    Returns list of { "angle_deg": float, "timestamp": str }.
    """
    angles_with_timestamps = []
    counter = 0
    for i in sensor_array_1:
        _, w1, x1, y1, z1 = i[0], float(i[1]), float(i[2]), float(i[3]), float(i[4])
        q1_conjugate = [w1, -x1, -y1, -z1]
        angle_calculated = False
        while not angle_calculated and counter < len(sensor_array_2):
            k = sensor_array_2[counter]
            ts = k[0]
            w2, x2, y2, z2 = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            q2 = [w2, x2, y2, z2]
            q_relative = multiply_quaternions(q2, q1_conjugate)
            theta = 2 * np.arccos(np.clip(q_relative[0], -1, 1))
            theta_deg = np.degrees(theta) + angle_offset
            angles_with_timestamps.append({"angle_deg": round(float(theta_deg), 2), "timestamp": ts})
            counter += 1
            angle_calculated = True
    return angles_with_timestamps


def analyze_imu_csv(sensor1_content: bytes, sensor2_content: bytes, delimiter="\t", skip_rows=3):
    """
    Parse two quaternion CSVs and return angle time series.
    Sensor 1 = reference (e.g. upper arm), Sensor 2 = segment (e.g. forearm).
    """
    s1 = parse_quaternion_csv(sensor1_content, delimiter=delimiter, skip_rows=skip_rows)
    s2 = parse_quaternion_csv(sensor2_content, delimiter=delimiter, skip_rows=skip_rows)
    if not s1 or not s2:
        return []
    return quaternion_to_angle(s2, s1)
