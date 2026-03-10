import pandas as pd
import numpy as np
import joblib
import json
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

# ==========================================================
# STEP 1: Load Dataset
# ==========================================================
print("=" * 50)
print("  ECO FERTILIZATION — MODEL TRAINER v2.0")
print("=" * 50)
print("\nStep 1: Loading Crop_recommendation.csv...")

file_name = 'Crop_recommendation.csv'

if not os.path.exists(file_name):
    print(f"❌ Error: {file_name} not found!")
else:
    df = pd.read_csv(file_name)
    print(f"✅ Loaded {len(df)} rows, {df['label'].nunique()} crops")

    # ==========================================================
    # STEP 2: Prepare Features
    # ==========================================================
    print("\nStep 2: Encoding features...")

    # One-Hot Encode crop labels → label_rice, label_maize, etc.
    df_encoded = pd.get_dummies(df, columns=['label'])

    # X = all inputs (weather + one-hot crop columns)
    # y = N, P, K separately
    X = df_encoded.drop(['N', 'P', 'K'], axis=1)
    y_N = df_encoded['N']
    y_P = df_encoded['P']
    y_K = df_encoded['K']

    print(f"✅ Features: {list(X.columns)}")

    # Save column order — app.py needs this to build input correctly
    joblib.dump(X.columns.tolist(), 'model_columns.pkl')
    print("✅ model_columns.pkl saved")

    # 80/20 train-test split
    X_train, X_test, \
    yN_train, yN_test, \
    yP_train, yP_test, \
    yK_train, yK_test = train_test_split(
        X, y_N, y_P, y_K,
        test_size=0.2,
        random_state=42
    )

    # ==========================================================
    # STEP 3: Train 3 Separate Models (N, P, K)
    # WHY: A single multi-output model gets confused between
    # nutrients. Apple/Grapes dominate because their NPK is
    # extreme. Separate models each focus on ONE nutrient only.
    # ==========================================================
    print("\nStep 3: Training 3 separate GradientBoosting models...")
    print("  (This takes ~30 seconds — please wait)")

    # --- MODEL N ---
    print("\n  Training Model N (Nitrogen)...")
    model_N = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    model_N.fit(X_train, yN_train)
    predN_test = model_N.predict(X_test)
    r2_N  = r2_score(yN_test, predN_test)
    mae_N = mean_absolute_error(yN_test, predN_test)
    print(f"  ✅ N Model → R² = {r2_N:.4f} | MAE = {mae_N:.2f} kg/ha")

    # --- MODEL P ---
    print("\n  Training Model P (Phosphorus)...")
    model_P = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    model_P.fit(X_train, yP_train)
    predP_test = model_P.predict(X_test)
    r2_P  = r2_score(yP_test, predP_test)
    mae_P = mean_absolute_error(yP_test, predP_test)
    print(f"  ✅ P Model → R² = {r2_P:.4f} | MAE = {mae_P:.2f} kg/ha")

    # --- MODEL K ---
    print("\n  Training Model K (Potassium)...")
    model_K = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    model_K.fit(X_train, yK_train)
    predK_test = model_K.predict(X_test)
    r2_K  = r2_score(yK_test, predK_test)
    mae_K = mean_absolute_error(yK_test, predK_test)
    print(f"  ✅ K Model → R² = {r2_K:.4f} | MAE = {mae_K:.2f} kg/ha")

    # ==========================================================
    # STEP 4: Quick Accuracy Check — compare predicted vs real
    # ==========================================================
    print("\nStep 4: Spot-checking predictions vs real values...")
    check_crops = ['rice', 'cotton', 'banana', 'maize', 'apple', 'orange']

    print(f"\n  {'Crop':<14} {'Pred N':>7} {'Real N':>7} | {'Pred P':>7} {'Real P':>7} | {'Pred K':>7} {'Real K':>7}")
    print("  " + "-" * 72)

    for crop in check_crops:
        real = df[df['label'] == crop][['N', 'P', 'K']].mean()

        row = pd.DataFrame(np.zeros((1, len(X.columns))), columns=X.columns)
        row['temperature'] = 27.0
        row['humidity']    = 65.0
        row['ph']          = 6.5
        row['rainfall']    = 5.0
        col = f'label_{crop}'
        if col in row.columns:
            row[col] = 1

        pN = int(round(model_N.predict(row)[0]))
        pP = int(round(model_P.predict(row)[0]))
        pK = int(round(model_K.predict(row)[0]))
        rN = int(round(real['N']))
        rP = int(round(real['P']))
        rK = int(round(real['K']))

        print(f"  {crop:<14} {pN:>7} {rN:>7} | {pP:>7} {rP:>7} | {pK:>7} {rK:>7}")

    # ==========================================================
    # STEP 5: Save Models
    # ==========================================================
    print("\nStep 5: Saving models...")
    joblib.dump(model_N, 'model_N.pkl')
    joblib.dump(model_P, 'model_P.pkl')
    joblib.dump(model_K, 'model_K.pkl')
    print("✅ model_N.pkl saved")
    print("✅ model_P.pkl saved")
    print("✅ model_K.pkl saved")

    # Also save combined metrics for dashboard
    avg_r2  = round((r2_N + r2_P + r2_K) / 3, 4)
    avg_mae = round((mae_N + mae_P + mae_K) / 3, 2)

    dashboard_metrics = {
        "r2_N":  round(r2_N, 4),
        "r2_P":  round(r2_P, 4),
        "r2_K":  round(r2_K, 4),
        "r2_avg": avg_r2,
        "mae_N": round(mae_N, 2),
        "mae_P": round(mae_P, 2),
        "mae_K": round(mae_K, 2),
        "mae_avg": avg_mae,
        "features": ["Temperature", "Humidity", "pH", "Rainfall", "Crop (one-hot)"],
        "model_type": "GradientBoostingRegressor x3 (separate N, P, K)"
    }

    with open('model_metrics.json', 'w') as f:
        json.dump(dashboard_metrics, f, indent=4)
    print("✅ model_metrics.json saved")

    # ==========================================================
    # FINAL SUMMARY
    # ==========================================================
    print("\n" + "=" * 50)
    print(f"  ✅ TRAINING COMPLETE")
    print(f"  N Model Accuracy (R²): {r2_N * 100:.1f}%  MAE: {mae_N:.1f}")
    print(f"  P Model Accuracy (R²): {r2_P * 100:.1f}%  MAE: {mae_P:.1f}")
    print(f"  K Model Accuracy (R²): {r2_K * 100:.1f}%  MAE: {mae_K:.1f}")
    print(f"  Average R²           : {avg_r2 * 100:.1f}%")
    print("=" * 50)
    print("\n  Files saved: model_N.pkl, model_P.pkl, model_K.pkl,")
    print("               model_columns.pkl, model_metrics.json")
    print("\n  ⚠️  Now restart app.py to load the new models.\n")