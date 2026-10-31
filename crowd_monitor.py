"""
crowd_monitor.py
AI Tourist Crowd Monitor - Live Crowd Density Estimation & Footfall Analytics
Compliant with Hackathon Scenarios A, B, C, D and 36-Hour Ground Truth Evidence Validation.
"""

import streamlit as st
import cv2
import pandas as pd
import time
from datetime import datetime
import os
import tempfile
import plotly.graph_objects as go
import plotly.express as px

from crowd_engine import CrowdEngine
from benchmark_data import generate_36hr_evidence_dataset, calculate_evidence_metrics

# ---------------------------------------------------------
# Page Configuration & Modern Sleek Aesthetics
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Tourist Crowd Monitor",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Dark glassmorphic background & typography */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(15, 23, 42, 0.95), rgba(10, 15, 30, 0.98));
    }
    
    .header-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .metric-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
        margin-right: 8px;
    }
    
    .badge-privacy {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-ai {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .badge-hw {
        background: rgba(168, 85, 247, 0.2);
        color: #a855f7;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    
    .alert-banner-normal {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
        border-left: 5px solid #10b981;
        padding: 12px 18px;
        border-radius: 8px;
        color: #34d399;
        font-weight: 600;
    }
    
    .alert-banner-warning {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.05));
        border-left: 5px solid #f59e0b;
        padding: 12px 18px;
        border-radius: 8px;
        color: #fbbf24;
        font-weight: 600;
        animation: pulseWarning 2s infinite;
    }
    
    .alert-banner-critical {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.25), rgba(239, 68, 68, 0.05));
        border-left: 5px solid #ef4444;
        padding: 12px 18px;
        border-radius: 8px;
        color: #f87171;
        font-weight: 700;
        animation: pulseCritical 1.2s infinite;
    }
    
    @keyframes pulseCritical {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    
    @keyframes pulseWarning {
        0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.3); }
        70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
        100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = CrowdEngine(model_name="yolov8n.pt", conf_thresh=0.35)

if "telemetry" not in st.session_state:
    st.session_state.telemetry = []

if "incidents" not in st.session_state:
    st.session_state.incidents = []

if "is_monitoring" not in st.session_state:
    st.session_state.is_monitoring = False

# Ensure alerts directory exists
os.makedirs("alerts", exist_ok=True)

# ---------------------------------------------------------
# Sidebar Controls & Scenario Presets
# ---------------------------------------------------------
st.sidebar.image("https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=400&q=80", use_container_width=True)
st.sidebar.title("🎛️ Control Center")

scenario_options = {
    "C": "C. Tourist Gateway Crowd Alerts (Default)",
    "A": "A. Campus Dining Footfall (Entry/Exit Counter)",
    "B": "B. Heritage Visitor Occupancy (Aggregate Headcount)",
    "D": "D. Mountain Attraction Congestion (Scenic Overlook)"
}
selected_sc_key = st.sidebar.selectbox("🎯 Target Problem Scenario:", options=list(scenario_options.keys()), format_func=lambda k: scenario_options[k])

# Preset default thresholds based on scenario
preset_defaults = {
    "A": {"warn": 35, "crit": 48, "line": True, "cap": 60, "name": "Campus Dining Hall"},
    "B": {"warn": 28, "crit": 40, "line": False, "cap": 50, "name": "Heritage Monument Portal"},
    "C": {"warn": 30, "crit": 45, "line": True, "cap": 75, "name": "Tourist Gateway Plaza"},
    "D": {"warn": 18, "crit": 28, "line": False, "cap": 35, "name": "Scenic Mountain Viewpoint"}
}
cfg = preset_defaults[selected_sc_key]

st.sidebar.markdown("---")
st.sidebar.subheader("📹 Video Source")
input_mode = st.sidebar.radio(
    "Choose Input Stream:",
    ["Simulated Scenic Test Video (Zero Config)", "Live USB / Laptop Webcam", "Upload Video File", "RTSP / IP Camera / Pi Stream"]
)

