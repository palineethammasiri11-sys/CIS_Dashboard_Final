"""
calculate_modules/fair_value.py — v17 (Blueprint ฉบับที่ 2)
========================================================================
สูตรคำนวณโมดูล "Fair Value" — คู่กับ pages_content/fair_value.py

=== DATA CONTRACT (key หลัก) ===
calculate_valuation_module(df_fin_ticker, current_price, ticker, beta=None, params=None) คืน dict:
    valuation_score, fair_value, dcf_fair_value, pe_fair_value, margin_of_safety, price_to_value,
    dcf_score, pe_score, dcf_mos, pe_mos, method_gap_pct, confidence_level, confidence_reason,
    valuation_status, warning_message, pe_ratio, pb_ratio, market_cap_mb, eps, fcf_base, net_debt_used,
    wacc_used, terminal_growth_used, target_pe_used, damodaran_industry, params_source, params_date,
    shares_outstanding, book_value_per_share,
    + Market Expectation: ke_capm, beta_used, beta_adjusted, pb_current, roe_hist_avg, roe_latest,
      roe_hist_years, implied_roe, roe_gap, expectation_label, expectation_color, expectation_note,
      fcf_quality_warning, fcf_to_ni

=== v17 ===
- [D8] WACC และ Target P/E มาจาก Dataset/valuation_params_2023_2025.csv (Damodaran, ตลาดเกิดใหม่,
       ข้อมูล ณ สิ้นปี 2025; WACC แปลงเป็นบาทด้วยส่วนต่างเงินเฟ้อ) ส่งเข้ามาทาง params
       g = 2% ทุกหุ้น (จุดกลางกรอบเป้าหมายเงินเฟ้อ ธปท. 1-3%) และตัดส่วนเพิ่ม 1.5% ในปีแรกออก
- [D7] คะแนนแต่ละวิธี = 50 + Margin of Safety ของวิธีนั้น ตัดที่ 0-100
       (มูลค่าที่ใช้คิดคะแนนถูกจำกัดไว้ที่ 65%-185% ของราคาเหมือนเดิม) → 50 = ราคาเท่ามูลค่าพอดี
       คะแนนรวม = DCF × 55% + P/E × 45%; วิธีที่คำนวณไม่ได้เพราะขาดทุนนับ 0 ในส่วนนั้น (D4)
- [D9] ความมั่นใจวัดจาก "สองวิธีให้ผลตรงกันแค่ไหน":
       สูง = มีทั้ง 2 วิธีและต่างกัน ≤ 25%; ปานกลาง = 25-50%; ต่ำ = > 50% หรือมีวิธีเดียว
       มีคำเตือน FCF สูงกว่ากำไรมาก → ลด 1 ระดับ (เส้น 25/50 เป็นการตัดสินใจของผู้ออกแบบ ไม่มีแหล่งอ้างอิง)
- [D2] Market Expectation ใช้ ROE จากไฟล์ (เดิมคำนวณ NI/Equity เอง)
- หนี้สุทธิ = หนี้สินรวม − เจ้าหนี้การค้า − เงินสด (FIX-F1 เดิม) — Dataset ไม่แยกหนี้ที่มีดอกเบี้ย
"""

import numpy as np
import pandas as pd
from calculate_modules.common import clean_float, RISK_FREE_RATE

# จำนวนหุ้นจดทะเบียน (Factsheet รายหุ้น เว็บไซต์ SET — ตรวจกับ กำไรสุทธิ ÷ EPS ใน Dataset แล้ว ต่างไม่เกินราว 1%)
SHARES_OUTSTANDING = {
    'ADVANC': 2974209736,
    'CCET':   10400000000,
    'DELTA':  12473816149,
    'HANA':   885366460,
    'JMART':  1458518485,
    'KCE':    1182429485,
    'THCOM':  1096000000,
    'TRUE':   34552100801,
}

STABLE_GROWTH = 0.020       # g: จุดกลางกรอบเป้าหมายเงินเฟ้อ ธปท. 1-3% (ใช้ทั้ง DCF และ Market Expectation)
DCF_WEIGHT, PE_WEIGHT = 0.55, 0.45
CLIP_LOW, CLIP_HIGH = 0.65, 1.85
CONF_HIGH_GAP, CONF_MED_GAP = 25.0, 50.0

