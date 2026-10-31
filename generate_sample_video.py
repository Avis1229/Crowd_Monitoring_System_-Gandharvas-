

import cv2
import numpy as np
import random
import os

def create_synthetic_crowd_video(output_path="sample_crowd.mp4", duration_sec=15, fps=25, num_people=14):
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration_sec * fps
    
    # Initialize people (each person has pos, speed, color, radius/size, direction)
    people = []
    for i in range(num_people):
        people.append({
            "id": i,
            "x": random.uniform(50, width - 50),
            "y": random.uniform(50, height - 50),
            "vx": random.uniform(-2.5, 2.5),
            "vy": random.uniform(-1.8, 1.8),
            "size": random.randint(18, 26),
            "shirt_color": (random.randint(50, 220), random.randint(50, 220), random.randint(50, 220)),
        })
    for frame_idx in range(total_frames):
        # Background: Cobblestone courtyard / scenic overlook pavement
        frame = np.full((height, width, 3), 42, dtype=np.uint8)
        
        # Draw some scenic ground tiles/guidelines
        for y_line in range(0, height, 40):
            cv2.line(frame, (0, y_line), (width, y_line), (55, 55, 58), 1)
        for x_line in range(0, width, 50):
            cv2.line(frame, (x_line, 0), (x_line, height), (55, 55, 58), 1)
            
        # Draw a gate / checkpoint line (mock tripwire)
        gate_y = height // 2
        cv2.line(frame, (40, gate_y), (width - 40, gate_y), (0, 180, 255), 2)
        cv2.putText(frame, "CHECKPOINT GATE / COUNT LINE", (45, gate_y - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 255), 1, cv2.LINE_AA)
                    
        # Update and draw each pedestrian (simplified top-down/isometric silhouette)
        for p in people:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            
            # Bounce off walls
            if p["x"] < 30 or p["x"] > width - 30:
                p["vx"] *= -1
            if p["y"] < 30 or p["y"] > height - 30:
                p["vy"] *= -1
                
            x, y = int(p["x"]), int(p["y"])
            s = p["size"]
            
            # Draw shadow
            cv2.ellipse(frame, (x + 3, y + s + 2), (s, int(s * 0.4)), 0, 0, 360, (20, 20, 20), -1)
            
            # Draw body (torso & shoulders)
            cv2.ellipse(frame, (x, y + s // 2), (s, int(s * 1.3)), 0, 0, 360, p["shirt_color"], -1)
            # Draw head
            cv2.circle(frame, (x, y - s // 3), int(s * 0.55), (190, 175, 160), -1)
            cv2.circle(frame, (x, y - s // 3), int(s * 0.55), (80, 80, 80), 1)
            
        # Timestamp overlay
        sec = frame_idx / fps
        cv2.putText(frame, f"Simulated Tourist Feed | T+{sec:.1f}s | Active Occupants: {len(people)}", 
                    (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
                    
        out.write(frame)
        
    out.release()
    print(f"Sample crowd video created at: {output_path} ({duration_sec}s, {total_frames} frames)")

if __name__ == "__main__":
    create_synthetic_crowd_video()
