"""
walk_forward_models.py — ทดสอบย้อนหลังรายปี 10 ปี (2016-2025) เทียบ 3 โมเดล + วิเคราะห์ Error
=================================================================================================
ต่อยอดจาก model_comparison.py (ซึ่งทดสอบเฉพาะปี 2025 ปีเดียว)

คำถาม:
    1. ผลของ AI ปี 2025 (ผ่าน 3/8) เป็นเรื่องบังเอิญของปีนั้นหรือไม่ ถ้าทดสอบทุกปีจะเป็นอย่างไร
    2. Random Forest ดีกว่าโมเดลอื่นอย่างสม่ำเสมอหรือไม่
    3. โมเดลพลาดเพราะอะไร (Error Analysis)

วิธี (Walk-forward / Expanding window — เงื่อนไขเดียวกับระบบจริงใน calculate_modules/ai_prediction.py):
    - ทดสอบทีละปี Y = 2016 ... 2025
    - ฝึกด้วยข้อมูลทั้งหมดก่อน 1 ม.ค. ปี Y และตัดแถวที่ Label (ราคาอีก 10 วันทำการ) ล้ำเข้าปี Y ทิ้ง (Purging)
    - ทดสอบกับข้อมูลทั้งปี Y แยกโมเดลรายหุ้น (per-stock) เหมือน Dashboard
    - Feature 11 ตัวเดียวกับระบบ (_build_features) และโมเดลชุดเดียวกับ model_comparison.py
    - "ผ่านด่าน" = Accuracy > Baseline (ทายคำตอบที่พบบ่อยที่สุดของปีนั้น) และ ROC-AUC > 0.5 (เกณฑ์เดียวกับ Dashboard)
    - ปี 2016 มีข้อมูลฝึกเพียงปีเดียว (2015) จึงควรอ่านผลปีแรก ๆ อย่างระวัง

วิธีใช้ (หลังรัน rebuild_database.py แล้ว ใช้เวลาประมาณ 2-3 นาที):
    python scripts/walk_forward_models.py
ผลลัพธ์: พิมพ์ตาราง + บันทึก
    walk_forward_by_stock_year.csv   ผลทุกหุ้น × ทุกปี × ทุกโมเดล
    walk_forward_summary.csv         สรุปรายโมเดล
    walk_forward_by_year.csv         สรุปรายปี (จำนวนผ่าน, AUC เฉลี่ย)
    walk_forward_error_analysis.csv  ตัวชี้วัดสำหรับวิเคราะห์ Error ของ Random Forest
"""

import os as _os, sys as _sys  # noqa: E401
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT)                                   # calculate_modules
_sys.path.insert(0, _os.path.join(_ROOT, "scripts"))         # model_comparison (ใช้โมเดลชุดเดียวกัน)

import sqlite3
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from calculate_modules.ai_prediction import FEATURES, PREDICTION_HORIZON_DAYS, _build_features
from model_comparison import MODELS

warnings.filterwarnings("ignore")
DB = "cis_database.db"
TEST_YEARS = list(range(2016, 2026))
COMPARE = ["Random Forest", "Gradient Boosting", "Logistic Regression"]


def build_all(px):
    """Feature + Label ของทุกหุ้น (Label = ราคาอีก 10 วันทำการสูงกว่าวันนี้หรือไม่)"""
    rows = []
    for t, d in px.groupby("ticker"):
        d = d.sort_values("date").reset_index(drop=True)
        f, close = _build_features(d)
        fut = close.shift(-PREDICTION_HORIZON_DAYS)
        f["y"] = np.where(fut.notna(), (fut > close).astype(float), np.nan)
        f["date"] = d["date"].values
        f["label_date"] = d["date"].shift(-PREDICTION_HORIZON_DAYS).values
        f["ticker"] = t
        rows.append(f)
    return pd.concat(rows).dropna(subset=FEATURES + ["y"])


def run(data):
    out = []
    for year in TEST_YEARS:
        start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year + 1}-01-01")
        for t, d in data.groupby("ticker"):
            tr = d[(d["date"] < start) & (d["label_date"] < start)]
            te = d[(d["date"] >= start) & (d["date"] < end)]
            if len(tr) < 50 or len(te) < 20 or te["y"].nunique() < 2:
                continue
            y = te["y"].astype(int)
            up_train, up_test = tr["y"].mean(), y.mean()
            base = max(up_test, 1 - up_test) * 100
            for name in COMPARE + ["Majority Baseline"]:
                m = MODELS[name]().fit(tr[FEATURES], tr["y"].astype(int))
                if name == "Majority Baseline":
                    pred = m.predict(te[FEATURES]).astype(int)
                    proba = np.full(len(te), 0.5)
                else:
                    proba = m.predict_proba(te[FEATURES])[:, 1]
                    pred = (proba > 0.5).astype(int)
                acc = (pred == y.values).mean() * 100
                auc = roc_auc_score(y, proba) if np.std(proba) > 0 else 0.5
                out.append({
                    "model": name, "year": year, "ticker": t, "n_train": len(tr), "n_test": len(te),
                    "accuracy": acc, "baseline": base, "roc_auc": auc,
                    "passed": bool(acc > base and auc > 0.5),
                    "up_ratio_train": up_train * 100, "up_ratio_test": up_test * 100,
                    "pred_up_ratio": pred.mean() * 100, "proba_std": float(np.std(proba)) * 100,
                })
    return pd.DataFrame(out)


