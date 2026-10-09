"""
model_comparison.py — เปรียบเทียบโมเดลทำนายทิศทางราคา 10 วัน (ตารางสำหรับเล่มรายงาน / สไลด์)
==========================================================================================
ใช้ข้อมูลและเงื่อนไขเดียวกับระบบจริงทุกอย่าง (calculate_modules/ai_prediction.py):
    - ข้อมูลราคาจากตาราง stock_daily_prices ใน cis_database.db (รัน rebuild_database.py ก่อน)
    - Feature 11 ตัวเชิงสัดส่วน (_build_features), Label = ราคาอีก 10 วันทำการสูงกว่าวันนี้หรือไม่
    - Train = ก่อน 1 ม.ค. 2025 (ตัดแถวที่ label ล้ำเข้าปี 2025 ทิ้ง = Purging), Test = ปี 2025 ทั้งปี
    - "ชนะ Baseline" = Accuracy > การเดาคำตอบที่พบบ่อยที่สุดของปี 2025 และ ROC-AUC > 0.5 (เกณฑ์เดียวกับ Dashboard)

วิธีใช้:
    python model_comparison.py
ผลลัพธ์: พิมพ์ตาราง + บันทึก model_comparison_summary.csv และ model_comparison_by_stock.csv
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # รันจาก folder หลัก: python scripts/<ชื่อไฟล์>.py

import sqlite3
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from calculate_modules.ai_prediction import FEATURES, PREDICTION_HORIZON_DAYS, TEST_START, _build_features

warnings.filterwarnings("ignore")
DB = "cis_database.db"
SEED = 42

MODELS = {
    "Majority Baseline": lambda: DummyClassifier(strategy="most_frequent"),
    "Logistic Regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000)),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=10,
                                                    random_state=SEED, n_jobs=-1),
    "Gradient Boosting": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                                                random_state=SEED),
}


def build_dataset(px, start_date=None):
    rows = []
    for t, d in px.groupby("ticker"):
        d = d.sort_values("date").reset_index(drop=True)
        if start_date:
            d = d[d["date"] >= start_date].reset_index(drop=True)
        f, close = _build_features(d)
        fut = close.shift(-PREDICTION_HORIZON_DAYS)
        f["y"] = np.where(fut.notna(), (fut > close).astype(float), np.nan)
        f["date"] = d["date"].values
        f["label_date"] = d["date"].shift(-PREDICTION_HORIZON_DAYS).values
        f["ticker"] = t
        rows.append(f)
    a = pd.concat(rows).dropna(subset=FEATURES + ["y"])
    T = pd.Timestamp(TEST_START)
    train = a[(a["date"] < T) & (a["label_date"] < T)]
    test = a[a["date"] >= T]
    return train, test


def evaluate(train, test, model_name, mode):
    make = MODELS[model_name]
    t0 = time.time()
    per_stock = []
    if mode == "pooled":
        m = make().fit(train[FEATURES], train["y"])
    for t in sorted(test["ticker"].unique()):
        te = test[test["ticker"] == t]
        if mode == "per-stock":
            tr = train[train["ticker"] == t]
            m = make().fit(tr[FEATURES], tr["y"])
        proba = m.predict_proba(te[FEATURES])[:, 1] if hasattr(m, "predict_proba") else m.predict(te[FEATURES])
        pred = (proba > 0.5).astype(int) if model_name != "Majority Baseline" else m.predict(te[FEATURES])
        acc = accuracy_score(te["y"], pred) * 100
        base = max(te["y"].mean(), 1 - te["y"].mean()) * 100
        auc = roc_auc_score(te["y"], proba) if te["y"].nunique() > 1 and np.std(proba) > 0 else 0.5
        f1 = f1_score(te["y"], pred, zero_division=0) * 100
        per_stock.append({"model": model_name, "data": mode, "ticker": t, "accuracy": acc, "baseline": base,
                          "roc_auc": auc, "f1": f1, "beats_baseline": bool(acc > base and auc > 0.5)})
    sec = time.time() - t0
    ps = pd.DataFrame(per_stock)
    summary = {
        "model": model_name, "data": mode,
        "train_rows": len(train) if mode == "pooled" else int(round(len(train) / train["ticker"].nunique())),
        "stocks_beat_baseline": f"{int(ps['beats_baseline'].sum())}/{len(ps)}",
        "mean_accuracy": ps["accuracy"].mean(), "mean_baseline": ps["baseline"].mean(),
        "mean_roc_auc": ps["roc_auc"].mean(), "mean_f1": ps["f1"].mean(), "train_seconds": sec,
    }
    return summary, ps


def main():
    px = pd.read_sql("SELECT * FROM stock_daily_prices", sqlite3.connect(DB))
    px["date"] = pd.to_datetime(px["date"])
    print(f"ข้อมูลราคา: {px['date'].min().date()} → {px['date'].max().date()}, {px['ticker'].nunique()} หุ้น")

    experiments = [("10 ปี (2015-2024)", None)]
    if px["date"].min() < pd.Timestamp("2022-01-01"):
        experiments.append(("2 ปี (2023-2024)", pd.Timestamp("2023-01-01")))

    summaries, details = [], []
    for label, start in experiments:
        train, test = build_dataset(px, start)
        for name in MODELS:
            for mode in (["per-stock"] if name == "Majority Baseline" else ["per-stock", "pooled"]):
                s, ps = evaluate(train, test, name, mode)
                s["train_period"] = label
                ps["train_period"] = label
                summaries.append(s)
                details.append(ps)

    summ = pd.DataFrame(summaries)
    det = pd.concat(details)
    for c in ["mean_accuracy", "mean_baseline", "mean_f1"]:
        summ[c] = summ[c].round(1)
    summ["mean_roc_auc"] = summ["mean_roc_auc"].round(3)
    summ["train_seconds"] = summ["train_seconds"].round(2)
    cols = ["train_period", "model", "data", "train_rows", "stocks_beat_baseline", "mean_accuracy",
            "mean_baseline", "mean_roc_auc", "mean_f1", "train_seconds"]
    pd.set_option("display.width", 220)
    print(summ[cols].to_string(index=False))
    summ[cols].to_csv("model_comparison_summary.csv", index=False, encoding="utf-8-sig")
    det.round(3).to_csv("model_comparison_by_stock.csv", index=False, encoding="utf-8-sig")
    print("\n💾 model_comparison_summary.csv, model_comparison_by_stock.csv")


if __name__ == "__main__":
    main()
