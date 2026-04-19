"""
=============================================================================
  utils.py  –  Shared helper functions for the Diabetes Risk API
=============================================================================
  Imported by app.py.  No Flask code here – pure logic.
=============================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# Feature column order  (must match the training CSV exactly)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    "HighBP", "HighChol", "CholCheck", "BMI", "Smoker",
    "Stroke", "HeartDiseaseorAttack", "PhysActivity", "Fruits", "Veggies",
    "HvyAlcoholConsump", "AnyHealthcare", "NoDocbcCost", "GenHlth",
    "MentHlth", "PhysHlth", "DiffWalk", "Sex", "Age", "Education", "Income",
]


# ─────────────────────────────────────────────────────────────────────────────
# Risk score helpers
# ─────────────────────────────────────────────────────────────────────────────
def compute_risk_score(proba_row):
    """
    Converts 3-class probabilities into a single continuous score [0, 100].

    Formula:
        Risk = P(Pre-Diabetes) × 50  +  P(Diabetes) × 100

    Interpretation:
        ~  0  → Very likely healthy
        ~ 50  → Likely pre-diabetic
        ~100  → Likely diabetic
    """
    p_pre  = proba_row[1]   # probability of pre-diabetes
    p_diab = proba_row[2]   # probability of diabetes
    return round(p_pre * 50 + p_diab * 100, 2)


def categorise_risk(score):
    """
    Maps a numeric risk score to a human-readable category.
    Thresholds:
        Low    : score < 30
        Medium : 30 ≤ score < 60
        High   : score ≥ 60
    """
    if score < 30:
        return "Low Risk"
    elif score < 60:
        return "Medium Risk"
    else:
        return "High Risk"


# ─────────────────────────────────────────────────────────────────────────────
# Lifestyle improvement simulation
# ─────────────────────────────────────────────────────────────────────────────
def apply_improvements(features_dict, stage):
    """
    Simulates progressive lifestyle improvements over 3 stages.

    Stage 1 – Easy wins : Quit smoking, stop heavy drinking, eat fruit/veg
    Stage 2 – Moderate  : Start exercising, improve general health, lose weight
    Stage 3 – Significant: More weight loss, manage blood pressure

    Parameters
    ----------
    features_dict : dict  {feature_name: value}
    stage         : int   0 = baseline, 1–3 = progressive improvements

    Returns
    -------
    dict  (copy of features_dict with improved values)
    """
    f = features_dict.copy()

    if stage >= 1:
        f["Smoker"]            = 0
        f["HvyAlcoholConsump"] = 0
        f["Fruits"]            = 1
        f["Veggies"]           = 1

    if stage >= 2:
        f["PhysActivity"] = 1
        f["GenHlth"]      = max(1, f.get("GenHlth", 3) - 1)
        f["BMI"]          = max(18.5, f.get("BMI", 30) - 3)

    if stage >= 3:
        f["BMI"]    = max(18.5, f.get("BMI", 30) - 5)
        f["GenHlth"]= max(1, f.get("GenHlth", 3) - 1)
        f["HighBP"] = max(0, f.get("HighBP", 0) - 1)

    return f


# ─────────────────────────────────────────────────────────────────────────────
# Wearable sensor data mapping
# ─────────────────────────────────────────────────────────────────────────────
def map_wearable_to_features(wearable_data):
    """
    Maps objective wearable sensor readings to BRFSS model features.

    Wearable keys (all optional, fall back to neutral defaults):
        steps_per_day   : int   daily step count
        avg_heart_rate  : int   resting heart rate (bpm)
        sleep_hours     : float hours of sleep per night
        calories_burned : int   active calories burned per day

    Mapping logic:
        PhysActivity:  steps ≥ 7500  → 1 (active), else 0
        GenHlth:       derived from heart_rate + sleep quality
        PhysHlth:      inverse of sleep quality (poor sleep → more bad days)
        MentHlth:      poor sleep → stress indicator

    Returns
    -------
    dict of partial BRFSS features derived from wearable data.
    Non-wearable features are NOT included (caller must fill them from manual input).
    """
    derived = {}

    steps         = wearable_data.get("steps_per_day",   0)
    heart_rate    = wearable_data.get("avg_heart_rate",  70)
    sleep_hours   = wearable_data.get("sleep_hours",     7)
    calories      = wearable_data.get("calories_burned", 0)

    # ── PhysActivity: ≥7500 steps/day = active ──────────────────────────
    derived["PhysActivity"] = 1 if steps >= 7500 else 0

    # ── GenHlth (1=Excellent … 5=Poor) ──────────────────────────────────
    # Normal resting HR: 60–80 bpm; tachycardia (>100) is a health concern
    # Normal sleep: 7–9 hours
    gen_health = 3  # default: "Good"
    if heart_rate <= 65 and sleep_hours >= 7.5 and steps >= 10000:
        gen_health = 1  # Excellent
    elif heart_rate <= 75 and sleep_hours >= 7:
        gen_health = 2  # Very Good
    elif heart_rate > 90 or sleep_hours < 5:
        gen_health = 4  # Fair
    elif heart_rate > 100 or sleep_hours < 4:
        gen_health = 5  # Poor
    derived["GenHlth"] = gen_health

    # ── PhysHlth: days physical health was "not good" ───────────────────
    # Under-sleeping and low activity suggest more unhealthy days
    if sleep_hours >= 7 and steps >= 7500:
        derived["PhysHlth"] = 2
    elif sleep_hours >= 6:
        derived["PhysHlth"] = 8
    else:
        derived["PhysHlth"] = 18

    # ── MentHlth: days mental health was "not good" ─────────────────────
    if sleep_hours >= 7:
        derived["MentHlth"] = 2
    elif sleep_hours >= 6:
        derived["MentHlth"] = 8
    else:
        derived["MentHlth"] = 15

    # ── HvyAlcoholConsump heuristic: calories burnt vs consumed ──────────
    # If user burns lots of calories, less likely to be a heavy drinker
    # (Very rough – just a heuristic default)
    derived["HvyAlcoholConsump"] = 0 if calories >= 400 else 0  # default 0

    return derived


# ─────────────────────────────────────────────────────────────────────────────
# Generate sample wearable CSV  (run once to create data/wearable_sample.csv)
# ─────────────────────────────────────────────────────────────────────────────
def generate_wearable_sample(output_path="data/wearable_sample.csv", n=500):
    """
    Creates a synthetic Fitbit-style dataset for demonstration purposes.
    Each row = one person's average daily wearable readings.
    """
    import os
    import pandas as pd
    import numpy as np

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rng = np.random.default_rng(42)

    data = {
        "user_id":        range(1, n + 1),
        "steps_per_day":  rng.integers(1000, 15000, n),
        "avg_heart_rate": rng.integers(55, 105, n),
        "sleep_hours":    rng.uniform(4, 9.5, n).round(1),
        "calories_burned":rng.integers(150, 800, n),
        "bmi_approx":     rng.uniform(18.5, 45, n).round(1),
    }

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"✔  Wearable sample saved → {output_path}  ({n} rows)")
    return df


if __name__ == "__main__":
    # Run directly to generate the sample CSV
    generate_wearable_sample("../data/wearable_sample.csv")
