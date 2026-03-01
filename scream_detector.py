"""
SentinelAI – scream_detector.py
=================================
Real-time microphone capture and loud sound detection using RMS energy.

HOW IT WORKS
─────────────
1. Captures audio in short chunks (default 2 seconds) using sounddevice
2. Computes RMS (Root Mean Square) energy of each chunk:
      RMS = sqrt( mean( samples² ) )
   RMS gives a single number representing the loudness of the chunk.
3. If RMS exceeds LOUD_THRESHOLD → marks "LOUD SOUND DETECTED"
4. Runs in a background thread so it never blocks the video loop
"""

import threading
import numpy as np
import sounddevice as sd
from dataclasses import dataclass, field

# ── Tuneable parameters ────────────────────────────────────────────────────────
SAMPLE_RATE:     int   = 16000   # Hz – good enough for energy detection
CHUNK_DURATION:  float = 2.0     # seconds per audio chunk
LOUD_THRESHOLD:  float = 0.02    # RMS threshold (0.0–1.0) – tune to your mic
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ScreamDetector:
    """
    Continuously captures microphone audio in a background thread.
    Read is_loud and rms_level from the main thread at any time.
    """
    sample_rate:    int   = SAMPLE_RATE
    chunk_duration: float = CHUNK_DURATION
    loud_threshold: float = LOUD_THRESHOLD

    # internal state
    _rms:       float = field(default=0.0,   init=False, repr=False)
    _is_loud:   bool  = field(default=False, init=False, repr=False)
    _running:   bool  = field(default=False, init=False, repr=False)
    _thread:    threading.Thread = field(default=None, init=False, repr=False)
    _lock:      threading.Lock   = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._lock = threading.Lock()

    # ── public read-only properties ───────────────────────────────────────────

    @property
    def is_loud(self) -> bool:
        """True if latest chunk exceeded the RMS threshold."""
        with self._lock:
            return self._is_loud

    @property
    def rms_level(self) -> float:
        """Latest RMS value (0.0 – 1.0+)."""
        with self._lock:
            return self._rms

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background audio capture thread."""
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("[ScreamDetector] Microphone capture started.")

    def stop(self) -> None:
        """Stop background capture."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[ScreamDetector] Microphone capture stopped.")

    # ── internal ──────────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Continuously capture audio chunks and compute RMS."""
        frames_per_chunk = int(self.sample_rate * self.chunk_duration)

        while self._running:
            try:
                audio = sd.rec(
                    frames_per_chunk,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()  # block until chunk is ready

                rms   = self._compute_rms(audio)
                loud  = rms > self.loud_threshold

                with self._lock:
                    self._rms     = rms
                    self._is_loud = loud

            except Exception as e:
                print(f"[ScreamDetector] Audio error: {e}")
                break

    @staticmethod
    def _compute_rms(audio: np.ndarray) -> float:
        """Return Root Mean Square energy of the audio chunk."""
        return float(np.sqrt(np.mean(audio ** 2)))