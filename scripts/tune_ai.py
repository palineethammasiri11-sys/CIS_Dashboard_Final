"""
tune_ai.py — ปรับจูนพารามิเตอร์ Random Forest ด้วย TimeSeriesSplit (Walk-forward) ตามแนวทาง Wahyuddin et al. (2025)
====================================================================================================================
คำถาม: พารามิเตอร์ที่ทีมตั้งไว้ (200 ต้น, ลึกสุด 4, ใบละ ≥ 10 แถว) ดีพอหรือไม่ ถ้าปรับจูนอย่างเป็นระบบจะดีขึ้นไหม

วิธี (กันข้อมูลอนาคตรั่วทุกขั้น):
    1. ใช้เฉพาะข้อมูลฝึก (ก่อน 2025) แบ่งแบบ TimeSeriesSplit 5 ช่วง — ฝึกด้วยอดีต ทดสอบกับช่วงถัดไปเสมอ
       เว้นช่องว่าง (gap) 10 วันระหว่างช่วงฝึกกับช่วงทดสอบ ให้ Label 10 วันข้างหน้าไม่ล้ำเข้าช่วงทดสอบ
    2. ลองทุกชุดพารามิเตอร์ใน PARAM_GRID เลือกชุดที่ ROC-AUC เฉลี่ยใน 5 ช่วงสูงสุด (แยกรายหุ้น)
    3. ฝึกใหม่ด้วยข้อมูลฝึกทั้งหมด แล้ววัดผลบนปี 2025 ที่ไม่เคยใช้เลือกพารามิเตอร์
    4. เทียบกับพารามิเตอร์ปัจจุบันด้วยเกณฑ์เดียวกับ Dashboard (ชนะ Baseline = Accuracy > Baseline และ AUC > 0.5)

วิธีใช้ (หลังรัน rebuild_database.py):
    python tune_ai.py
ผลลัพธ์: พิมพ์ตาราง + บันทึก tune_ai_results.csv
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # รันจาก folder หลัก: python scripts/<ชื่อไฟล์>.py

import itertools
import sqlite3
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from calculate_modules.ai_prediction import FEATURES, PREDICTION_HORIZON_DAYS, TEST_START, _build_features

warnings.filterwarnings("ignore")
DB = "cis_database.db"
CURRENT = {"max_depth": 4, "min_samples_leaf": 10}
PARAM_GRID = {"max_depth": [3, 4, 6, 8], "min_samples_leaf": [10, 25, 50]}
N_SPLITS = 5


def dataset(g):
    g = g.sort_values("date").reset_index(drop=True)
    f, close = _build_features(g)
    fut = close.shift(-PREDICTION_HORIZON_DAYS)
    f["y"] = np.where(fut.notna(), (fut > close).astype(float), np.nan)
    f["date"] = g["date"].values
    f["label_date"] = g["date"].shift(-PREDICTION_HORIZON_DAYS).values
    a = f.dropna(subset=FEATURES + ["y"])
    T = pd.Timestamp(TEST_START)
    return a[(a["date"] < T) & (a["label_date"] < T)], a[a["date"] >= T]


def rf(params):
    return RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, **params)


def cv_auc(train, params):
    tss = TimeSeriesSplit(n_splits=N_SPLITS, gap=PREDICTION_HORIZON_DAYS)
    scores = []
    for tr_idx, va_idx in tss.split(train):
        tr, va = train.iloc[tr_idx], train.iloc[va_idx]
        if va["y"].nunique() < 2:
            continue
        p = rf(params).fit(tr[FEATURES], tr["y"]).predict_proba(va[FEATURES])[:, 1]
        scores.append(roc_auc_score(va["y"], p))
    return float(np.mean(scores)) if scores else np.nan


def test_eval(train, test, params):
    p = rf(params).fit(train[FEATURES], train["y"]).predict_proba(test[FEATURES])[:, 1]
    acc = accuracy_score(test["y"], p > 0.5) * 100
    base = max(test["y"].mean(), 1 - test["y"].mean()) * 100
    auc = roc_auc_score(test["y"], p)
    return acc, base, auc, bool(acc > base and auc > 0.5)


def main():
    px = pd.read_sql("SELECT * FROM stock_daily_prices", sqlite3.connect(DB))
    px["date"] = pd.to_datetime(px["date"])
    grid = [dict(zip(PARAM_GRID, v)) for v in itertools.product(*PARAM_GRID.values())]
    t0 = time.time()
    rows = []
    for t, g in px.groupby("ticker"):
        train, test = dataset(g)
        cv = {tuple(p.values()): cv_auc(train, p) for p in grid}
        best = dict(zip(PARAM_GRID, max(cv, key=lambda k: (np.nan_to_num(cv[k], nan=-1)))))
        a0, b0, u0, w0 = test_eval(train, test, CURRENT)
        a1, b1, u1, w1 = test_eval(train, test, best)
        rows.append({"หุ้น": t, "พารามิเตอร์ที่ดีที่สุด (ลึก, ใบ)": f"{best['max_depth']}, {best['min_samples_leaf']}",
                     "CV AUC ปัจจุบัน": round(cv[tuple(CURRENT.values())], 3), "CV AUC ที่ดีที่สุด": round(cv[tuple(best.values())], 3),
                     "2025 AUC ปัจจุบัน": round(u0, 3), "2025 AUC ปรับจูน": round(u1, 3),
                     "ชนะ Baseline ปัจจุบัน": "✓" if w0 else "·", "ชนะ Baseline ปรับจูน": "✓" if w1 else "·"})
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(out.to_string(index=False))
    n0, n1 = (out["ชนะ Baseline ปัจจุบัน"] == "✓").sum(), (out["ชนะ Baseline ปรับจูน"] == "✓").sum()
    print(f"\nสรุปบนปี 2025: พารามิเตอร์ปัจจุบันชนะ Baseline {n0}/8 หุ้น · ปรับจูนแล้ว {n1}/8 หุ้น · "
          f"AUC เฉลี่ย {out['2025 AUC ปัจจุบัน'].mean():.3f} → {out['2025 AUC ปรับจูน'].mean():.3f}")
    print(f"ลอง {len(grid)} ชุดพารามิเตอร์ × {N_SPLITS} ช่วง × 8 หุ้น ใช้เวลา {time.time() - t0:.0f} วินาที")
    out.to_csv("tune_ai_results.csv", index=False, encoding="utf-8-sig")
    print("💾 tune_ai_results.csv")


if __name__ == "__main__":
    main()
