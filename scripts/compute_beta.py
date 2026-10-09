"""
compute_beta.py — คำนวณ Beta ของ 8 หุ้นเทียบดัชนี SET จากข้อมูลจริง แทนค่าใน stock_risk_metrics.csv
=====================================================================================================
ปัญหาของไฟล์เดิม: Beta ไม่ทราบที่มา (ตรวจสอบไม่ได้) และ Max Drawdown = -29.36% เท่ากันทั้ง 8 หุ้น (ผิดชัดเจน)

สคริปต์นี้:
    1. ดึงดัชนี SET รายวันจาก Yahoo Finance (^SET.BK) → บันทึก Dataset/set_index_<ปี>_<ปี>.csv (ตรวจสอบย้อนหลังได้)
    2. อ่านราคาหุ้นจาก Dataset/stock_cleaned_data_*.csv (ไฟล์ที่ระบบใช้อยู่)
    3. ตัดแถว "วันหยุดปลอม" (Volume = 0 และ High = Low = Close) ทิ้ง — แถวเหล่านี้มีผลตอบแทน 0% ทำให้ Beta ต่ำกว่าจริง
    4. จับคู่วันที่หุ้นกับดัชนี แล้วคำนวณจากผลตอบแทนรายวันในช่วง BETA_WINDOW_YEARS ปีล่าสุด:
         Beta          = Cov(หุ้น, ตลาด) / Var(ตลาด)                                  (CAPM — Sharpe 1964)
         Downside Beta = Cov(หุ้น, ตลาด | ตลาด < ค่าเฉลี่ย) / Var(ตลาด | ตลาด < ค่าเฉลี่ย)   (Ang, Chen & Xing 2006)
         Beta R2       = สัดส่วนความผันผวนของหุ้นที่อธิบายได้ด้วยตลาด (0-1)
       Volatility และ Max Drawdown คำนวณในช่วงเดียวกัน (แก้ค่า -29.36% ที่ผิด)
    5. เขียน Dataset/stock_risk_metrics.csv ใหม่ (รูปแบบเดิม + คอลัมน์เสริม) และเก็บไฟล์เดิมไว้ที่ Dataset/_archive/

ทำไม 3 ปี: เป็นช่วงที่นิยมใช้ประเมิน Beta (2-5 ปี) ยาวพอให้ค่านิ่ง แต่สะท้อนโครงสร้างธุรกิจปัจจุบัน
TRUE: ใช้ข้อมูลตั้งแต่ 3 มี.ค. 2023 (หลังควบรวม TRUE-DTAC) เพราะก่อนหน้านั้นเป็นบริษัทเดิม

วิธีใช้ (ต้องต่ออินเทอร์เน็ต รันที่ Colab ได้):
    pip install yfinance
    python compute_beta.py
    python compute_beta.py --years 5          เปลี่ยนช่วงคำนวณ
    python compute_beta.py --offline          ใช้ไฟล์ดัชนี SET ที่ดึงไว้แล้ว ไม่ต้องต่อเน็ต
    python compute_beta.py --index-file SET.csv   ใช้ไฟล์ดัชนีที่ดาวน์โหลดเอง (เช่น จาก Investing.com)
"""

import argparse
import glob
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

DATASET_DIR = "Dataset"
TICKERS = ["ADVANC", "CCET", "DELTA", "HANA", "JMART", "KCE", "THCOM", "TRUE"]
# ลองตามลำดับ — ถ้าดัชนี SET ดึงไม่ได้ จะใช้ตัวแทนตลาดที่ใกล้ที่สุดแทน และระบุชื่อไว้ในผลลัพธ์ทุกครั้ง
INDEX_CANDIDATES = [
    ("^SET.BK", "ดัชนี SET"),
    ("^SET", "ดัชนี SET"),
    ("^SET50.BK", "ดัชนี SET50 (ตัวแทนตลาด)"),
    ("TDEX.BK", "ETF อ้างอิง SET50 - TDEX (ตัวแทนตลาด)"),
]
END_DATE = "2025-12-31"
BETA_WINDOW_YEARS = 3
MIN_OBS = 120                                  # วันซื้อขายขั้นต่ำที่ยอมให้คำนวณ Beta
TICKER_START_OVERRIDE = {
    "TRUE": ("2023-03-03", "หลังควบรวม TRUE-DTAC"),
}


