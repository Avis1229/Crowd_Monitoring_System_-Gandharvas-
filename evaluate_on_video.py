import argparse
import sys

import cv2
import pandas as pd

from crowd_engine import CrowdEngine
from benchmark_data import calculate_evidence_metrics

MIN_RELIABLE_SAMPLES = 30


def classify_alert(count: int, config: dict) -> str:
    """Count ke hisaab se alert level return karta hai."""
    if count >= config["critical"]:
        return "CRITICAL"
    if count >= config["warning"]:
        return "WARNING"
    return "NORMAL"


def load_labels(labels_csv):
    df = pd.read_csv(labels_csv)
    missing = {"frame", "true_count"} - set(df.columns)
    if missing:
        raise ValueError(f"Labels CSV mein columns missing hain: {sorted(missing)}")
    df = df.dropna(subset=["frame", "true_count"]).drop_duplicates("frame")
    df["frame"] = df["frame"].astype(int)
    df["true_count"] = df["true_count"].astype(int)
    if (df["frame"] < 0).any() or (df["true_count"] < 0).any():
        raise ValueError("frame aur true_count negative nahi ho sakte")
    if df.empty:
        raise ValueError("Labels CSV khali hai")
    return dict(zip(df["frame"], df["true_count"]))


def evaluate(video_path, labels_csv, engine=None, warning=25, critical=40, max_frames=None):
    """
    Video chalata hai (HAR frame engine ko deta hai, kyunki tracking ko continuity chahiye) aur sirf
    labelled frames par predicted headcount record karta hai.

    Returns: (results_df, metrics_dict)
    """
    labels = load_labels(labels_csv)
    last_needed = max(labels) if max_frames is None else min(max(labels), max_frames)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video khul nahi saki: {video_path}")

    engine = engine or CrowdEngine()
    if engine.model is None:
        cap.release()
        raise RuntimeError("Detection model load nahi hua (ultralytics install hai? weights mile?)")
    engine.reset_counters()

    cfg = {"warning": warning, "critical": critical}
    rows, idx = [], 0
    try:
        while idx <= last_needed:
            ok, frame = cap.read()
            if not ok:
                break
            _, m = engine.process_frame(
                frame,
                privacy_mode="none",
                line_crossing_enabled=False,
                cctv_style=False,           # sirf insaan, headcount ke liye kaafi
                density_threshold_warning=warning,
                density_threshold_critical=critical,
            )
            if idx in labels:
                true_c, pred_c = int(labels[idx]), int(m["headcount"])
                true_a, pred_a = classify_alert(true_c, cfg), classify_alert(pred_c, cfg)
                rows.append({
                    "frame": idx,
                    "ground_truth_count": true_c,
                    "predicted_count": pred_c,
                    "count_error": pred_c - true_c,
                    "absolute_error": abs(pred_c - true_c),
                    "true_alert": true_a,
                    "predicted_alert": pred_a,
                    "alert_match": true_a == pred_a,
                })
            idx += 1
    finally:
        cap.release()

    if not rows:
        raise RuntimeError("Koi labelled frame video mein nahi mila (frame numbers check karein)")

    df = pd.DataFrame(rows)
    metrics = calculate_evidence_metrics(df, cfg)
    metrics["mean_error_bias"] = round(float(df["count_error"].mean()), 2)  # negative = undercount
    metrics["labelled_frames_used"] = len(df)
    skipped = len(labels) - len(df)
    metrics["labels_not_reached"] = skipped
    return df, metrics


def main(argv=None):
    ap = argparse.ArgumentParser(description="CrowdEngine ki real accuracy video + manual labels se naapo")
    ap.add_argument("--video", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--warning", type=int, default=25)
    ap.add_argument("--critical", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=320, help="480/640 try karein agar log chhote dikhte hain")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=None, help="Per-frame results CSV save karne ke liye")
    args = ap.parse_args(argv)

    engine = CrowdEngine(model_name=args.model)
    df, metrics = evaluate(args.video, args.labels, engine, args.warning, args.critical)

    print("\nREAL evaluation (manual labels vs model):")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    if len(df) < MIN_RELIABLE_SAMPLES:
        print(f"\n[!] Sirf {len(df)} labelled frames hain; {MIN_RELIABLE_SAMPLES}+ ho to numbers zyada bharosemand honge.")
    if metrics["mean_error_bias"] < -1:
        print("[!] Model systematically kam gin raha hai (undercount). imgsz badhane ya conf_thresh ghatane ka try karein.")
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"\nPer-frame results saved: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
