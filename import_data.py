"""
import_data.py
----------------
นำเข้าข้อมูลจากไฟล์ Dataset ทั้ง 5 ไฟล์ (งบการเงิน, ราคาหุ้นรายวัน, ความเสี่ยง)
เข้า SQLite (cis_database.db) เพื่อให้ calculate_scores.py และ app.py ใช้งานต่อ

ตาราง (tables) ที่จะถูกสร้าง:
- stock_financials      : งบการเงินปี 2023-2025 ของ 8 หุ้นเป้าหมาย (ตัวเลขถูกแปลงเป็น float แล้ว)
- stock_daily_prices    : ราคาหุ้นรายวัน + technical indicators (ช่วงตาม PRICE_START_DATE - PRICE_END_DATE)
- stock_risk_static     : Beta / Volatility / Max Drawdown รายหุ้น จาก stock_risk_metrics.csv
- valuation_params      : WACC (บาท) และ Target P/E รายหุ้น รายปี 2023-2025 จาก valuation_params_2023_2025.csv (Damodaran)
"""

import os
import glob
import pandas as pd
from sqlalchemy import create_engine

DB_NAME = 'cis_database.db'
TARGET_STOCKS = ['ADVANC', 'CCET', 'DELTA', 'HANA', 'JMART', 'KCE', 'THCOM', 'TRUE']
TARGET_YEARS = [2023, 2024, 2025]

# [FIX-D2] ช่วงวันที่ของราคาที่นำเข้า — เดิม hardcode >= 2023-01-01 ทำให้ไฟล์ราคา 10 ปี (2015-2025)
# ถูกตัดเหลือ 3 ปีโดยไม่มีข้อความเตือน ตอนนี้รับทุกวันที่ในไฟล์ตั้งแต่ 2015 (เปลี่ยนได้ที่นี่ที่เดียว)
PRICE_START_DATE = "2015-01-01"
PRICE_END_DATE = "2025-12-31"

SEARCH_DIRS = ['.', 'Dataset', 'Dataset/train_test', 'dataset', 'dataset/train_test']


def write_table(df, name, engine):
    """[v17.3] เขียนตารางลง SQLite แบบ "ลบของเดิมก่อนเสมอ" แล้วค่อยสร้างใหม่ ภายใน transaction เดียว
    แก้ error บน Streamlit Cloud: (sqlite3.OperationalError) table ... already exists
    ซึ่งเกิดเมื่อ pandas ตรวจไม่เจอตารางเดิม (หรือมีการสร้างฐานข้อมูลซ้อนกัน 2 รอบ) แล้วสั่ง CREATE TABLE ซ้ำ"""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
        df.to_sql(name, con=conn, if_exists='replace', index=False)


def find_file(pattern):
    """ค้นหาไฟล์ตาม pattern ในหลาย ๆ โฟลเดอร์ที่เป็นไปได้"""
    for d in SEARCH_DIRS:
        matches = glob.glob(os.path.join(d, pattern))
        if matches:
            return sorted(matches)[0]
    return None


def find_all_files(pattern):
    found = []
    for d in SEARCH_DIRS:
        found.extend(glob.glob(os.path.join(d, pattern)))
    # unique, keep order
    seen = set()
    out = []
    for f in found:
        rp = os.path.abspath(f)
        if rp not in seen:
            seen.add(rp)
            out.append(f)
    return out


def read_csv_smart(path):
    """อ่าน CSV โดยลองหลาย encoding (ไฟล์งบการเงินเป็น cp874 เพราะมีหัวคอลัมน์ภาษาไทย)"""
    for enc in ['utf-8', 'cp874', 'cp1252', 'latin1']:
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # last resort
    return pd.read_csv(path, encoding='utf-8', errors='replace')


def clean_numeric_series(s):
    """แปลงคอลัมน์ตัวเลขที่มี comma / % / ช่องว่าง ให้เป็น float"""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    return (
        s.astype(str)
        .str.replace(',', '', regex=False)
        .str.replace('%', '', regex=False)
        .str.strip()
        .replace({'': None, '-': None, 'nan': None, 'None': None})
        .astype(float)
    )


