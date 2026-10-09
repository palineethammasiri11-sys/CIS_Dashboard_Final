"""
calculate_modules/industry_benchmark.py
-------------------------------------------
สูตรคำนวณโมดูล "Industry Benchmark" (📊) — คู่กับ pages_content/industry_benchmark.py

ต่างจากโมดูลอื่น: โมดูลนี้ "ไม่ได้" คำนวณจากงบการเงิน/ราคาหุ้นโดยตรง แต่คำนวณจาก
"ผลลัพธ์ที่โมดูลอื่นทั้ง 5 คำนวณมาแล้ว" (เพราะการจัดอันดับ/เทียบกลุ่มต้องรู้คะแนนของทุกหุ้นก่อน)
ดังนั้นฟังก์ชันนี้จะถูกเรียกเป็นลำดับสุดท้ายใน calculate_scores.py หลัง 5 โมดูลอื่นคำนวณครบทุกหุ้นแล้ว

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key โดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

compute_industry_rankings(df_res) รับ:
    df_res : pd.DataFrame ที่มีคะแนนครบทุกหุ้น (แถวละ 1 หุ้น) ต้องมีคอลัมน์ต่อไปนี้อยู่แล้ว
             (มาจาก 5 โมดูลอื่น + ข้อมูลพื้นฐาน): ticker, sector, health_score, valuation_score,
             timing_score, ai_score, risk_score

คืนค่า df_res เดิม "บวกเพิ่ม" คอลัมน์ต่อไปนี้ (ไม่ลบคอลัมน์เดิม):
    industry_score   : float 0-100  (percentile ของ base_score ภายในกลุ่ม sector — ใช้แสดงอันดับ ไม่นับใน overall_score)
    overall_score    : float 0-100  (คะแนนรวมถ่วงน้ำหนักทุกโมดูล — ใช้ทำ Recommendation หน้า Overview)
    sector_rank      : int          (อันดับภายในกลุ่ม sector เดียวกัน จากทั้งหมดที่ติดตาม)
    overall_rank     : int          (อันดับเทียบทั้งหมดที่ติดตาม ไม่แบ่งกลุ่ม)
    recommendation   : str          (STRONG BUY / BUY / ACCUMULATE / REDUCE-SELL)

ที่มาของสูตร: ดูละเอียดใน DATA_FORMULA_AUDIT.md หัวข้อ 6-7 (Industry Benchmark + Overall Score)
สรุปสั้น: การจัดอันดับ (rank) และ percentile เป็นวิธีทางสถิติมาตรฐาน (pandas.rank())
แต่น้ำหนักถ่วง Overall Score (สัดส่วน 25:25:15:15 ของ Health/Valuation/Timing/Risk — AI และ Industry ไม่นับ ดู v17.1, FIX-I1) และเกณฑ์ Recommendation (75/65/50)
เป็นค่าที่กำหนดเองทั้งหมด — จุดสำคัญ: ฐานเทียบมีแค่ 8 หุ้นเท่านั้น ไม่ใช่ทั้งตลาด SET จริง
"""


import json
import numpy as np
import pandas as pd

from calculate_modules import labels as L

# [v17.1] ตัด AI ออกจากคะแนนรวม: ทุกหุ้นคิดจากฐานเดียวกัน 4 โมดูล (เดิม AI 10 นับเฉพาะหุ้นที่โมเดลผ่านด่าน
#         ทำให้บางหุ้นคิดจาก 5 โมดูล บางหุ้น 4 โมดูล) · AI ยังคำนวณและแสดงในหน้าของตัวเองเป็นข้อมูลประกอบ
#         สัดส่วน 25 : 25 : 15 : 15 = Health 31.25% / Fair Value 31.25% / Timing 18.75% / Risk 18.75%
BASE_WEIGHTS = {'health_score': 0.25, 'valuation_score': 0.25,
                'timing_score': 0.15, 'risk_score': 0.15}
# [FIX-I1] Industry Score ไม่ถูกนับใน Overall Score แล้ว (เดิม 10%)
# เหตุผล: industry_score คือ percentile ของ base_score ซึ่งคำนวณจากคะแนน 5 โมดูลเดียวกันกับที่รวมอยู่ใน Overall
# การบวกเข้าไปอีก 10% จึงเป็นการนับคะแนนเดิมซ้ำ ตอนนี้ Overall = ค่าเฉลี่ยถ่วงน้ำหนักของ 4 โมดูลใน BASE_WEIGHTS
# (หารด้วยผลรวมน้ำหนักของโมดูลที่มีคะแนน) ส่วน industry_score ยังคำนวณไว้แสดงอันดับในกลุ่มบนหน้าจอเหมือนเดิม
INDUSTRY_WEIGHT = 0.0
MIN_SECTOR_SIZE = 2
NO_DATA_LABEL = "ข้อมูลไม่พอ"


def sanitize_for_sqlite(df):          # ข้อ 1
    df = df.copy()
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (dict, list, tuple, set))).any():
            df[col] = df[col].map(
                lambda v: json.dumps(sorted(v) if isinstance(v, set) else v, ensure_ascii=False, default=str)
                if isinstance(v, (dict, list, tuple, set)) else v)
    return df


def _weighted_mean(df, weights):      # ข้อ 2
    vals = df[list(weights)].apply(pd.to_numeric, errors='coerce')
    w = pd.Series(weights)
    mask = vals.notna()
    num = (vals.fillna(0) * w).sum(axis=1)
    den = (mask * w).sum(axis=1)
    return (num / den.where(den > 0)).round(1)

