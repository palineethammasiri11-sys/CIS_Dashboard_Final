"""
calculate_scores.py — Orchestrator (Data Pipeline / Integration Lead ดูแลไฟล์นี้)
------------------------------------------------------------------------------------
ไฟล์นี้ "ไม่มีสูตรคำนวณของโมดูลไหนอยู่ในนี้แล้ว" — ทำหน้าที่แค่:
    1. โหลดข้อมูลจากฐานข้อมูล
    2. วนลูปแต่ละหุ้น เรียกฟังก์ชันคำนวณของทั้ง 6 โมดูลจาก calculate_modules/
    3. รวมผลลัพธ์ + บันทึกกลับลงฐานข้อมูล

สูตร/ตรรกะการคำนวณจริงของแต่ละโมดูลอยู่ที่:
    calculate_modules/company_health.py       (เจ้าของ: คนที่ดูแล pages_content/company_health.py)
    calculate_modules/fair_value.py           (เจ้าของ: คนที่ดูแล pages_content/fair_value.py)
    calculate_modules/entry_timing.py         (เจ้าของ: คนที่ดูแล pages_content/entry_timing.py)
    calculate_modules/ai_prediction.py        (เจ้าของ: คนที่ดูแล pages_content/ai_prediction.py)
    calculate_modules/risk_analysis.py        (เจ้าของ: คนที่ดูแล pages_content/risk_analysis.py)
    calculate_modules/industry_benchmark.py   (เจ้าของ: คนที่ดูแล pages_content/industry_benchmark.py)

⚠️ ไฟล์นี้เป็น "ของกลาง" เหมือน common.py ของฝั่ง UI — โดยปกติ เจ้าของแต่ละโมดูลไม่ต้องแก้ไฟล์นี้เลย
แก้แค่ calculate_modules/<โมดูลของตัวเอง>.py พอ ถ้าจำเป็นต้องแก้ไฟล์นี้ (เช่น เพิ่มตารางผลลัพธ์ใหม่)
ให้แจ้ง Data Pipeline / Integration Lead ก่อน

ตารางผลลัพธ์ที่สร้าง:
- cis_summary_scores      : สรุปคะแนนรายหุ้น (ใช้ในทุกหน้าของ Dashboard)
- ai_feature_importance   : Feature importance ของโมเดล Random Forest รายหุ้น (ใช้ในหน้า AI Prediction)
- ai_backtest_history     : ผลทำนายจริงบนชุด Test ปี 2025 (ใช้ในหน้า AI Prediction)
- risk_rolling_history    : Rolling volatility / drawdown รายสัปดาห์ (ใช้วาดกราฟหน้า Risk Analysis)
- health_score_yearly     : คะแนนสุขภาพการเงินรายปี 2023-2025 (ใช้วาดกราฟ trend หน้า Company Health)
- fair_value_yearly       : Fair Value ย้อนหลังรายปี เทียบราคาจริง (ใช้วาดกราฟหน้า Fair Value)
"""

import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from import_data import write_table  # [v17.3] ลบตารางเดิมก่อนเขียน (กัน error "table already exists")

from calculate_modules.common import clean_float, SECTOR_MAP
from calculate_modules import (
    company_health,
    fair_value,
    entry_timing,
    ai_prediction,
    risk_analysis,
    industry_benchmark,
)

DB_NAME = "cis_database.db"

# [FIX-S4] เวอร์ชันของสูตรคำนวณ — บันทึกลง DB ทุกแถว (คอลัมน์ calc_version)
# common.py (ฝั่ง UI) จะเทียบค่านี้กับใน DB ถ้าไม่ตรง = DB เก่า → คำนวณใหม่อัตโนมัติตอนเปิดแอป
# ⚠️ ทุกครั้งที่แก้สูตรใน calculate_modules/ ให้เปลี่ยนเลขนี้ (เช่น เพิ่มวันที่) ไม่งั้นเว็บที่ deploy จะยังใช้ตัวเลขเก่า
# [v17.4] เปลี่ยนเฉพาะข้อความสรุปสั้นของ Entry Timing (summary_short) — คะแนนทุกตัวเท่า v17.3
CALC_VERSION = "2026-10-10-v17.4"
TARGET_STOCKS = ["ADVANC", "CCET", "DELTA", "HANA", "JMART", "KCE", "THCOM", "TRUE"]