def import_financial_data(engine):
    print("\n--- 1. กำลังประมวลผลไฟล์งบการเงิน (Financials) ---")

    # ไฟล์หลัก master_all_8_stocks_financials + ไฟล์ train/test (โครงสร้างคอลัมน์เดียวกัน)
    # ใช้ master เป็นหลักเพราะครอบคลุมทั้ง 2023-2025 อยู่แล้ว แต่รวมทุกไฟล์ที่เจอไว้กันตกหล่น
    candidate_files = find_all_files("*master_all_8_stocks_financials*.csv")
    train_test_files = find_all_files("*financials_train*.csv") + find_all_files("*financials_test*.csv")

    if not candidate_files and not train_test_files:
        print("❌ ไม่พบไฟล์งบการเงิน")
        return

    frames = []
    for fp in (candidate_files or train_test_files):
        try:
            frames.append(read_csv_smart(fp))
        except Exception as e:
            print(f"⚠️ อ่านไฟล์ {fp} ไม่ได้: {e}")

    if not frames:
        print("❌ ไม่สามารถอ่านไฟล์งบการเงินได้เลย")
        return

    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()

    stock_col = [c for c in df.columns if 'Stock' in c][0]
    # หาปี ค.ศ. โดยตรงก่อน ถ้าไม่เจอค่อย fallback ไปแปลงจาก พ.ศ.
    year_ad_col = [c for c in df.columns if 'ค.ศ' in c or c.lower().strip() == 'year']
    year_be_col = [c for c in df.columns if 'พ.ศ' in c]

    df['stock_symbol'] = df[stock_col].astype(str).str.strip().str.upper().str.replace('.BK', '', regex=False)

    def clean_year_generic(val):
        try:
            y = int(float(str(val).split('.')[0].strip()))
            return y - 543 if y > 2500 else y
        except Exception:
            return None

    if year_ad_col:
        df['year_clean'] = df[year_ad_col[0]].apply(clean_year_generic)
    elif year_be_col:
        df['year_clean'] = df[year_be_col[0]].apply(clean_year_generic)
    else:
        print("❌ ไม่พบคอลัมน์ปีในไฟล์งบการเงิน")
        return

    df = df.drop_duplicates(subset=['stock_symbol', 'year_clean'], keep='first')

    filtered_df = df[
        (df['stock_symbol'].isin(TARGET_STOCKS)) &
        (df['year_clean'].isin(TARGET_YEARS))
    ].copy()

    # แปลงคอลัมน์ตัวเลข (ที่มี comma/% ปนอยู่) ให้เป็น float ทั้งหมด
    non_numeric_cols = {stock_col, 'stock_symbol'}
    if year_ad_col:
        non_numeric_cols.add(year_ad_col[0])
    if year_be_col:
        non_numeric_cols.add(year_be_col[0])

    for col in filtered_df.columns:
        if col in non_numeric_cols or col == 'year_clean':
            continue
        try:
            filtered_df[col] = clean_numeric_series(filtered_df[col])
        except Exception:
            pass  # คอลัมน์ที่แปลงไม่ได้ ปล่อยไว้เป็น string เดิม

    rename_mapping = {
        'stock_symbol': 'ticker',
        'year_clean': 'year',
        'Total Revenue': 'total_revenue',
        'Operating Revenue': 'operating_revenue',
        'COGS': 'cogs',
        'Gross Profit': 'gross_profit',
        'EBIT': 'ebit',
        'EBITDA': 'ebitda',
        'Gross Margin (%)': 'gross_margin',
        'Operating Margin (%)': 'operating_margin',
        'EBITDA Margin (%)': 'ebitda_margin',
        'Net Margin (%)': 'net_margin',
        'ROE (%)': 'roe',
        'ROA (%)': 'roa',
        'D/E (x)': 'de_ratio',
        'Current Ratio (x)': 'current_ratio',
        'Quick Ratio (x)': 'quick_ratio',
        'Interest Coverage (x)': 'interest_coverage',
        'OCF_to_NI': 'ocf_to_ni',
        'Free Cash Flow': 'free_cash_flow',
        'Operating CF': 'operating_cash_flow',
        'Capital Expenditure': 'capex',
        'Total Assets': 'total_assets',
        'Total Equity': 'total_equity',
        'Total Liabilities': 'total_liabilities',
        'Current Assets': 'current_assets',
        'Current Liabilities': 'current_liabilities',
        'Cash Equivalent': 'cash_and_equivalents',
        'Inventory': 'inventory',
        'Accounts Receivable': 'accounts_receivable',
        'Accounts Payable': 'accounts_payable',
        'Fixed Assets': 'fixed_assets',
        'INT': 'interest_expense',
        'EPS': 'eps',
        'NI (Parent)': 'net_income',
    }

    save_df = filtered_df.rename(columns=rename_mapping)
    keep_cols = ['ticker', 'year'] + [v for v in rename_mapping.values() if v not in ('ticker', 'year') and v in save_df.columns]
    save_df = save_df[keep_cols].sort_values(['ticker', 'year']).reset_index(drop=True)

    # [v17 / Blueprint D2] ใช้ ROE / ROA จากไฟล์ของทีมข้อมูล "ทุกแถว" ไม่คำนวณใหม่
    # (เดิม FIX-D1 คำนวณใหม่จากงบ — ยกเลิกตามคำสั่งเจ้าของงาน: ทีมข้อมูลคำนวณค่าเหล่านี้มาแล้ว)
    # ทุกหน้าของ Dashboard อ่านคอลัมน์ roe / roa จากตารางนี้ จึงเห็นค่าเดียวกันทั้งระบบ
    save_df['roe_reported'] = save_df['roe']
    save_df['roa_reported'] = save_df['roa']

    write_table(save_df, 'stock_financials', engine)
    print(f"✅ นำเข้าข้อมูลงบการเงินสำเร็จ: {len(save_df)} แถว "
          f"(ครอบคลุม {save_df['ticker'].nunique()} หุ้น, ปี {sorted(save_df['year'].unique())})")