MARKET_RF = RISK_FREE_RATE  # ThaiBMA: พันธบัตรรัฐบาลไทย 10 ปี ณ สิ้นปี 2568 = 1.66%
MARKET_ERP = 0.0630         # Damodaran Country Risk Premiums (ปรับปรุง 5 ม.ค. 2026 = ข้อมูล ณ สิ้นปี 2025): Thailand 6.30%
BLUME_W = 0.67              # Beta ปรับแบบ Blume (1971) = 0.67 × Beta + 0.33
FCF_NI_WARN = 1.5           # FCF เกินกำไรสุทธิปกติกี่เท่าจึงเตือน (ทีมกำหนด)
EXPECT_BANDS = [            # (ช่องว่าง ROE คาดหวัง − ROE จริง, ป้าย, สี) — เส้นเดิมของทีม
    (-2.0, "ราคาคาดหวังต่ำกว่าผลงานจริง", "#10B981"),
    (2.0, "ราคาสอดคล้องกับผลงานจริง", "#10B981"),
    (10.0, "ราคาคาดหวังสูงกว่าผลงานจริง", "#F59E0B"),
    (float("inf"), "ราคาคาดหวังสูงกว่าผลงานจริงมาก", "#EF4444"),
]

PARAMS_SOURCE_TEXT = ("Damodaran (2026) ค่าเฉลี่ยรายอุตสาหกรรม กลุ่มตลาดเกิดใหม่ ข้อมูล ณ สิ้นปี 2025 "
                      "(WACC แปลงจากดอลลาร์เป็นบาทด้วยส่วนต่างเงินเฟ้อ 2.0% / 2.5%)")
PARAMS_LIMITATIONS = [
    "เป็นค่าเฉลี่ยของตลาดเกิดใหม่ทั้งหมด ไม่ใช่ของไทยโดยตรง บริษัทไทยในกลุ่มที่ใช้มีน้อย",
    "การแปลงจากดอลลาร์ด้วยเงินเฟ้อให้ดอกเบี้ยไร้ความเสี่ยงโดยนัยราว 3.4% สูงกว่าพันธบัตรไทย 10 ปีจริง (1.66%) WACC จึงอาจสูงกว่าความจริง",
    "Target P/E คือค่าที่ตลาดให้กับกลุ่มนั้นตอนนี้ (มูลค่าตลาดรวม ÷ กำไรรวมของบริษัทที่มีกำไร) ไม่ใช่ราคาเป้าหมาย",
    "การจัดกลุ่มอุตสาหกรรมใช้ตามที่ Damodaran จัดไว้ (เช่น JMART = Computer Services)",
]


def _rnd(v, d=2):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), d)


