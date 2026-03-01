"""
SentinelAI – fall_detector.py
==============================
Detects falls using the angle between the torso and the vertical axis.

HOW THE ANGLE CALCULATION WORKS
─────────────────────────────────
1. Shoulder midpoint  = average of left & right shoulder (x, y)
2. Hip midpoint       = average of left & right hip (x, y)
3. Torso vector       = hip_mid → shoulder_mid  (dx, dy)
4. Vertical reference = (0, -1)  ← pointing straight up in image coords
                        (in OpenCV, y increases downward, so "up" is -y)
5. Angle (degrees)    = arctan2(|dx|, |dy|)
                        → 0°  when perfectly upright
                        → 90° when completely horizontal (lying flat)

A person is flagged as FALLEN when:
   angle > FALL_ANGLE_THRESHOLD  for longer than  CONFIRM_SECONDS
The time gate prevents a single stumble or lean from triggering a false alarm.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional

# ── Tuneable parameters ────────────────────────────────────────────────────────
FALL_ANGLE_THRESHOLD: float = 55.0   # degrees from vertical → tune as needed
CONFIRM_SECONDS:      float = 1.0    # must stay above threshold for this long
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class FallDetector:
    """
    Stateful fall detector.  Call update() on every frame; read is_fallen.
    """
    fall_angle_threshold: float = FALL_ANGLE_THRESHOLD
    confirm_seconds:      float = CONFIRM_SECONDS

    # internal state – do not set manually
    _angle:           float         = field(default=0.0,  init=False, repr=False)
    _fall_start_time: Optional[float] = field(default=None, init=False, repr=False)
    _is_fallen:       bool          = field(default=False, init=False, repr=False)

    # ── public read-only properties ───────────────────────────────────────────

    @property
    def is_fallen(self) -> bool:
        """True once fall is confirmed (angle high for ≥ confirm_seconds)."""
        return self._is_fallen

    @property
    def torso_angle(self) -> float:
        """Latest torso angle in degrees (0 = upright, 90 = horizontal)."""
        return self._angle

    # ── main API ──────────────────────────────────────────────────────────────

    def update(self, landmarks, frame_width: int, frame_height: int) -> bool:
        """
        Process one frame's landmarks.

        Parameters
        ----------
        landmarks    : mediapipe NormalizedLandmarkList (or None if no person)
        frame_width  : pixel width  of the video frame
        frame_height : pixel height of the video frame

        Returns
        -------
        bool – current is_fallen state
        """
        if landmarks is None:
            # No person visible – reset timer but keep fallen flag
            self._fall_start_time = None
            return self._is_fallen

        angle = self._compute_torso_angle(landmarks, frame_width, frame_height)
        if angle is None:
            self._fall_start_time = None
            return self._is_fallen

        self._angle = angle
        self._update_fall_state(angle)
        return self._is_fallen

    def reset(self) -> None:
        """Manually clear the fallen state (e.g. after an alert is sent)."""
        self._is_fallen       = False
        self._fall_start_time = None

    # ── internal helpers ──────────────────────────────────────────────────────

    def _compute_torso_angle(self, landmarks, w: int, h: int) -> Optional[float]:
        """
        Return the angle (degrees) between the torso vector and vertical.
        Returns None if any required landmark has low visibility.
        """
        import mediapipe as mp
        lm = landmarks.landmark
        L  = mp.solutions.pose.PoseLandmark

        # Require decent visibility on all four anchor points
        required = [L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.LEFT_HIP, L.RIGHT_HIP]
        if any(lm[p].visibility < 0.5 for p in required):
            return None

        # --- pixel coordinates -------------------------------------------
        def px(landmark):
            return landmark.x * w, landmark.y * h

        ls_x, ls_y = px(lm[L.LEFT_SHOULDER])
        rs_x, rs_y = px(lm[L.RIGHT_SHOULDER])
        lh_x, lh_y = px(lm[L.LEFT_HIP])
        rh_x, rh_y = px(lm[L.RIGHT_HIP])

        # --- midpoints ---------------------------------------------------
        shoulder_mid = ((ls_x + rs_x) / 2, (ls_y + rs_y) / 2)
        hip_mid      = ((lh_x + rh_x) / 2, (lh_y + rh_y) / 2)

        # --- torso vector (hip → shoulder) --------------------------------
        dx = shoulder_mid[0] - hip_mid[0]
        dy = shoulder_mid[1] - hip_mid[1]   # negative = shoulder above hip (normal)

        # --- angle from vertical -----------------------------------------
        # arctan2(horizontal_component, vertical_component)
        # We use |dy| so the sign of dy doesn't affect the result;
        # the angle is always 0–90°.
        angle_rad = math.atan2(abs(dx), abs(dy))
        angle_deg = math.degrees(angle_rad)
        return angle_deg

    def _update_fall_state(self, angle: float) -> None:
        """Apply the time-confirmation gate to avoid flickering."""
        now = time.time()

        if angle > self.fall_angle_threshold:
            if self._fall_start_time is None:
                self._fall_start_time = now          # start the clock
            elif now - self._fall_start_time >= self.confirm_seconds:
                self._is_fallen = True               # confirmed fall
        else:
            # Angle back to safe range – reset everything
            self._fall_start_time = None
            self._is_fallen       = False