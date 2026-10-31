"""
pi_camera_stream.py
Native Raspberry Pi Camera Module & Video Capture Handler for CivicGuard.
Supports:
  1. Official Picamera2 library on Raspberry Pi OS Bookworm / Bullseye (CSI Ribbon Cable)
  2. V4L2 hardware driver (/dev/video0) for Raspberry Pi Camera Module v2 / v3 / HQ
  3. Seamless fallback to standard OpenCV VideoCapture on development machines
"""

import cv2
import os

class UniversalCameraCapture:
    def __init__(self, source=0, width=640, height=480, fps=30):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.backend_type = "unknown"
        self.cap = None
        self.picam2 = None
        self.is_opened = False
        
        self.init_camera()

    def is_raspberry_pi(self):
        """Checks if current host is an actual Raspberry Pi"""
        try:
            if os.path.exists('/sys/firmware/devicetree/base/model'):
                with open('/sys/firmware/devicetree/base/model', 'r') as f:
                    model = f.read().lower()
                    if 'raspberry pi' in model:
                        return True
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    if 'Raspberry Pi' in f.read() or 'BCM' in f.read():
                        return True
        except Exception:
            pass
        return False

    def init_camera(self):
        """Initializes the camera using Picamera2, V4L2, or OpenCV"""
        # If user passed a video file path or string URL
        if isinstance(self.source, str) and (os.path.exists(self.source) or self.source.startswith("http") or self.source.startswith("rtsp")):
            print(f"[CameraCapture] Opening stream / file source: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            self.backend_type = "stream"
            self.is_opened = self.cap.isOpened()
            return

        # 1. Try native Raspberry Pi Camera Module (Picamera2) on Pi OS
        try:
            from picamera2 import Picamera2
            print("[CameraCapture] Detected Raspberry Pi Picamera2! Initializing CSI Camera...")
            self.picam2 = Picamera2()
            config = self.picam2.create_video_configuration(main={"size": (self.width, self.height), "format": "BGR888"})
            self.picam2.configure(config)
            self.picam2.start()
            self.backend_type = "picamera2_csi"
            self.is_opened = True
            print(f"[CameraCapture] ✅ Raspberry Pi Camera (Picamera2 CSI) successfully active at {self.width}x{self.height}!")
            return
        except (ImportError, Exception):
            # Not on Pi with Picamera2 or Picamera2 not installed
            pass

        # 2. Try V4L2 backend on Linux/Raspberry Pi (/dev/video0)
        cam_idx = int(self.source) if str(self.source).isdigit() else 0
        print(f"[CameraCapture] Probing V4L2 hardware camera device index {cam_idx}...")
        
        try:
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.backend_type = "v4l2_hardware"
                self.is_opened = True
                print(f"[CameraCapture] ✅ Hardware V4L2 Camera {cam_idx} opened successfully!")
                return
        except Exception:
            pass

        # 3. Fallback to standard OpenCV VideoCapture
        print(f"[CameraCapture] Falling back to standard OpenCV VideoCapture({cam_idx})...")
        self.cap = cv2.VideoCapture(cam_idx)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.backend_type = "opencv_standard"
            self.is_opened = True
            print(f"[CameraCapture] ✅ Camera {cam_idx} active via OpenCV standard backend!")
        else:
            print(f"[CameraCapture] ⚠️ Camera {cam_idx} could not be opened.")
            if os.path.exists("sample_crowd.mp4"):
                print("[CameraCapture] Auto-fallback to local sample_crowd.mp4 test feed!")
                self.cap = cv2.VideoCapture("sample_crowd.mp4")
                if self.cap.isOpened():
                    self.source = "sample_crowd.mp4"
                    self.backend_type = "stream"
                    self.is_opened = True
                    return
            self.is_opened = False

    def read(self):
        """Reads a single BGR frame from the active camera backend"""
        if not self.is_opened:
            return False, None

        # Picamera2 native capture
        if self.backend_type == "picamera2_csi" and self.picam2 is not None:
            try:
                frame = self.picam2.capture_array()
                if frame is not None and frame.size > 0:
                    return True, frame
            except Exception as e:
                print(f"[CameraCapture] Picamera2 frame read error: {e}")
                return False, None

        # OpenCV / V4L2 / Stream capture
        if self.cap is not None:
            ret, frame = self.cap.read()
            if not ret and isinstance(self.source, str) and os.path.exists(self.source):
                # Loop video file seamlessly
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            return ret, frame

        return False, None

    def release(self):
        """Releases all camera resources safely"""
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.is_opened = False
        print("[CameraCapture] Camera released.")
