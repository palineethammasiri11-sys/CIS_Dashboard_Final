"""
fetch_price_history.py — ดึงราคาหุ้นย้อนหลัง 10 ปี (2015-2025) ของทั้ง 8 หุ้น จาก Yahoo Finance
=====================================================================================
ผลลัพธ์: Dataset/stock_cleaned_data_2015_2025.csv
    รูปแบบเดียวกับ stock_cleaned_data_2023_2025.csv เดิมทุกอย่าง (คอลัมน์, ลำดับ, รูปแบบวันที่, encoding)
    import_data.py / calculate_scores.py / Dashboard ใช้ต่อได้ทันทีโดยไม่ต้องแก้โค้ด

สูตรตัวชี้วัด — ตรวจแล้วว่าตรงกับไฟล์เดิมแบบเป๊ะ (ต่างกัน 0.0000 ทุกตัว ทดสอบกับ ADVANC/KCE):
    EMA20, EMA50      : Exponential MA ของ Close (ไม่ใช่ Adj Close), adjust=False
    MACD              : EMA12 - EMA26 ของ Close | MACD_Signal = EMA9 ของ MACD | MACD_Hist = MACD - Signal
    RSI14             : Wilder's RSI (smoothing alpha = 1/14)
    ADX14             : Wilder's ADX จาก High/Low/Close (alpha = 1/14)
    Volume_Avg20      : ค่าเฉลี่ย Volume 20 วัน (รวมวันปัจจุบัน)
    ดึงข้อมูลก่อนวันเริ่ม 400 วัน (warm-up) ให้ EMA/ADX นิ่งก่อน แล้วค่อยตัดทิ้ง

วิธีใช้ (รันที่โฟลเดอร์หลักของโปรเจกต์ ต้องต่ออินเทอร์เน็ต):
    pip install yfinance
    python fetch_price_history.py
    python rebuild_database.py        ← คำนวณ DB ใหม่ด้วยข้อมูล 10 ปี

ตัวเลือก:
    python fetch_price_history.py --start 2018-01-01        เปลี่ยนปีเริ่มต้น
    python fetch_price_history.py --keep-old                 ไม่ย้ายไฟล์ราคาเดิมออกจาก Dataset/

หมายเหตุ: import_data.py เลือกไฟล์ *stock_cleaned*.csv ตัวแรกตามตัวอักษร สคริปต์นี้จึงย้ายไฟล์ราคาเดิม
ไปไว้ที่ Dataset/_archive/ ให้อัตโนมัติ (ย้ายกลับได้ถ้าต้องการใช้ข้อมูลชุดเดิม)
"""

import argparse
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

TICKERS = ["ADVANC", "CCET", "DELTA", "HANA", "JMART", "KCE", "THCOM", "TRUE"]
YF_SUFFIX = ".BK"                      # ตลาดหลักทรัพย์แห่งประเทศไทยบน Yahoo Finance
WARMUP_DAYS = 400
DATASET_DIR = "Dataset"
OUTPUT_COLUMNS = ["Ticker", "Date", "Adj Close", "Close", "High", "Low", "Open", "Volume",
                  "EMA20", "EMA50", "Volume_Avg20", "RSI14", "MACD", "MACD_Signal", "MACD_Hist", "ADX14"]
JUMP_ALERT = 0.40                      # ราคาเปลี่ยนเกิน 40% ใน 1 วัน = น่าสงสัย (แตกพาร์/ควบรวม/ข้อมูลผิด)


