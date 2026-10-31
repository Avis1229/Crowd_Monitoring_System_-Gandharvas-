import copy
import warnings
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd

# NOTE: Yeh poora dataset SIMULATED (synthetic) hai. Ground truth aur model
# predictions dono random process se bante hain, isliye yeh metrics asli YOLOv8
# performance ka saboot nahi hain. Asli benchmark ke liye real labelled data use karein.

INTERVAL_MINUTES = 15
TOTAL_INTERVALS = 144  # 144 x 15 min = 36 hours
DEFAULT_SCENARIO = "C"

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "Campus Dining Footfall",
        "capacity": 60, "warning": 40, "critical": 50,
        "peak_hours": [12, 13, 19, 20],
        "base_count": 8, "peak_mult": 4.5,
    },
    "B": {
        "name": "Heritage Visitor Occupancy",
        "capacity": 50, "warning": 30, "critical": 42,
        "peak_hours": [10, 11, 14, 15],
        "base_count": 6, "peak_mult": 5.2,
    },
    "C": {
        "name": "Tourist Gateway Crowd Alerts",
        "capacity": 75, "warning": 45, "critical": 60,
        "peak_hours": [11, 12, 15, 16, 17],
        "base_count": 12, "peak_mult": 4.0,
    },
    "D": {
        "name": "Mountain Attraction Congestion",
        "capacity": 35, "warning": 22, "critical": 30,
        "peak_hours": [6, 7, 17, 18],  # Sunrise & Sunset
        "base_count": 4, "peak_mult": 6.0,
    },
}


def classify_alert(count: int, config: Dict[str, Any]) -> str:
    """Count ke hisaab se alert level return karta hai."""
    if count >= config["critical"]:
        return "CRITICAL"
    if count >= config["warning"]:
        return "WARNING"
    return "NORMAL"


def generate_36hr_evidence_dataset(
    scenario: str = DEFAULT_SCENARIO,
    base_date: Optional[datetime] = None,
    seed: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    36 ghante ka synthetic time-series dataset banata hai (ground truth headcount +
    simulated model predictions) taaki count error aur alert accuracy benchmark ho sake.

    Unknown scenario par default scenario "C" use hota hai (pehle jaisa behavior).
    """
    if base_date is None:
        # Aaj raat 12:00 baje se 36 ghante peeche: din ke ghante har run mein same rehte hain,
        # isliye results reproducible hain (pehle datetime.now() se start hone ki wajah se
        # peak hours har run mein shift ho jate the aur metrics badal jate the).
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        base_date = today_midnight - timedelta(hours=36)

    if scenario not in SCENARIOS:
        warnings.warn(
            f"Unknown scenario '{scenario}', default '{DEFAULT_SCENARIO}' use ho raha hai.",
            stacklevel=2,
        )
    # deepcopy: caller returned config badle to global SCENARIOS kharab na ho
    sc = copy.deepcopy(SCENARIOS.get(scenario, SCENARIOS[DEFAULT_SCENARIO]))
    timestamps = [
        base_date + timedelta(minutes=INTERVAL_MINUTES * i)
        for i in range(TOTAL_INTERVALS)
    ]

    rng = np.random.RandomState(seed)  # np.random.seed jaisa hi stream, par global state nahi chhedta
    records = []

    for dt in timestamps:
        hour = dt.hour

        # Diurnal pattern
        if hour in sc["peak_hours"]:
            scale = sc["peak_mult"] * (1.0 + rng.uniform(-0.15, 0.25))
        elif 8 <= hour <= 21:
            scale = 1.8 * (1.0 + rng.uniform(-0.2, 0.2))
        else:
            scale = 0.3 * (1.0 + rng.uniform(-0.1, 0.1))

        true_count = int(
            np.clip(
                sc["base_count"] * scale + rng.normal(0, 2),
                0,
                sc["capacity"] + 15,
            )
        )

        # Simulated detector error: low density mein chhota error, high density mein occlusion se undercount
        if true_count < 10:
            error = int(rng.choice([-1, 0, 0, 1]))
        elif true_count < 30:
            error = int(rng.normal(-0.5, 1.5))
        else:
            error = int(-0.06 * true_count + rng.normal(0, 2))

        pred_count = max(0, true_count + error)

        true_alert = classify_alert(true_count, sc)
        pred_alert = classify_alert(pred_count, sc)

        records.append({
            "timestamp": dt,
            "hour": dt.strftime("%Y-%m-%d %H:%M"),
            "ground_truth_count": true_count,
            "predicted_count": pred_count,
            "count_error": pred_count - true_count,
            "absolute_error": abs(pred_count - true_count),
            "true_alert": true_alert,
            "predicted_alert": pred_alert,
            "alert_match": true_alert == pred_alert,
        })

    return pd.DataFrame(records), sc


def calculate_evidence_metrics(df: pd.DataFrame, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
    """Count error aur alert performance metrics nikalta hai."""
    if df.empty:
        raise ValueError("DataFrame khali hai, metrics nahi nikal sakte.")

    y_true = df["ground_truth_count"].to_numpy()
    y_pred = df["predicted_count"].to_numpy()

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # MAPE mein zero division se bachne ke liye sirf non-zero ground truth lete hain
    non_zero = y_true > 0
    if np.any(non_zero):
        mape = float(
            np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100
        )
    else:
        mape = 0.0
    accuracy_percentage = max(0.0, 100.0 - mape)

    # Alert confusion counts (WARNING threshold ya usse upar = alert)
    warning = scenario_config["warning"]
    true_alert = y_true >= warning
    pred_alert = y_pred >= warning

    total_alerts = int(np.sum(true_alert))
    detected_alerts = int(np.sum(pred_alert & true_alert))
    false_alerts = int(np.sum(pred_alert & ~true_alert))
    missed_alerts = int(np.sum(~pred_alert & true_alert))

    def safe_div(num: float, den: float, default: float = 1.0) -> float:
        return float(num / den) if den > 0 else default

    alert_precision = safe_div(detected_alerts, detected_alerts + false_alerts)
    alert_recall = safe_div(detected_alerts, detected_alerts + missed_alerts)
    alert_f1 = safe_div(
        2 * alert_precision * alert_recall, alert_precision + alert_recall
    )

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2),
        "accuracy_pct": round(accuracy_percentage, 1),
        "total_intervals": len(df),
        "total_true_alert_intervals": total_alerts,
        "detected_alerts": detected_alerts,
        "false_alerts": false_alerts,
        "missed_alerts": missed_alerts,
        "alert_precision": round(alert_precision * 100, 1),
        "alert_recall": round(alert_recall * 100, 1),
        "alert_f1": round(alert_f1 * 100, 1),
        # Naya (extra) key: NORMAL/WARNING/CRITICAL level exact match %
        "alert_level_accuracy": round(float(df["alert_match"].mean()) * 100, 1),
    }


if __name__ == "__main__":
    df, sc = generate_36hr_evidence_dataset("C")
    metrics = calculate_evidence_metrics(df, sc)
    print(f"Scenario C ({sc['name']}) 36-hr SIMULATED Evidence Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")