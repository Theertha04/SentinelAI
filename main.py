"""
SentinelAI – Real-Time Emergency Detection System
main.py  |  Step 3: Audio (Loud Sound) Detection integrated
"""

import cv2
import mediapipe as mp
from fall_detector import FallDetector
from scream_detector import ScreamDetector

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
WINDOW_TITLE = "SentinelAI – Emergency Detection"
COLOR_GREEN  = (0, 255, 0)
COLOR_RED    = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE  = (255, 255, 255)
FONT         = cv2.FONT_HERSHEY_SIMPLEX
EXIT_KEY     = ord("q")

# ──────────────────────────────────────────────
# MediaPipe setup
# ──────────────────────────────────────────────
mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_styles  = mp.solutions.drawing_styles


def build_pose_detector() -> mp_pose.Pose:
    return mp_pose.Pose(
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )


# ──────────────────────────────────────────────
# Drawing helpers
# ──────────────────────────────────────────────
def draw_skeleton(frame, landmarks) -> None:
    mp_drawing.draw_landmarks(
        frame,
        landmarks,
        mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style(),
    )


def draw_status(frame, is_fallen: bool) -> None:
    if is_fallen:
        text, color = "FALL DETECTED", COLOR_RED
    else:
        text, color = "SAFE", COLOR_GREEN

    cv2.putText(frame, f"Status: {text}", (20, 50),
                FONT, 1.2, color, 2, cv2.LINE_AA)


def draw_angle(frame, angle: float) -> None:
    """Show live torso angle for debugging / demo."""
    cv2.putText(frame, f"Torso angle: {angle:.1f} deg", (20, 90),
                FONT, 0.7, COLOR_WHITE, 1, cv2.LINE_AA)


def draw_audio_status(frame, is_loud: bool, rms: float) -> None:
    if is_loud:
        text, color = "LOUD SOUND DETECTED", COLOR_YELLOW
    else:
        text, color = "Audio: Normal", COLOR_GREEN
    cv2.putText(frame, text, (20, 130),
                FONT, 0.8, color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"RMS: {rms:.4f}", (20, 160),
                FONT, 0.6, COLOR_WHITE, 1, cv2.LINE_AA)


def draw_hint(frame) -> None:
    h = frame.shape[0]
    cv2.putText(frame, "Press 'q' to quit", (20, h - 20),
                FONT, 0.6, COLOR_WHITE, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────
# Frame processing
# ──────────────────────────────────────────────
def process_frame(frame, pose):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    results = pose.process(rgb)
    rgb.flags.writeable = True
    annotated = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    if results.pose_landmarks:
        draw_skeleton(annotated, results.pose_landmarks)

    return annotated, results.pose_landmarks


# ──────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────
def run() -> None:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam.")

    fall_detector   = FallDetector(fall_angle_threshold=55.0, confirm_seconds=1.0)
    scream_detector = ScreamDetector(loud_threshold=0.01)
    scream_detector.start()

    print("[SentinelAI] Running – press 'q' to quit.")

    with build_pose_detector() as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w  = frame.shape[:2]

            annotated, landmarks = process_frame(frame, pose)

            # ── detections ─────────────────────────────────────────────
            is_fallen = fall_detector.update(landmarks, w, h)
            is_loud   = scream_detector.is_loud
            rms       = scream_detector.rms_level

            # ── UI ─────────────────────────────────────────────────────
            draw_status(annotated, is_fallen)
            draw_angle(annotated, fall_detector.torso_angle)
            draw_audio_status(annotated, is_loud, rms)
            draw_hint(annotated)

            cv2.imshow(WINDOW_TITLE, annotated)
            if cv2.waitKey(1) & 0xFF == EXIT_KEY:
                break

    scream_detector.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()