def _sanitize_for_sql(record: dict) -> dict:
    """แปลงค่าที่เป็น dict, list, tuple หรือ set ให้เป็น JSON string
    เนื่องจาก SQLite / Pandas to_sql ไม่รองรับการ bind ข้อมูลแบบ dictionary/list ลง column ตรง ๆ
    การแปลงเป็น JSON string จะช่วยป้องกันข้อผิดพลาด sqlite3.ProgrammingError: type 'dict' is not supported
    """
    clean = {}
    for k, v in record.items():
        if isinstance(v, (dict, list, tuple, set)):
            clean[k] = json.dumps(v, ensure_ascii=False, default=str)
        else:
            clean[k] = v
    return clean


def load_data_from_db(engine):
    df_fin = pd.read_sql("SELECT * FROM stock_financials", con=engine)
    df_price = pd.read_sql("SELECT * FROM stock_daily_prices", con=engine)
    df_price["date"] = pd.to_datetime(df_price["date"])
    try:
        df_risk = pd.read_sql("SELECT * FROM stock_risk_static", con=engine)
    except Exception:
        df_risk = pd.DataFrame(
            columns=["ticker", "beta", "volatility_pct", "max_drawdown_pct"]
        )
    try:   # v17 / D8: WACC และ Target P/E รายปี จาก Dataset/valuation_params_2023_2025.csv
        df_params = pd.read_sql("SELECT * FROM valuation_params", con=engine)
    except Exception:
        df_params = pd.DataFrame(columns=["ticker"])
    return df_fin, df_price, df_risk, df_params