def compute_industry_rankings(df_res):
    """รับ DataFrame ที่มีคะแนนทุกโมดูลของทุกหุ้นแล้ว (แถวละ 1 หุ้น) คำนวณ Industry Benchmark
    + Overall Score + Recommendation แล้วคืน DataFrame เดิมที่เพิ่มคอลัมน์เหล่านี้เข้าไป"""

    # Percentile ของ health_score ภายในกลุ่ม sector เดียวกัน (0-100, ยิ่งสูงยิ่งดีกว่ากลุ่ม)
    df_res = df_res.copy()
    for c in BASE_WEIGHTS:
        df_res[c] = pd.to_numeric(df_res[c], errors='coerce')
    sector_key = df_res['sector'].fillna('N/A')

    df_res['base_score'] = _weighted_mean(df_res, BASE_WEIGHTS)                    # ข้อ 4
    valid = df_res['base_score'].notna()
    df_res['sector_size'] = valid.groupby(sector_key).transform('sum').astype(int)
    df_res['sector_comparable'] = df_res['sector_size'] >= MIN_SECTOR_SIZE         # ข้อ 3

    pct_sector = df_res['base_score'].groupby(sector_key).rank(pct=True) * 100
    pct_universe = df_res['base_score'].rank(pct=True) * 100
    df_res['industry_score'] = pd.Series(
        np.where(df_res['sector_comparable'], pct_sector, pct_universe), index=df_res.index).round(1)
    df_res['industry_score_basis'] = np.where(df_res['sector_comparable'], 'sector', 'universe')

    # คะแนนรวมถ่วงน้ำหนัก — น้ำหนักนี้เป็นค่าที่กำหนดเอง ปรับได้ตามที่ทีมเห็นสมควร
    df_res['overall_score'] = (_weighted_mean(df_res, {**BASE_WEIGHTS, 'industry_score': INDUSTRY_WEIGHT})
                               if INDUSTRY_WEIGHT > 0 else df_res['base_score'])          # FIX-I1

    df_res['sector_rank'] = df_res.groupby(sector_key)['overall_score'].rank(ascending=False, method='min').astype('Int64')
    df_res['overall_rank'] = df_res['overall_score'].rank(ascending=False, method='min').astype('Int64')

    # v17 / D5: คำแนะนำมาจากตารางป้ายกลาง (labels.py) ที่เดียว
    df_res['recommendation'] = df_res['overall_score'].apply(L.recommendation_code)

    # v17 / D4: บอกว่าคะแนนรวมคิดจากกี่โมดูล และโมดูลไหนไม่นับ
    names = {'health_score': 'Health', 'valuation_score': 'Fair Value', 'risk_score': 'Risk',
             'timing_score': 'Entry Timing'}
    vals = df_res[list(BASE_WEIGHTS)].apply(pd.to_numeric, errors='coerce')
    df_res['modules_used'] = vals.notna().sum(axis=1).astype(int)
    df_res['modules_missing'] = vals.apply(lambda r: json.dumps([names[c] for c in BASE_WEIGHTS if pd.isna(r[c])],
                                                                ensure_ascii=False), axis=1)
    df_res['weight_used'] = vals.notna().mul(pd.Series(BASE_WEIGHTS)).sum(axis=1).round(2)

    # v17 / D14: อันดับรายตัวชี้วัด (1 = ดีที่สุด) เทียบ 8 หุ้น และเทียบในกลุ่ม — ทุกหน้าอ่านจากที่นี่
    for col, higher_better in RANK_METRICS.items():
        if col not in df_res.columns:
            continue
        v = pd.to_numeric(df_res[col], errors='coerce')
        if col == 'de_ratio':                     # D/E ติดลบ = ส่วนผู้ถือหุ้นติดลบ → แย่ที่สุด ไม่ใช่ดีที่สุด
            v = v.where(v >= 0, np.inf)
        df_res[f'rank_{col}'] = v.rank(ascending=not higher_better, method='min').astype('Int64')
        df_res[f'srank_{col}'] = v.groupby(sector_key).rank(ascending=not higher_better, method='min').astype('Int64')
        df_res[f'n_{col}'] = int(v.notna().sum())
        fin = v.replace([np.inf, -np.inf], np.nan)
        df_res[f'median_{col}'] = None if fin.notna().sum() == 0 else round(float(fin.median()), 3)
    df_res['sector_n'] = df_res.groupby(sector_key)['ticker'].transform('count').astype(int)
    return df_res


# ตัวชี้วัดที่ต้องจัดอันดับ: ชื่อคอลัมน์ → True ถ้า "ยิ่งสูงยิ่งดี"
RANK_METRICS = {
    'overall_score': True, 'health_score': True, 'valuation_score': True, 'risk_score': True,
    'timing_score': True, 'ai_score': True, 'revenue_growth_yoy': True,
    'roe': True, 'roa': True, 'net_margin': True, 'de_ratio': False, 'current_ratio': True,
    'asset_turnover': True, 'accrual_ratio': False, 'interest_coverage': True,
    'var_95': False, 'cvar_95': False, 'sharpe_ratio': True, 'sortino_ratio': True, 'calmar_ratio': True,
    'psr': True, 'beta': False, 'volatility': False, 'max_drawdown': False,
}
