"""
common.py
---------
โค้ดส่วนกลางที่ทุกหน้าของ CIS Dashboard ใช้ร่วมกัน

⚠️ กติกาสำคัญสำหรับทีม (9 คน):
- ไฟล์นี้เป็น "ของกลาง" ที่ทุกโมดูลอิงใช้ ถ้าจะแก้ (CSS, สี, ธีม, helper function, โครงสร้าง PageContext)
  ต้องแจ้ง/ขอความเห็นชอบจาก Layout Lead หรือ QA Lead ก่อนเสมอ ไม่งั้นจะกระทบทุกหน้าพร้อมกัน
- ห้าม copy โค้ดจากไฟล์นี้ไปแปะซ้ำในไฟล์หน้าโมดูลของตัวเอง — ให้ import มาใช้แทน
  (ถ้ามีจุดที่คิดว่าควรเพิ่ม helper ใหม่ที่ "ทุกหน้า" น่าจะได้ใช้ ให้เพิ่มที่นี่ที่เดียว)

โครงสร้างไฟล์:
1. ค่าคงที่ (TARGET_STOCKS, SECTOR_MAP, COMPANY_NAMES, PAGES)
2. CSS/ธีมของทั้งแอป
3. Helper functions ที่ใช้ข้ามหน้า (fmt_mb, safe, show_chart, render_nav_footer, create_gauge)
4. การเชื่อมต่อฐานข้อมูล + auto-healing (database_is_ready, build_database, load_all_data)
5. PageContext — โครงสร้างข้อมูลที่ส่งต่อให้ทุกหน้า
6. render_sidebar() / render_header_bar() — UI ส่วนที่ใช้ร่วมกันทุกหน้า
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from dataclasses import dataclass

from calculate_modules import labels as L


# ============================================================================
# 1. ค่าคงที่ที่ใช้ร่วมกันทั้งแอป
# ============================================================================
TARGET_STOCKS = ['ADVANC', 'CCET', 'DELTA', 'HANA', 'JMART', 'KCE', 'THCOM', 'TRUE']

SECTOR_MAP = {
    'ADVANC': 'Technology & Telecomm', 'TRUE': 'Technology & Telecomm', 'THCOM': 'Technology & Telecomm',
    'DELTA': 'Electronic Components', 'HANA': 'Electronic Components', 'KCE': 'Electronic Components',
    'CCET': 'Electronic Components', 'JMART': 'Commerce & Technology'
}

COMPANY_NAMES = {
    'ADVANC': 'Advanced Info Service PCL', 'CCET': 'Cal-Comp Electronics PCL', 'DELTA': 'Delta Electronics (Thailand) PCL',
    'HANA': 'Hana Microelectronics PCL', 'JMART': 'Jaymart Group Holdings PCL', 'KCE': 'KCE Electronics PCL',
    'THCOM': 'Thaicom PCL', 'TRUE': 'True Corporation PCL'
}

# ลำดับหน้า (Blueprint D18): เรื่อง "ควรซื้อไหม" (คุณภาพ ราคา ความเสี่ยง) มาก่อนเรื่อง "ซื้อเมื่อไร" (จังหวะ AI)
PAGES = [
    " Industry Benchmark", " Stock Overview", " Company Health", " Fair Value",
    " Risk Analysis", " Entry Timing", " AI Prediction"
]
HOME_PAGE = PAGES[0]

PAGE_COLORS = {
    " Industry Benchmark": "#06B6D4", " Stock Overview": "#3B82F6", " Company Health": "#10B981",
    " Fair Value": "#F59E0B", " Risk Analysis": "#EF4444", " Entry Timing": "#6366F1", " AI Prediction": "#A855F7",
}

# ============================================================================
# 2. CSS / ธีม Light Clean ของทั้งแอป
# ============================================================================
def setup_page_and_css():
    """เรียกครั้งเดียวตอนเริ่ม app.py เท่านั้น ห้ามเรียกซ้ำในไฟล์หน้าโมดูล"""
    st.set_page_config(
        page_title="CIS - Comprehensive Investment System",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>

        /* =========================================================
           GLOBAL — Clean Financial Platform
           ========================================================= */

        html, body, [class*="css"] {
            font-size: 16px;
        }

        .stApp {
            background-color: #F8FAFC;
        }

        .main .block-container {
            max-width: 1400px;
            padding-top: 2rem;
            padding-bottom: 3rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }


        /* =========================================================
           CARDS — Clean / Soft / Minimal
           ========================================================= */

        .metric-card {
            background: #FFFFFF;
            padding: 20px;
            border-radius: 14px;
            border: 1px solid #E2E8F0;
            text-align: center;
            height: 100%;
            box-shadow: none;
        }

        .hero-card {
            background: #FFFFFF;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #E2E8F0;
            box-shadow: none;
        }

        .dim-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: none;
        }


        /* =========================================================
           BUTTONS — Minimal
           ========================================================= */

        .stButton > button {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            color: #334155 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            padding: 9px 16px !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: none !important;
        }

        .stButton > button:hover {
            background-color: #F8FAFC !important;
            border-color: #CBD5E1 !important;
            color: #0F172A !important;
        }

        .stButton > button p {
            font-size: 14px !important;
            font-weight: 600 !important;
        }


        /* =========================================================
           SIDEBAR — Clean White
           ========================================================= */

        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E2E8F0;
        }

        [data-testid="stSidebar"] * {
            font-size: 15px;
        }


        /* Hide radio circles */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label > div:first-child,

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        input[type="radio"],

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        svg {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
        }


        /* Navigation spacing */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"] {
            gap: 4px !important;
        }


        /* Navigation item */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label {
            background-color: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 8px !important;
            padding: 10px 12px !important;
            margin: 0 !important;
            cursor: pointer !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            transition: all 0.15s ease-in-out !important;
        }


        /* Hover */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label:hover {
            background-color: #F8FAFC !important;
            border-color: #F1F5F9 !important;
        }


        /* Navigation text */

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label p {
            font-size: 14px !important;
            color: #475569 !important;
            font-weight: 500 !important;
            margin: 0 !important;
            line-height: 1.4 !important;
        }


        /* Sidebar labels */

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"]
        [data-testid="stCaptionContainer"] {
            color: #64748B !important;
        }
  
        [data-testid="stSidebar"]
        [data-testid="stSelectbox"]
        label p {
            color: #64748B !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }


        /* Selectbox */

        [data-testid="stSidebar"]
        [data-testid="stSelectbox"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"]
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border-color: #E2E8F0 !important;
            border-radius: 8px !important;
            color: #0F172A !important;
        }

        [data-testid="stSidebar"]
        [data-testid="stSelectbox"] [data-baseweb="select"] span {
            color: #0F172A !important;
        }


        /* =========================================================
           SECTION HEADINGS
           ========================================================= */

        h1, h2, h3 {
            color: #0F172A !important;
        }

        p {
            color: #475569;
        }

    </style>
    """, unsafe_allow_html=True)
  