# =====================================================================
# ดัชนี SET
# =====================================================================
def _normalize_yf(raw):
    if raw is None or raw.empty:
        raise ValueError("Yahoo ไม่ส่งข้อมูลกลับมา (ว่าง)")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.reset_index()
    date_col = "Date" if "Date" in raw.columns else raw.columns[0]
    raw = raw.rename(columns={date_col: "Date"})
    raw["Date"] = pd.to_datetime(raw["Date"])
    if getattr(raw["Date"].dt, "tz", None) is not None:
        raw["Date"] = raw["Date"].dt.tz_localize(None)
    raw["Date"] = raw["Date"].dt.normalize()
    out = raw[["Date", "Close"]].dropna()
    if len(out) < 250:
        raise ValueError(f"ได้ข้อมูลเพียง {len(out)} วัน น้อยเกินไป")
    return out


def download_set_index(start, end, retries=2):
    """ลองทุกสัญลักษณ์ใน INDEX_CANDIDATES ด้วย 2 วิธี (download / Ticker.history)"""
    import yfinance as yf
    print(f"  (yfinance เวอร์ชัน {getattr(yf, '__version__', '?')})")
    fetch_end = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    methods = [
        ("download", lambda sym: yf.download(sym, start=start, end=fetch_end, auto_adjust=False,
                                             progress=False, threads=False)),
        ("history", lambda sym: yf.Ticker(sym).history(start=start, end=fetch_end, auto_adjust=False)),
    ]
    for sym, label in INDEX_CANDIDATES:
        for mname, fn in methods:
            for attempt in range(1, retries + 1):
                try:
                    out = _normalize_yf(fn(sym))
                    print(f"  ✅ {sym} [{label}] ด้วยวิธี {mname}: {len(out):,} วัน "
                          f"({out['Date'].min().date()} → {out['Date'].max().date()})")
                    return out, sym, label
                except Exception as e:
                    print(f"  ⚠️ {sym} ({mname}) ครั้งที่ {attempt}/{retries}: {str(e)[:120]}")
                    time.sleep(1.5 * attempt)
    return None, None, None


def read_index_file(path):
    """อ่านไฟล์ดัชนีที่ดาวน์โหลดเอง (รองรับ Investing.com / SET / Yahoo: คอลัมน์วันที่ + ราคาปิด)"""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    low = {c.lower(): c for c in df.columns}
    date_col = next((low[k] for k in ["date", "วันที่", "datetime"] if k in low), df.columns[0])
    close_col = next((low[k] for k in ["close", "price", "ราคาปิด", "ปิด", "last", "adj close"] if k in low), None)
    if close_col is None:
        sys.exit(f"❌ ไม่พบคอลัมน์ราคาปิดในไฟล์ {path} (ต้องมีคอลัมน์ชื่อ Close หรือ Price)")
    # เลือกรูปแบบวันที่ (เดือน/วัน หรือ วัน/เดือน) ที่อ่านได้ครบทุกแถวและเรียงลำดับต่อเนื่อง
    raw_dates = df[date_col].astype(str).str.strip()
    parsed = None
    for dayfirst in (False, True):
        d = pd.to_datetime(raw_dates, errors="coerce", dayfirst=dayfirst, format="mixed")
        if d.notna().all() and (d.is_monotonic_increasing or d.is_monotonic_decreasing):
            parsed = d
            break
    if parsed is None:
        parsed = pd.to_datetime(raw_dates, errors="coerce", format="mixed")
    out = pd.DataFrame({
        "Date": parsed,
        "Close": pd.to_numeric(df[close_col].astype(str).str.replace(",", "", regex=False), errors="coerce"),
    }).dropna()
    if out["Date"].dt.year.max() > 2500:                       # พ.ศ. → ค.ศ.
        out["Date"] = out["Date"].apply(lambda d: d.replace(year=d.year - 543))
    out = out.sort_values("Date").drop_duplicates("Date")
    if len(out) < 250:
        sys.exit(f"❌ ไฟล์ {path} มีข้อมูลเพียง {len(out)} วัน (ต้องการอย่างน้อย 250 วัน)")
    print(f"  📂 อ่านไฟล์ดัชนีที่ดาวน์โหลดเอง: {path} ({len(out):,} วัน, "
          f"{out['Date'].min().date()} → {out['Date'].max().date()})")
    return out