def normalize_colname(c):
    """ทำให้ชื่อคอลัมน์เทียบกันง่าย ไม่สนตัวพิมพ์เล็ก/ใหญ่ ช่องว่าง หรือ underscore
    (เช่น 'Volume_Avg20', 'volume avg', 'VolumeAvg' ถือว่าเป็นชื่อเดียวกัน)"""
    return c.strip().lower().replace(' ', '').replace('_', '')


# แผนที่ชื่อคอลัมน์ปลายทาง (canonical) -> รายชื่อ alias ที่อาจเจอได้จากไฟล์ Dataset หลายเวอร์ชัน
# รองรับทั้งไฟล์เก่า (stock_cleaned_data_2016_2025.csv) และไฟล์ใหม่ (คอลัมน์ Ticker/Date/Volume_Avg20/ADX14 ฯลฯ)
PRICE_COLUMN_ALIASES = {
    'ticker': ['ticker', 'stock', 'symbol'],
    'date': ['date', 'datetime', 'วันที่'],
    'open': ['open'],
    'high': ['high'],
    'low': ['low'],
    'close': ['close'],
    'volume': ['volume'],
    'EMA20': ['ema20'],
    'EMA50': ['ema50'],
    'Volume Avg': ['volumeavg', 'volumeavg20'],
    'RSI14': ['rsi14', 'rsi'],
    'MACD': ['macd'],
    'ADX': ['adx', 'adx14'],
    # คอลัมน์เสริมที่มีเฉพาะในไฟล์เวอร์ชันใหม่ (ยังไม่มีโมดูลไหนใช้ตอนนี้ แต่เก็บไว้เผื่ออนาคต)
    'adj_close': ['adjclose'],
    'macd_signal': ['macdsignal'],
    'macd_hist': ['macdhist'],
}