# =====================================================================
# สูตรตัวชี้วัด (ตรงกับไฟล์เดิม)
# =====================================================================
def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _rsi_wilder(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def _adx_wilder(high, low, close, n=14):
    up, down = high.diff(), -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    a = 1 / n
    atr = tr.ewm(alpha=a, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=a, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=a, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=a, adjust=False).mean()


def add_indicators(df):
    """รับ DataFrame ราคารายวันของหุ้น 1 ตัว (Date, Open, High, Low, Close, Adj Close, Volume)
    เรียงตามวันที่ แล้วเพิ่มคอลัมน์ตัวชี้วัดทั้งหมด"""
    out = df.sort_values("Date").reset_index(drop=True).copy()
    c = out["Close"]
    out["EMA20"] = _ema(c, 20)
    out["EMA50"] = _ema(c, 50)
    out["Volume_Avg20"] = out["Volume"].rolling(20).mean()
    out["RSI14"] = _rsi_wilder(c, 14)
    out["MACD"] = _ema(c, 12) - _ema(c, 26)
    out["MACD_Signal"] = _ema(out["MACD"], 9)
    out["MACD_Hist"] = out["MACD"] - out["MACD_Signal"]
    out["ADX14"] = _adx_wilder(out["High"], out["Low"], c, 14)
    return out


# =====================================================================
# ดาวน์โหลด
# =====================================================================
def download_one(ticker, start, end, retries=3):
    import yfinance as yf
    fetch_start = (pd.Timestamp(start) - pd.Timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
    fetch_end = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")   # yfinance end = ไม่รวมวันนั้น
    for attempt in range(1, retries + 1):
        try:
            raw = yf.download(ticker + YF_SUFFIX, start=fetch_start, end=fetch_end,
                              auto_adjust=False, progress=False, threads=False)
            if raw is None or raw.empty:
                raise ValueError("ไม่ได้รับข้อมูล")
            if isinstance(raw.columns, pd.MultiIndex):          # yfinance รุ่นใหม่คืน MultiIndex แม้ดึงตัวเดียว
                raw.columns = raw.columns.get_level_values(0)
            raw = raw.reset_index().rename(columns={"index": "Date"})
            raw["Date"] = pd.to_datetime(raw["Date"]).dt.tz_localize(None).dt.normalize()
            need = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
            missing = [c for c in need if c not in raw.columns]
            if missing:
                raise ValueError(f"ไม่มีคอลัมน์ {missing}")
            return raw[need]
        except Exception as e:
            print(f"    ⚠️ {ticker} ครั้งที่ {attempt}/{retries} ล้มเหลว: {e}")
            time.sleep(3 * attempt)
    return None


def quality_report(ticker, df, start):
    """ตรวจคุณภาพข้อมูล: วันแรกที่มีข้อมูล, ราคากระโดดผิดปกติ, วันที่ Volume = 0"""
    notes = []
    first = df["Date"].min()
    if first > pd.Timestamp(start) + pd.Timedelta(days=10):
        notes.append(f"ข้อมูลเริ่ม {first.date()} (ช้ากว่าที่ขอ — อาจเพิ่งเข้าตลาด/เปลี่ยนชื่อ)")
    ret = df["Close"].pct_change().abs()
    jumps = df.loc[ret > JUMP_ALERT, "Date"].dt.strftime("%Y-%m-%d").tolist()
    if jumps:
        notes.append(f"ราคาเปลี่ยนเกิน {JUMP_ALERT:.0%} ใน 1 วัน: {', '.join(jumps[:5])}"
                     f"{' ...' if len(jumps) > 5 else ''} → ตรวจว่าเป็นแตกพาร์/ควบรวม/ข้อมูลผิด")
    zero_vol = int((df["Volume"] == 0).sum())
    if zero_vol > 5:
        notes.append(f"Volume = 0 จำนวน {zero_vol} วัน (วันหยุด/หุ้นถูกพักการซื้อขาย)")
    return notes


def compare_with_old(new_df, old_path):
    """เทียบช่วงที่ซ้อนกับไฟล์เดิม — ราคาและตัวชี้วัดควรตรงกัน (ยืนยันว่าสูตรและแหล่งข้อมูลเดียวกัน)"""
    try:
        old = pd.read_csv(old_path, encoding="utf-8-sig")
    except Exception:
        return
    old["Date"] = pd.to_datetime(old["Date"]).dt.normalize()
    m = new_df.merge(old, on=["Ticker", "Date"], suffixes=("_new", "_old"))
    if m.empty:
        print("  (ไม่มีช่วงวันที่ซ้อนกับไฟล์เดิม)")
        return
    late = m[m["Date"] >= m["Date"].min() + pd.Timedelta(days=250)]      # ข้ามช่วงที่ไฟล์เดิมยัง warm-up
    print(f"  เทียบกับไฟล์เดิม {len(m):,} แถวที่ซ้อนกัน (ค่าต่างสูงสุด):")
    for col in ["Close", "EMA20", "EMA50", "RSI14", "MACD", "ADX14"]:
        by_t = (late[f"{col}_new"] - late[f"{col}_old"]).abs().groupby(late["Ticker"]).max()
        bad = by_t[by_t >= 0.05]
        flag = "✅" if bad.empty else "⚠️"
        detail = "" if bad.empty else "  ← " + ", ".join(f"{t} {v:.2f}" for t, v in bad.items())
        print(f"    {flag} {col:8s} {by_t.max():.4f}{detail}")
    print("  หมายเหตุ: ถ้าต่างเฉพาะ ADX14 ประมาณ 1-3 จุด (เช่น CCET/JMART/THCOM) แต่ EMA/RSI/MACD ตรงกัน\n"
          "  = ไฟล์เดิมคำนวณ ADX จาก High/Low ชุดก่อนที่ Yahoo แก้ข้อมูล (ตรวจแล้วจากไฟล์ 2023-2025)\n"
          "  ไม่ใช่ปัญหาของสคริปต์ — ไฟล์ใหม่คำนวณ ADX จาก High/Low ชุดเดียวกับที่บันทึกจึงสอดคล้องกว่า\n"
          "  ถ้า Close/EMA ต่างกันมาก = Yahoo ปรับราคาย้อนหลัง (เช่น แตกพาร์) ให้ใช้ไฟล์ใหม่")


# =====================================================================
# Main
# =====================================================================
def main():
    ap = argparse.ArgumentParser(description="ดึงราคาหุ้นย้อนหลังจาก Yahoo Finance")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--keep-old", action="store_true", help="ไม่ย้ายไฟล์ราคาเดิมออกจาก Dataset/")
    # parse_known_args: ข้ามค่าที่ Jupyter/Colab แนบมาเอง (เช่น -f kernel.json) ให้วางโค้ดรันในช่อง Colab ได้
    args, _unknown = ap.parse_known_args()

    try:
        import yfinance  # noqa: F401
    except ImportError:
        sys.exit("❌ ยังไม่ได้ติดตั้ง yfinance → รัน: pip install yfinance")

    y0, y1 = args.start[:4], args.end[:4]
    out_path = os.path.join(DATASET_DIR, f"stock_cleaned_data_{y0}_{y1}.csv")
    os.makedirs(DATASET_DIR, exist_ok=True)

    print(f"\n📥 ดึงราคา {len(TICKERS)} หุ้น ช่วง {args.start} ถึง {args.end} (+ warm-up {WARMUP_DAYS} วัน)\n")
    frames, failed, all_notes = [], [], {}
    for t in TICKERS:
        print(f"  {t}{YF_SUFFIX} ...", end=" ", flush=True)
        raw = download_one(t, args.start, args.end)
        if raw is None:
            print("❌ ล้มเหลว")
            failed.append(t)
            continue
        df = add_indicators(raw)
        df = df[(df["Date"] >= args.start) & (df["Date"] <= args.end)].dropna(subset=["Close"])
        df.insert(0, "Ticker", t)
        frames.append(df)
        all_notes[t] = quality_report(t, df, args.start)
        print(f"✅ {len(df):,} วัน ({df['Date'].min().date()} → {df['Date'].max().date()})")

    if not frames:
        sys.exit("\n❌ ดึงข้อมูลไม่ได้เลย — ตรวจอินเทอร์เน็ต หรือรอสักครู่แล้วลองใหม่ (Yahoo อาจจำกัดจำนวนครั้ง)")

    result = pd.concat(frames, ignore_index=True)[OUTPUT_COLUMNS]

    print("\n🔎 ตรวจคุณภาพข้อมูล")
    for t, notes in all_notes.items():
        for n in notes:
            print(f"  ⚠️ {t}: {n}")
    if not any(all_notes.values()):
        print("  ✅ ไม่พบความผิดปกติ")

    old_files = sorted(f for f in os.listdir(DATASET_DIR)
                       if f.startswith("stock_cleaned") and f.endswith(".csv")
                       and os.path.join(DATASET_DIR, f) != out_path)
    if old_files:
        compare_with_old(result, os.path.join(DATASET_DIR, old_files[-1]))

    out = result.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d 00:00:00")      # รูปแบบเดียวกับไฟล์เดิม
    out["Volume"] = out["Volume"].round().astype("Int64")             # จำนวนเต็มเหมือนไฟล์เดิม
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 บันทึก {out_path} ({len(out):,} แถว)")

    if old_files and not args.keep_old:
        archive = os.path.join(DATASET_DIR, "_archive")
        os.makedirs(archive, exist_ok=True)
        for f in old_files:
            shutil.move(os.path.join(DATASET_DIR, f), os.path.join(archive, f))
            print(f"📦 ย้ายไฟล์เดิม {f} → Dataset/_archive/ (import_data.py จะใช้ไฟล์ใหม่แทน)")

    print("\n" + "=" * 70)
    if failed:
        print(f"⚠️ ดึงไม่สำเร็จ: {failed} — รันสคริปต์ซ้ำอีกครั้ง")
    print("ต่อไป: python rebuild_database.py")


if __name__ == "__main__":
    main()
