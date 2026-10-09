"""
app.py — CIS Dashboard (Entry Point)
--------------------------------------
ไฟล์นี้ทำหน้าที่แค่ "ประกอบร่าง" ทั้งแอป ไม่มี logic การแสดงผลของแต่ละโมดูลอยู่ในนี้แล้ว
(ย้ายไปอยู่ที่ pages_content/*.py แยกไฟล์ตามโมดูล เพื่อให้ทีมแบ่งงานแก้ไขพร้อมกันได้โดยไม่ conflict กัน)

โครงสร้างที่เกี่ยวข้อง:
    common.py                            ← CSS, helper functions, การโหลดข้อมูล, PageContext, sidebar/header ที่ใช้ร่วมกัน
    pages_content/overview.py            ← หน้า Overview
    pages_content/company_health.py      ← หน้า Company Health
    pages_content/fair_value.py          ← หน้า Fair Value
    pages_content/entry_timing.py        ← หน้า Entry Timing
    pages_content/ai_prediction.py       ← หน้า AI Prediction
    pages_content/risk_analysis.py       ← หน้า Risk Analysis
    pages_content/industry_benchmark.py  ← หน้า Industry Benchmark

ถ้าคุณรับผิดชอบโมดูลใดโมดูลหนึ่ง ปกติไม่ต้องแก้ไฟล์นี้เลย ให้ไปแก้ที่ pages_content/<ชื่อโมดูล>.py ของตัวเอง
และทดสอบเดี่ยวด้วย `streamlit run preview_my_page.py` ก่อน แล้วค่อยรวมกับทีม
"""

import common
from pages_content import (
    overview,
    company_health,
    fair_value,
    entry_timing,
    ai_prediction,
    risk_analysis,
    industry_benchmark,
)


# 1. ตั้งค่าหน้าเว็บ + CSS ธีมทั้งหมด (ต้องเรียกเป็นคำสั่งแรกสุดของแอป)
common.setup_page_and_css()

# 2. เช็ค/สร้างฐานข้อมูลอัตโนมัติถ้ายังไม่พร้อม (เช่น deploy ใหม่ครั้งแรก)
common.ensure_database_ready()

# 3. โหลดข้อมูลทั้งหมดจากฐานข้อมูล (cache ไว้ ไม่โหลดซ้ำทุกครั้งที่เปลี่ยนหน้า)
try:
    (scores_df, daily_df, fin_df, feat_imp_df, backtest_df, risk_hist_df,
     health_yearly_df, fair_value_yearly_df, risk_static_df) = common.load_all_data()
    if scores_df.empty:
        raise ValueError("cis_summary_scores ว่างเปล่า")
except Exception as e:
    import streamlit as st
    st.error(f"⚠️ ไม่สามารถโหลดข้อมูลจากฐานข้อมูลได้: {e}\n\n"
              f"กรุณารัน `python import_data.py` แล้วตามด้วย `python calculate_scores.py` ก่อนเปิด Dashboard")
    st.stop()

# 4. Sidebar (โลโก้ + เมนู + เลือกหุ้น) → ได้หน้าที่เลือกกับหุ้นที่เลือกกลับมา
nav_page, selected_ticker = common.render_sidebar(scores_df)

# 4.1 [v17.4] เปลี่ยนหน้าแล้วเลื่อนขึ้นบนสุดของหน้าใหม่อัตโนมัติ
common.scroll_to_top_on_page_change(nav_page)

# 5. ประกอบ PageContext ส่งต่อให้ทุกหน้าใช้ร่วมกัน
ctx = common.build_context(
    selected_ticker=selected_ticker,
    scores_df=scores_df,
    daily_df=daily_df,
    fin_df=fin_df,
    feat_imp_df=feat_imp_df,
    backtest_df=backtest_df,
    risk_hist_df=risk_hist_df,
    health_yearly_df=health_yearly_df,
    fair_value_yearly_df=fair_value_yearly_df,
)

# 6. Header bar (เหมือนกันทุกหน้า)
common.render_header_bar(ctx)

# 7. Routing → เรียกหน้าที่เลือกอยู่
PAGE_RENDERERS = {
    " Stock Overview": overview.render,
    " Company Health": company_health.render,
    " Fair Value": fair_value.render,
    " Entry Timing": entry_timing.render,
    " AI Prediction": ai_prediction.render,
    " Risk Analysis": risk_analysis.render,
    " Industry Benchmark": industry_benchmark.render,
}

render_fn = PAGE_RENDERERS.get(nav_page, industry_benchmark.render)   # หน้าหลัก = Industry Benchmark
render_fn(ctx)