def load_or_fetch_index(start, end, offline, index_file=None):
    y0, y1 = start[:4], end[:4]
    path = os.path.join(DATASET_DIR, f"set_index_{y0}_{y1}.csv")
    if index_file:
        df = read_index_file(index_file)
        label = f"ไฟล์ {os.path.basename(index_file)} (SET ดาวน์โหลดเอง)"
    elif offline:
        existing = sorted(glob.glob(os.path.join(DATASET_DIR, "set_index_*.csv")))
        if not existing:
            sys.exit("❌ --offline แต่ไม่พบ Dataset/set_index_*.csv — รันแบบต่อเน็ตก่อน 1 ครั้ง")
        print(f"  📂 ใช้ไฟล์ดัชนีที่มีอยู่: {existing[-1]}")
        df = pd.read_csv(existing[-1], encoding="utf-8-sig", parse_dates=["Date"])
        label = (str(df["Source"].dropna().iloc[0]) if "Source" in df.columns and df["Source"].notna().any()
                 else "ดัชนีตลาด (ไฟล์ " + os.path.basename(existing[-1]) + ")")
        return df[["Date", "Close"]], label
    else:
        try:
            import yfinance  # noqa: F401
        except ImportError:
            sys.exit("❌ ยังไม่ได้ติดตั้ง yfinance → รัน: pip install yfinance")
        df, sym, label = download_set_index(start, end)
        if df is None:
            sys.exit(
                "\n❌ ดึงข้อมูลตลาดจาก Yahoo ไม่ได้ทุกสัญลักษณ์\n"
                "ทางแก้: ดาวน์โหลดดัชนี SET รายวันเองเป็นไฟล์ CSV แล้วรัน\n"
                "    python compute_beta.py --index-file ชื่อไฟล์.csv\n"
                "แหล่งที่ใช้ได้: Investing.com → ค้นหา 'SET Index' → Historical Data → ตั้งช่วง 2015-2025, Daily → Download\n"
                "(ไฟล์ต้องมีคอลัมน์วันที่ และ Close หรือ Price)")
        label = f"{sym} {label} (Yahoo Finance)"
    out = df[["Date", "Close"]].copy()
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    out["Source"] = label                                          # ระบุที่มาไว้ในไฟล์ (ใช้ซ้ำตอน --offline)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  💾 บันทึกข้อมูลตลาดที่ใช้ → {path}")
    return df, label


# =====================================================================
# คำนวณ
# =====================================================================
def load_stock_prices():
    files = sorted(glob.glob(os.path.join(DATASET_DIR, "*stock_cleaned*.csv")))
    if not files:
        sys.exit("❌ ไม่พบไฟล์ราคาหุ้น Dataset/stock_cleaned_data_*.csv")
    path = files[0]                                    # เลือกไฟล์เดียวกับที่ import_data.py ใช้
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    print(f"  📂 ราคาหุ้น: {path} ({len(df):,} แถว)")
    return df


def beta_stats(r_stock, r_mkt):
    cov = np.cov(r_stock, r_mkt, ddof=1)
    beta = cov[0, 1] / cov[1, 1]
    down = r_mkt < r_mkt.mean()
    if down.sum() >= 30:
        cd = np.cov(r_stock[down], r_mkt[down], ddof=1)
        dbeta = cd[0, 1] / cd[1, 1]
    else:
        dbeta = np.nan
    corr = np.corrcoef(r_stock, r_mkt)[0, 1]
    return beta, dbeta, corr ** 2


def compute_all(prices, index_df, years):
    end = pd.Timestamp(END_DATE)
    default_start = end - pd.DateOffset(years=years) + pd.Timedelta(days=1)
    idx = index_df.sort_values("Date").copy()
    idx["r_mkt"] = idx["Close"].pct_change()

    rows, notes = [], []
    for t in TICKERS:
        s = prices[prices["Ticker"] == t].sort_values("Date").copy()
        fake = (s["Volume"] == 0) & (s["High"] == s["Low"]) & (s["Low"] == s["Close"])
        n_fake = int(fake.sum())
        s = s[~fake]

        start = default_start
        window_note = f"{years} ปี"
        if t in TICKER_START_OVERRIDE:
            o_start, why = TICKER_START_OVERRIDE[t]
            if pd.Timestamp(o_start) > start:
                start = pd.Timestamp(o_start)
                window_note = f"ตั้งแต่ {o_start} ({why})"

        # คิดผลตอบแทนหลังตัดช่วงแล้วเท่านั้น — กันผลตอบแทน "ข้ามรอยต่อ" (เช่น วันควบรวม TRUE) หลุดเข้ามา
        s = s[(s["Date"] >= start) & (s["Date"] <= end)].copy()
        s["r"] = s["Close"].pct_change()
        m = s.merge(idx[["Date", "r_mkt"]], on="Date", how="inner").dropna(subset=["r", "r_mkt"])
        if len(m) < MIN_OBS:
            notes.append(f"{t}: ข้อมูลที่จับคู่กับดัชนีได้เพียง {len(m)} วัน (< {MIN_OBS}) ไม่คำนวณ Beta")
            beta = dbeta = r2 = np.nan
        else:
            beta, dbeta, r2 = beta_stats(m["r"].values, m["r_mkt"].values)

        w = s
        vol = w["r"].std() * np.sqrt(252) * 100
        dd = ((w["Close"] / w["Close"].cummax()) - 1).min() * 100

        rows.append({
            "Stock": t,
            "Beta": round(beta, 2) if pd.notna(beta) else "",
            "Volatility (p.a.)": f"{vol:.2f}%",
            "Max Drawdown": f"{dd:.2f}%",
            "Downside Beta": round(dbeta, 2) if pd.notna(dbeta) else "",
            "Beta R2": round(r2, 3) if pd.notna(r2) else "",
            "Beta Window": f"{m['Date'].min().date() if len(m) else '-'} ถึง {m['Date'].max().date() if len(m) else '-'} "
                           f"({len(m)} วัน, {window_note})",
            "_fake_rows": n_fake,
        })
    return pd.DataFrame(rows), notes


