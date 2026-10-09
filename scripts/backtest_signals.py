"""
backtest_signals.py — ทดสอบย้อนหลังว่าสัญญาณ Entry Timing (STRONG BUY / NEUTRAL / BEARISH) ใช้ได้จริงหรือไม่
==========================================================================================================
คำถาม: หลังวันที่ระบบให้สัญญาณ STRONG BUY ผลตอบแทน 10/20 วันข้างหน้าดีกว่า "ซื้อวันไหนก็ได้" หรือไม่
       (หักค่าธรรมเนียมซื้อขายไปกลับแล้ว ตาม Anghel, 2022 ที่ชี้ว่าถ้าไม่หักต้นทุนจะได้ผลดีเกินจริง)

วิธี:
    - คำนวณสัญญาณ "ทุกวัน" ด้วยกติกาเดียวกับ calculate_modules/entry_timing.py (v2.3) ใช้ข้อมูลถึงวันนั้นเท่านั้น
        Trend 60   : ราคา > EMA20, EMA20 > EMA50, ราคา > MA200 (ข้อละ 20)
        Momentum 40: MACD > 0, ADX >= 25, Volume > ค่าเฉลี่ย 20 วันก่อนหน้า (ข้อละ 13.33)
        >= 70 STRONG BUY · >= 40 NEUTRAL · < 40 BEARISH · ราคา < MA200 บังคับ BEARISH (Trend Veto)
      และตรวจว่าคะแนนวันล่าสุดตรงกับโมดูลจริงทุกหุ้นก่อนใช้ผล
    - Baseline = ผลตอบแทนเฉลี่ยของ "ทุกวัน" (เหมือนซื้อสุ่มวันไหนก็ได้ / Buy-and-Hold)
    - ต้นทุนซื้อขายไปกลับ ROUND_TRIP_COST (สมมติฐาน 0.30% — ค่าคอมมิชชันออนไลน์ราว 0.15% ต่อขา รวม VAT)
    - ช่วงทดสอบ: 2016-2025 (ปี 2015 ใช้สะสม MA200) แยกดูช่วง 3 ปีล่าสุด 2023-2025 ด้วย

ข้อจำกัด: ผลตอบแทนของวันติดกันซ้อนทับกัน (ไม่เป็นอิสระต่อกัน) จำนวนสัญญาณจึงดูมากกว่าข้อมูลอิสระจริง
         และ Overall Recommendation ทดสอบย้อนหลังไม่ได้ เพราะงบการเงินมีแค่ปี 2023-2025

วิธีใช้ (หลังรัน rebuild_database.py แล้ว):
    python backtest_signals.py
ผลลัพธ์: พิมพ์ตาราง + บันทึก backtest_signals_summary.csv
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # รันจาก folder หลัก: python scripts/<ชื่อไฟล์>.py

import sqlite3

import numpy as np
import pandas as pd

DB = "cis_database.db"
ROUND_TRIP_COST = 0.0030
HORIZONS = (10, 20)
START = "2016-01-01"
RECENT_START = "2023-01-01"


def signals_for(df):
    """คะแนนและสัญญาณรายวันตามกติกา entry_timing.py v2.3 (ใช้ข้อมูลถึงวันนั้นเท่านั้น)"""
    d = df.sort_values("date").reset_index(drop=True).copy()
    c = d["close"]
    ma200 = c.rolling(200).mean()
    vol_prev_avg = d["volume"].shift(1).rolling(20).mean()          # 20 วันก่อนหน้า ไม่รวมวันนี้
    k = pd.DataFrame({
        "k15": c > d["EMA20"], "k16": d["EMA20"] > d["EMA50"], "k17": c > ma200,
        "k18": d["MACD"] > 0, "k19": d["ADX"] >= 25, "k20": d["volume"] > vol_prev_avg,
    })
    trend = k[["k15", "k16", "k17"]].sum(axis=1) * (60 / 3)
    mom = k[["k18", "k19", "k20"]].sum(axis=1) * (40 / 3)
    score = (trend + mom).round()
    veto = ma200.notna() & (c < ma200)
    sig = np.where(veto | (score < 40), "BEARISH", np.where(score >= 70, "STRONG BUY", "NEUTRAL"))
    d["score"], d["signal"] = score, sig
    d["valid"] = ma200.notna() & vol_prev_avg.notna()
    for h in HORIZONS:
        d[f"fwd{h}"] = c.shift(-h) / c - 1
    return d


def summarize(panel, label):
    rows = []
    for h in HORIZONS:
        col = f"fwd{h}"
        p = panel.dropna(subset=[col])
        base_mean = p[col].mean() - ROUND_TRIP_COST
        base_hit = (p[col] > ROUND_TRIP_COST).mean()
        rows.append({"ช่วง": label, "ถือ (วัน)": h, "สัญญาณ": "ทุกวัน (Baseline)", "จำนวนวัน": len(p),
                     "ผลตอบแทนเฉลี่ยสุทธิ (%)": round(base_mean * 100, 2),
                     "โอกาสกำไรสุทธิ (%)": round(base_hit * 100, 1), "ส่วนต่างจาก Baseline (จุด %)": 0.0})
        for s in ["STRONG BUY", "NEUTRAL", "BEARISH"]:
            q = p[p["signal"] == s]
            if q.empty:
                continue
            m = q[col].mean() - ROUND_TRIP_COST
            rows.append({"ช่วง": label, "ถือ (วัน)": h, "สัญญาณ": s, "จำนวนวัน": len(q),
                         "ผลตอบแทนเฉลี่ยสุทธิ (%)": round(m * 100, 2),
                         "โอกาสกำไรสุทธิ (%)": round((q[col] > ROUND_TRIP_COST).mean() * 100, 1),
                         "ส่วนต่างจาก Baseline (จุด %)": round((m - base_mean) * 100, 2)})
    return rows


def verify_against_module(px):
    """ตรวจว่าคะแนนวันล่าสุดจากสคริปต์นี้ตรงกับ calculate_modules/entry_timing.py ทุกหุ้น"""
    try:
        from calculate_modules.entry_timing import calculate_timing_module
    except Exception as e:
        print(f"⚠️ ตรวจกับโมดูลจริงไม่ได้: {e}")
        return
    bad = []
    for t, g in px.groupby("ticker"):
        mine = signals_for(g).iloc[-1]["score"]
        real = calculate_timing_module(g.sort_values("date"))["timing_score"]
        if real is None or abs(float(real) - float(mine)) > 0.5:
            bad.append((t, mine, real))
    print("✅ คะแนนตรงกับโมดูลจริงครบทุกหุ้น" if not bad else f"❌ คะแนนไม่ตรง: {bad}")


def robustness(panel, h=20):
    """ผลตอบแทนวันติดกันซ้อนทับกัน → สุ่มตัวอย่างทุก h วัน (ไม่ซ้อนทับ) 20 จุดเริ่มต้น แล้วดูว่าผลยังอยู่หรือไม่"""
    p = panel.dropna(subset=[f"fwd{h}"])
    rows = []
    for off in range(h):
        smp = p.groupby("ticker", group_keys=False).apply(lambda g: g.iloc[off::h])
        sb, allv = smp[smp["signal"] == "STRONG BUY"][f"fwd{h}"], smp[f"fwd{h}"]
        se = np.sqrt(sb.var() / len(sb) + allv.var() / len(allv))
        rows.append({"diff": (sb.mean() - allv.mean()) * 100, "t": (sb.mean() - allv.mean()) / se, "n": len(sb)})
    r = pd.DataFrame(rows)
    print(f"\nตรวจความทนทาน (ตัวอย่างไม่ซ้อนทับ ทุก {h} วัน × {h} จุดเริ่มต้น, STRONG BUY ราว {int(r.n.mean())} ครั้งต่อชุด):")
    print(f"  STRONG BUY ชนะ Baseline {int((r['diff'] > 0).sum())}/{h} ชุด · ส่วนต่างเฉลี่ย {r['diff'].mean():.2f} จุด % "
          f"(ต่ำสุด {r['diff'].min():.2f}) · ค่า t เฉลี่ย {r['t'].mean():.2f} (|t| > 1.96 = มีนัยสำคัญที่ 5%)")


def main():
    px = pd.read_sql("SELECT * FROM stock_daily_prices", sqlite3.connect(DB))
    px["date"] = pd.to_datetime(px["date"])
    for col in ["close", "EMA20", "EMA50", "MACD", "ADX", "volume"]:
        px[col] = pd.to_numeric(px[col], errors="coerce")
    verify_against_module(px)

    panel = pd.concat([signals_for(g).assign(ticker=t) for t, g in px.groupby("ticker")])
    panel = panel[panel["valid"] & (panel["date"] >= START)]
    print(f"ช่วงทดสอบ {panel['date'].min().date()} → {panel['date'].max().date()} · ต้นทุนไปกลับ {ROUND_TRIP_COST:.2%}\n")

    rows = summarize(panel, "2016-2025") + summarize(panel[panel["date"] >= RECENT_START], "2023-2025")
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(out.to_string(index=False))

    robustness(panel)

    by_stock = (panel.dropna(subset=["fwd20"]).assign(net=lambda x: x["fwd20"] - ROUND_TRIP_COST)
                .pivot_table(index="ticker", columns="signal", values="net", aggfunc="mean") * 100).round(2)
    by_stock["Baseline"] = ((panel.dropna(subset=["fwd20"]).groupby("ticker")["fwd20"].mean()
                             - ROUND_TRIP_COST) * 100).round(2)
    print("\nผลตอบแทนเฉลี่ยสุทธิ 20 วัน แยกรายหุ้น (%), 2016-2025:")
    print(by_stock[[c for c in ["STRONG BUY", "NEUTRAL", "BEARISH", "Baseline"] if c in by_stock]].to_string())

    out.to_csv("backtest_signals_summary.csv", index=False, encoding="utf-8-sig")
    by_stock.to_csv("backtest_signals_by_stock.csv", encoding="utf-8-sig")
    print("\n💾 backtest_signals_summary.csv, backtest_signals_by_stock.csv")


if __name__ == "__main__":
    main()
