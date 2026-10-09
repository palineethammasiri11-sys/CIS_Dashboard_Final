"""
calculate_modules/company_health.py
-------------------------------------
สูตรคำนวณโมดูล "Company Health" — คู่กับ pages_content/company_health.py

=== DATA CONTRACT ===
calculate_health_module(df_fin_ticker) คืน dict:
    health_score, roe, roa, de_ratio, current_ratio,
    s_roe, s_roa, s_liquidity, s_debt, s_profitability           (คะแนนย่อย 0-100 ของแต่ละองค์ประกอบ)
    health_components_used, health_data_status, health_fy
    revenue_growth_pct, asset_turnover, accrual_ratio, interest_coverage   (ตัวชี้วัดเสริม ไม่นับในคะแนน)
    net_margin, net_income_latest, equity_negative, revenue_down_2y           (ใช้ทำสัญญาณเตือน)
build_health_score_yearly(df_fin_ticker) คืน DataFrame [year, health_score]

=== v17 (Blueprint ฉบับที่ 2) ===
- [D2] ROE / ROA ใช้ค่าในไฟล์ของทีมข้อมูลทุกแถว (ยกเลิก FIX-H1 ที่คำนวณใหม่จากงบ)
- [D3] คะแนนคิดจาก 4 องค์ประกอบเท่าเดิม: ROE 30%, ROA 25%, Current Ratio 20%, D/E 25%
       คะแนนย่อย: ROE × 3.5, ROA × 7, Current Ratio × 45, (2.5 − D/E) × 40 ตัดที่ 0-100
       ต้องมีอย่างน้อย 3 ใน 4 องค์ประกอบ (มี 3 → ถ่วงน้ำหนักใหม่ให้รวม 100%)
       ตัวคูณและน้ำหนักเป็นค่าที่ทีมกำหนด (ผ่านการทดสอบความไวแล้ว) — ไม่ได้มาจากแหล่งภายนอก
- [D3] ตัวชี้วัดเสริม 4 ตัว (ไม่แปลงเป็นคะแนน ไม่นับใน Health Score):
       การเติบโตของรายได้, Asset Turnover (Soliman 2008), Accrual Ratio (Sloan 1996), Interest Coverage (คอลัมน์ในไฟล์)
- D/E ติดลบ (ส่วนผู้ถือหุ้นติดลบ) → คะแนนหนี้ 0
- ไม่มีข้อมูล → None (ไม่ใส่ค่าปลอม)
"""

import numpy as np
import pandas as pd

from calculate_modules.common import clean_float

W_ROE, W_ROA, W_LIQ, W_DEBT = 0.30, 0.25, 0.20, 0.25
MIN_COMPONENTS = 3

# ตัวคูณคะแนนย่อย (ใช้ร่วมกับหน้าจอเพื่ออธิบาย "เต็มเมื่อ ...")
MULT_ROE, MULT_ROA, MULT_CR, MULT_DE, DE_CAP = 3.5, 7.0, 45.0, 40.0, 2.5


def _num(r, key):
    return clean_float(r.get(key), default=None) if r is not None else None


def _sub_scores(roe, roa, cr, de):
    s_roe = float(np.clip(roe * MULT_ROE, 0, 100)) if roe is not None else None
    s_roa = float(np.clip(roa * MULT_ROA, 0, 100)) if roa is not None else None
    s_liq = float(np.clip(cr * MULT_CR, 0, 100)) if cr is not None else None
    if de is None:
        s_debt = None
    elif de < 0:
        s_debt = 0.0
    else:
        s_debt = float(np.clip((DE_CAP - de) * MULT_DE, 0, 100))
    return s_roe, s_roa, s_liq, s_debt