# =====================================================================
# Main
# =====================================================================
def main():
    ap = argparse.ArgumentParser(description="คำนวณ Beta เทียบดัชนี SET")
    ap.add_argument("--years", type=int, default=BETA_WINDOW_YEARS)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--index-file", default=None, help="ไฟล์ CSV ดัชนี SET ที่ดาวน์โหลดเอง")
    args, _unknown = ap.parse_known_args()             # ข้ามค่าที่ Colab แนบมาเอง

    print("\n📥 ดัชนี SET")
    prices = load_stock_prices()
    start_needed = (prices["Date"].min()).strftime("%Y-%m-%d")
    index_df, source = load_or_fetch_index(start_needed, END_DATE, args.offline, args.index_file)

    print(f"\n🧮 คำนวณ Beta จากผลตอบแทนรายวัน ช่วง {args.years} ปีล่าสุด (สิ้นสุด {END_DATE})")
    res, notes = compute_all(prices, index_df, args.years)
    res["Beta Source"] = f"คำนวณเองเทียบ {source} ผลตอบแทนรายวัน"

    old_path = os.path.join(DATASET_DIR, "stock_risk_metrics.csv")
    old = None
    if os.path.exists(old_path):
        try:
            old = pd.read_csv(old_path, encoding="utf-8-sig")
            old.columns = old.columns.str.strip()
        except Exception:
            old = None

    print(f"\n{'หุ้น':7s} {'Beta เดิม':>9s} {'Beta ใหม่':>9s} {'Downside':>9s} {'R2':>6s}  ช่วงข้อมูล")
    for _, r in res.iterrows():
        ob = "-"
        if old is not None and "Beta" in old.columns:
            hit = old[old.iloc[:, 0].astype(str).str.upper().str.strip() == r["Stock"]]
            if not hit.empty:
                ob = f"{float(hit['Beta'].iloc[0]):.2f}"
        print(f"{r['Stock']:7s} {ob:>9s} {str(r['Beta']):>9s} {str(r['Downside Beta']):>9s} "
              f"{str(r['Beta R2']):>6s}  {r['Beta Window']}")
    fake_total = res["_fake_rows"].sum()
    if fake_total:
        print(f"\n🧹 ตัดแถววันหยุดปลอม (Volume=0, High=Low=Close) ออก {fake_total} แถวก่อนคำนวณ")
    for n in notes:
        print("⚠️ " + n)

    # เก็บไฟล์ต้นฉบับครั้งเดียว — รันซ้ำจะไม่เขียนทับต้นฉบับด้วยไฟล์ที่คำนวณแล้ว
    archive_path = os.path.join(DATASET_DIR, "_archive", "stock_risk_metrics_original.csv")
    is_original = old is not None and "Beta Source" not in old.columns
    if is_original and not os.path.exists(archive_path):
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        shutil.copy2(old_path, archive_path)
        print(f"\n📦 เก็บไฟล์ต้นฉบับไว้ที่ Dataset/_archive/stock_risk_metrics_original.csv")

    res.drop(columns=["_fake_rows"]).to_csv(old_path, index=False, encoding="utf-8-sig")
    print(f"💾 เขียน {old_path} ใหม่แล้ว")
    print("\nต่อไป: python rebuild_database.py  (หรือเปลี่ยน CALC_VERSION แล้ว Reboot app บน Streamlit Cloud)")


if __name__ == "__main__":
    main()
