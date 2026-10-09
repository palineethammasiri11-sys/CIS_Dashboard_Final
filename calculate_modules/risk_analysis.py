"""
calculate_modules/risk_analysis.py
--------------------------------------
สูตรคำนวณโมดูล "Risk Analysis" (🛡️) — คู่กับ pages_content/risk_analysis.py

=== DATA CONTRACT (key เดิมครบ + key ใหม่) ===
key เดิม: risk_score, volatility, volatility_calc, max_drawdown, var_95, beta, sharpe_ratio, sortino_ratio,
          cvar_95, psr, recovery_days, risk_free_rate_annual,
          risk_dim_tail, risk_dim_drawdown, risk_dim_volatility, risk_dim_market, risk_dim_quality,
          beta_verified, beta_note
key ใหม่: volatility_static, max_drawdown_static, risk_dims_used, risk_data_note

=== CHANGELOG (รอบแก้ "ตัวเลขต้องถูกก่อน") ===
- [FIX-R1] Volatility ใช้ค่าที่คำนวณจากราคาจริงใน Dataset (std ผลตอบแทนรายวัน x sqrt(252)) แทนค่าใน
  stock_risk_metrics.csv — เดิมใช้ค่าจาก CSV แต่ Drawdown/VaR/CVaR/Sharpe คำนวณจากราคาจริง ทำให้ตัวเลข
  ในหน้าเดียวกันมาจากคนละแหล่ง/คนละช่วงเวลา ค่า CSV ยังเก็บไว้ที่ volatility_static เพื่อเทียบ
- [FIX-R2] Max Drawdown ใน CSV = -29.36% เท่ากันทั้ง 8 หุ้น (ข้อมูลต้นทางผิด) — ใช้ค่าจากราคาจริงเหมือนเดิม
  และเก็บค่า CSV ไว้ที่ max_drawdown_static เพื่อรายงานเป็น data-quality finding
- [FIX-R3] ไม่มี Beta → คืน None (เดิมใส่ 1.0 ปลอม) Beta จาก CSV ยังไม่ยืนยันที่มา (beta_verified=False)
  เพราะ Dataset ไม่มีดัชนี SET ให้คำนวณเอง
- [FIX-R4] ไม่มี PSR → มิติ quality = None (เดิมใส่ 50 ปลอม)
- [FIX-R6] ถ้า stock_risk_metrics.csv มาจาก compute_beta.py (มีคอลัมน์ Beta Source) → beta_verified = True
  และแสดงที่มา/ช่วงข้อมูลของ Beta พร้อม Downside Beta (Ang, Chen & Xing 2006) ถ้าเป็นไฟล์เดิม → ยังเตือนเหมือนเดิม
- [FIX-R7] ช่วงข้อมูลความเสี่ยง = 3 ปีล่าสุด (เดิมใช้ราคาทั้งหมดในไฟล์ ซึ่งตอนนี้ยาว 10 ปี)
  ให้ Volatility / Max Drawdown / VaR / CVaR / Sharpe / Sortino / PSR / กราฟ Rolling ใช้ช่วงเดียวกับ Beta
  ตาม Daves, Ehrhardt & Kunkel (2000) ที่แนะนำผลตอบแทนรายวันและช่วงไม่เกิน 3 ปี
  TRUE ใช้ข้อมูลตั้งแต่ 3 มี.ค. 2023 (หลังควบรวม TRUE-DTAC) เหมือน compute_beta.py
  และตัดแถววันหยุดปลอม (Volume = 0 และ High = Low = Close) ที่ทำให้ผลตอบแทน 0% เกินจริง
  ปรับช่วงได้ที่ RISK_WINDOW_YEARS (ตั้ง None = ใช้ข้อมูลทั้งหมดแบบเดิม)
- [v17] เพิ่ม calmar_ratio, annual_return (ช่วง 3 ปีเดียวกัน), risk_window_start/end, recovered และ
  risk_breakdown (ที่มาของคะแนน 5 มิติ) ให้หน้าจออ่านค่าจากหลังบ้านอย่างเดียว ไม่คำนวณซ้ำ (Blueprint R3, R6, R8)
- [FIX-R5] Risk Score คำนวณจากมิติที่มีจริง (ถ่วงน้ำหนักใหม่) ต้องมีอย่างน้อย 4 ใน 5 มิติ
  และเลิก clip 25-92 → ช่วง 0-100
"""

import math
import numpy as np
import pandas as pd
from calculate_modules.common import clean_float, RISK_FREE_RATE

RISK_FREE_RATE_ANNUAL = RISK_FREE_RATE   # [FIX-R8] 1.66% จาก ThaiBMA (เดิม 2.0% ที่ทีมกำหนดเอง) ใช้ค่าเดียวกับ Fair Value