def import_price_data(engine):
    print("\n--- 2. กำลังประมวลผลไฟล์ราคาและดัชนีเทคนิคอล (Stock Prices) ---")
    file_path = find_file("*stock_cleaned*.csv") or find_file("*stock_data*.csv")
    if not file_path:
        print("❌ ไม่พบไฟล์ราคาหุ้น")
        return

    df = read_csv_smart(file_path)
    df.columns = df.columns.str.strip()
    print(f"   ใช้ไฟล์: {file_path}")

    # จับคู่ชื่อคอลัมน์จริงในไฟล์ -> ชื่อคอลัมน์มาตรฐาน (canonical) โดยไม่สนตัวพิมพ์เล็ก/ใหญ่หรือ underscore
    norm_to_original = {normalize_colname(c): c for c in df.columns}
    rename_map = {}
    for canonical, aliases in PRICE_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in norm_to_original:
                rename_map[norm_to_original[alias]] = canonical
                break
    df = df.rename(columns=rename_map)

    missing_required = [c for c in ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume',
                                     'EMA20', 'EMA50', 'RSI14', 'MACD', 'ADX'] if c not in df.columns]
    if missing_required:
        print(f"❌ ไฟล์ราคาหุ้นขาดคอลัมน์ที่จำเป็น: {missing_required} (เจอคอลัมน์จริง: {list(df.columns)})")
        return

    df['clean_ticker'] = df['ticker'].astype(str).str.strip().str.upper().str.replace('.BK', '', regex=False)
    df['parsed_date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=False)

    if df['parsed_date'].notna().any() and df['parsed_date'].dt.year.max() > 2500:
        df['parsed_date'] = df['parsed_date'].apply(
            lambda x: x.replace(year=x.year - 543) if pd.notnull(x) and x.year > 2500 else x
        )

    mask_stock = df['clean_ticker'].isin(TARGET_STOCKS)
    mask_date = (df['parsed_date'] >= PRICE_START_DATE) & (df['parsed_date'] <= PRICE_END_DATE)

    filtered_df = df[mask_stock & mask_date].copy()

    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'EMA20', 'EMA50', 'Volume Avg',
                     'RSI14', 'MACD', 'ADX', 'adj_close', 'macd_signal', 'macd_hist']
    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = clean_numeric_series(filtered_df[col])

    filtered_df = filtered_df.sort_values(by=['clean_ticker', 'parsed_date']).reset_index(drop=True)
    filtered_df['date'] = filtered_df['parsed_date'].dt.strftime('%Y-%m-%d')
    filtered_df['ticker'] = filtered_df['clean_ticker']
    filtered_df = filtered_df.drop(columns=['clean_ticker', 'parsed_date'], errors='ignore')

    # ถ้าไฟล์ไม่มีคอลัมน์ Volume Avg มาให้ตรงๆ (เช่นไฟล์ใหม่บางเวอร์ชัน) คำนวณ rolling 20 วันเอาเองจาก volume จริง
    if 'Volume Avg' not in filtered_df.columns:
        filtered_df = filtered_df.sort_values(['ticker', 'date'])
        filtered_df['Volume Avg'] = filtered_df.groupby('ticker')['volume'].transform(
            lambda s: s.rolling(20, min_periods=1).mean()
        )

    write_table(filtered_df, 'stock_daily_prices', engine)

    if len(filtered_df) > 0:
        print(f"✅ นำเข้าข้อมูลราคาหุ้นสำเร็จ: {len(filtered_df)} แถว "
              f"(ครอบคลุม {filtered_df['ticker'].nunique()} หุ้น, "
              f"วันที่ {filtered_df['date'].min()} ถึง {filtered_df['date'].max()})")
    else:
        print("⚠️ ไม่พบแถวที่ตรงตามเงื่อนไข ลองตรวจตัวอย่างข้อมูล:")
        print("ตัวอย่าง Ticker ในไฟล์:", df['ticker'].unique()[:5])
        print("ตัวอย่าง Date ในไฟล์:", df['date'].head(3).tolist())


def import_risk_metrics(engine):
    print("\n--- 3. กำลังประมวลผลไฟล์ Risk Metrics (Beta / Volatility / Max Drawdown) ---")
    file_path = find_file("*stock_risk_metrics*.csv")
    if not file_path:
        print("❌ ไม่พบไฟล์ stock_risk_metrics")
        return

    df = read_csv_smart(file_path)
    df.columns = df.columns.str.strip()

    stock_col = [c for c in df.columns if c.lower() in ['stock', 'ticker', 'symbol']][0]
    df['ticker'] = df[stock_col].astype(str).str.strip().str.upper().str.replace('.BK', '', regex=False)

    # [FIX-D3] เลือกคอลัมน์ Beta แบบชื่อตรงก่อน (ไฟล์ใหม่จาก compute_beta.py มีทั้ง "Beta" และ "Downside Beta")
    def _pick(exact, contains, exclude=()):
        for c in df.columns:
            if c.lower() == exact:
                return c
        for c in df.columns:
            if contains in c.lower() and not any(x in c.lower() for x in exclude):
                return c
        return None

    beta_col = _pick('beta', 'beta', exclude=('downside', 'source', 'window', 'r2'))
    vol_col = _pick('volatility (p.a.)', 'volatility')
    dd_col = _pick('max drawdown', 'drawdown')

    out = pd.DataFrame({
        'ticker': df['ticker'],
        'beta': clean_numeric_series(df[beta_col]),
        'volatility_pct': clean_numeric_series(df[vol_col]),
        'max_drawdown_pct': clean_numeric_series(df[dd_col]),
    })
    # คอลัมน์เสริมจาก compute_beta.py (ถ้ามี) — ไฟล์เดิมไม่มีคอลัมน์เหล่านี้ก็ยังนำเข้าได้ตามปกติ
    for src, dst, numeric in [('Downside Beta', 'downside_beta', True), ('Beta R2', 'beta_r2', True),
                              ('Beta Window', 'beta_window', False), ('Beta Source', 'beta_source', False)]:
        if src in df.columns:
            out[dst] = clean_numeric_series(df[src]) if numeric else df[src].astype(str).values
    out = out[out['ticker'].isin(TARGET_STOCKS)].drop_duplicates(subset=['ticker']).reset_index(drop=True)

    write_table(out, 'stock_risk_static', engine)
    print(f"✅ นำเข้าข้อมูลความเสี่ยงสำเร็จ: {len(out)} หุ้น")


