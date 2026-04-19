# DiabetesGuard — Full-Stack Diabetes Risk Early Warning System
### B.Tech AIML Final Year Project · CDC BRFSS 2015 · Random Forest

---

## 📁 Project Structure

```
diabetes_risk_project/
│
├── backend/
│   ├── app.py          ← Flask API (5 endpoints)
│   ├── utils.py        ← Risk score, simulation, wearable mapping logic
│   ├── model.pkl       ← Saved Random Forest (auto-created by /train)
│   └── scaler.pkl      ← Saved StandardScaler (auto-created by /train)
│
├── frontend/
│   ├── index.html      ← Full single-page app
│   ├── style.css       ← Medical-themed UI
│   └── script.js       ← API calls, chart rendering
│
├── data/
│   ├── brfss.csv           ← BRFSS 2015 dataset (you must add this)
│   └── wearable_sample.csv ← Auto-generated synthetic wearable data
│
├── generate_wearable_data.py  ← Run once to create wearable CSV
├── requirements.txt
└── README.md
```

---

## ⚙️ VS Code Setup — Step by Step

### Step 1: Install Python dependencies

```bash
# From the project root folder
pip install -r requirements.txt
```

This installs: flask, flask-cors, pandas, numpy, scikit-learn, joblib, matplotlib, seaborn

---

### Step 2: Add the dataset

Download the BRFSS 2015 dataset from Kaggle:
https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset

Look for the file:
```
diabetes_012_health_indicators_BRFSS2015.csv
```

Rename it to `brfss.csv` and place it in the `data/` folder:
```
data/brfss.csv
```

---

### Step 3: Train the model (one-time only)

First start the Flask server:
```bash
cd backend
python app.py
```

Then in a **new terminal**, run:
```bash
curl -X POST http://127.0.0.1:5000/train
```

Or open your browser and use a tool like Postman to POST to:
```
http://127.0.0.1:5000/train
```

This creates:
- `backend/model.pkl`   ← Trained Random Forest
- `backend/scaler.pkl`  ← Fitted StandardScaler

You only need to do this ONCE. After that, the model loads automatically on every restart.

---

### Step 4: Open the frontend

Option A — Open directly in browser (simplest):
```
Right-click frontend/index.html → Open with → Chrome / Firefox
```

Option B — Serve with VS Code Live Server extension:
```
Install "Live Server" extension → Right-click index.html → Open with Live Server
```

Option C — Serve with Python:
```bash
cd frontend
python -m http.server 8080
# Then open http://localhost:8080
```

---

### Step 5: Use the app

1. Open the frontend in your browser
2. Fill in the Health Assessment form
3. Optionally toggle **Wearable Integration** and enter smartwatch data
4. Click **Calculate My Risk Score**
5. See your:
   - Risk score (0–100) with animated ring
   - Model probabilities
   - Color-coded risk category
   - Personalised lifestyle improvement plan
   - Top AI risk factors

---

## 🌐 API Endpoints

| Method | URL                  | Description                         |
|--------|----------------------|-------------------------------------|
| POST   | `/train`             | Train and save model (run once)     |
| POST   | `/predict`           | Get risk score from form data       |
| POST   | `/simulate`          | Lifestyle improvement simulation    |
| GET    | `/feature-importance`| Top 10 feature importances          |
| POST   | `/wearable`          | Hybrid: wearable + manual input     |

---

## 📊 Example API Usage

### /predict
```json
POST http://127.0.0.1:5000/predict
{
  "HighBP": 1, "HighChol": 1, "CholCheck": 1, "BMI": 32.0,
  "Smoker": 0, "Stroke": 0, "HeartDiseaseorAttack": 0,
  "PhysActivity": 0, "Fruits": 1, "Veggies": 1,
  "HvyAlcoholConsump": 0, "AnyHealthcare": 1, "NoDocbcCost": 0,
  "GenHlth": 3, "MentHlth": 5, "PhysHlth": 10, "DiffWalk": 0,
  "Sex": 1, "Age": 9, "Education": 5, "Income": 5
}
```

Response:
```json
{
  "predicted_class": 2,
  "predicted_label": "Diabetes",
  "probabilities": {
    "no_diabetes": 22.3,
    "pre_diabetes": 18.5,
    "diabetes": 59.2
  },
  "risk_score": 68.45,
  "risk_category": "High Risk"
}
```

### /wearable (Hybrid Mode)
```json
POST http://127.0.0.1:5000/wearable
{
  "wearable": {
    "steps_per_day": 4000,
    "avg_heart_rate": 88,
    "sleep_hours": 5.5,
    "calories_burned": 250
  },
  "manual": {
    "BMI": 31.0, "Age": 9, "HighBP": 1, "HighChol": 1,
    "CholCheck": 1, "Smoker": 1, "Stroke": 0,
    "HeartDiseaseorAttack": 0, "Fruits": 0, "Veggies": 0,
    "HvyAlcoholConsump": 0, "AnyHealthcare": 1, "NoDocbcCost": 0,
    "DiffWalk": 0, "Sex": 1, "Education": 5, "Income": 4
  }
}
```

---

## 🔬 Model Details

| Property        | Value                                 |
|-----------------|---------------------------------------|
| Algorithm       | Random Forest Classifier              |
| Trees           | 100                                   |
| Max Depth       | 10                                    |
| Classes         | 0 (No Diabetes), 1 (Pre), 2 (Full)   |
| Risk Formula    | P(Pre)×50 + P(Diabetes)×100          |
| Risk Threshold  | Low <30, Medium 30–60, High ≥60       |
| Dataset         | CDC BRFSS 2015 (~253,000 records)     |
| Expected Accuracy | ~85–87%                             |

---

## 🩺 Wearable Data Mapping

| Sensor Reading    | Model Feature   | Logic                              |
|-------------------|-----------------|------------------------------------|
| steps_per_day     | PhysActivity    | ≥7500 steps → Active (1)          |
| avg_heart_rate    | GenHlth         | HR + sleep → health rating 1–5    |
| sleep_hours       | PhysHlth        | <6 hrs → more unhealthy days      |
| sleep_hours       | MentHlth        | Poor sleep → stress indicator     |
| calories_burned   | HvyAlcoholConsump | Heuristic default mapping       |

---

## 📝 Quick Troubleshooting

**"Model not loaded. POST /train first."**
→ Run `curl -X POST http://127.0.0.1:5000/train` once

**"CORS error in browser"**
→ Make sure `flask-cors` is installed and Flask is running

**"Dataset not found"**
→ Place `brfss.csv` in the `data/` folder

**Frontend shows no results**
→ Open browser DevTools (F12) → Console — check for network errors
→ Make sure Flask is running on port 5000
