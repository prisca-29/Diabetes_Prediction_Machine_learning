"""
=============================================================================
  Diabetes Risk Early Warning System – Flask API Backend
=============================================================================
  Endpoints:
    POST /predict          → Returns risk score, category, probabilities
    POST /simulate         → Returns 4-stage lifestyle improvement scores
    GET  /feature-importance → Returns top-10 feature importances
    POST /wearable         → Accepts wearable data, maps to model features
    POST /train            → (One-time) trains and saves model to disk

  Run:
    python app.py
  Then visit:
    http://127.0.0.1:5000
=============================================================================
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from utils import (
    compute_risk_score,
    categorise_risk,
    apply_improvements,
    map_wearable_to_features,
    FEATURE_NAMES,
)

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)  # Allow requests from the frontend (different port / file://)

# Paths
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
DATA_PATH   = os.path.join(BASE_DIR, "..", "data", "brfss.csv")

# ── Load model once at startup (not on every request) ────────────────────
if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✔  Model and scaler loaded from disk.")
else:
    model  = None
    scaler = None
    print("⚠  No saved model found. POST /train first.")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: predict risk from a feature dict
# ─────────────────────────────────────────────────────────────────────────────
def predict_from_dict(features_dict):
    """
    Takes a dict of {feature_name: value}, scales it, runs the model,
    and returns (probabilities, risk_score, risk_category, predicted_class).
    """
    row_df     = pd.DataFrame([features_dict])[FEATURE_NAMES]
    row_scaled = scaler.transform(row_df)
    proba      = model.predict_proba(row_scaled)[0]         # shape (3,)
    pred_class = int(model.predict(row_scaled)[0])
    risk_score = compute_risk_score(proba)
    risk_cat   = categorise_risk(risk_score)
    return proba, risk_score, risk_cat, pred_class


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 1 – /train  (run once to create model.pkl and scaler.pkl)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/train", methods=["POST"])
def train():
    """
    Trains the Random Forest on the BRFSS CSV and saves model + scaler.
    Call this once with:
        curl -X POST http://127.0.0.1:5000/train
    """
    global model, scaler

    if not os.path.exists(DATA_PATH):
        return jsonify({"error": f"Dataset not found at {DATA_PATH}"}), 404

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(DATA_PATH)
    df.fillna(df.median(numeric_only=True), inplace=True)

    X = df.drop(columns=["Diabetes_012"])
    y = df["Diabetes_012"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)

    joblib.dump(model,  MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    from sklearn.metrics import accuracy_score
    y_pred = model.predict(scaler.transform(X_test))
    acc    = accuracy_score(y_test, y_pred)

    print(f"✔  Training complete. Accuracy: {acc*100:.2f}%")
    return jsonify({"message": "Model trained and saved.", "accuracy": round(acc * 100, 2)})


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 2 – /predict
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    """
    Accepts JSON with user health features.
    Returns: predicted_class, probabilities, risk_score, risk_category.

    Example request body:
    {
      "HighBP": 1, "HighChol": 1, "CholCheck": 1, "BMI": 32.0,
      "Smoker": 0, "Stroke": 0, "HeartDiseaseorAttack": 0,
      "PhysActivity": 0, "Fruits": 1, "Veggies": 1,
      "HvyAlcoholConsump": 0, "AnyHealthcare": 1, "NoDocbcCost": 0,
      "GenHlth": 3, "MentHlth": 5, "PhysHlth": 10, "DiffWalk": 0,
      "Sex": 1, "Age": 9, "Education": 5, "Income": 5
    }
    """
    if model is None:
        return jsonify({"error": "Model not loaded. POST /train first."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body received."}), 400

    # Fill any missing features with safe defaults (0 or median-like values)
    features = {f: float(data.get(f, 0)) for f in FEATURE_NAMES}

    proba, risk_score, risk_cat, pred_class = predict_from_dict(features)

    class_labels = {0: "No Diabetes", 1: "Pre-Diabetes", 2: "Diabetes"}

    return jsonify({
        "predicted_class":    pred_class,
        "predicted_label":    class_labels[pred_class],
        "probabilities": {
            "no_diabetes":   round(float(proba[0]) * 100, 1),
            "pre_diabetes":  round(float(proba[1]) * 100, 1),
            "diabetes":      round(float(proba[2]) * 100, 1),
        },
        "risk_score":    risk_score,
        "risk_category": risk_cat,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 3 – /simulate
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/simulate", methods=["POST"])
def simulate():
    """
    Accepts same JSON as /predict.
    Returns risk scores for all 4 lifestyle improvement stages.
    """
    if model is None:
        return jsonify({"error": "Model not loaded. POST /train first."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body received."}), 400

    features = {f: float(data.get(f, 0)) for f in FEATURE_NAMES}

    stages = []
    stage_labels = [
        "Current Lifestyle",
        "Quit smoking · Eat better",
        "Exercise · Lose ~3 BMI pts",
        "Major weight loss · BP control",
    ]

    for stage in range(4):
        improved = apply_improvements(features, stage)
        row_df   = pd.DataFrame([improved])[FEATURE_NAMES]
        row_sc   = scaler.transform(row_df)
        proba    = model.predict_proba(row_sc)[0]
        score    = compute_risk_score(proba)
        cat      = categorise_risk(score)
        stages.append({
            "stage":    stage,
            "label":    stage_labels[stage],
            "score":    score,
            "category": cat,
        })

    return jsonify({"stages": stages})


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 4 – /feature-importance
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/feature-importance", methods=["GET"])
def feature_importance():
    """Returns top-10 feature importances from the trained Random Forest."""
    if model is None:
        return jsonify({"error": "Model not loaded. POST /train first."}), 503

    importances = model.feature_importances_
    feat_list   = sorted(
        zip(FEATURE_NAMES, importances),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    return jsonify({
        "features": [
            {"name": name, "importance": round(float(imp), 4)}
            for name, imp in feat_list
        ]
    })


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 5 – /wearable  (Hybrid: wearable + manual input)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/wearable", methods=["POST"])
def wearable():
    """
    Accepts wearable sensor data and optional manual overrides.
    Maps wearable metrics → model features, then predicts risk.

    Expected JSON:
    {
      "wearable": {
        "steps_per_day":  8000,
        "avg_heart_rate": 72,
        "sleep_hours":    7,
        "calories_burned": 2200
      },
      "manual": {   <- optional; values here override wearable-derived values
        "BMI": 27.5, "Age": 8, "HighBP": 0, ...
      }
    }
    """
    if model is None:
        return jsonify({"error": "Model not loaded. POST /train first."}), 503

    data     = request.get_json() or {}
    wearable_data = data.get("wearable", {})
    manual_data   = data.get("manual", {})

    # Map wearable readings to model features
    wearable_features = map_wearable_to_features(wearable_data)

    # Merge: wearable first, then manual overrides
    merged = {**wearable_features, **{f: float(v) for f, v in manual_data.items()}}
    features = {f: float(merged.get(f, 0)) for f in FEATURE_NAMES}

    proba, risk_score, risk_cat, pred_class = predict_from_dict(features)

    class_labels = {0: "No Diabetes", 1: "Pre-Diabetes", 2: "Diabetes"}

    return jsonify({
        "source":          "hybrid (wearable + manual)",
        "derived_features": wearable_features,
        "predicted_class":  pred_class,
        "predicted_label":  class_labels[pred_class],
        "probabilities": {
            "no_diabetes":  round(float(proba[0]) * 100, 1),
            "pre_diabetes": round(float(proba[1]) * 100, 1),
            "diabetes":     round(float(proba[2]) * 100, 1),
        },
        "risk_score":    risk_score,
        "risk_category": risk_cat,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Serve frontend index.html at root
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Diabetes Risk API  –  http://127.0.0.1:5000")
    print("  POST /train           → Train and save model")
    print("  POST /predict         → Predict risk from form data")
    print("  POST /simulate        → Lifestyle improvement stages")
    print("  GET  /feature-importance → Top features")
    print("  POST /wearable        → Hybrid wearable+manual input")
    print("=" * 60)
    app.run(debug=True, port=5000)