# ============================================================================
# 3. Helper functions ที่ใช้ข้ามหน้า
# ============================================================================
def fmt_mb(x, unit="MB"):
    """แปลงตัวเลขบาทดิบ ให้เป็นหน่วยล้านบาท พร้อม comma"""
    if L.is_missing(x):
        return "N/A"
    try:
        return f"{float(x)/1e6:,.1f} {unit}"
    except Exception:
        return "N/A"


def fmt_ratio(v, suffix="x", decimals=2):
    """แสดงอัตราส่วน (P/E, P/B ฯลฯ) อย่างปลอดภัย — คืน '-' ถ้าเป็น None/NaN
    (เช่น หุ้นที่ EPS ติดลบจะไม่มีค่า P/E ที่มีความหมาย — ป้องกันไม่ให้จอโชว์ 'nanx')"""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        return f"{float(v):.{decimals}f}{suffix}"
    except Exception:
        return "-"


def safe(v, default=0.0):
    """แปลงค่าเป็น float อย่างปลอดภัย กัน None/NaN/string แปลกๆ ทำแอปพัง"""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)
    except Exception:
        return default


def create_gauge(score, title, color_hex):
    """เผื่อบางโมดูลอยากใช้ gauge แบบ Plotly Indicator (ปัจจุบันทุกหน้าใช้ SVG/HTML gauge เอง แต่มีฟังก์ชันนี้ไว้เผื่อ)"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={'font': {'size': 38, 'color': 'white'}},
        title={'text': f"<br><span style='font-size:15px;color:#94A3B8'>{title}</span>", 'font': {'size': 14}},
        gauge={'axis': {'range': [None, 100], 'visible': False}, 'bar': {'color': color_hex, 'thickness': 0.85},
               'bgcolor': "rgba(255,255,255,0.05)", 'borderwidth': 0}
    ))
    fig.update_layout(height=170, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


@st.dialog("ขยายกราฟ", width="large")
def _open_chart_dialog(fig, expand_height):
    big_fig = go.Figure(fig)
    big_fig.update_layout(height=expand_height)
    try:
        big_fig.update_xaxes(tickfont=dict(size=13))
        big_fig.update_yaxes(tickfont=dict(size=13))
    except Exception:
        pass
    st.plotly_chart(
        big_fig,
        use_container_width=True,
        config={
            'displayModeBar': True
        },
        key=f"dlg_{id(fig)}"
    )


def render_chart_note(key):
    """แถบพับ 'ⓘ วิธีอ่านกราฟและเทคนิคที่ใช้' ใต้กราฟ — ข้อความทั้งหมดอยู่ใน chart_notes.py
    (คอมเมนต์อาจารย์: ต้องระบุว่ากราฟแต่ละตัวใช้เทคนิคอะไร ไม่ใช่แสดงแค่กราฟ)"""
    try:
        from chart_notes import note_markdown
    except ImportError:
        return
    md = note_markdown(key)
    if md:
        with st.expander("ⓘ วิธีอ่านกราฟและเทคนิคที่ใช้", expanded=False):
            st.markdown(md)


def show_chart(fig, key, expand_height=680):
    """แสดงกราฟ Plotly พร้อมปุ่ม '🔍 ขยายกราฟ' ที่เปิดกราฟเวอร์ชันใหญ่ในหน้าต่างลอย (dialog)
    ใช้แทน st.plotly_chart ตรงๆ ทุกจุดที่เป็นกราฟหลักของหน้า
    ถ้า key มีคำอธิบายใน chart_notes.py จะแสดงแถบ 'ⓘ วิธีอ่านกราฟ' ใต้กราฟให้อัตโนมัติ"""
    # [FIX-UI9] ให้ Plotly ขยายขอบเองเมื่อชื่อแกน/ตัวเลขยาวเกิน แทนการตัดทิ้งบนจอแคบ (ไม่มีผลกับกราฟเรดาร์)
    try:
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
    except Exception:
        pass
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'responsive': True},
                    key=f"{key}_small")
    if st.button("🔍 ขยายกราฟ", key=f"{key}_expand_btn", use_container_width=True):
        _open_chart_dialog(fig, expand_height)
    render_chart_note(key)


def render_source_line(ctx):
    """G7: บรรทัดที่มาของข้อมูลท้ายหน้า (ช่วงวันที่ของราคาและปีงบอ่านจากข้อมูลจริง)"""
    try:
        d0 = pd.to_datetime(ctx.stock_daily['date']).min().strftime('%d/%m/%Y')
        d1 = pd.to_datetime(ctx.stock_daily['date']).max().strftime('%d/%m/%Y')
    except Exception:
        d0 = d1 = "-"
    fy = (f"FY{int(ctx.fin_stock['year'].min())}-FY{int(ctx.fin_stock['year'].max())}"
          if not ctx.fin_stock.empty else "-")
    st.html(f"""<div style="font-size:13px;color:#94A3B8;margin-top:10px;line-height:1.6;">
        ข้อมูลราคา: {d0} ถึง {d1} (Yahoo Finance ผ่านไฟล์ใน Dataset) · งบการเงิน: {fy} ·
        ดัชนีอ้างอิง Beta: TDEX (ETF อ้างอิง SET50) · WACC / Target P/E: Damodaran (2026)</div>""")


def render_nav_footer(ctx, current_page):
    """ปุ่มนำทางท้ายทุกหน้า (G5) — ก่อนหน้า/ถัดไปคิดจากลำดับ PAGES อัตโนมัติ, หน้าหลัก = Industry Benchmark"""
    idx = PAGES.index(current_page) if current_page in PAGES else 0
    prev_page = PAGES[idx - 1] if idx > 0 else None
    next_page = PAGES[idx + 1] if idx < len(PAGES) - 1 else None
    key_prefix = current_page.strip().replace(" ", "_").lower()
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown("""<div style="border-top:1px solid #E2E8F0; padding-top:16px; margin-bottom:6px;"></div>""", unsafe_allow_html=True)
    col_prev, col_home, col_next, col_disc = st.columns([1.3, 1.3, 1.3, 3.3])
    with col_prev:
        if prev_page and st.button(f"⬅ ก่อนหน้า: {prev_page.strip()}", key=f"btn_prev_{key_prefix}",
                                   use_container_width=True):
            st.session_state["pending_nav"] = prev_page
            st.rerun()
    with col_home:
        if current_page != HOME_PAGE and st.button("หน้าหลัก", key=f"btn_home_{key_prefix}", use_container_width=True):
            st.session_state["pending_nav"] = HOME_PAGE
            st.rerun()
    with col_next:
        if next_page and st.button(f"ถัดไป: {next_page.strip()} ➡", key=f"btn_next_{key_prefix}",
                                   use_container_width=True):
            st.session_state["pending_nav"] = next_page
            st.rerun()
    with col_disc:
        st.markdown('<div style="font-size:15px; color:#64748B; text-align:right; padding-top:11px; line-height:1.5;">'
                    'หมายเหตุ: การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูลก่อนการตัดสินใจลงทุน</div>', unsafe_allow_html=True)
    render_source_line(ctx)


# ----------------------------------------------------------------------------
# 3.1 Helper สำหรับแสดงผล (ทุกหน้าใช้ร่วมกัน — Blueprint 5.4 ข/จ)
# ----------------------------------------------------------------------------
NA = "N/A"
CARD = "background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:16px;box-sizing:border-box;"


def is_na(v):
    return L.is_missing(v)


def num(v):
    """float หรือ None (ไม่แทนค่าที่หายด้วย 0/50)"""
    return None if L.is_missing(v) else float(v)


def fmt_num(v, d=2, suffix="", sign=False, na=NA):
    if L.is_missing(v):
        return na
    x = float(v)
    return f"{'+' if sign and x > 0 else ''}{x:,.{d}f}{suffix}"


def fmt_pct(v, d=1, sign=False, na=NA):
    return fmt_num(v, d, "%", sign, na)


def fmt_score(v, d=0, na=NA):
    return fmt_num(v, d, "", False, na)


def html(markup):
    st.html(markup)


def page_title(title, subtitle):
    st.html(f"""<div style="margin-bottom:18px;">
        <div class="module-title" style="font-size:26px;font-weight:700;color:#0F172A;letter-spacing:0.3px;">{title}</div>
        <div class="module-subtitle" style="font-size:16px;color:#64748B;margin-top:4px;">{subtitle}</div></div>""")


def section_title(text, sub=""):
    sub_html = f'<span style="font-size:13.5px;font-weight:400;color:#94A3B8;margin-left:8px;">{sub}</span>' if sub else ""
    return (f'<div style="font-size:14.5px;font-weight:800;color:#475569;letter-spacing:0.5px;margin-bottom:10px;">'
            f'{text}{sub_html}</div>')


def badge(lab, size=13):
    """ป้ายสี จาก dict ที่ได้จาก labels.*_label()"""
    return (f'<span style="display:inline-block;background:{lab["bg"]};color:{lab["color"]};border:1px solid {lab["color"]};'
            f'border-radius:14px;padding:2px 10px;font-size:{size}px;font-weight:700;white-space:nowrap;">'
            f'{lab["th"]} · {lab["en"]}</span>')


def ring(score, color, center=None, sub="/100", size=92):
    """วงแหวนคะแนน 0-100 (score None → วงเทา)"""
    pct = 0 if L.is_missing(score) else max(0.0, min(100.0, float(score)))
    center = (NA if L.is_missing(score) else f"{float(score):.0f}") if center is None else center
    inner = size - 16
    return f"""<div style="margin:0 auto;width:{size}px;height:{size}px;border-radius:50%;
        background:conic-gradient({color} 0% {pct}%,#E2E8F0 {pct}% 100%);display:flex;align-items:center;justify-content:center;">
        <div style="width:{inner}px;height:{inner}px;border-radius:50%;background:#FFFFFF;display:flex;flex-direction:column;
        align-items:center;justify-content:center;"><span style="font-size:{int(size/4.3)}px;font-weight:800;color:#0F172A;line-height:1;">{center}</span>
        <span style="font-size:12.5px;color:#64748B;">{sub}</span></div></div>"""


def scale_bar(score, color, marks=(50, 65, 75), labels_txt=None):
    """แถบ 0-100 พร้อมขีดบอกเส้นเกณฑ์ (ใช้ในการ์ดคำแนะนำ)"""
    pct = 0 if L.is_missing(score) else max(0.0, min(100.0, float(score)))
    ticks = "".join(f'<div style="position:absolute;left:{m}%;top:-4px;height:18px;border-left:2px dashed #475569;"></div>'
                    f'<div style="position:absolute;left:{m}%;top:16px;transform:translateX(-50%);font-size:11.5px;color:#64748B;">{m}</div>'
                    for m in marks)
    return f"""<div style="position:relative;height:10px;background:#E2E8F0;border-radius:6px;margin:8px 0 22px 0;">
        <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;"></div>{ticks}</div>"""


def rank_text(info, col, with_sector=True):
    """'อันดับ x จาก n' (+ 'ในกลุ่ม y/m') จากคอลัมน์ rank_<col> ที่หลังบ้านคำนวณไว้"""
    r = info.get(f"rank_{col}")
    n = info.get(f"n_{col}")
    if L.is_missing(r) or L.is_missing(n):
        return "อันดับ N/A"
    txt = f"อันดับ {int(r)} จาก {int(n)}"
    sr, sn = info.get(f"srank_{col}"), info.get("sector_n")
    if with_sector and not L.is_missing(sr) and not L.is_missing(sn) and int(sn) > 1:
        txt += f" · ในกลุ่ม {int(sr)}/{int(sn)}"
    return txt


def na_box(text, color="#94A3B8"):
    return (f'<div style="background:rgba(148,163,184,0.10);border:1px dashed {color};border-radius:10px;padding:14px;'
            f'color:#475569;font-size:14.5px;line-height:1.6;">{text}</div>')


def json_list(v):
    import json
    try:
        out = json.loads(v) if isinstance(v, str) else (v or [])
        return out if isinstance(out, list) else []
    except Exception:
        return []


# ============================================================================
# 4. เชื่อมต่อฐานข้อมูล SQLite + ระบบซ่อมตัวเอง (auto-healing)
# ============================================================================
@st.cache_resource
def get_connection():
    return create_engine("sqlite:///cis_database.db")


def database_is_ready():
    """เช็คว่าฐานข้อมูลมีตารางผลลัพธ์พร้อมใช้งาน "และคำนวณด้วยสูตรเวอร์ชันปัจจุบัน" หรือไม่

    [FIX-UI1] เดิมเช็คแค่ว่ามีตาราง cis_summary_scores อยู่ → ถ้ามี DB เก่าค้างอยู่ แอปจะไม่คำนวณใหม่เลย
    แม้แก้สูตรใน calculate_modules/ แล้ว (สาเหตุที่ตัวเลขบนหน้าจอไม่เปลี่ยน) ตอนนี้เทียบ calc_version ใน DB
    กับ CALC_VERSION ใน calculate_scores.py ถ้าไม่ตรง → ถือว่ายังไม่พร้อม → build_database() คำนวณใหม่ให้เอง
    """
    try:
        from calculate_scores import CALC_VERSION
    except Exception:
        CALC_VERSION = None
    try:
        engine = get_connection()
        with engine.connect() as conn:
            if CALC_VERSION is None:
                conn.execute(text("SELECT ticker FROM cis_summary_scores LIMIT 1"))
                return True
            row = conn.execute(text("SELECT calc_version FROM cis_summary_scores LIMIT 1")).fetchone()
        return row is not None and row[0] == CALC_VERSION
    except Exception:
        return False


def build_database():
    """รัน import_data.py + calculate_scores.py อัตโนมัติ กรณีฐานข้อมูลหาย/ว่างเปล่า
    (เช่น ตอน deploy บน Streamlit Cloud แล้ว .db ไม่ได้ถูกอัปโหลดไปด้วย หรือ container ถูกสร้างใหม่)"""
    import os
    import import_data
    import calculate_scores

    missing = []
    if not import_data.find_file("*master_all_8_stocks_financials*.csv") and not import_data.find_all_files("*financials_train*.csv"):
        missing.append("งบการเงิน (master_all_8_stocks_financials*.csv หรือ financials_train/test*.csv)")
    if not import_data.find_file("*stock_cleaned*.csv"):
        missing.append("ราคาหุ้นรายวัน (stock_cleaned_data*.csv)")
    if not import_data.find_file("*stock_risk_metrics*.csv"):
        missing.append("ความเสี่ยง (stock_risk_metrics*.csv)")
    if not import_data.find_file("*valuation_params*.csv"):
        missing.append("WACC / Target P/E (valuation_params_2023_2025.csv)")

    if missing:
        cwd_listing = "\n".join(f"  - {f}" for f in sorted(os.listdir("."))) if os.path.isdir(".") else "(อ่านโฟลเดอร์ปัจจุบันไม่ได้)"
        ds_listing = "\n".join(f"  - {f}" for f in sorted(os.listdir("Dataset"))) if os.path.isdir("Dataset") else "  (ไม่พบโฟลเดอร์ Dataset/ เลย)"
        raise FileNotFoundError(
            "ไม่พบไฟล์ข้อมูลต่อไปนี้ใน repo: " + "; ".join(missing) +
            f"\n\nไฟล์/โฟลเดอร์ใน working directory ปัจจุบัน:\n{cwd_listing}" +
            f"\n\nไฟล์ใน Dataset/ ที่เจอ:\n{ds_listing}" +
            "\n\n➡️ กรุณาตรวจสอบว่าโฟลเดอร์ Dataset/ (พร้อมไฟล์ CSV ทั้ง 5 ไฟล์ รวม valuation_params_2023_2025.csv) ถูก push ขึ้น GitHub จริง "
            "(เช็คได้จากหน้า repo บน GitHub ว่าเห็นโฟลเดอร์ Dataset/ และไฟล์ .csv ข้างในหรือไม่ "
            "และเช็ค .gitignore ว่าไม่ได้ ignore *.csv หรือทั้งโฟลเดอร์ Dataset/ อยู่)"
        )

    engine = get_connection()
    import_data.import_all(engine)
    calculate_scores.run_full_pipeline()


@st.cache_data(ttl=600)
def load_all_data():
    """โหลดทุกตารางจากฐานข้อมูลครั้งเดียว (cache ไว้ 10 นาที) แชร์ให้ทุกหน้าใช้ร่วมกัน"""
    engine = get_connection()
    scores_df = pd.read_sql("SELECT * FROM cis_summary_scores ORDER BY ticker", engine)
    daily_df = pd.read_sql("SELECT * FROM stock_daily_prices ORDER BY ticker, date", engine)
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    fin_df = pd.read_sql("SELECT * FROM stock_financials ORDER BY ticker, year", engine)
    feat_imp_df = pd.read_sql("SELECT * FROM ai_feature_importance", engine)
    try:
        backtest_df = pd.read_sql("SELECT * FROM ai_backtest_history", engine)
        backtest_df['date'] = pd.to_datetime(backtest_df['date'])
    except Exception:
        backtest_df = pd.DataFrame()
    try:
        risk_hist_df = pd.read_sql("SELECT * FROM risk_rolling_history", engine)
        risk_hist_df['date'] = pd.to_datetime(risk_hist_df['date'])
    except Exception:
        risk_hist_df = pd.DataFrame()
    try:
        health_yearly_df = pd.read_sql("SELECT * FROM health_score_yearly", engine)
    except Exception:
        health_yearly_df = pd.DataFrame()
    try:
        fair_value_yearly_df = pd.read_sql("SELECT * FROM fair_value_yearly", engine)
    except Exception:
        fair_value_yearly_df = pd.DataFrame()
    try:
        risk_static_df = pd.read_sql("SELECT * FROM stock_risk_static", engine)
    except Exception:
        risk_static_df = pd.DataFrame()
    return scores_df, daily_df, fin_df, feat_imp_df, backtest_df, risk_hist_df, health_yearly_df, fair_value_yearly_df, risk_static_df


def ensure_database_ready():
    """เรียกจาก app.py ครั้งเดียวตอนเริ่มแอป — ถ้าฐานข้อมูลไม่พร้อมจะพยายามสร้างให้อัตโนมัติ
    return True ถ้าพร้อมใช้งาน, False ถ้าล้มเหลว (จะ st.stop() ให้เองถ้าล้มเหลว)"""
    if not database_is_ready():
        with st.spinner("⏳ กำลังประมวลผลข้อมูลครั้งแรก (import + calculate scores)... อาจใช้เวลาสักครู่"):
            try:
                build_database()
                st.cache_data.clear()
            except Exception as build_err:
                st.error(f"⚠️ สร้างฐานข้อมูลอัตโนมัติไม่สำเร็จ: {build_err}\n\n"
                         f"กรุณาตรวจสอบว่าโฟลเดอร์ `Dataset/` ถูกอัปโหลดขึ้น GitHub ครบถ้วน "
                         f"หรือรัน `python import_data.py` แล้วตามด้วย `python calculate_scores.py` เองก่อนเปิด Dashboard")
                st.stop()
    return True


# ============================================================================
# 5. PageContext — โครงสร้างข้อมูลที่ส่งให้ทุกหน้าโมดูล
# ============================================================================
@dataclass
class PageContext:
    """ข้อมูลทั้งหมดที่หน้าโมดูลแต่ละหน้าอาจต้องใช้ ถูกสร้างครั้งเดียวใน app.py ต่อ 1 รอบการรัน
    แล้วส่งต่อ (ctx) ให้ฟังก์ชัน render(ctx) ของแต่ละหน้าเรียกใช้

    ⚠️ ถ้าโมดูลของคุณต้องใช้ข้อมูลเพิ่มเติมที่ยังไม่มีใน ctx (เช่น ตารางใหม่ที่คุณเพิ่มใน calculate_scores.py)
    ให้เพิ่ม field ใหม่ตรงนี้ + เพิ่มการโหลดข้อมูลใน load_all_data() ด้านบน แล้วแจ้งทีมว่าเพิ่ม field อะไร
    """
    selected_ticker: str
    stock_info: dict
    stock_daily: pd.DataFrame
    fin_stock: pd.DataFrame
    sector_peers: pd.DataFrame
    scores_df: pd.DataFrame
    fin_df: pd.DataFrame
    feat_imp_df: pd.DataFrame
    backtest_df: pd.DataFrame
    risk_hist_df: pd.DataFrame
    health_yearly_df: pd.DataFrame
    fair_value_yearly_df: pd.DataFrame
    current_price: float
    change_pct: float
    change_val: float
    change_color: str
    change_sign: str
    arrow_sign: str


def build_context(selected_ticker, scores_df, daily_df, fin_df, feat_imp_df,
                   backtest_df, risk_hist_df, health_yearly_df, fair_value_yearly_df):
    """ประกอบ PageContext จากข้อมูลดิบที่โหลดมาจาก load_all_data() + ticker ที่เลือกใน sidebar"""
    stock_info = scores_df[scores_df['ticker'] == selected_ticker].iloc[0].to_dict()
    stock_daily = daily_df[daily_df['ticker'] == selected_ticker].sort_values('date').reset_index(drop=True)
    fin_stock = fin_df[fin_df['ticker'] == selected_ticker].sort_values('year').reset_index(drop=True)
    sector_peers = scores_df[scores_df['sector'] == stock_info['sector']]

    current_price = safe(stock_info.get('current_price'))
    change_pct = safe(stock_info.get('change_pct'))
    change_val = safe(stock_info.get('change_val'))
    change_color = "#10B981" if change_pct >= 0 else "#EF4444"
    change_sign = "+" if change_pct >= 0 else ""
    arrow_sign = "▲" if change_pct >= 0 else "▼"

    return PageContext(
        selected_ticker=selected_ticker,
        stock_info=stock_info,
        stock_daily=stock_daily,
        fin_stock=fin_stock,
        sector_peers=sector_peers,
        scores_df=scores_df,
        fin_df=fin_df,
        feat_imp_df=feat_imp_df,
        backtest_df=backtest_df,
        risk_hist_df=risk_hist_df,
        health_yearly_df=health_yearly_df,
        fair_value_yearly_df=fair_value_yearly_df,
        current_price=current_price,
        change_pct=change_pct,
        change_val=change_val,
        change_color=change_color,
        change_sign=change_sign,
        arrow_sign=arrow_sign,
    )


# ============================================================================
# 6. UI ส่วนกลาง: Sidebar + Header Bar (ใช้เหมือนกันทุกหน้า)
# ============================================================================
def render_sidebar(scores_df):
    """วาด sidebar (โลโก้, เมนู navigation, dropdown เลือกหุ้น) แล้ว return (nav_page, selected_ticker)"""
    st.sidebar.markdown("""
    <div style="padding: 8px 0 14px 0;">
        <div style="display: flex; align-items: flex-start; gap: 10px; min-width: 0;">
            <div style="width: 26px; height: 26px; flex-shrink: 0; border-radius: 7px; background:#0F172A; display:flex; align-items:center; justify-content:center;">
                <span style="font-size: 13px; font-weight:800; color:#FFFFFF;">CI</span>
            </div>
            <span style="font-size: 15px; font-weight: 800; color: #0F172A; letter-spacing: -0.1px; line-height: 1.3; min-width: 0; word-break: break-word; overflow-wrap: break-word;">
                Comprehensive Investment System
            </span>
        </div>
        <div style="font-size: 12px; color: #94A3B8; margin-top: 4px; padding-left: 36px; letter-spacing: 0.3px; font-weight: 600;">
            Investment Decision Support
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = PAGES[0]

    # ปุ่ม "หน้าก่อนหน้า/หน้าหลัก/หน้าถัดไป" (render_nav_footer) จะฝากคำขอเปลี่ยนหน้าไว้ใน pending_nav แล้ว rerun
    # ต้องอัปเดตค่าให้ widget ตรงนี้ (ก่อน radio ถูกสร้าง) เพราะ Streamlit ไม่อนุญาตให้แก้ session_state
    # ของ key ที่ widget ใช้อยู่ หลังจาก widget ถูกสร้างไปแล้วในรอบเดียวกัน
    # *** ห้ามลบ/ย้ายกลไกนี้โดยไม่ปรึกษาทีมก่อน — เคยเป็นบั๊กที่ sidebar ไม่ sync กับปุ่มนำทางมาแล้ว ***
    
    if "pending_nav" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("pending_nav")


    # =========================
    # COMPANY SELECTOR
    # =========================

    st.sidebar.markdown(
        "<div style='font-size:12px; font-weight:700; color:#64748B; "
        "margin-bottom:6px; letter-spacing:0.5px;'>COMPANY</div>",
        unsafe_allow_html=True
    )

    # G2: ค่าเริ่มต้น = หุ้นอันดับ 1 ของคะแนนรวม (เปิดมาเจอหุ้นที่น่าสนใจที่สุดก่อน)
    tickers = list(scores_df.sort_values('ticker')['ticker'].unique())
    default_idx = 0
    if 'overall_rank' in scores_df.columns:
        top = scores_df.sort_values('overall_rank')['ticker']
        if not top.empty and top.iloc[0] in tickers:
            default_idx = tickers.index(top.iloc[0])
    selected_ticker = st.sidebar.selectbox(
        "Choose a company",
        tickers,
        index=default_idx,
        format_func=lambda t: f"{t} — {COMPANY_NAMES.get(t, '')}",
        label_visibility="collapsed",
        key="selected_ticker",
    )

    st.sidebar.markdown("---")

    selected_page = st.sidebar.radio(
        "Navigation",
        PAGES,
        key="nav_page"
    )

    nav_colors = PAGE_COLORS

    active_color = nav_colors.get(selected_page, "#3B82F6")

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label:has(input:checked) {{
            background-color: {active_color}12 !important;
            border: 1px solid {active_color}30 !important;
            box-shadow: none !important;
        }}

        [data-testid="stSidebar"]
        [data-testid="stRadio"]
        div[role="radiogroup"]
        label:has(input:checked) p {{
            color: {active_color} !important;
            font-weight: 700 !important;
        }}

      /* =========================================================
         RESPONSIVE / MOBILE
         ========================================================= */

        @media (max-width: 768px) {{

            /* ---------- Main content ---------- */
            .main .block-container {{
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
                padding: 1rem 0.85rem 2rem 0.85rem !important;
            }}

            /* ---------- Prevent horizontal overflow ---------- */
            html,
            body,
            .stApp {{
                width: 100% !important;
                max-width: 100vw !important;
                overflow-x: hidden !important;
            }}

            .main,
            .main > div,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {{
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: hidden !important;
                box-sizing: border-box !important;
            }}

            /* ---------- HTML cards / markdown blocks ---------- */
            .stMarkdown,
            .stMarkdown > div {{
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}

            .stMarkdown div {{
                max-width: 100%;
                box-sizing: border-box;
            }}

            /* ---------- Responsive HTML grids ---------- */
            .stMarkdown [style*="grid-template-columns"] {{
                width: 100% !important;
                max-width: 100% !important;
                grid-template-columns: 1fr !important;
                box-sizing: border-box !important;
            }}

            .stMarkdown [style*="grid-template-columns"] > div {{
                min-width: 0 !important;
                max-width: 100% !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }}

            /* ---------- Prevent inner flex overflow ---------- */
            .stMarkdown [style*="display:flex"] {{
                max-width: 100% !important;
                box-sizing: border-box !important;
                min-width: 0 !important;
            }}

            .stMarkdown [style*="display:flex"] > * {{
                min-width: 0 !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}

            /* ---------- Streamlit columns ---------- */
            [data-testid="stHorizontalBlock"] {{
                width: 100% !important;
                max-width: 100% !important;
                flex-wrap: wrap !important;
                gap: 0.75rem !important;
                box-sizing: border-box !important;
            }}

            /* [FIX-UI9] Streamlit รุ่นใหม่ใช้ data-testid="stColumn" (เดิม "column") — ใส่ทั้งสองชื่อ
               ไม่งั้นกฎจัดคอลัมน์บนมือถือไม่ทำงานเลย การ์ดจึงถูกบีบอยู่แถวเดียว */
            [data-testid="column"],
            [data-testid="stColumn"] {{
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 100% !important;
                box-sizing: border-box !important;
            }}
        
            /* ---------- Shared Header ---------- */
            .cis-header {{
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 10px !important;
                padding: 14px 16px !important;
            }}
  
            .cis-header-info {{
                width: 100% !important;
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 6px 10px !important;
                font-size: 13px !important;
            }}

            .cis-header-divider {{
                display: none !important;
            }}

            /* ---------- Titles ---------- */
            .module-title {{
                font-size: 21px !important;
                line-height: 1.25 !important;
            }}

            .module-subtitle {{
                font-size: 14px !important;
                line-height: 1.5 !important;
            }}

            /* ---------- Tables ---------- */
            [data-testid="stDataFrame"] {{
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                box-sizing: border-box !important;
            }}

            /* ---------- Plotly charts ---------- */
            .js-plotly-plot,
            .plot-container,
            .plotly,
            [data-testid="stPlotlyChart"] {{
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}
        }}

        /* =========================
           iPad / Tablet
           769px - 1024px
           ========================= */
        @media (min-width: 769px) and (max-width: 1024px) {{

            .main .block-container {{
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
                padding: 1.5rem 1.5rem 2.5rem 1.5rem !important;
            }}

            [data-testid="stHorizontalBlock"] {{
                width: 100% !important;
                max-width: 100% !important;
                gap: 1rem !important;
                box-sizing: border-box !important;
            }}

            [data-testid="column"],
            [data-testid="stColumn"] {{
                min-width: 0 !important;
                box-sizing: border-box !important;
            }}

            /* [FIX-UI9] แถวที่มีการ์ดตั้งแต่ 4 ใบขึ้นไป (เช่น การ์ด KPI 5 ใบ) ให้ขึ้นบรรทัดใหม่เป็นแถวละ 3 ใบ
               แทนการบีบทุกใบให้แคบจนข้อความตกบรรทัด — แถว 2-3 คอลัมน์ยังอยู่บรรทัดเดียวตามเดิม */
            [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) {{
                flex-wrap: wrap !important;
                row-gap: 1rem !important;
            }}
            [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"],
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) > [data-testid="column"] {{
                flex: 1 1 calc(33.333% - 1rem) !important;
                min-width: 200px !important;
            }}

            .module-title {{
                font-size: 24px !important;
            }}

            .stMarkdown,
            .stMarkdown > div {{
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}

            [data-testid="stDataFrame"] {{
                max-width: 100% !important;
                overflow-x: auto !important;
                box-sizing: border-box !important;
            }}

            .js-plotly-plot,
            .plot-container,
            .plotly,
            [data-testid="stPlotlyChart"] {{
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}
        }}


        /* =========================================================
           VERY SMALL MOBILE
           ========================================================= */

        @media (max-width: 480px) {{

            .main .block-container {{
                padding: 0.75rem 0.65rem 1.5rem 0.65rem !important;
            }}

            .module-title {{
                font-size: 19px !important;
            }}

            .module-subtitle {{
                font-size: 13.5px !important;
            }}

            [data-testid="stHorizontalBlock"] {{
                gap: 0.6rem !important;
            }}
        }}

        </style>
         """,
         unsafe_allow_html=True
     )

    nav_page = st.session_state["nav_page"]


    # =========================
    # DATA INFORMATION
    # =========================

    st.sidebar.caption(
        f"📅 ข้อมูล ณ วันที่ล่าสุดในชุดข้อมูล: **{scores_df['latest_date'].max()}**\n\n"
        f"(ราคาทั้งหมดอ้างอิงจากไฟล์ Dataset ไม่ใช่ราคาตลาดสด)"
    )

    return nav_page, selected_ticker


def render_header_bar(ctx):
    """G4: แถบหัวทุกหน้า (ชื่อหุ้น, กลุ่ม, ราคา, % เปลี่ยน, P/E, ROE พร้อมป้าย FY, วันที่ข้อมูล)"""
    info = ctx.stock_info
    pe = info.get('pe_ratio')
    pe_txt = "N/A (ขาดทุน)" if L.is_missing(pe) else f"{float(pe):.2f}x"
    fy = info.get('health_fy')
    fy_txt = f"FY{int(fy)}" if not L.is_missing(fy) else "FY"
    roe = info.get('roe')
    roe_txt = NA if L.is_missing(roe) else f"{float(roe):.2f}%"
    st.markdown(f"""
    <div class="cis-header" style="display:flex; justify-content:space-between; align-items:center; background:#FFFFFF; padding:14px 24px; border-radius:12px; border:1px solid #E2E8F0; margin-bottom:20px;">
        <div>
            <span style="font-size:24px; font-weight:bold; color:#0F172A;">{ctx.selected_ticker}</span>
            <span style="color:#64748B; font-size:15px; margin-left:8px;">{COMPANY_NAMES.get(ctx.selected_ticker, '')} · {info.get('sector','-')} (SET)</span>
        </div>
        <div class="cis-header-info" style="font-size:16px; color:#64748B;">
            ราคา: <b style="color:#0F172A; font-size:19px;">{ctx.current_price:.2f}</b> บาท
            <span style="color:{ctx.change_color}; font-weight:bold; margin-left:6px;">({ctx.change_sign}{ctx.change_pct:.2f}%) {ctx.arrow_sign}</span>
            <span class="cis-header-divider" style="margin: 0 12px; color:#CBD5E1;">|</span>
            P/E ({fy_txt}): <b style="color:#0F172A;">{pe_txt}</b>
            <span class="cis-header-divider" style="margin: 0 12px; color:#CBD5E1;">|</span>
            ROE ({fy_txt}): <b style="color:#0F172A;">{roe_txt}</b>
            <span class="cis-header-divider" style="margin: 0 12px; color:#CBD5E1;">|</span>
            ข้อมูล ณ: <b style="color:#475569;">{info.get('latest_date','-')}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