# FIX-R7: ช่วงข้อมูลที่ใช้วัดความเสี่ยง (ให้ตรงกับ compute_beta.py → BETA_WINDOW_YEARS, TICKER_START_OVERRIDE)
RISK_WINDOW_YEARS = 3
RISK_TICKER_START_OVERRIDE = {"TRUE": "2023-03-03"}   # หลังควบรวม TRUE-DTAC

RISK_WEIGHT_TAIL = 0.30
RISK_WEIGHT_DRAWDOWN = 0.25
RISK_WEIGHT_VOLATILITY = 0.20
RISK_WEIGHT_MARKET = 0.15
RISK_WEIGHT_QUALITY = 0.10
MIN_RISK_DIMS = 4

BETA_VERIFIED = False
BETA_UNVERIFIED_NOTE = "⚠️ Beta มาจาก stock_risk_metrics.csv ยังไม่ยืนยันแหล่งที่มา (Dataset ไม่มีดัชนี SET ให้คำนวณเอง)"


def _risk_window(df_price_ticker):
    """FIX-R7: ตัดข้อมูลให้เหลือช่วงที่ใช้วัดความเสี่ยง + ตัดแถววันหยุดปลอม แล้วคืน (df, คำอธิบายช่วง)"""
    df = df_price_ticker.sort_values(by='date').reset_index(drop=True).copy()
    df['date'] = pd.to_datetime(df['date'])
    if {'volume', 'high', 'low', 'close'}.issubset(df.columns):
        fake = (pd.to_numeric(df['volume'], errors='coerce') == 0) & (df['high'] == df['low']) & (df['low'] == df['close'])
        df = df[~fake]
    if df.empty or RISK_WINDOW_YEARS is None:
        return df.reset_index(drop=True), "ข้อมูลทั้งหมด"
    end = df['date'].max()
    start = end - pd.DateOffset(years=RISK_WINDOW_YEARS) + pd.Timedelta(days=1)
    note = f"{RISK_WINDOW_YEARS} ปีล่าสุด"
    ticker = str(df['ticker'].iloc[0]).upper() if 'ticker' in df.columns else ''
    if ticker in RISK_TICKER_START_OVERRIDE and pd.Timestamp(RISK_TICKER_START_OVERRIDE[ticker]) > start:
        start = pd.Timestamp(RISK_TICKER_START_OVERRIDE[ticker])
        note = f"ตั้งแต่ {start.date()} (หลังควบรวม)"
    df = df[df['date'] >= start].reset_index(drop=True)
    if not df.empty:
        note += f" ({df['date'].min().date()} ถึง {df['date'].max().date()})"
    return df, note


def _clean_price_series(df, price_col='close'):
    out = df.copy()
    out[price_col] = pd.to_numeric(out[price_col], errors='coerce')
    out = out.dropna(subset=[price_col]).reset_index(drop=True)
    return out


def _compute_cvar(returns, confidence=0.95):
    r = returns.dropna()
    if len(r) < 20:
        return None
    cutoff = np.percentile(r, (1 - confidence) * 100)
    tail = r[r <= cutoff]
    if tail.empty:
        return None
    return round(float(abs(tail.mean()) * 100), 2)


def _compute_var_historical(returns, confidence=0.95):
    r = returns.dropna()
    if len(r) < 20:
        return None
    cutoff = np.percentile(r, (1 - confidence) * 100)
    return round(float(abs(cutoff) * 100), 2)


