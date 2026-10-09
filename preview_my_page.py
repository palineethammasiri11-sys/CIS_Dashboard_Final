"""
preview_my_page.py
--------------------
ไฟล์นี้ให้แต่ละคนใช้ดูหน้าโมดูลของตัวเอง "แบบเดี่ยว" โดยไม่ต้องรอให้คนอื่นในทีมทำเสร็จก่อน
และไม่ต้องรันแอปเต็ม (app.py) ที่มีทุกหน้ารวมกัน

รองรับทั้ง 2 กรณี:
    (A) แก้แค่ pages_content/<โมดูล>.py (หน้าตา/Layout)        → แค่ save ไฟล์ แล้ว refresh หน้าเว็บได้เลย
    (B) แก้ calculate_modules/<โมดูล>.py (สูตร/การคำนวณ)       → ต้องกดปุ่ม "🔄 คำนวณคะแนนใหม่" ด้านบนก่อน
        (เพราะตัวเลขที่แสดงมาจาก cis_database.db ที่ถูกคำนวณไว้ล่วงหน้า ไม่ได้คำนวณสดทุกครั้งที่เปิดหน้า
         กดปุ่มนี้ = สั่งรัน calculate_scores.py ใหม่ทั้งหมดด้วยโค้ดล่าสุดของคุณ แล้วโหลดผลลัพธ์ใหม่ทันที)

วิธีใช้:
1. แก้ตัวแปร MODULE_NAME ด้านล่างให้ตรงกับโมดูลที่คุณรับผิดชอบ (แก้บรรทัดเดียว)
2. รันคำสั่ง:
       streamlit run preview_my_page.py
3. ถ้าแก้สูตรใน calculate_modules/ → กดปุ่ม "🔄 คำนวณคะแนนใหม่จากสูตรล่าสุด" ทุกครั้งที่แก้เสร็จ
4. เลือกหุ้นจาก dropdown ไล่ดูให้ครบทั้ง 8 ตัว (ADVANC, CCET, DELTA, HANA, JMART, KCE, THCOM, TRUE)
   เพราะบางสูตรอาจพังเฉพาะบางหุ้น (เช่น หุ้นที่กำไรติดลบ, ค่าผิดปกติ)

ก่อนรันไฟล์นี้ครั้งแรก ต้องมีไฟล์ cis_database.db อยู่ในโฟลเดอร์เดียวกันแล้ว (ถ้ายังไม่มี ระบบจะสร้างให้อัตโนมัติ)
"""

import time
import importlib

import streamlit as st
import common

# ⬇️⬇️⬇️ แก้บรรทัดนี้บรรทัดเดียว ให้ตรงกับโมดูลที่คุณรับผิดชอบ ⬇️⬇️⬇️
MODULE_NAME = "industry_benchmark"
# ตัวเลือก: "overview", "company_health", "fair_value", "entry_timing",
#           "ai_prediction", "risk_analysis", "industry_benchmark"
# (หมายเหตุ: "overview" ไม่มีไฟล์คู่ใน calculate_modules/ เพราะเป็นหน้ารวมผลจากทุกโมดูล ไม่ได้คำนวณเอง)
# ⬆️⬆️⬆️ ส่วนล่างนี้ไม่ต้องแก้ ⬆️⬆️⬆️


common.setup_page_and_css()
common.ensure_database_ready()

my_page_module = importlib.import_module(f"pages_content.{MODULE_NAME}")
try:
    my_calc_module = importlib.import_module(f"calculate_modules.{MODULE_NAME}")
except ModuleNotFoundError:
    my_calc_module = None  # เช่น overview ที่ไม่มีไฟล์คำนวณของตัวเอง

st.markdown("### 🔍 Preview Mode — ดูหน้าโมดูลของตัวเองแบบเดี่ยว")
col_info, col_btn = st.columns([3, 1.3])

with col_info:
    st.caption(
        f"📄 หน้าจอ: `pages_content/{MODULE_NAME}.py`" +
        (f"  |  🧮 สูตรคำนวณ: `calculate_modules/{MODULE_NAME}.py`" if my_calc_module else "  |  🧮 ไม่มีไฟล์คำนวณเฉพาะ (หน้านี้รวมผลจากโมดูลอื่น)")
    )

with col_btn:
    if st.button("🔄 คำนวณคะแนนใหม่จากสูตรล่าสุด", use_container_width=True, type="primary"):
        with st.spinner("กำลังรัน calculate_scores.py ใหม่ทั้งหมด (ใช้เวลาสัก 10-30 วินาที)..."):
            import calculate_scores
            importlib.reload(calculate_scores)  # กันเคส Python cache โมดูลเก่าไว้ในหน่วยความจำ
            calculate_scores.run_full_pipeline()
            st.cache_data.clear()  # เคลียร์ cache ของ common.load_all_data() ให้โหลดข้อมูลใหม่
        st.success("คำนวณเสร็จแล้ว! กำลังโหลดข้อมูลใหม่...")
        time.sleep(0.8)
        st.rerun()

(scores_df, daily_df, fin_df, feat_imp_df, backtest_df, risk_hist_df,
 health_yearly_df, fair_value_yearly_df, risk_static_df) = common.load_all_data()

last_updated = scores_df['updated_at'].iloc[0] if 'updated_at' in scores_df.columns and not scores_df.empty else "ไม่ทราบ"
st.caption(f"🕒 ข้อมูลชุดนี้คำนวณล่าสุดเมื่อ: **{last_updated}** — ถ้าเพิ่งแก้ `calculate_modules/{MODULE_NAME}.py` แล้วเวลานี้ยังเก่า ให้กดปุ่ม 🔄 ด้านบนก่อน")

st.markdown("---")

selected_ticker = st.selectbox("เลือกหุ้นทดสอบ (ไล่ดูให้ครบทั้ง 8 ตัว)", scores_df['ticker'].unique())

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

common.render_header_bar(ctx)

st.markdown("---")

# เรียก render(ctx) ของโมดูลที่เลือกไว้ด้านบน — จะเห็นผลทั้งสูตรที่เพิ่งคำนวณใหม่ (ถ้ากดปุ่ม 🔄) และหน้าตาล่าสุด
my_page_module.render(ctx)