def market_expectation(df_fin_ticker, current_price, ticker, beta=None):
    """ROE ที่ราคาปัจจุบันคาดหวัง เทียบ ROE จริง (ค่าในไฟล์) — กลับสมการ Residual Income แบบคงที่
       ROE ที่คาดหวัง = Ke + (P/B − 1) × (Ke − g) ÷ (1 + g)"""
    keys = ['ke_capm', 'beta_used', 'beta_adjusted', 'bvps', 'pb_current', 'roe_hist_avg', 'roe_latest',
            'roe_hist_years', 'implied_roe', 'roe_gap', 'expectation_label', 'expectation_color',
            'expectation_note', 'fcf_quality_warning', 'fcf_to_ni']
    out = {k: None for k in keys}
    shares = SHARES_OUTSTANDING.get(str(ticker).replace('.BK', '').strip().upper())
    if df_fin_ticker is None or df_fin_ticker.empty or not shares or current_price is None or current_price <= 0:
        out['expectation_note'] = 'ข้อมูลไม่พอสำหรับคำนวณ'
        return out
    g = df_fin_ticker.sort_values('year')
    roe_y = g['roe'].apply(clean_float, default=np.nan).dropna() / 100.0        # D2: ROE จากไฟล์
    equity_now = clean_float(g.iloc[-1].get('total_equity'), default=None)
    if roe_y.empty or equity_now is None or equity_now <= 0:
        out['expectation_note'] = 'ส่วนผู้ถือหุ้นติดลบหรือไม่มีข้อมูล ROE'
        return out

    b_raw = clean_float(beta, default=None)
    b_used = 1.0 if b_raw is None else b_raw
    b_adj = BLUME_W * b_used + (1 - BLUME_W)
    ke = MARKET_RF + b_adj * MARKET_ERP
    bvps = equity_now / shares
    pb = current_price / bvps
    implied = ke + (pb - 1) * (ke - STABLE_GROWTH) / (1 + STABLE_GROWTH)
    roe_avg = float(roe_y.mean())
    gap_pts = (implied - roe_avg) * 100
    label, color = next((lab, col) for thr, lab, col in EXPECT_BANDS if gap_pts <= thr)

    fcf = g['free_cash_flow'].apply(clean_float, default=np.nan).tail(2).mean()
    ni_candidates = [x for x in (roe_avg * equity_now, clean_float(g.iloc[-1].get('net_income'), default=None))
                     if x is not None and x > 0]
    ni_ref = ni_candidates[0] if ni_candidates else None
    fcf_ratio = (fcf / ni_ref) if (ni_ref and pd.notna(fcf) and fcf > 0) else None

    out.update({
        'ke_capm': round(ke * 100, 2), 'beta_used': round(b_used, 2), 'beta_adjusted': round(b_adj, 2),
        'bvps': round(bvps, 2), 'pb_current': round(pb, 2),
        'roe_hist_avg': round(roe_avg * 100, 1), 'roe_latest': round(float(roe_y.iloc[-1]) * 100, 1),
        'roe_hist_years': f"{int(g['year'].iloc[0])}-{int(g['year'].iloc[-1])}",
        'implied_roe': round(implied * 100, 1), 'roe_gap': round(gap_pts, 1),
        'expectation_label': label, 'expectation_color': color,
        'expectation_note': ('Beta ไม่มีข้อมูล ใช้ค่าตลาด 1.0' if b_raw is None else ''),
        'fcf_quality_warning': bool(fcf_ratio is not None and fcf_ratio > FCF_NI_WARN),
        'fcf_to_ni': None if fcf_ratio is None else round(float(fcf_ratio), 2),
    })
    return out


def method_score(raw_fair_value, current_price):
    """คะแนน 0-100 ของวิธีเดียว (D7): 50 + Margin of Safety โดยจำกัดมูลค่าไว้ 65%-185% ของราคาก่อนคิด
    คืน (score, mos_ที่ใช้คิดคะแนน, ถูกจำกัดหรือไม่)"""
    if raw_fair_value is None or current_price is None or current_price <= 0:
        return None, None, False
    lo, hi = current_price * CLIP_LOW, current_price * CLIP_HIGH
    fv = float(np.clip(raw_fair_value, lo, hi))
    clipped = bool(raw_fair_value < lo - 1e-4 or raw_fair_value > hi + 1e-4)
    mos = (fv - current_price) / fv * 100
    return round(float(np.clip(50.0 + mos, 0.0, 100.0)), 1), round(mos, 1), clipped


def confidence(dcf, pe, fcf_warning):
    """D9: ความมั่นใจจากการที่สองวิธีให้ผลตรงกันแค่ไหน คืน (ระดับ, ส่วนต่าง %, เหตุผล)"""
    levels = ['Low', 'Medium', 'High']
    if dcf is None or pe is None:
        return 'Low', None, 'ประเมินได้วิธีเดียว จึงเทียบความสอดคล้องไม่ได้'
    gap = abs(dcf - pe) / ((dcf + pe) / 2) * 100
    lvl = 2 if gap <= CONF_HIGH_GAP else (1 if gap <= CONF_MED_GAP else 0)
    reason = f"DCF กับ P/E ต่างกัน {gap:.0f}%"
    if fcf_warning and lvl > 0:
        lvl -= 1
        reason += " และ FCF สูงกว่ากำไรมาก (ลด 1 ระดับ)"
    return levels[lvl], round(gap, 1), reason


def _net_debt(r):
    """หนี้สุทธิไม่รวมเจ้าหนี้การค้า"""
    total_liab = clean_float(r.get('total_liabilities'), default=0.0)
    cash = clean_float(r.get('cash_and_equivalents'), default=0.0)
    ap = clean_float(r.get('accounts_payable'), default=None)
    if ap is not None and 0 <= ap <= total_liab:
        return total_liab - ap - cash
    return total_liab - cash


