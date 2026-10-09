"""
sensitivity_analysis.py — ทดสอบว่าน้ำหนักที่ทีมกำหนดเอง "บิด" อันดับหุ้นหรือไม่ (ตามแนวทาง Yeh & Liu, 2020)
=====================================================================================================
แนวคิด: ถ้าเปลี่ยนน้ำหนักเป็นแบบอื่นที่สมเหตุสมผล (เช่น เท่ากันหมด) แล้วอันดับหุ้นแทบไม่เปลี่ยน
       แปลว่าผลลัพธ์ไม่ได้ขึ้นกับน้ำหนักที่ทีมเลือก → ใช้เป็นหลักฐานรองรับน้ำหนักได้
       ถ้าอันดับเปลี่ยนมาก → ต้องอธิบายเหตุผลของน้ำหนักให้ชัด หรือแจ้งเป็นข้อจำกัด

ทดสอบ 4 จุดที่ใช้น้ำหนัก:
    1. Overall Score   : น้ำหนัก 4 โมดูล (25/25/15/15) — v17.1 ตัด AI ออกจากคะแนนรวม
    2. Health Score    : ROE/ROA/สภาพคล่อง/หนี้ (30/25/20/25)
    3. Risk Score      : 5 มิติ (30/25/20/15/10)
    4. Entry Timing    : Trend/Momentum (60/40)

ตัววัด:
    Spearman ρ      = ความสัมพันธ์ของอันดับกับน้ำหนักปัจจุบัน (1.00 = อันดับเหมือนเดิมทุกตัว)
    หุ้นอันดับ 1 เดิม = หุ้นอันดับ 1 ยังเป็นตัวเดิมหรือไม่
    Top-3 เหมือนเดิม = จำนวนหุ้นที่ยังอยู่ใน 3 อันดับแรก
    เปลี่ยนอันดับสูงสุด = หุ้นที่อันดับขยับมากที่สุดกี่อันดับ

วิธีใช้ (หลังรัน rebuild_database.py แล้ว):
    python sensitivity_analysis.py
ผลลัพธ์: พิมพ์ตาราง + บันทึก sensitivity_results.csv
"""

import sqlite3

import numpy as np
import pandas as pd

DB = "cis_database.db"


def wmean(df, weights):
    """ค่าเฉลี่ยถ่วงน้ำหนักแบบข้ามค่าว่าง (เหมือน industry_benchmark._weighted_mean)"""
    vals = df[list(weights)].apply(pd.to_numeric, errors="coerce")
    w = pd.Series(weights, dtype=float)
    num = (vals.fillna(0) * w).sum(axis=1)
    den = (vals.notna() * w).sum(axis=1)
    return num / den.where(den > 0)


def compare(base, alt, label_group, label_scenario):
    rb, ra = base.rank(ascending=False, method="min"), alt.rank(ascending=False, method="min")
    rho = pd.concat([base, alt], axis=1).corr(method="spearman").iloc[0, 1]
    top1_same = base.idxmax() == alt.idxmax()
    top3 = len(set(base.nlargest(3).index) & set(alt.nlargest(3).index))
    shift = (rb - ra).abs()
    return {
        "ส่วนที่ทดสอบ": label_group, "สถานการณ์": label_scenario,
        "Spearman ρ": round(float(rho), 3),
        "อันดับ 1 เดิม": "ใช่" if top1_same else f"ไม่ ({base.idxmax()} → {alt.idxmax()})",
        "Top-3 เหมือนเดิม": f"{top3}/3",
        "เปลี่ยนอันดับสูงสุด": f"{int(shift.max())} ({shift.idxmax()})" if shift.max() > 0 else "0",
    }