def import_valuation_params(engine):
    """[v17 / Blueprint D8] WACC และ Target P/E รายหุ้น รายปี จาก Dataset/valuation_params_2023_2025.csv
    ที่มา: Damodaran Cost of capital / PE by industry, Emerging Markets — ไฟล์ปัจจุบัน (ม.ค. 2026 = สิ้นปี 2025)
    และไฟล์ย้อนหลังใน Archive (ม.ค. 2024 = สิ้นปี 2023, ม.ค. 2025 = สิ้นปี 2024)
    [v17.2] คอลัมน์ Fiscal Year: ปีงบที่ใช้ค่านั้น (ไม่มีคอลัมน์นี้ = ถือเป็นปี 2025 เหมือนไฟล์เดิม)
    แปลง WACC จากดอลลาร์เป็นบาทด้วยส่วนต่างเงินเฟ้อ (ดูคอลัมน์ Source ในไฟล์)"""
    print("\n--- 4. กำลังประมวลผลไฟล์ WACC / Target P/E (valuation_params) ---")
    file_path = find_file("*valuation_params*.csv")
    if not file_path:
        print("❌ ไม่พบไฟล์ valuation_params_*.csv (ต้องมีใน Dataset/)")
        return
    df = read_csv_smart(file_path)
    df.columns = df.columns.str.strip()
    out = pd.DataFrame({
        'ticker': df['Stock'].astype(str).str.strip().str.upper(),
        'fiscal_year': (clean_numeric_series(df['Fiscal Year']) if 'Fiscal Year' in df.columns
                        else pd.Series(2025, index=df.index)).astype(int),
        'damodaran_industry': df['Damodaran Industry'].astype(str),
        'industry_firms': clean_numeric_series(df['Industry Firms (EM)']),
        'wacc_usd_pct': clean_numeric_series(df['WACC USD (%)']),
        'wacc_thb_pct': clean_numeric_series(df['WACC THB (%)']),
        'target_pe': clean_numeric_series(df['Target P/E (x)']),
        'us_inflation_pct': clean_numeric_series(df['US Expected Inflation (%)']),
        'th_inflation_pct': clean_numeric_series(df['TH Expected Inflation (%)']),
        'pe_basis': df['P/E Basis'].astype(str),
        'data_date': df['Data Date'].astype(str),
        'source': df['Source'].astype(str),
    })
    out = (out[out['ticker'].isin(TARGET_STOCKS)].drop_duplicates(subset=['ticker', 'fiscal_year'])
              .sort_values(['ticker', 'fiscal_year']).reset_index(drop=True))
    write_table(out, 'valuation_params', engine)
    years = sorted(out['fiscal_year'].unique())
    print(f"✅ นำเข้า WACC / Target P/E สำเร็จ: {out['ticker'].nunique()} หุ้น × ปี {years} (ไฟล์ {file_path})")


def import_all(engine):
    """นำเข้าทุกไฟล์ใน Dataset ตามลำดับ (ใช้ร่วมกันทั้ง __main__, common.build_database และ run_tests)"""
    import_financial_data(engine)
    import_price_data(engine)
    import_risk_metrics(engine)
    import_valuation_params(engine)


if __name__ == '__main__':
    engine = create_engine(f'sqlite:///{DB_NAME}')
    import_all(engine)
    print("\n" + "=" * 60)
    print("นำเข้าข้อมูลทั้งหมดเสร็จสมบูรณ์ -> รันต่อด้วย: python calculate_scores.py")