_KEYS = ['valuation_score', 'fair_value', 'dcf_fair_value', 'pe_fair_value', 'margin_of_safety', 'price_to_value',
         'dcf_score', 'pe_score', 'dcf_mos', 'pe_mos', 'method_gap_pct', 'confidence_level', 'confidence_reason',
         'valuation_status', 'warning_message', 'pe_ratio', 'pb_ratio', 'market_cap_mb', 'eps', 'fcf_base',
         'net_debt_used', 'wacc_used', 'terminal_growth_used', 'target_pe_used', 'damodaran_industry',
         'params_source', 'params_date', 'shares_outstanding', 'book_value_per_share', 'is_clipped']


def _empty_output(message, status='NO_DATA'):
    out = {k: None for k in _KEYS}
    out.update({k: None for k in ['ke_capm', 'beta_used', 'beta_adjusted', 'bvps', 'pb_current', 'roe_hist_avg',
                                  'roe_latest', 'roe_hist_years', 'implied_roe', 'roe_gap', 'expectation_label',
                                  'expectation_color', 'expectation_note', 'fcf_quality_warning', 'fcf_to_ni']})
    out.update({'valuation_status': status, 'confidence_level': 'Low', 'warning_message': message})
    return out


def calculate_valuation_module(df_fin_ticker, current_price, ticker, beta=None, params=None, **kwargs):
    """Module 2: Fair Value (DCF + P/E)
    params: dict {'wacc_thb_pct', 'target_pe', 'damodaran_industry', 'data_date'} จากตาราง valuation_params"""
    if df_fin_ticker is None or df_fin_ticker.empty or current_price is None or current_price <= 0:
        return _empty_output('ไม่มีข้อมูลงบการเงิน หรือราคาหุ้นไม่ถูกต้อง')
    ticker_clean = str(ticker).replace('.BK', '').strip().upper() if ticker else ''
    shares = SHARES_OUTSTANDING.get(ticker_clean)
    if not shares:
        return _empty_output(f'ไม่มีจำนวนหุ้นของ {ticker_clean}')
    wacc_pct = clean_float((params or {}).get('wacc_thb_pct'), default=None)
    target_pe = clean_float((params or {}).get('target_pe'), default=None)
    if wacc_pct is None or target_pe is None:
        return _empty_output('ไม่พบ WACC / Target P/E ของหุ้นนี้ใน Dataset/valuation_params_2023_2025.csv')
    wacc, g = wacc_pct / 100.0, STABLE_GROWTH

    fin_sorted = df_fin_ticker.sort_values(by='year')
    r = fin_sorted.iloc[-1]
    eps = clean_float(r.get('eps'), default=None)
    fcf_hist = fin_sorted['free_cash_flow'].apply(clean_float, default=np.nan).tail(2).dropna()
    fcf_base = float(fcf_hist.mean()) if len(fcf_hist) else None
    net_debt = _net_debt(r)

    dcf = None
    if fcf_base is not None and fcf_base > 0 and wacc > g:
        equity_value = fcf_base * (1 + g) / (wacc - g) - net_debt
        dcf = equity_value / shares if equity_value > 0 else None
    pe = eps * target_pe if (eps is not None and eps > 0) else None

    dcf_score, dcf_mos, dcf_clip = method_score(dcf, current_price)
    pe_score, pe_mos, pe_clip = method_score(pe, current_price)

    valid = [(v, w) for v, w in [(dcf, DCF_WEIGHT), (pe, PE_WEIGHT)] if v is not None]
    if not valid:
        blended = mos = p2v = None
        val_score = 0.0
        status = 'NOT_RATED'
        warning = 'ประเมินไม่ได้ทั้ง 2 วิธี เพราะขาดทุนทั้งกำไรและกระแสเงินสด (คะแนน Fair Value = 0)'
    else:
        blended = sum(v * w for v, w in valid) / sum(w for _, w in valid)
        mos = (blended - current_price) / blended * 100
        p2v = current_price / blended
        val_score = round((dcf_score or 0.0) * DCF_WEIGHT + (pe_score or 0.0) * PE_WEIGHT, 1)   # D4: วิธีที่ขาด = 0
        status = 'OK' if len(valid) == 2 else 'PARTIAL'
        if status == 'PARTIAL':
            missing = 'DCF (FCF ≤ 0)' if dcf is None else 'P/E (EPS ≤ 0)'
            warning = f'คำนวณได้วิธีเดียว — {missing} คำนวณไม่ได้และนับ 0 คะแนนในส่วนนั้น'
        else:
            warning = None

    exp = market_expectation(df_fin_ticker, current_price, ticker, beta)
    conf, gap, conf_reason = confidence(dcf, pe, bool(exp.get('fcf_quality_warning')))
    if status == 'NOT_RATED':
        conf, conf_reason = 'Low', 'ประเมินมูลค่าไม่ได้'

    bvps = clean_float(r.get('total_equity'), 0.0) / shares
    out = {
        'valuation_score': val_score,
        'fair_value': _rnd(blended), 'dcf_fair_value': _rnd(dcf), 'pe_fair_value': _rnd(pe),
        'margin_of_safety': _rnd(mos, 1), 'price_to_value': _rnd(p2v, 2),
        'dcf_score': dcf_score, 'pe_score': pe_score, 'dcf_mos': dcf_mos, 'pe_mos': pe_mos,
        'method_gap_pct': gap, 'confidence_level': conf, 'confidence_reason': conf_reason,
        'valuation_status': status, 'warning_message': warning,
        'pe_ratio': _rnd(current_price / eps) if (eps is not None and eps > 0) else None,
        'pb_ratio': _rnd(current_price / bvps) if bvps > 0 else None,
        'market_cap_mb': round(current_price * shares / 1e6, 1),
        'eps': _rnd(eps), 'fcf_base': _rnd(fcf_base, 1), 'net_debt_used': _rnd(net_debt, 1),
        'wacc_used': round(wacc_pct, 2), 'terminal_growth_used': round(g * 100, 2), 'target_pe_used': round(target_pe, 2),
        'damodaran_industry': (params or {}).get('damodaran_industry'),
        'params_source': PARAMS_SOURCE_TEXT, 'params_date': (params or {}).get('data_date'),
        'shares_outstanding': shares, 'book_value_per_share': _rnd(bvps),
        'is_clipped': bool(dcf_clip or pe_clip),
    }
    out.update(exp)
    return out