def _score_row(r):
    """คะแนนของงบ 1 ปี — ใช้ทั้งปีล่าสุดและกราฟรายปี (สูตรเดียวกัน)"""
    roe = _num(r, 'roe')                 # D2: ค่าในไฟล์
    roa = _num(r, 'roa')
    de = _num(r, 'de_ratio')
    cr = _num(r, 'current_ratio')
    s_roe, s_roa, s_liq, s_debt = _sub_scores(roe, roa, cr, de)

    parts = [(s_roe, W_ROE), (s_roa, W_ROA), (s_liq, W_LIQ), (s_debt, W_DEBT)]
    avail = [(s, w) for s, w in parts if s is not None]
    score = round(sum(s * w for s, w in avail) / sum(w for _, w in avail), 1) if len(avail) >= MIN_COMPONENTS else None

    if s_roe is not None and s_roa is not None:
        s_prof = round(s_roe * 0.6 + s_roa * 0.4, 1)
    else:
        s_prof = s_roe if s_roe is not None else s_roa

    rnd = lambda v, d=1: None if v is None else round(float(v), d)
    return {
        'health_score': score,
        'roe': rnd(roe, 2), 'roa': rnd(roa, 2), 'de_ratio': rnd(de, 2), 'current_ratio': rnd(cr, 2),
        's_roe': rnd(s_roe), 's_roa': rnd(s_roa), 's_liquidity': rnd(s_liq), 's_debt': rnd(s_debt),
        's_profitability': rnd(s_prof),
        'health_components_used': len(avail),
        'health_data_status': 'OK' if score is not None else 'INSUFFICIENT_DATA',
    }


def _supplementary(fin_sorted):
    """ตัวชี้วัดเสริม (ไม่นับในคะแนน) + ข้อมูลสำหรับสัญญาณเตือน"""
    r = fin_sorted.iloc[-1]
    prev = fin_sorted.iloc[-2] if len(fin_sorted) >= 2 else None
    rev = _num(r, 'total_revenue')
    ta = _num(r, 'total_assets')
    ni = _num(r, 'net_income')
    ocf = _num(r, 'operating_cash_flow')
    eq = _num(r, 'total_equity')

    rev_prev = _num(prev, 'total_revenue') if prev is not None else None
    growth = (rev - rev_prev) / abs(rev_prev) * 100 if (rev is not None and rev_prev) else None
    turnover = rev / ta if (rev is not None and ta) else None
    accrual = (ni - ocf) / ta if (ni is not None and ocf is not None and ta) else None
    icov = _num(r, 'interest_coverage')

    revs = [_num(x, 'total_revenue') for _, x in fin_sorted.tail(3).iterrows()]
    down_2y = bool(len(revs) == 3 and None not in revs and revs[2] < revs[1] < revs[0])

    rnd = lambda v, d: None if v is None else round(float(v), d)
    return {
        'revenue_growth_pct': rnd(growth, 1),
        'asset_turnover': rnd(turnover, 2),
        'accrual_ratio': rnd(accrual, 3),
        'interest_coverage': rnd(icov, 2),
        'net_margin': rnd(_num(r, 'net_margin'), 2),
        'net_income_latest': ni,
        'equity_negative': bool(eq is not None and eq < 0),
        'revenue_down_2y': down_2y,
    }


_SUPP_KEYS = ['revenue_growth_pct', 'asset_turnover', 'accrual_ratio', 'interest_coverage',
              'net_margin', 'net_income_latest', 'equity_negative', 'revenue_down_2y']


def calculate_health_module(df_fin_ticker):
    """Module 1: Company Health (ใช้งบปีล่าสุดที่มีจริง)"""
    if df_fin_ticker is None or df_fin_ticker.empty:
        out = _score_row({})
        out.update({k: None for k in _SUPP_KEYS})
        out['health_data_status'] = 'NO_DATA'
        out['health_fy'] = None
        return out
    fin_sorted = df_fin_ticker.sort_values(by='year')
    out = _score_row(fin_sorted.iloc[-1])
    out.update(_supplementary(fin_sorted))
    out['health_fy'] = int(fin_sorted.iloc[-1]['year'])
    return out


def build_health_score_yearly(df_fin_ticker):
    """คะแนน Health รายปี (สูตรเดียวกับปีล่าสุด)"""
    if df_fin_ticker is None or df_fin_ticker.empty:
        return pd.DataFrame(columns=['year', 'health_score'])
    rows = [{'year': int(r['year']), 'health_score': _score_row(r)['health_score']}
            for _, r in df_fin_ticker.sort_values('year').iterrows()]
    return pd.DataFrame(rows)
