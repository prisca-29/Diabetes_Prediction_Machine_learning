"""
generate_wearable_data.py
─────────────────────────
Run this once to create data/wearable_sample.csv
  python generate_wearable_data.py
"""

import os
import pandas as pd
import numpy as np

os.makedirs("data", exist_ok=True)
rng = np.random.default_rng(42)
n   = 500

df = pd.DataFrame({
    "user_id":         range(1, n + 1),
    "steps_per_day":   rng.integers(1000, 15000, n),
    "avg_heart_rate":  rng.integers(55, 105, n),
    "sleep_hours":     rng.uniform(4, 9.5, n).round(1),
    "calories_burned": rng.integers(150, 800, n),
    "bmi_approx":      rng.uniform(18.5, 45, n).round(1),
})

df.to_csv("data/wearable_sample.csv", index=False)
print(f"✔  wearable_sample.csv created  ({n} rows)")
print(df.head(5))