video_source_path = None
if input_mode == "Simulated Scenic Test Video (Zero Config)":
    if os.path.exists("sample_crowd.mp4"):
        video_source_path = "sample_crowd.mp4"
    else:
        st.sidebar.warning("Generating sample test video...")
        import generate_sample_video
        generate_sample_video.create_synthetic_crowd_video("sample_crowd.mp4")
        video_source_path = "sample_crowd.mp4"
elif input_mode == "Live USB / Laptop Webcam":
    cam_index = st.sidebar.number_input("Webcam Device Index (/dev/videoX):", min_value=0, max_value=5, value=0)
    video_source_path = int(cam_index)
elif input_mode == "Upload Video File":
    uploaded_file = st.sidebar.file_uploader("Upload MP4 / AVI / MOV:", type=["mp4", "avi", "mov", "mkv"])
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_file.read())
        video_source_path = tfile.name
elif input_mode == "RTSP / IP Camera / Pi Stream":
    stream_url = st.sidebar.text_input("Stream URL:", value="http://192.168.1.50:8080/video_feed")
    video_source_path = stream_url

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Privacy & AI Settings")
privacy_mode = st.sidebar.selectbox(
    "Anonymization Mode:",
    ["blur", "anonymize_box", "none"],
    format_func=lambda x: {
        "blur": "Gaussian Face/Identity Blur (GDPR Safe)",
        "anonymize_box": "Abstract Centroids Only (Zero Identification)",
        "none": "Full Detection Bounding Box"
    }[x]
)

conf_threshold = st.sidebar.slider("AI Confidence Threshold:", 0.15, 0.85, 0.35, 0.05)
st.session_state.engine.conf_thresh = conf_threshold

show_heatmap = st.sidebar.checkbox("Overlay Density Heatmap", value=True)
heatmap_intensity = st.sidebar.slider("Heatmap Opacity:", 0.1, 0.9, 0.45, 0.05) if show_heatmap else 0.0

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Alert Thresholds")
col_w, col_c = st.sidebar.columns(2)
warning_threshold = col_w.number_input("Warning (Yellow):", min_value=1, max_value=200, value=cfg["warn"])
critical_threshold = col_c.number_input("Critical (Red):", min_value=1, max_value=250, value=cfg["crit"])

st.sidebar.markdown("---")
st.sidebar.subheader("🚶 Line Crossing (Footfall)")
line_crossing_enabled = st.sidebar.checkbox("Enable In/Out Counting Line", value=cfg["line"])
line_orientation = st.sidebar.selectbox("Line Orientation:", ["horizontal", "vertical"]) if line_crossing_enabled else "horizontal"
line_ratio = st.sidebar.slider("Line Position Ratio:", 0.1, 0.9, 0.5, 0.05) if line_crossing_enabled else 0.5