def main():
    px = pd.read_sql("SELECT * FROM stock_daily_prices", sqlite3.connect(DB))
    px["date"] = pd.to_datetime(px["date"])
    print(f"ข้อมูลราคา: {px['date'].min().date()} → {px['date'].max().date()}, {px['ticker'].nunique()} หุ้น")
    r = run(build_all(px))
    pd.set_option("display.width", 220)

    # 1) สรุปรายโมเดล
    n_tests = r[r["model"] == "Random Forest"].shape[0]
    summ = (r.groupby("model")
              .agg(passed=("passed", "sum"), mean_accuracy=("accuracy", "mean"), mean_baseline=("baseline", "mean"),
                   mean_roc_auc=("roc_auc", "mean"))
              .reindex(COMPARE + ["Majority Baseline"]))
    summ["passed"] = summ["passed"].astype(int).astype(str) + f"/{n_tests}"
    summ["passed_2025"] = (r[r["year"] == 2025].groupby("model")["passed"].sum()
                           .reindex(summ.index).astype(int).astype(str) + "/8")
    summ = summ.round({"mean_accuracy": 1, "mean_baseline": 1, "mean_roc_auc": 3})
    print("\n=== 1) สรุปรายโมเดล (8 หุ้น × 10 ปี) ===")
    print(summ.to_string())

    # 2) รายปี
    cmp = r[r["model"].isin(COMPARE)]
    year_pass = cmp.pivot_table(index="model", columns="year", values="passed", aggfunc="sum").astype(int)
    year_auc = cmp.pivot_table(index="model", columns="year", values="roc_auc", aggfunc="mean").round(3)
    by_year = pd.concat({"passed": year_pass, "mean_auc": year_auc})
    print("\n=== 2.1) รายปี: จำนวนหุ้นที่ผ่าน (จาก 8) ===")
    print(year_pass.to_string())
    print("\n=== 2.2) รายปี: ROC-AUC เฉลี่ย 8 หุ้น ===")
    print(year_auc.to_string())

    # 3) Error analysis ของ Random Forest
    rf = r[r["model"] == "Random Forest"].copy()
    rf["edge"] = rf["accuracy"] - rf["baseline"]
    rf["regime_shift"] = (rf["up_ratio_test"] - rf["up_ratio_train"]).abs()
    print("\n=== 3) Error Analysis — Random Forest ===")
    per_stock = rf.groupby("ticker").agg(passed=("passed", "sum"), mean_auc=("roc_auc", "mean"),
                                         mean_edge=("edge", "mean")).round(3)
    per_stock["passed"] = per_stock["passed"].astype(int).astype(str) + "/10"
    print("3.1 รายหุ้น (ผ่านกี่ปีจาก 10, AUC เฉลี่ย, Accuracy − Baseline เฉลี่ย):")
    print(per_stock.to_string())
    rho_shift, p_shift = spearmanr(rf["regime_shift"], rf["edge"])
    rho_base, p_base = spearmanr(rf["baseline"], rf["edge"])
    print(f"\n3.2 ทิศทางตลาดเปลี่ยน (|สัดส่วนวันขึ้นปีทดสอบ − ปีฝึก|) กับ Accuracy − Baseline: "
          f"Spearman ρ = {rho_shift:.2f} (p = {p_shift:.3f})")
    print(f"3.3 Baseline สูง (ปีที่ขึ้นหรือลงฝั่งเดียวชัด) กับ Accuracy − Baseline: "
          f"Spearman ρ = {rho_base:.2f} (p = {p_base:.3f})")
    print(f"3.4 ความกระจายของโอกาสขึ้นที่โมเดลให้ (SD) เฉลี่ย {rf['proba_std'].mean():.1f} จุด %")
    mb = r[r["model"] == "Majority Baseline"]
    print(f"3.7 Baseline ที่ใช้ในด่าน (ทายฝั่งที่พบบ่อยของปีทดสอบ ซึ่งรู้ได้หลังจบปี) เฉลี่ย {mb['baseline'].mean():.1f}% "
          f"แต่การทายฝั่งที่พบบ่อยของช่วงฝึก (รู้ได้ล่วงหน้า) แม่นจริงเฉลี่ย {mb['accuracy'].mean():.1f}% "
          f"· Random Forest {rf['accuracy'].mean():.1f}%")
    print(f"3.5 สัดส่วนวันที่ทาย 'ขึ้น' เฉลี่ย {rf['pred_up_ratio'].mean():.1f}% "
          f"เทียบวันที่ขึ้นจริง {rf['up_ratio_test'].mean():.1f}%")
    worst = rf.groupby("year")["edge"].mean().idxmin()
    print(f"3.6 ปีที่แย่ที่สุด: {worst} (Accuracy − Baseline เฉลี่ย {rf.groupby('year')['edge'].mean().min():.1f} จุด %)")

    ea = pd.DataFrame([
        {"metric": "spearman_regime_shift_vs_edge", "value": rho_shift, "p_value": p_shift},
        {"metric": "spearman_baseline_vs_edge", "value": rho_base, "p_value": p_base},
        {"metric": "mean_proba_sd_pct", "value": rf["proba_std"].mean(), "p_value": None},
        {"metric": "mean_pred_up_pct", "value": rf["pred_up_ratio"].mean(), "p_value": None},
        {"metric": "mean_actual_up_pct", "value": rf["up_ratio_test"].mean(), "p_value": None},
        {"metric": "worst_year", "value": worst, "p_value": None},
    ])

    r.round(3).to_csv("walk_forward_by_stock_year.csv", index=False, encoding="utf-8-sig")
    summ.to_csv("walk_forward_summary.csv", encoding="utf-8-sig")
    by_year.to_csv("walk_forward_by_year.csv", encoding="utf-8-sig")
    ea.to_csv("walk_forward_error_analysis.csv", index=False, encoding="utf-8-sig")
    print("\n💾 walk_forward_summary.csv, walk_forward_by_year.csv, walk_forward_by_stock_year.csv, "
          "walk_forward_error_analysis.csv")


if __name__ == "__main__":
    main()
