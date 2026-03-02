# SentinelAI

**Real-time fall detection and emergency alert system using computer vision and audio monitoring.**

SentinelAI monitors a camera feed for fall events and loud sounds, automatically sending email alerts (with a video clip) to emergency contacts when a fall is confirmed.

---

## Features

- **Fall Detection** – Tracks body pose in real time using MediaPipe; flags a fall when the torso angle exceeds 30° from vertical for more than 1 second
- **Audio Monitoring** – Continuously captures microphone audio and detects loud sounds (screams, crashes) using RMS energy analysis
- **Video Clip Recording** – Saves a 10-second clip (5s before + 5s after the fall) as a compressed AVI file
- **Email Alerts** – Sends two emails to configured emergency contacts: an instant text alert, followed by the video clip as an attachment
- **False Alarm Cancel** – A 30-second cancel window lets you press `SPACE` to suppress an accidental alert before it sends
- **Web Dashboard** – A browser-based live monitoring view with pose overlay, status panels, and a cancel button
- **Desktop UI** – An OpenCV window with real-time overlays for fall status, torso angle, audio level, alert state, and FPS

---

## Project Structure

```
sentinelai/
├── main.py              # Desktop app entry point (OpenCV window)
├── web_server.py        # Flask web server entry point
├── fall_detector.py     # Pose-based fall detection logic
├── scream_detector.py   # Microphone audio / loud sound detection
├── video_buffer.py      # Rolling pre/post-fall video recording
├── alert_sender.py      # Email alert dispatch (instant + video clip)
├── alert_config.py      # Configuration: contacts, credentials, timing
├── testcam.py           # Quick camera connectivity test
├── dashboard.html       # Web dashboard UI
├── intro.html           # Web intro/landing page
├── requirements.txt     # Python dependencies
└── fall_clips/          # Auto-created folder for saved video clips
```

---

## Requirements

- Python 3.9+
- A webcam
- A microphone
- A Gmail account with an **App Password** enabled (standard passwords won't work)

Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `opencv-python`, `mediapipe`, `sounddevice`, `numpy`, `requests`, `flask`

---

## Configuration

Edit `alert_config.py` before running:

```python
EMERGENCY_CONTACTS = [
    {"name": "Your Contact", "email": "contact@example.com"},
]

SENDER_EMAIL    = "your_gmail@gmail.com"
SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password (16-char)

PRE_FALL_SECONDS  = 5    # Seconds of footage to keep before a fall
POST_FALL_SECONDS = 5    # Seconds of footage to record after a fall
ALERT_COOLDOWN_SECONDS = 60   # Minimum time between alerts
```

### Setting up a Gmail App Password

1. Enable 2-Step Verification on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Generate a password for "Mail" and paste the 16-character code into `SENDER_PASSWORD`

---

## Running

### Desktop mode (OpenCV window)

```bash
python main.py
```

**Controls:**
- `SPACE` — Cancel a false alarm during the 30-second window
- `Q` — Quit (waits for any in-progress email to finish)

### Web mode (browser dashboard)

```bash
python web_server.py
```

Then open:
- **Intro page** → http://localhost:5000
- **Live dashboard** → http://localhost:5000/dashboard

The dashboard streams the live camera feed with pose overlay and shows the same status indicators as the desktop UI.

### Camera test

```bash
python testcam.py
```

---

## How Fall Detection Works

1. MediaPipe Pose estimates body landmarks on every frame
2. The midpoints of the shoulders and hips are computed
3. The angle between the torso vector (hip → shoulder) and the vertical axis is calculated
4. If the angle stays above **30°** for at least **1 second**, a fall is confirmed
5. A 30-second cancel window opens — press `SPACE` or click Cancel in the dashboard to dismiss
6. If not cancelled, two emails are sent: an instant text alert, then the video clip once it is ready

The 30° threshold and 1-second confirmation delay are tunable in `fall_detector.py`.

---

## Alert Flow

```
Fall confirmed
     │
     ▼
30-second cancel window opens
     │
     ├─ SPACE / Cancel button → alert suppressed
     │
     └─ Window expires →
           Email 1: Instant text alert (sent immediately)
           Email 2: Video clip attached  (sent once clip is written, up to 40s wait)
```

Video clips larger than 23 MB are skipped for the attachment email. Clips are saved to `fall_clips/` as compressed MJPG AVI files (~2 MB typical).

---

## Tuning

| Parameter | Location | Default | Effect |
|---|---|---|---|
| `fall_angle_threshold` | `fall_detector.py` | 30° | Lower = more sensitive |
| `confirm_seconds` | `fall_detector.py` | 1.0 s | Higher = fewer false alarms |
| `loud_threshold` | `scream_detector.py` | 0.02 | Lower = more sensitive to sound |
| `PRE_FALL_SECONDS` | `alert_config.py` | 5 s | Pre-fall clip length |
| `POST_FALL_SECONDS` | `alert_config.py` | 5 s | Post-fall clip length |
| `ALERT_COOLDOWN_SECONDS` | `alert_config.py` | 60 s | Min time between alerts |

---

## Troubleshooting

**Camera not opening** — Run `testcam.py` to verify the camera index. If index `0` fails, try `cv2.VideoCapture(1)` in `main.py` / `web_server.py`.

**Gmail auth failed** — Ensure you are using an App Password (not your regular Gmail password) and that 2-Step Verification is active on the account.

**Too many false alarms** — Increase `fall_angle_threshold` (e.g. 45°) or `confirm_seconds` (e.g. 2.0 s) in `fall_detector.py`.

**Missing detections** — Ensure the person is fully visible in the frame, especially shoulders and hips. Poor lighting reduces MediaPipe's landmark confidence.

---

## License

This project is provided as-is for personal and educational use.