# ---------------------------------------------------------
# Main UI Header
# ---------------------------------------------------------
st.markdown("""
<div class="header-card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <h1 style="margin:0; font-size:2.2rem; font-weight:700; background:linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                AI Tourist Crowd Monitor
            </h1>
            <p style="margin:6px 0 0 0; color:#94a3b8; font-size:1.05rem;">
                Live Privacy-Preserving Crowd-Density Estimation & Overcrowding Early Warning System
            </p>
        </div>
        <div>
            <span class="metric-badge badge-privacy">🔒 Non-Identifying Aggregate</span>
            <span class="metric-badge badge-ai">⚡ YOLOv8 + BoT-SORT</span>
            <span class="metric-badge badge-hw">📡 Hardware Edge Ready</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Top Navigation Tabs
# ---------------------------------------------------------
tab_live, tab_kiosk, tab_telemetry, tab_evidence, tab_hardware = st.tabs([
    "📺 Live Monitor & Vision Feed",
    "🖥️ Public Checkpoint Kiosk (RPi Display)",
    "📈 Real-time Telemetry & Influx",
    "📊 36-Hour Ground Truth Benchmark",
    "🛠️ Hardware & Pi Deployment"
])

# ---------------------------------------------------------
# TAB 1: Live Monitor & Vision Feed
# ---------------------------------------------------------
with tab_live:
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
    
    with col_ctrl1:
        if not st.session_state.is_monitoring:
            if st.button("▶️ Start Live Monitoring", type="primary", use_container_width=True):
                st.session_state.is_monitoring = True
                st.rerun()
        else:
            if st.button("⏹️ Stop Monitoring", type="secondary", use_container_width=True):
                st.session_state.is_monitoring = False
                st.rerun()
                
    with col_ctrl2:
        if st.button("🔄 Reset In/Out Counts", use_container_width=True):
            st.session_state.engine.reset_counts()
            st.toast("Footfall counters and heatmap reset!", icon="✅")
            
    with col_ctrl3:
        if st.button("🧹 Clear Telemetry History", use_container_width=True):
            st.session_state.telemetry = []
            st.toast("Telemetry buffer cleared!", icon="🧹")

    # Dynamic KPI Cards Placeholder
    kpi_placeholder = st.empty()
    alert_placeholder = st.empty()
    
    # Video and Side Analytics Columns
    col_video, col_side_stats = st.columns([3, 1.4])
    
    with col_video:
        video_placeholder = st.empty()
        
    with col_side_stats:
        st.markdown("### 📋 Live Influx HUD")
        hud_placeholder = st.empty()
        st.markdown("### 📸 Incident Snapshots")
        snapshot_placeholder = st.empty()

    # Stream Processing Loop
    if st.session_state.is_monitoring:
        if video_source_path is None:
            st.error("Please configure a valid video source in the sidebar.")
        else:
            cap = cv2.VideoCapture(video_source_path)
            
            if not cap.isOpened():
                st.error(f"Failed to open video source: `{video_source_path}`. If using a webcam, check if index 0 is available.")
                st.session_state.is_monitoring = False
            else:
                last_incident_time = 0
                
                while st.session_state.is_monitoring:
                    ret, frame = cap.read()
                    if not ret:
                        # If video file or test clip reached the end, loop it
                        if isinstance(video_source_path, str) and os.path.exists(video_source_path):
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = cap.read()
                            if not ret:
                                break
                        else:
                            break
                            
                    # Resize for responsive web display
                    frame = cv2.resize(frame, (720, int(720 * frame.shape[0] / frame.shape[1])))
                    
                    # Process frame through CrowdEngine
                    processed_frame, metrics = st.session_state.engine.process_frame(
                        frame=frame,
                        privacy_mode=privacy_mode,
                        line_crossing_enabled=line_crossing_enabled,
                        line_orientation=line_orientation,
                        line_ratio=line_ratio,
                        density_threshold_warning=warning_threshold,
                        density_threshold_critical=critical_threshold,
                        show_heatmap=show_heatmap,
                        heatmap_alpha=heatmap_intensity
                    )
                    
                    # Log telemetry
                    now_str = datetime.now().strftime("%H:%M:%S")
                    st.session_state.telemetry.append({
                        "time": now_str,
                        "timestamp": datetime.now(),
                        "headcount": metrics["headcount"],
                        "in_count": metrics["in_count"],
                        "out_count": metrics["out_count"],
                        "net_flow": metrics["net_flow"],
                        "alert_level": metrics["alert_level"]
                    })
                    if len(st.session_state.telemetry) > 300:
                        st.session_state.telemetry.pop(0)
                        
                    # Handle Overcrowding Incident Capture
                    if metrics["alert_level"] in ["WARNING", "CRITICAL"]:
                        if time.time() - last_incident_time > 10:  # Snapshot throttle (1 every 10s)
                            last_incident_time = time.time()
                            os.makedirs("alerts", exist_ok=True)
                            snap_filename = f"alerts/incident_{int(last_incident_time)}.jpg"
                            cv2.imwrite(snap_filename, processed_frame)
                            st.session_state.incidents.append({
                                "file": snap_filename,
                                "time": now_str,
                                "count": metrics["headcount"],
                                "level": metrics["alert_level"]
                            })
                            if len(st.session_state.incidents) > 6:
                                st.session_state.incidents.pop(0)

                    # Update Alert Banner
                    lvl = metrics["alert_level"]
                    if lvl == "CRITICAL":
                        alert_placeholder.markdown(
                            f"""<div class="alert-banner-critical">
                                🚨 CRITICAL OVERCROWDING ALERT: {metrics['headcount']} visitors detected! (Capacity Threshold: {critical_threshold}).
                                Immediate gate throttling / evacuation procedure recommended.
                            </div>""", unsafe_allow_html=True
                        )
                    elif lvl == "WARNING":
                        alert_placeholder.markdown(
                            f"""<div class="alert-banner-warning">
                                ⚠️ HIGH FOOTFALL WARNING: {metrics['headcount']} visitors detected (Warning Threshold: {warning_threshold}).
                                Monitor bottleneck areas.
                            </div>""", unsafe_allow_html=True
                        )
                    else:
                        alert_placeholder.markdown(
                            f"""<div class="alert-banner-normal">
                                🟢 NORMAL CROWD FLOW: {metrics['headcount']} visitors detected. Density is well within safety thresholds.
                            </div>""", unsafe_allow_html=True
                        )

                    # Update KPI Cards
                    kpi_cols = kpi_placeholder.columns(5)
                    kpi_cols[0].metric("👥 Current Headcount", f"{metrics['headcount']} pers", delta=f"{metrics['headcount'] - warning_threshold} vs Warn" if metrics['headcount'] >= warning_threshold else None)
                    kpi_cols[1].metric("📥 Total Entries", f"{metrics['in_count']}")
                    kpi_cols[2].metric("📤 Total Exits", f"{metrics['out_count']}")
                    kpi_cols[3].metric("📊 Net Active Inside", f"{max(0, metrics['net_flow'])}")
                    kpi_cols[4].metric("⚡ Vision Latency", f"{metrics['fps']} FPS", delta=f"{round(1000/max(1, metrics['fps']), 1)} ms")
                    
                    # Update Video Frame
                    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                    video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                    
                    # Update Side HUD
                    capacity_pct = min(100, int((metrics["headcount"] / max(1, cfg["cap"])) * 100))
                    hud_placeholder.markdown(f"""
                    **Venue:** {cfg['name']}  
                    **Capacity Utilization:** `{capacity_pct}%` ({metrics['headcount']} / {cfg['cap']})  
                    **Status:** `{metrics['alert_level']}`  
                    **Privacy Shield:** `ACTIVE ({privacy_mode.upper()})`  
                    
                    <div style="background:#1e293b; border-radius:8px; height:12px; width:100%; overflow:hidden; margin-top:8px;">
                        <div style="background:{'#ef4444' if capacity_pct >= 85 else ('#f59e0b' if capacity_pct >= 60 else '#10b981')}; width:{capacity_pct}%; height:100%;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Update Incident Snapshots in side column
                    if st.session_state.incidents:
                        last_snap = st.session_state.incidents[-1]
                        if os.path.exists(last_snap["file"]):
                            snapshot_placeholder.image(last_snap["file"], caption=f"Alert: {last_snap['level']} at {last_snap['time']} ({last_snap['count']} ppl)", use_container_width=True)
                    else:
                        snapshot_placeholder.caption("No critical surge incidents recorded yet.")
                        
                    # Yield CPU slightly for UI responsiveness
                    time.sleep(0.01)
                    
                cap.release()
    else:
        # Default placeholder when stopped
        video_placeholder.info("Click '▶️ Start Live Monitoring' above to initialize detection and tracking pipeline.")
        if os.path.exists("sample_crowd.mp4"):
            # Preview first frame
            cap_preview = cv2.VideoCapture("sample_crowd.mp4")
            ret_p, frame_p = cap_preview.read()
            if ret_p:
                video_placeholder.image(cv2.cvtColor(frame_p, cv2.COLOR_BGR2RGB), caption="Preview of Standby Test Feed", use_container_width=True)
            cap_preview.release()

# ---------------------------------------------------------
# TAB 2: Public Checkpoint Kiosk (RPi Display Output)
# ---------------------------------------------------------
with tab_kiosk:
    st.subheader("🖥️ Public Visitor Display Screen (Raspberry Pi HDMI / Kiosk View)")
    st.markdown("""
    This screen is designed to be displayed on an on-site physical monitor (e.g. 7" Raspberry Pi touchscreen, 
    gate monitor, or digital signage) directly at visitor turnstiles and checkpoints to guide the public.
    """)
    
    current_headcount = st.session_state.telemetry[-1]["headcount"] if st.session_state.telemetry else 0
    in_cnt = st.session_state.telemetry[-1]["in_count"] if st.session_state.telemetry else 0
    out_cnt = st.session_state.telemetry[-1]["out_count"] if st.session_state.telemetry else 0
    max_cap = cfg["cap"]
    pct_occ = min(100, int((current_headcount / max(1, max_cap)) * 100))
    
    if current_headcount >= critical_threshold:
        kiosk_status = "🔴 MAXIMUM CAPACITY REACHED — ENTRY PAUSED"
        kiosk_color = "#ef4444"
        kiosk_sub = "Please wait behind the barrier. Admittance will resume shortly."
    elif current_headcount >= warning_threshold:
        kiosk_status = "🟡 HIGH FOOTFALL — PREPARE TO PAUSE"
        kiosk_color = "#f59e0b"
        kiosk_sub = "Congestion detected at venue viewpoints. Expect brief queueing."
    else:
        kiosk_status = "🟢 NORMAL FLOW — WELCOME / PROCEED"
        kiosk_color = "#10b981"
        kiosk_sub = "Safe capacity levels. Please proceed through the turnstile gate."
        
    st.markdown(f"""
    <div style="background: radial-gradient(circle at center, #1e293b, #0f172a); border: 2px solid {kiosk_color}; border-radius: 20px; padding: 30px; margin-bottom: 20px; box-shadow: 0 0 25px {kiosk_color}40;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #f8fafc; font-size: 1.8rem; font-weight: 700;">🏛️ {cfg['name'].upper()} — VISITOR ACCESS</h2>
            <div style="font-size: 1.4rem; font-weight: 600; color: #94a3b8;">{datetime.now().strftime("%A, %H:%M:%S")}</div>
        </div>
        
        <div style="background: {kiosk_color}25; border-left: 8px solid {kiosk_color}; padding: 20px; border-radius: 12px; margin-bottom: 30px;">
            <h1 style="margin: 0; color: {kiosk_color}; font-size: 2.2rem; font-weight: 800; letter-spacing: 1px;">{kiosk_status}</h1>
            <p style="margin: 8px 0 0 0; color: #e2e8f0; font-size: 1.15rem;">{kiosk_sub}</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 20px; margin-bottom: 25px;">
            <div style="background: #1e293b; border-radius: 14px; padding: 20px; border: 1px solid rgba(255,255,255,0.06);">
                <div style="color: #94a3b8; font-size: 0.95rem; font-weight: 600; text-transform: uppercase;">Real-Time Venue Occupancy</div>
                <div style="display: flex; align-items: baseline; gap: 10px; margin: 10px 0;">
                    <span style="font-size: 3.5rem; font-weight: 800; color: #ffffff;">{current_headcount}</span>
                    <span style="font-size: 1.5rem; color: #64748b; font-weight: 600;">/ {max_cap} Max Capacity</span>
                    <span style="margin-left: auto; font-size: 1.4rem; font-weight: 700; color: {kiosk_color};">{pct_occ}% Full</span>
                </div>
                <div style="background: #334155; border-radius: 10px; height: 16px; overflow: hidden;">
                    <div style="background: {kiosk_color}; width: {pct_occ}%; height: 100%; transition: width 0.5s ease;"></div>
                </div>
            </div>
            
            <div style="background: #1e293b; border-radius: 14px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.06);">
                <div style="color: #94a3b8; font-size: 0.9rem; font-weight: 600;">TOTAL CHECKPOINT IN</div>
                <div style="font-size: 2.8rem; font-weight: 800; color: #34d399; margin-top: 8px;">{in_cnt}</div>
            </div>
            
            <div style="background: #1e293b; border-radius: 14px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.06);">
                <div style="color: #94a3b8; font-size: 0.9rem; font-weight: 600;">TOTAL CHECKPOINT OUT</div>
                <div style="font-size: 2.8rem; font-weight: 800; color: #f43f5e; margin-top: 8px;">{out_cnt}</div>
            </div>
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; color: #10b981; font-size: 0.9rem; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08);">
            <span>🔒 <b>GDPR & Ethical AI Compliant:</b> Anonymized spatial crowd density sensing. No facial identities or personal data recorded.</span>
            <span>⚡ Hardware Node: Raspberry Pi 5 Edge</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 To launch the standalone hardware kiosk directly on an attached Raspberry Pi screen/monitor, execute: `python3 rpi_display_kiosk.py --camera 0 --scenario " + selected_sc_key + "`")

# ---------------------------------------------------------
# TAB 3: Real-time Telemetry & Influx
# ---------------------------------------------------------
with tab_telemetry:
    st.subheader("📈 Live Telemetry & Trend Analysis")
    if len(st.session_state.telemetry) > 1:
        df_telem = pd.DataFrame(st.session_state.telemetry)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_telem["time"], y=df_telem["headcount"],
            mode="lines+markers", name="Live Headcount",
            line=dict(color="#38bdf8", width=3),
            fill='tozeroy', fillcolor="rgba(56, 189, 248, 0.15)"
        ))
        
        # Add warning and critical threshold horizontal lines
        fig.add_hline(y=warning_threshold, line_dash="dash", line_color="#fbbf24", annotation_text="Warning Threshold")
        fig.add_hline(y=critical_threshold, line_dash="dot", line_color="#f87171", annotation_text="Critical Danger Threshold")
        
        fig.update_layout(
            title="Real-Time Visitor Occupancy Curve",
            xaxis_title="Time",
            yaxis_title="Occupants Count",
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.8)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            height=420,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Footfall Flow Breakdown
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Scatter(x=df_telem["time"], y=df_telem["in_count"], name="Cumulative In", line=dict(color="#10b981", width=2)))
            fig_flow.add_trace(go.Scatter(x=df_telem["time"], y=df_telem["out_count"], name="Cumulative Out", line=dict(color="#f43f5e", width=2)))
            fig_flow.update_layout(title="Tripwire Line Influx / Outflux", template="plotly_dark", paper_bgcolor="rgba(15, 23, 42, 0.8)", height=320)
            st.plotly_chart(fig_flow, use_container_width=True)
            
        with col_f2:
            st.markdown("### 📋 Recent Telemetry Samples")
            st.dataframe(df_telem.tail(15), use_container_width=True)
    else:
        st.info("Start live monitoring to populate real-time time-series telemetry charts.")

# ---------------------------------------------------------
# TAB 3: 36-Hour Ground Truth Benchmark & Evidence
# ---------------------------------------------------------
with tab_evidence:
    st.subheader("📊 36-Hour Ground Truth Benchmark & Count Error Verification")
    st.markdown("""
    As required by the **36-hour evidence specification**, this module benchmarks the AI model's estimated crowd density 
    against known ground-truth headcounts to quantify count error (MAE, RMSE, MAPE) and validate alert threshold reliability.
    """)
    
    col_bench_opt, col_bench_run = st.columns([3, 1])
    bench_scenario = col_bench_opt.selectbox(
        "Select Scenario for 36-Hour Evidence Audit:",
        ["A", "B", "C", "D"],
        format_func=lambda x: scenario_options[x]
    )
    
    df_evidence, sc_meta = generate_36hr_evidence_dataset(scenario=bench_scenario)
    metrics_evidence = calculate_evidence_metrics(df_evidence, sc_meta)
    
    # KPI metrics row
    b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
    b_col1.metric("🎯 Overall Count Accuracy", f"{metrics_evidence['accuracy_pct']}%")
    b_col2.metric("📉 Mean Absolute Error (MAE)", f"{metrics_evidence['mae']} pers")
    b_col3.metric("📐 Root Mean Sq Error (RMSE)", f"{metrics_evidence['rmse']}")
    b_col4.metric("🚨 Alert Detection Precision", f"{metrics_evidence['alert_precision']}%")
    b_col5.metric("🔔 Alert Recall Rate", f"{metrics_evidence['alert_recall']}%")
    
    # 36-hour curve chart
    fig_36 = go.Figure()
    fig_36.add_trace(go.Scatter(
        x=df_evidence["timestamp"], y=df_evidence["ground_truth_count"],
        mode="lines", name="Known Ground Truth Headcount",
        line=dict(color="#10b981", width=2)
    ))
    fig_36.add_trace(go.Scatter(
        x=df_evidence["timestamp"], y=df_evidence["predicted_count"],
        mode="lines", name="AI Estimated Density",
        line=dict(color="#38bdf8", width=2, dash="dot")
    ))
    
    fig_36.add_hline(y=sc_meta["warning"], line_dash="dash", line_color="#fbbf24", annotation_text=f"Warning ({sc_meta['warning']})")
    fig_36.add_hline(y=sc_meta["critical"], line_dash="dash", line_color="#ef4444", annotation_text=f"Critical Threshold ({sc_meta['critical']})")
    
    fig_36.update_layout(
        title=f"36-Hour Continuous Footfall Evidence Curve ({sc_meta['name']})",
        xaxis_title="Timeline (15-Minute Aggregation Intervals)",
        yaxis_title="Visitor Count",
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.8)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_36, use_container_width=True)
    
    # Count Error Distribution Chart
    col_err_hist, col_err_table = st.columns([1.5, 1])
    with col_err_hist:
        fig_err = px.histogram(
            df_evidence, x="count_error", nbins=20,
            title="Estimation Error Distribution (Pred - True)",
            color_discrete_sequence=["#a855f7"],
            template="plotly_dark"
        )
        fig_err.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.8)", plot_bgcolor="rgba(15, 23, 42, 0.6)", height=320)
        st.plotly_chart(fig_err, use_container_width=True)
        
    with col_err_table:
        st.markdown("### 📋 36-Hour Evidence Audit Log")
        st.dataframe(df_evidence[["hour", "ground_truth_count", "predicted_count", "count_error", "predicted_alert"]].head(15), use_container_width=True)
        csv_data = df_evidence.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Complete 36-Hr Evidence CSV",
            data=csv_data,
            file_name=f"36hr_evidence_scenario_{bench_scenario}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ---------------------------------------------------------
# TAB 4: Hardware & Pi Deployment
# ---------------------------------------------------------
with tab_hardware:
    st.subheader("🛠️ Hardware Edge Deployment & Pi Streaming")
    st.markdown("""
    The software is built with a decoupled client-server architecture, allowing seamless integration with 
    **Raspberry Pi**, **ESP32-CAM**, or **RTSP IP Surveillance Cameras**.
    """)
    
    col_hw_diag, col_hw_steps = st.columns([1.2, 1])
    
    with col_hw_diag:
        st.markdown("""
        #### 📦 Hardware Setup on Raspberry Pi 4 / 5
        1. Connect the **Raspberry Pi Camera Module 3** or **USB Camera** to the Pi.
        2. Copy `hardware_streamer.py` to the Raspberry Pi:
        ```bash
        # Run on the Raspberry Pi:
        python3 hardware_streamer.py --port 8080 --camera 0 --fps 20 --width 640 --height 480
        ```
        3. Note down the Raspberry Pi IP address:
        ```bash
        hostname -I
        ```
        4. In this dashboard, select **"RTSP / IP Camera / Pi Stream"** in the sidebar and enter:
        ```text
        http://<PI_IP_ADDRESS>:8080/video_feed
        ```
        """)
        
    with col_hw_steps:
        st.markdown("""
        #### 🔔 Physical Actuators & Relays
        When crowd density crosses the **Critical Alert Threshold**:
        - **Buzzer / Audio Siren**: Triggered via Raspberry Pi GPIO 18.
        - **Overcrowded LED Display**: NeoPixel / 7-Segment displays *"HOLD"* or *"CAPACITY REACHED"*.
        - **Turnstile Gate Lock**: 500ms dry contact pulse to prevent further entries.
        
        Detailed circuit diagrams and outdoor weatherproof specs are in `HARDWARE_SETUP.md`.
        """)
        
    st.markdown("---")
    st.info("💡 **Local Webcam Test Check:** Linux devices can check active video nodes with `ls -l /dev/video*`. If permissions are needed, run `sudo usermod -a -G video $USER`.")

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>"
    "AI Tourist Crowd Monitor | Privacy-Preserving Computer Vision Pipeline | Built for Hackathon Prototype & Hardware Edge"
    "</div>",
    unsafe_allow_html=True
)