def main():
    df = pd.read_sql("SELECT * FROM cis_summary_scores", sqlite3.connect(DB)).set_index("ticker")
    rows = []

    # ---------- 1. Overall Score ----------
    mods = ["health_score", "valuation_score", "timing_score", "risk_score"]   # v17.1: AI ไม่นับในคะแนนรวม
    cur = dict(zip(mods, [25, 25, 15, 15]))
    base = wmean(df, cur)
    scen = {
        "น้ำหนักเท่ากัน (25 ทุกโมดูล)": dict.fromkeys(mods, 25),
        "เน้นพื้นฐาน (Health/Valuation 35, อื่น 15)": dict(zip(mods, [35, 35, 15, 15])),
        "เน้นจังหวะ/ความเสี่ยง (Timing/Risk 35, อื่น 15)": dict(zip(mods, [15, 15, 35, 35])),
        "ใส่ AI กลับ 10 (เฉพาะหุ้นที่ผ่านด่าน)": {**cur, "ai_score": 10},
    }
    for m in mods:
        scen[f"ตัด {m.replace('_score', '')} ออก"] = {k: v for k, v in cur.items() if k != m}
    for name, w in scen.items():
        rows.append(compare(base, wmean(df, w), "Overall Score", name))

    # ---------- 2. Health Score ----------
    h = pd.DataFrame({
        "s_roe": np.clip(pd.to_numeric(df["roe"], errors="coerce") * 3.5, 0, 100),
        "s_roa": np.clip(pd.to_numeric(df["roa"], errors="coerce") * 7.0, 0, 100),
        "s_liq": pd.to_numeric(df["s_liquidity"], errors="coerce"),
        "s_debt": pd.to_numeric(df["s_debt"], errors="coerce"),
    }, index=df.index)
    hcur = {"s_roe": 30, "s_roa": 25, "s_liq": 20, "s_debt": 25}
    hbase = wmean(h, hcur)
    for name, w in {
        "น้ำหนักเท่ากัน (25 ทุกตัว)": dict.fromkeys(hcur, 25),
        "เน้นกำไร (ROE/ROA 35, อื่น 15)": {"s_roe": 35, "s_roa": 35, "s_liq": 15, "s_debt": 15},
        "เน้นความมั่นคง (สภาพคล่อง/หนี้ 35, อื่น 15)": {"s_roe": 15, "s_roa": 15, "s_liq": 35, "s_debt": 35},
    }.items():
        rows.append(compare(hbase, wmean(h, w), "Health Score", name))

    # ---------- 3. Risk Score (คะแนนสูง = เสี่ยงต่ำ) ----------
    dims = ["risk_dim_tail", "risk_dim_drawdown", "risk_dim_volatility", "risk_dim_market", "risk_dim_quality"]
    rcur = dict(zip(dims, [30, 25, 20, 15, 10]))
    rbase = 100 - wmean(df, rcur)
    for name, w in {
        "น้ำหนักเท่ากัน (20 ทุกมิติ)": dict.fromkeys(dims, 20),
        "ไม่ใช้ Beta (ตัดมิติ Market)": {k: v for k, v in rcur.items() if k != "risk_dim_market"},
        "เน้น Volatility/Beta (30, อื่น 13.3)": dict(zip(dims, [13.3, 13.3, 30, 30, 13.3])),
    }.items():
        rows.append(compare(rbase, 100 - wmean(df, w), "Risk Score", name))

    # ---------- 4. Entry Timing ----------
    t = pd.to_numeric(df["trend_score"], errors="coerce") / 60.0      # สัดส่วนเกณฑ์ Trend ที่ผ่าน (0-1)
    mo = pd.to_numeric(df["mom_score"], errors="coerce") / 40.0       # สัดส่วนเกณฑ์ Momentum ที่ผ่าน (0-1)
    tbase = t * 60 + mo * 40
    for name, (wt, wm) in {"Trend 50 / Momentum 50": (50, 50), "Trend 70 / Momentum 30": (70, 30),
                           "Trend 40 / Momentum 60": (40, 60)}.items():
        rows.append(compare(tbase, t * wt + mo * wm, "Entry Timing", name))

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 60)
    print(out.to_string(index=False))
    print("\nสรุปต่อส่วน (Spearman ρ ต่ำสุดในทุกสถานการณ์ — ยิ่งใกล้ 1 ยิ่งไม่ขึ้นกับน้ำหนัก):")
    print(out.groupby("ส่วนที่ทดสอบ", sort=False)["Spearman ρ"].agg(["min", "mean"]).round(3).to_string())
    out.to_csv("sensitivity_results.csv", index=False, encoding="utf-8-sig")
    print("\n💾 sensitivity_results.csv")


if __name__ == "__main__":
    main()