def run_full_pipeline():
    engine = create_engine(f"sqlite:///{DB_NAME}", connect_args={"timeout": 60})
    df_fin_all, df_price_all, df_risk_all, df_params_all = load_data_from_db(engine)
    # [v17.2] ค่าปีล่าสุดใช้กับการประเมินปัจจุบัน / ค่ารายปีใช้กับกราฟย้อนหลัง (ไม่เอาค่าปีหลังไปใช้กับปีก่อน)
    if 'fiscal_year' not in df_params_all.columns:
        df_params_all['fiscal_year'] = 2025
    params_by_year = {}
    for r in df_params_all.sort_values('fiscal_year').to_dict('records'):
        params_by_year.setdefault(r['ticker'], {})[int(r['fiscal_year'])] = r
    params_by_ticker = {t: yrs[max(yrs)] for t, yrs in params_by_year.items()}

    print("\n--- เริ่มประมวลผลระบบ CIS Scoring สำหรับหุ้นทั้ง 8 ตัว (ใช้ข้อมูลจริงทั้งหมด) ---")
    all_summary = []
    all_feature_importance = []
    all_backtest = []
    all_risk_history = []
    all_health_yearly = []
    all_fair_value_yearly = []

    for ticker in TARGET_STOCKS:
        fin_sub = df_fin_all[df_fin_all["ticker"] == ticker]
        price_sub = df_price_all[df_price_all["ticker"] == ticker].sort_values(by="date")
        risk_sub = (
            df_risk_all[df_risk_all["ticker"] == ticker]
            if not df_risk_all.empty
            else None
        )

        # [FIX-S1] ตัดวันที่ราคาปิดว่างทิ้งก่อน แล้วใช้ราคาล่าสุดที่มีจริง
        # (เดิมถ้าราคาวันล่าสุดว่างจะใส่ 10.0 บาทปลอม ทำให้ Fair Value / P/E / Market Cap ผิดทั้งหมด)
        price_sub = price_sub[pd.to_numeric(price_sub["close"], errors="coerce").notna()]
        if price_sub.empty:
            print(f"⚠️ {ticker}: ไม่มีราคาปิดที่ใช้ได้ ข้ามหุ้นนี้")
            continue

        current_price = round(clean_float(price_sub.iloc[-1]["close"]), 2)
        latest_date = str(price_sub.iloc[-1]["date"])[:10]
        if len(price_sub) >= 2:
            prev_close = clean_float(price_sub.iloc[-2]["close"])
            change_val = round(current_price - prev_close, 2)
            change_pct = round((change_val / prev_close) * 100, 2) if prev_close else None
        else:
            change_val, change_pct = None, None

        # ===== เรียกฟังก์ชันคำนวณของทั้ง 5 โมดูล =====
        m1 = company_health.calculate_health_module(fin_sub)
        # [FIX-S5] ส่ง Beta (จาก stock_risk_metrics ที่คำนวณด้วย compute_beta.py) ให้ Fair Value ใช้คำนวณ Ke ด้วย CAPM
        beta_for_valuation = (clean_float(risk_sub.iloc[0].get("beta"), default=None)
                              if risk_sub is not None and not risk_sub.empty else None)
        params = params_by_ticker.get(ticker)
        m2 = fair_value.calculate_valuation_module(fin_sub, current_price, ticker, beta=beta_for_valuation,
                                                  params=params)
        m3 = entry_timing.calculate_timing_module(price_sub)
        m4, feat_imp, backtest_df = ai_prediction.train_and_predict_ai(price_sub, ticker)
        m5 = risk_analysis.calculate_risk_module(price_sub, risk_sub)

        # เมตริกเพิ่มเติมสำหรับ Overview / Key Highlights
        fin_sorted = fin_sub.sort_values("year")
        rev_growth, ni_growth = None, None
        if len(fin_sorted) >= 2:
            # [FIX-S3] หารด้วยค่าสัมบูรณ์ของปีก่อน — เดิมหารด้วยค่าที่ติดลบตรงๆ ทำให้บริษัทที่ "ขาดทุนน้อยลง/
            # กลับมามีกำไร" โชว์การเติบโตเป็นลบ เช่น TRUE ปี 2025 (-10,954 → +9,111 ล้านบาท) เดิมแสดง -183%
            # ตอนนี้แสดง +183% และติดธง ni_turnaround ให้ UI เขียนอธิบาย
            rev_prev = clean_float(fin_sorted.iloc[-2]["total_revenue"], default=None)
            rev_curr = clean_float(fin_sorted.iloc[-1]["total_revenue"], default=None)
            ni_prev = clean_float(fin_sorted.iloc[-2]["net_income"], default=None)
            ni_curr = clean_float(fin_sorted.iloc[-1]["net_income"], default=None)
            if rev_prev and rev_curr is not None:
                rev_growth = round((rev_curr - rev_prev) / abs(rev_prev) * 100, 1)
            if ni_prev and ni_curr is not None:
                ni_growth = round((ni_curr - ni_prev) / abs(ni_prev) * 100, 1)
            ni_turnaround = bool(ni_prev is not None and ni_curr is not None and (ni_prev < 0) != (ni_curr < 0))
        else:
            ni_turnaround = False
        latest_row = fin_sorted.iloc[-1] if not fin_sorted.empty else None
        # [FIX-S2] FCF ว่าง → None (เดิม clean_float คืน 0.0 ทำให้ดูเหมือน FCF = 0 จริง)
        fcf_raw = clean_float(latest_row.get("free_cash_flow"), default=None) if latest_row is not None else None
        fcf_latest = round(fcf_raw, 1) if fcf_raw is not None else None

        # ห่อด้วย _sanitize_for_sql เพื่อแปลง dict/list ทุกตัว (เช่น risk_score_breakdown) เป็น string ที่ SQLite บันทึกได้
        all_summary.append(
            _sanitize_for_sql(
                {
                    "ticker": ticker,
                    "current_price": current_price,
                    "change_val": change_val,
                    "change_pct": change_pct,
                    "latest_date": latest_date,
                    "sector": SECTOR_MAP.get(ticker, "Technology"),
                    "revenue_growth_yoy": rev_growth,
                    "net_income_growth_yoy": ni_growth,
                    "free_cash_flow_latest": fcf_latest,
                    "ni_turnaround": ni_turnaround,
                    **m1,
                    **m2,
                    **m3,
                    **m4,
                    **m5,
                    # หน้า Entry Timing แสดงในแถบหัวหน้า (เดิมไม่มี backend ไหนส่งมา จึงขึ้น "-")
                    "sector_label": SECTOR_MAP.get(ticker, "Technology"),
                    "roe_pct": m1.get("roe"),
                    "data_as_of": latest_date,
                    "price_change_pct": change_pct,
                }
            )
        )

        for f, imp in feat_imp.items():
            all_feature_importance.append(
                {"ticker": ticker, "feature": f, "importance": imp}
            )

        if not backtest_df.empty:
            bt = backtest_df.copy()
            bt["ticker"] = ticker
            all_backtest.append(bt)

        rh = risk_analysis.build_risk_rolling_history(price_sub)
        rh["ticker"] = ticker
        all_risk_history.append(rh)

        hy = company_health.build_health_score_yearly(fin_sub)
        hy["ticker"] = ticker
        all_health_yearly.append(hy)

        fv = fair_value.build_fair_value_yearly(fin_sub, price_sub, ticker,
                                               params_by_year=params_by_year.get(ticker, {}))
        fv["ticker"] = ticker
        all_fair_value_yearly.append(fv)

    df_res = pd.DataFrame(all_summary)

    # ===== โมดูลสุดท้าย: Industry Benchmark =====
    df_res = industry_benchmark.compute_industry_rankings(df_res)
    df_res["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_res["calc_version"] = CALC_VERSION

    # แปลงคอลัมน์คงค้างที่เป็น dict/list อีกชั้นหนึ่งเพื่อความปลอดภัย 100%
    for col in df_res.columns:
        df_res[col] = df_res[col].apply(
            lambda x: json.dumps(x, ensure_ascii=False, default=str)
            if isinstance(x, (dict, list, tuple, set))
            else x
        )

    # ===== บันทึกผลลัพธ์ทั้งหมดลงฐานข้อมูล =====
    df_feat = pd.DataFrame(all_feature_importance)
    write_table(df_feat, "ai_feature_importance", engine)

    if all_backtest:
        df_bt = pd.concat(all_backtest, ignore_index=True)
        df_bt["date"] = df_bt["date"].astype(str)
        write_table(df_bt, "ai_backtest_history", engine)

    if all_risk_history:
        df_rh = pd.concat(all_risk_history, ignore_index=True)
        df_rh["date"] = df_rh["date"].astype(str)
        write_table(df_rh, "risk_rolling_history", engine)

    if all_health_yearly:
        df_hy = pd.concat(all_health_yearly, ignore_index=True)
        df_hy["date"] = df_hy["date"].astype(str) if "date" in df_hy.columns else ""
        write_table(df_hy, "health_score_yearly", engine)

    if all_fair_value_yearly:
        df_fv = pd.concat(all_fair_value_yearly, ignore_index=True)
        df_fv["date"] = df_fv["date"].astype(str) if "date" in df_fv.columns else ""
        write_table(df_fv, "fair_value_yearly", engine)

    # [v17.3] เขียนตารางสรุปเป็นตารางสุดท้าย — แอปเช็ค calc_version จากตารางนี้ จึงถือว่า "พร้อม" ได้
    # ก็ต่อเมื่อทุกตารางเขียนเสร็จแล้วเท่านั้น
    write_table(df_res, "cis_summary_scores", engine)

    print("\n✅ ประมวลผลและบันทึกคะแนนจริงของหุ้นทั้ง 8 ตัวลง cis_database.db เรียบร้อยแล้ว:")
    print("=" * 85)
    print(
        df_res[
            [
                "ticker",
                "current_price",
                "fair_value",
                "margin_of_safety",
                "overall_score",
                "recommendation",
                "health_score",
                "ai_score",
                "beta",
            ]
        ]
    )
    print("=" * 85)


if __name__ == "__main__":
    run_full_pipeline()
