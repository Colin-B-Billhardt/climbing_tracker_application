#!/usr/bin/env python3
"""Download MediaPipe pose landmarker model if not present."""
import os
import ssl
import urllib.request
import urllib.error

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
LITE_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
OUT_PATH = os.path.join(MODEL_DIR, "pose_landmarker_lite.task")


def _download(url, path, ssl_verify=True):
    if ssl_verify:
        ctx = ssl.create_default_context()
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
    else:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, path)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if os.path.isfile(OUT_PATH):
        print(f"Model already exists: {OUT_PATH}")
        return
    print(f"Downloading pose_landmarker_lite.task to {OUT_PATH} ...")
    try:
        _download(LITE_URL, OUT_PATH, ssl_verify=True)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
            print("SSL verification failed (common on macOS Homebrew Python). Retrying without verification for this download ...")
            _download(LITE_URL, OUT_PATH, ssl_verify=False)
        else:
            raise
    print("Done.")


if __name__ == "__main__":
    main()
