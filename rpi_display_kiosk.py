"""
rpi_display_kiosk.py
Hardware Display Module for Raspberry Pi / On-Site Kiosk Screen.
Fulfills the 'RPi, camera, display' requirement of the AI Tourist Crowd Monitor.

Renders a public-facing digital signage HUD for visitor checkpoints:
- Live privacy-blurred feed & density heatmap
- High-visibility traffic light occupancy status (GREEN / AMBER / RED)
- Real-time occupancy gauge & capacity limits
- GDPR-compliant anonymous sensing declaration

Usage:
    python3 rpi_display_kiosk.py --camera 0 --scenario B --capacity 50 --fullscreen
"""

import cv2
import numpy as np
import time
import argparse
from crowd_engine import CrowdEngine

def draw_rounded_rect(img, pt1, pt2, color, thickness=-1, radius=12):
    x1, y1 = pt1
    x2, y2 = pt2
    if thickness == -1:
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)
    else:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

def run_kiosk_display(camera_src=0, scenario="B", capacity=50, warn_limit=32, crit_limit=45, fullscreen=False):
    engine = CrowdEngine(model_name=None, conf_thresh=0.35)
    
    cap = cv2.VideoCapture(camera_src)
    if not cap.isOpened():
        print(f"[RPi Display] Could not open camera {camera_src}. Falling back to sample_crowd.mp4...")
        cap = cv2.VideoCapture("sample_crowd.mp4")
        if not cap.isOpened():
            print("[RPi Display] Error: No camera or sample video available.")
            return

    window_name = "AI Tourist Crowd Monitor - Public Display"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    else:
        cv2.resizeWindow(window_name, 1280, 720)

    scenario_names = {
        "A": "CAMPUS DINING HALL",
        "B": "HERITAGE MONUMENT PORTAL",
        "C": "TOURIST GATEWAY CHECKPOINT",
        "D": "MOUNTAIN SCENIC VIEWPOINT"
    }
    venue_title = scenario_names.get(scenario.upper(), "TOURIST CHECKPOINT")

    print(f"[RPi Display] Active on screen for {venue_title}. Press 'q' or ESC to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break

        # Process frame with privacy blur
        processed_frame, metrics = engine.process_frame(
            frame=frame,
            privacy_mode="blur",
            line_crossing_enabled=True,
            density_threshold_warning=warn_limit,
            density_threshold_critical=crit_limit,
            show_heatmap=True,
            heatmap_alpha=0.4
        )

        headcount = metrics["headcount"]
        
        # Build 1280x720 public kiosk canvas
        canvas = np.full((720, 1280, 3), (20, 24, 33), dtype=np.uint8)

        # 1. Top Header Banner
        cv2.rectangle(canvas, (0, 0), (1280, 80), (15, 18, 25), -1)
        cv2.line(canvas, (0, 80), (1280, 80), (45, 52, 70), 2)
        cv2.putText(canvas, f"AI TOURIST CROWD MONITOR  |  {venue_title}", (30, 52),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (240, 240, 245), 2, cv2.LINE_AA)
        
        # Live Time
        time_str = time.strftime("%H:%M:%S")
        cv2.putText(canvas, time_str, (1130, 52), cv2.FONT_HERSHEY_DUPLEX, 0.9, (130, 145, 170), 2, cv2.LINE_AA)

        # 2. Left: Video Stream Box (680x510)
        feed_w, feed_h = 680, 510
        cam_resized = cv2.resize(processed_frame, (feed_w, feed_h))
        canvas[110:110+feed_h, 30:30+feed_w] = cam_resized
        cv2.rectangle(canvas, (30, 110), (30+feed_w, 110+feed_h), (50, 60, 80), 2)
        cv2.putText(canvas, "LIVE CAMERA (ANONYMIZED & HEATMAP)", (45, 138),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 210), 1, cv2.LINE_AA)

        # 3. Right: Large Status & Occupancy Cards (X: 740 to 1250)
        # Determine status colors
        if headcount >= crit_limit:
            status_title = "CAPACITY REACHED"
            status_desc = "ENTRY TEMPORARILY PAUSED"
            status_bg = (30, 30, 180)  # Red BGR
            indicator_color = (0, 0, 255)
        elif headcount >= warn_limit:
            status_title = "HIGH FOOTFALL"
            status_desc = "EXPECT SHORT WAIT AT COUNTER"
            status_bg = (20, 120, 200) # Amber BGR
            indicator_color = (0, 200, 255)
        else:
            status_title = "NORMAL FLOW"
            status_desc = "SAFE CAPACITY - PROCEED"
            status_bg = (30, 140, 50)  # Green BGR
            indicator_color = (0, 255, 100)

        # Big Status Badge
        draw_rounded_rect(canvas, (740, 110), (1250, 250), status_bg, -1, 16)
        cv2.circle(canvas, (785, 165), 18, indicator_color, -1)
        cv2.putText(canvas, status_title, (820, 175), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, status_desc, (820, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 235, 245), 1, cv2.LINE_AA)

        # Occupancy Counter Box
        draw_rounded_rect(canvas, (740, 270), (1250, 480), (30, 36, 50), -1, 16)
        cv2.putText(canvas, "CURRENT ESTIMATED OCCUPANCY", (765, 305),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 155, 180), 1, cv2.LINE_AA)
        
        occ_str = f"{headcount}"
        cv2.putText(canvas, occ_str, (765, 385), cv2.FONT_HERSHEY_DUPLEX, 2.6, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(canvas, f"/ {capacity} MAX CAPACITY", (940, 375),
                    cv2.FONT_HERSHEY_DUPLEX, 0.85, (130, 145, 170), 2, cv2.LINE_AA)

        # Progress bar
        bar_x1, bar_y1 = 765, 420
        bar_w, bar_h = 450, 22
        pct = min(1.0, headcount / max(1, capacity))
        cv2.rectangle(canvas, (bar_x1, bar_y1), (bar_x1 + bar_w, bar_y1 + bar_h), (50, 58, 75), -1)
        fill_w = int(bar_w * pct)
        cv2.rectangle(canvas, (bar_x1, bar_y1), (bar_x1 + fill_w, bar_y1 + bar_h), indicator_color, -1)
        cv2.putText(canvas, f"{int(pct*100)}% Full", (bar_x1 + bar_w - 95, bar_y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

        # Line Crossing Stats Box
        draw_rounded_rect(canvas, (740, 500), (1250, 620), (25, 30, 42), -1, 16)
        cv2.putText(canvas, f"GATE FLOW COUNTERS:   TOTAL IN: {metrics['in_count']}    |    TOTAL OUT: {metrics['out_count']}",
                    (765, 565), cv2.FONT_HERSHEY_DUPLEX, 0.65, (220, 220, 230), 1, cv2.LINE_AA)

        # 4. Bottom Footer Banner (Privacy Declaration)
        cv2.rectangle(canvas, (0, 650), (1280, 720), (15, 18, 25), -1)
        cv2.line(canvas, (0, 650), (1280, 650), (45, 52, 70), 1)
        privacy_text = "🔒 PRIVACY-PRESERVING AGGREGATE SYSTEM: NO FACES OR IDENTITIES STORED | GDPR & ETHICAL AI COMPLIANT"
        cv2.putText(canvas, privacy_text, (180, 690), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 180, 140), 1, cv2.LINE_AA)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(20) & 0xFF
        if key == ord('q') or key == 27: # 'q' or ESC
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPi Kiosk Display for Tourist Crowd Monitor")
    parser.add_argument("--camera", default=0, help="Camera index or video file")
    parser.add_argument("--scenario", default="B", help="Scenario letter (A, B, C, D)")
    parser.add_argument("--capacity", type=int, default=50, help="Max venue capacity")
    parser.add_argument("--warn", type=int, default=32, help="Warning threshold")
    parser.add_argument("--crit", type=int, default=45, help="Critical threshold")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen")
    args = parser.parse_args()
    
    # Try parsing camera as int if numeric
    cam_src = int(args.camera) if str(args.camera).isdigit() else args.camera
    run_kiosk_display(
        camera_src=cam_src,
        scenario=args.scenario,
        capacity=args.capacity,
        warn_limit=args.warn,
        crit_limit=args.crit,
        fullscreen=args.fullscreen
    )