def _compute_psr(returns, sr_benchmark=0.0):
    r = returns.dropna()
    n = len(r)
    if n < 30 or r.std() == 0:
        return None
    sr_hat = r.mean() / r.std()
    skew = r.skew()
    kurt = r.kurtosis() + 3
    denom_sq = 1 - skew * sr_hat + ((kurt - 1) / 4) * (sr_hat ** 2)
    if denom_sq <= 0:
        return None
    z = (sr_hat - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(denom_sq)
    return round(float(0.5 * (1 + math.erf(z / math.sqrt(2)))) * 100, 1)


def _compute_recovery_days(df):
    if len(df) < 2:
        return None
    cum_max = df['close'].cummax()
    drawdown = (df['close'] - cum_max) / cum_max
    if drawdown.isna().all():
        return None
    trough_idx = drawdown.idxmin()
    peak_value = cum_max.loc[trough_idx]
    trough_date = df.loc[trough_idx, 'date']
    recovered = df[(df['date'] > trough_date) & (df['close'] >= peak_value)]
    if recovered.empty:
        return None
    return int((recovered.iloc[0]['date'] - trough_date).days)


def _recovery_penalty(recovery_days):
    if recovery_days is None:
        return 10.0
    if recovery_days > 365:
        return 7.0
    if recovery_days > 180:
        return 3.0
    return 0.0


def _static_value(risk_static_row, col):
    if risk_static_row is None or risk_static_row.empty:
        return None
    return clean_float(risk_static_row.iloc[0].get(col), default=None)


def _static_text(risk_static_row, col):
    if risk_static_row is None or risk_static_row.empty or col not in risk_static_row.columns:
        return None
    v = risk_static_row.iloc[0].get(col)
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() in ('', 'nan') else str(v)


def _beta_provenance(risk_static_row):
    """(beta_verified, beta_note) — verified เมื่อ Beta คำนวณเองเทียบดัชนี SET ด้วย compute_beta.py"""
    source = _static_text(risk_static_row, 'beta_source')
    window = _static_text(risk_static_row, 'beta_window')
    if source and 'SET' in source.upper():
        return True, f"Beta {source} ช่วง {window}" if window else f"Beta {source}"
    return BETA_VERIFIED, BETA_UNVERIFIED_NOTE if not BETA_VERIFIED else None


def _r(v, d=1):
    return None if v is None or pd.isna(v) else round(float(v), d)


def calculate_risk_module(df_price_ticker, risk_static_row):
    """ตัวชี้วัดความเสี่ยง 5 มิติของหุ้น 1 ตัว"""
    df, risk_window_note = _risk_window(df_price_ticker)            # FIX-R7
    df = _clean_price_series(df, 'close')

    beta = _static_value(risk_static_row, 'beta')                     # FIX-R3
    downside_beta = _static_value(risk_static_row, 'downside_beta')    # FIX-R6
    beta_r2 = _static_value(risk_static_row, 'beta_r2')
    beta_verified, beta_note = _beta_provenance(risk_static_row)
    vol_static = _static_value(risk_static_row, 'volatility_pct')
    dd_static = _static_value(risk_static_row, 'max_drawdown_pct')

    if len(df) < 2:
        return {
            'risk_score': None, 'volatility': None, 'volatility_calc': None,
            'max_drawdown': None, 'var_95': None, 'beta': _r(beta, 2),
            'sharpe_ratio': None, 'sortino_ratio': None, 'cvar_95': None,
            'psr': None, 'recovery_days': None, 'risk_free_rate_annual': RISK_FREE_RATE_ANNUAL,
            'risk_dim_tail': None, 'risk_dim_drawdown': None, 'risk_dim_volatility': None,
            'risk_dim_market': None, 'risk_dim_quality': None,
            'beta_verified': beta_verified, 'beta_note': beta_note,
            'downside_beta': _r(downside_beta, 2), 'beta_r2': _r(beta_r2, 3),
            'volatility_static': vol_static, 'max_drawdown_static': dd_static,
            'risk_dims_used': 0, 'risk_data_note': 'ข้อมูลราคาไม่พอ',
            'risk_window': risk_window_note,
        }

    df['returns'] = df['close'].pct_change()
    daily_vol = df['returns'].std()
    annual_vol = daily_vol * np.sqrt(252) * 100                       # FIX-R1: ใช้ค่าจากราคาจริงเสมอ

    cum_max = df['close'].cummax()
    max_dd = abs(((df['close'] - cum_max) / cum_max).min()) * 100     # FIX-R2

    var_95 = _compute_var_historical(df['returns'])
    cvar_95 = _compute_cvar(df['returns'])

    rf_daily = RISK_FREE_RATE_ANNUAL / 252
    excess = df['returns'] - rf_daily
    n_ret = len(df['returns'].dropna())
    if pd.isna(daily_vol) or n_ret < 2:
        sharpe = None
    elif daily_vol > 0:
        sharpe = round(float((excess.mean() * 252) / (daily_vol * np.sqrt(252))), 2)
    else:
        sharpe = 0.0

    downside = np.minimum(0, df['returns'] - rf_daily).dropna()
    dd_dev = np.sqrt(np.mean(downside ** 2)) if len(downside) > 1 else None
    if dd_dev is None or pd.isna(dd_dev):
        sortino = None
    elif dd_dev > 0:
        sortino = round(float((excess.mean() * 252) / (dd_dev * np.sqrt(252))), 2)
    else:
        sortino = 0.0

    psr = _compute_psr(df['returns'])
    recovery_days = _compute_recovery_days(df)
    # v17: Calmar คำนวณที่หลังบ้านด้วยช่วง 3 ปีเดียวกับตัวชี้วัดอื่น (เดิมหน้าจอคิดเองจากข้อมูล 11 ปี)
    annual_return = float(df['returns'].mean() * 252 * 100) if n_ret >= 2 else None
    calmar = round(annual_return / max_dd, 2) if (annual_return is not None and max_dd and max_dd > 0) else None

    tail_input = cvar_95 if cvar_95 is not None else var_95
    dims = {
        'tail': (float(np.clip(tail_input * 10, 5, 95)) if tail_input is not None else None, RISK_WEIGHT_TAIL),
        'drawdown': (float(np.clip(max_dd * 1.5 + _recovery_penalty(recovery_days), 5, 95))
                     if pd.notna(max_dd) else None, RISK_WEIGHT_DRAWDOWN),
        'volatility': (float(np.clip(annual_vol * 1.3, 5, 95)) if pd.notna(annual_vol) else None,
                       RISK_WEIGHT_VOLATILITY),
        'market': (float(np.clip(beta * 40, 5, 95)) if beta is not None else None, RISK_WEIGHT_MARKET),
        'quality': (float(np.clip(100 - psr, 5, 95)) if psr is not None else None,   # FIX-R4
                    RISK_WEIGHT_QUALITY),
    }

    avail = [(v, w) for v, w in dims.values() if v is not None]
    if len(avail) >= MIN_RISK_DIMS:                                    # FIX-R5
        risk_index = sum(v * w for v, w in avail) / sum(w for _, w in avail)
        risk_score = round(float(np.clip(100 - risk_index, 0, 100)), 1)
    else:
        risk_score = None
    missing = [k for k, (v, _) in dims.items() if v is None]

    # v17 / D13: ที่มาของคะแนน 5 มิติ (ค่าจริง → คะแนนอันตราย → น้ำหนักที่ใช้จริง → หักคะแนนไปเท่าไร)
    w_total = sum(w for _, w in avail) or 1.0
    real_values = {'tail': cvar_95 if cvar_95 is not None else var_95, 'drawdown': max_dd,
                   'volatility': annual_vol, 'market': beta, 'quality': psr}
    names = {'tail': 'ขาดทุนในวันแย่ ๆ (CVaR 95%)', 'drawdown': 'การร่วงลึกสุด (Max Drawdown)',
             'volatility': 'ความผันผวนต่อปี', 'market': 'ความไวต่อตลาด (Beta)',
             'quality': 'ความสม่ำเสมอของผลตอบแทน (100 − PSR)'}
    breakdown = []
    for k, (v, w) in dims.items():
        w_used = (w / w_total) if v is not None else None
        breakdown.append({'dim': k, 'name': names[k], 'real_value': _r(real_values[k], 2),
                          'hazard': _r(v), 'weight_nominal': w, 'weight_used': None if w_used is None else round(w_used, 4),
                          'deduction': None if v is None else round(v * w_used, 1)})

    return {
        'risk_score': risk_score,
        'volatility': _r(annual_vol),
        'volatility_calc': _r(annual_vol),
        'max_drawdown': _r(max_dd),
        'var_95': _r(var_95, 2),
        'beta': _r(beta, 2),
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'cvar_95': cvar_95,
        'psr': psr,
        'recovery_days': recovery_days,
        'risk_free_rate_annual': RISK_FREE_RATE_ANNUAL,
        'risk_dim_tail': _r(dims['tail'][0]),
        'risk_dim_drawdown': _r(dims['drawdown'][0]),
        'risk_dim_volatility': _r(dims['volatility'][0]),
        'risk_dim_market': _r(dims['market'][0]),
        'risk_dim_quality': _r(dims['quality'][0]),
        'beta_verified': beta_verified,
        'beta_note': beta_note,
        'downside_beta': _r(downside_beta, 2),
        'beta_r2': _r(beta_r2, 3),
        'volatility_static': vol_static,
        'max_drawdown_static': dd_static,
        'risk_dims_used': len(avail),
        'risk_data_note': ('ไม่มีข้อมูลมิติ: ' + ', '.join(missing)) if missing else '',
        'risk_window': risk_window_note,
        'risk_window_start': str(df['date'].min().date()), 'risk_window_end': str(df['date'].max().date()),
        'annual_return': _r(annual_return, 2), 'calmar_ratio': calmar,
        'recovered': recovery_days is not None,
        'recovery_penalty': _recovery_penalty(recovery_days),
        'risk_breakdown': breakdown,
    }


def build_risk_rolling_history(df_price_ticker):
    """rolling 30 วันของ Volatility และ Drawdown ในช่วงเดียวกับตัวชี้วัดความเสี่ยง (FIX-R7)"""
    df, _ = _risk_window(df_price_ticker)
    df = _clean_price_series(df, 'close')
    if len(df) < 30:
        return pd.DataFrame(columns=['date', 'rolling_vol_30d', 'drawdown_pct'])
    df['returns'] = df['close'].pct_change()
    df['rolling_vol_30d'] = df['returns'].rolling(30).std() * np.sqrt(252) * 100
    cum_max = df['close'].cummax()
    df['drawdown_pct'] = (df['close'] - cum_max) / cum_max * 100
    out = df[['date', 'rolling_vol_30d', 'drawdown_pct']].dropna(subset=['rolling_vol_30d']).copy()
    return out.set_index('date').resample('W').last().dropna().reset_index()
