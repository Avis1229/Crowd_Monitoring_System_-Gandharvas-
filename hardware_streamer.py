"""
hardware_streamer.py
Lightweight Edge Camera Streamer for Raspberry Pi / External Device / Second Machine.
Streams video from a connected USB camera or Raspberry Pi Camera module over HTTP MJPEG.

Usage on Raspberry Pi / Camera Device:
    python3 hardware_streamer.py --port 8080 --camera 0 --fps 20 --width 640 --height 480

Then in the AI Tourist Crowd Monitor dashboard, select 'RTSP / IP Camera / Network Stream'
and enter:
    http://<DEVICE_IP>:8080/video_feed
"""

import cv2
import time
import argparse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

global_frame = None
lock = threading.Lock()

class VideoCaptureThread(threading.Thread):
    def __init__(self, src=0, width=640, height=480, fps=20):
        super().__init__()
        self.src = src
        self.width = width
        self.height = height
        self.fps = fps
        self.running = True
        
    def run(self):
        global global_frame
        cap = cv2.VideoCapture(self.src)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        if not cap.isOpened():
            print(f"[HardwareStreamer] ERROR: Could not open camera source {self.src}")
            return
            
        print(f"[HardwareStreamer] Camera source {self.src} initialized successfully.")
        
        while self.running:
            ret, frame = cap.read()
            if ret:
                with lock:
                    global_frame = frame.copy()
            else:
                time.sleep(0.05)
            time.sleep(1.0 / self.fps)
            
        cap.release()

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            
            try:
                while True:
                    with lock:
                        if global_frame is None:
                            time.sleep(0.05)
                            continue
                        ret, jpeg = cv2.imencode('.jpg', global_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        
                    if ret:
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(jpeg)))
                        self.end_headers()
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b'\r\n')
                    time.sleep(0.04) # ~25 fps max
            except Exception:
                pass
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <html>
                <head><title>AI Tourist Crowd Monitor - Edge Stream</title></head>
                <body style="font-family:sans-serif; text-align:center; background:#121212; color:#fff; padding:20px;">
                    <h2>AI Tourist Crowd Monitor - Edge Stream Active</h2>
                    <p>Endpoint: <code>/video_feed</code></p>
                    <img src="/video_feed" style="border:2px solid #00d2ff; border-radius:8px; max-width:90%;">
                </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

def main():
    parser = argparse.ArgumentParser(description="Edge Camera Streamer for Crowd Monitor")
    parser.add_argument("--port", type=int, default=8080, help="HTTP streaming port")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (e.g. 0 or /dev/video0)")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--fps", type=int, default=20, help="Streaming FPS")
    args = parser.parse_args()
    
    cap_thread = VideoCaptureThread(src=args.camera, width=args.width, height=args.height, fps=args.fps)
    cap_thread.daemon = True
    cap_thread.start()
    
    server_address = ('', args.port)
    httpd = HTTPServer(server_address, StreamHandler)
    print(f"\n[HardwareStreamer] Server running at http://0.0.0.0:{args.port}/video_feed")
    print("[HardwareStreamer] Connect from AI Tourist Crowd Monitor dashboard.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[HardwareStreamer] Stopping streamer...")
        cap_thread.running = False
        httpd.server_close()

if __name__ == '__main__':
    main()