def build_fair_value_yearly(df_fin_ticker, df_price_ticker, ticker, params_by_year=None, params=None):
    """มูลค่าเหมาะสมย้อนหลังรายปี (งบถึงปีนั้น) เทียบราคาปิดสิ้นปี — สูตรเดียวกับปีล่าสุด
    [v17.2] ใช้ WACC และ Target P/E ของปีนั้น (params_by_year = {ปี: params}) ปีไหนไม่มีค่าจะไม่คำนวณ
    เพื่อไม่ให้ใช้ข้อมูลของปีหลังย้อนไปประเมินปีก่อน · params (ค่าเดียวทุกปี) เก็บไว้ให้โค้ดเดิมเรียกได้"""
    rows = []
    if df_fin_ticker is None or df_fin_ticker.empty or df_price_ticker is None or df_price_ticker.empty:
        return pd.DataFrame(rows)
    price_df = df_price_ticker.copy()
    price_df['date'] = pd.to_datetime(price_df['date'])
    for yr in sorted(df_fin_ticker['year'].unique()):
        p_year = params_by_year.get(int(yr)) if params_by_year is not None else params
        if p_year is None:
            continue
        fin_upto = df_fin_ticker[df_fin_ticker['year'] <= yr]
        year_end_prices = price_df[price_df['date'] <= f'{yr}-12-31']
        if fin_upto.empty or year_end_prices.empty:
            continue
        price = clean_float(year_end_prices.sort_values('date').iloc[-1]['close'], default=None)
        if price is None:
            continue
        val = calculate_valuation_module(fin_upto, price, ticker, params=p_year)
        rows.append({'year': int(yr), 'price': round(price, 2), 'fair_value': val.get('fair_value'),
                     'wacc_used': val.get('wacc_used'), 'target_pe_used': val.get('target_pe_used'),
                     'status': val.get('valuation_status')})
    return pd.DataFrame(rows)
