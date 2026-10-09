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
2. CSS/ธีมของทั้งแอป (Design tokens ชุดเดียว — v17.4)
3. Helper functions ที่ใช้ข้ามหน้า (fmt_*, kpi, card, grid, show_chart, render_nav_footer)
4. การเชื่อมต่อฐานข้อมูล + auto-healing (database_is_ready, build_database, load_all_data)
5. PageContext — โครงสร้างข้อมูลที่ส่งต่อให้ทุกหน้า
6. render_sidebar() / render_header_bar() / scroll_to_top_on_page_change() — UI ส่วนที่ใช้ร่วมกันทุกหน้า

[v17.4] ปรับ UX/UI ทั้งแอป
- เปลี่ยนหน้าแล้วเลื่อนขึ้นบนสุดอัตโนมัติ (scroll_to_top_on_page_change)
- ระยะห่าง/ขนาดตัวอักษร/การ์ดชุดเดียวทุกหน้า (ค่าคงที่ GAP, CARD, ฟังก์ชัน kpi(), grid(), card())
- แถวการ์ดใช้ CSS Grid ใน HTML ก้อนเดียว → การ์ดในแถวเดียวกันสูงเท่ากันเสมอ
- ใต้กราฟเหลือแถบเครื่องมือแถวเดียว: "ⓘ วิธีอ่านกราฟ" (popover ไม่กินพื้นที่) + "🔍 ขยายกราฟ"
- กราฟทุกตัวใช้รูปแบบเดียวกัน (style_fig) และกันข้อความ/ชื่อแกนทับกัน
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

# ---------------------------------------------------------------------------
# Design tokens (v17.4) — แก้ที่นี่ที่เดียว ทุกหน้าใช้ร่วมกัน
# ---------------------------------------------------------------------------
GAP = 12                       # ระยะห่างระหว่างการ์ด (px) — เท่ากับช่องว่างของคอลัมน์ Streamlit ใน CSS ด้านล่าง
INK, INK2, MUTED, FAINT = "#0F172A", "#334155", "#64748B", "#94A3B8"
LINE, SOFT, PANEL = "#E2E8F0", "#F1F5F9", "#F8FAFC"
CHART_H = 300                  # ความสูงมาตรฐานของกราฟ (px)
TOOLS_H = 46                   # ความสูงแถบเครื่องมือใต้กราฟ (ปุ่ม 34 px + ระยะห่าง 12 px) — ใช้คำนวณให้การ์ดข้างกราฟสูงเท่ากัน
FONT = '"Source Sans Pro", "Sarabun", "Leelawadee UI", "Tahoma", sans-serif'


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

    st.markdown(f"""
    <style>
        /* =========================================================
           GLOBAL
           ========================================================= */
        .stApp {{ background-color: {PANEL}; }}
        .stApp, .stApp p, .stApp li {{ font-size: 14.5px; }}
        p {{ color: #475569; }}
        h1, h2, h3 {{ color: {INK} !important; }}

        /* แถบหัวของ Streamlit ให้โปร่งและเตี้ยลง เนื้อหาจึงขึ้นได้สูงขึ้น */
        header[data-testid="stHeader"] {{ background: transparent; height: 2.6rem; }}

        /* พื้นที่เนื้อหาหลัก (Streamlit 1.38+ ใช้ stMainBlockContainer; รุ่นเก่าใช้ .main .block-container) */
        [data-testid="stMainBlockContainer"], .stMainBlockContainer, .main .block-container {{
            max-width: 1480px;
            padding: 2.6rem 2rem 2rem 2rem !important;
        }}

        /* ระยะห่างแนวตั้ง/แนวนอนชุดเดียวทั้งแอป */
        [data-testid="stMain"] [data-testid="stVerticalBlock"] {{ gap: {GAP}px; }}
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{ gap: {GAP}px; }}
        [data-testid="stElementContainer"]:has(> iframe[height="0"]),
        .element-container:has(> iframe[height="0"]) {{ display: none; }}

        /* =========================================================
           CARDS
           ========================================================= */
        .cis-card {{
            background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px;
            padding: 14px 16px; box-sizing: border-box; min-width: 0;
        }}
        .cis-grid {{ display: grid; gap: {GAP}px; align-items: stretch; }}
        .cis-grid > * {{ min-width: 0; }}
        /* กราฟทุกตัวเป็นการ์ดเดียวกับการ์ด HTML (กรอบ มุมโค้ง พื้นขาว) */
        [data-testid="stPlotlyChart"] {{
            background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; box-sizing: border-box;
        }}
        [data-testid="stDialog"] [data-testid="stPlotlyChart"] {{ border: none; }}

        /* =========================================================
           BUTTONS / POPOVER / EXPANDER
           ========================================================= */
        .stButton > button, [data-testid="stPopover"] > div > button {{
            background-color: #FFFFFF !important;
            border: 1px solid {LINE} !important;
            color: {INK2} !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 4px 12px !important;
            min-height: 34px !important;
            box-shadow: none !important;
            transition: all 0.15s ease-in-out !important;
        }}
        .stButton > button p, [data-testid="stPopover"] > div > button p {{
            font-size: 13px !important; font-weight: 600 !important;
        }}
        .stButton > button:hover, [data-testid="stPopover"] > div > button:hover {{
            background-color: {PANEL} !important; border-color: #CBD5E1 !important; color: {INK} !important;
        }}
        [data-testid="stPopoverBody"] {{ max-width: 560px; }}
        [data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] li {{ font-size: 13.5px; line-height: 1.6; }}

        /* ตัวเลือกช่วงเวลา (radio แนวนอน) ให้เป็นแถวเตี้ย ๆ */
        [data-testid="stMain"] [data-testid="stRadio"] label p {{ font-size: 13px; }}
        [data-testid="stMain"] [data-testid="stRadio"] > label {{ display: none; }}
        [data-testid="stMain"] [data-testid="stSelectbox"] label p {{ font-size: 13px; color: {MUTED}; }}

        /* =========================================================
           SIDEBAR
           ========================================================= */
        [data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid {LINE}; }}
        [data-testid="stSidebar"] * {{ font-size: 14.5px; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label > div:first-child,
        [data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"],
        [data-testid="stSidebar"] [data-testid="stRadio"] svg {{
            display: none !important; width: 0 !important; height: 0 !important; margin: 0 !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {{ gap: 2px !important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {{
            background-color: transparent !important; border: 1px solid transparent !important;
            border-radius: 8px !important; padding: 8px 12px !important; margin: 0 !important;
            cursor: pointer !important; width: 100% !important; display: flex !important; align-items: center !important;
            transition: all 0.15s ease-in-out !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {{
            background-color: {PANEL} !important; border-color: {SOFT} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p {{
            font-size: 14px !important; color: #475569 !important; font-weight: 500 !important;
            margin: 0 !important; line-height: 1.4 !important;
        }}
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div {{
            background-color: #FFFFFF !important; border: 1px solid {LINE} !important;
            border-radius: 8px !important; box-shadow: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
            background-color: #FFFFFF !important; border-color: {LINE} !important;
            border-radius: 8px !important; color: {INK} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] span {{ color: {INK} !important; }}
        [data-testid="stSidebar"] hr {{ margin: 10px 0 !important; }}
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


# ----------------------------------------------------------------------------
# 3.1 กราฟ: รูปแบบเดียวกันทุกหน้า + แถบเครื่องมือใต้กราฟ
# ----------------------------------------------------------------------------
def style_fig(fig, height=CHART_H, legend=False, margin=None, title=None, sub=None):
    """รูปแบบมาตรฐานของกราฟทุกตัว (ฟอนต์ สีพื้น เส้นตาราง ระยะขอบ หัวข้อในกรอบกราฟ)
    - title/sub: หัวข้ออยู่ "ในกรอบกราฟ" มุมซ้ายบน → กราฟทุกตัวเป็นการ์ดเดียวกับหัวข้อ (สูงเท่ากันเมื่อวางคู่กัน)
    - legend=True: วาง legend ใต้หัวข้อ เหนือพื้นที่กราฟ (ไม่ทับเส้นกราฟ ไม่ทับหัวข้อ)
    - automargin ให้ Plotly ขยายขอบเองเมื่อชื่อแกน/ตัวเลขยาว (กันข้อความถูกตัด/ทับกัน)
    - ชื่อแกนห่างจากตัวเลขบนแกน (title standoff) กันชื่อแกนภาษาไทยทับตัวเลข"""
    top = 14 + (32 if title else 0) + (26 if legend else 0)
    m = dict(l=10, r=14, t=top, b=10)
    if margin:
        m.update(margin)
    fig.update_layout(
        height=height, margin=m, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family=FONT, size=12, color="#475569"),
        hoverlabel=dict(font=dict(family=FONT, size=12)),
        showlegend=legend,
    )
    if title:
        t = f"<b>{title}</b>"
        if sub:
            t += f"<span style='font-size:12px;color:{FAINT};font-weight:400;'>   {sub}</span>"
        fig.update_layout(title=dict(text=t, x=0, xanchor="left", xref="container", y=1, yanchor="top",
                                     yref="container", pad=dict(t=12, l=14),
                                     font=dict(family=FONT, size=13.5, color=INK2)))
    if legend:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                                      font=dict(size=11.5), bgcolor="rgba(255,255,255,0)"))
    try:
        fig.update_xaxes(automargin=True, gridcolor=SOFT, zeroline=False, title_standoff=8,
                         title_font=dict(size=12), tickfont=dict(size=11.5))
        fig.update_yaxes(automargin=True, gridcolor=SOFT, zeroline=False, title_standoff=10,
                         title_font=dict(size=12), tickfont=dict(size=11.5))
    except Exception:
        pass
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
    st.plotly_chart(big_fig, use_container_width=True, config={'displayModeBar': True}, key=f"dlg_{id(fig)}")


def render_chart_note(key, compact=False):
    """ปุ่ม 'ⓘ วิธีอ่านกราฟ' แบบ popover (เปิดเป็นกล่องลอย ไม่ดันเนื้อหาลง) — ข้อความทั้งหมดอยู่ใน chart_notes.py
    (คอมเมนต์อาจารย์: ต้องระบุว่ากราฟแต่ละตัวใช้เทคนิคอะไร ไม่ใช่แสดงแค่กราฟ)"""
    try:
        from chart_notes import note_markdown
    except ImportError:
        return
    md = note_markdown(key)
    if not md:
        return
    label = "ⓘ วิธีอ่าน" if compact else "ⓘ วิธีอ่านกราฟและเทคนิค"
    with st.popover(label, use_container_width=True):
        st.markdown(md)


def show_chart(fig, key, expand_height=680, expandable=True, compact_tools=False):
    """แสดงกราฟ Plotly + แถบเครื่องมือแถวเดียวใต้กราฟ: [ⓘ วิธีอ่านกราฟ] [🔍 ขยายกราฟ]
    ใช้ฟังก์ชันนี้แทน st.plotly_chart ตรง ๆ ทุกจุด (กราฟทุกตัวจะหน้าตาเหมือนกัน)
    compact_tools=True → ข้อความปุ่มสั้น (ใช้กับกราฟที่อยู่ในคอลัมน์แคบ เช่น 3 กราฟเรียงกัน)"""
    try:
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
    except Exception:
        pass
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'responsive': True},
                    key=f"{key}_small")
    try:
        from chart_notes import CHART_NOTES
        has_note = key in CHART_NOTES
    except ImportError:
        has_note = False
    if not (has_note or expandable):
        return
    cols = st.columns(2) if (has_note and expandable) else [st.container()]
    i = 0
    if has_note:
        with cols[i]:
            render_chart_note(key, compact=compact_tools)
        i += 1
    if expandable:
        with cols[min(i, len(cols) - 1)]:
            if st.button("🔍 ขยาย" if compact_tools else "🔍 ขยายกราฟ", key=f"{key}_expand_btn", use_container_width=True):
                _open_chart_dialog(fig, expand_height)


def render_source_line(ctx):
    """G7: บรรทัดที่มาของข้อมูลท้ายหน้า (ช่วงวันที่ของราคาและปีงบอ่านจากข้อมูลจริง)"""
    try:
        d0 = pd.to_datetime(ctx.stock_daily['date']).min().strftime('%d/%m/%Y')
        d1 = pd.to_datetime(ctx.stock_daily['date']).max().strftime('%d/%m/%Y')
    except Exception:
        d0 = d1 = "-"
    fy = (f"FY{int(ctx.fin_stock['year'].min())}-FY{int(ctx.fin_stock['year'].max())}"
          if not ctx.fin_stock.empty else "-")
    st.html(f"""<div style="font-size:12.5px;color:{FAINT};line-height:1.6;">
        ข้อมูลราคา: {d0} ถึง {d1} (Yahoo Finance ผ่านไฟล์ใน Dataset) · งบการเงิน: {fy} ·
        ดัชนีอ้างอิง Beta: TDEX (ETF อ้างอิง SET50) · WACC / Target P/E: Damodaran (2026)</div>""")


def render_nav_footer(ctx, current_page):
    """ปุ่มนำทางท้ายทุกหน้า (G5) — ก่อนหน้า/ถัดไปคิดจากลำดับ PAGES อัตโนมัติ, หน้าหลัก = Industry Benchmark"""
    idx = PAGES.index(current_page) if current_page in PAGES else 0
    prev_page = PAGES[idx - 1] if idx > 0 else None
    next_page = PAGES[idx + 1] if idx < len(PAGES) - 1 else None
    key_prefix = current_page.strip().replace(" ", "_").lower()
    st.html(f'<div style="border-top:1px solid {LINE};margin-top:6px;"></div>')
    col_prev, col_home, col_next, col_disc = st.columns([1.75, 0.9, 1.75, 2.4], vertical_alignment="center")
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
        st.html(f'<div style="font-size:13px;color:{MUTED};text-align:right;line-height:1.5;">'
                'หมายเหตุ: การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูลก่อนการตัดสินใจลงทุน</div>')
    render_source_line(ctx)


# ----------------------------------------------------------------------------
# 3.2 Helper สำหรับแสดงผล (ทุกหน้าใช้ร่วมกัน — Blueprint 5.4 ข/จ)
# ----------------------------------------------------------------------------
NA = "N/A"
CARD = f"background:#FFFFFF;border:1px solid {LINE};border-radius:12px;padding:14px 16px;box-sizing:border-box;min-width:0;"
TILE = f"background:{PANEL};border:1px solid {LINE};border-radius:10px;padding:10px 12px;box-sizing:border-box;min-width:0;"


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


def card(inner, style="", cls=""):
    """การ์ดพื้นขาวมาตรฐาน (ใช้ซ้อนใน grid ได้)"""
    return f'<div class="cis-card {cls}" style="height:100%;{style}">{inner}</div>'


def centered_card(title_html, body, style=""):
    """การ์ดที่หัวข้ออยู่บน และเนื้อหาอยู่กึ่งกลางแนวตั้งของพื้นที่ที่เหลือ
    (ใช้กับการ์ดคะแนนที่ถูกยืดให้สูงเท่ากราฟข้าง ๆ → ไม่มีที่ว่างโล่งค้างอยู่ด้านล่าง)"""
    return (f'<div class="cis-card" style="height:100%;display:flex;flex-direction:column;{style}">{title_html}'
            f'<div style="flex:1 1 auto;display:flex;flex-direction:column;justify-content:center;">{body}</div></div>')


def grid(items, cols=None, template=None, style=""):
    """วางการ์ดหลายใบในแถวเดียวด้วย CSS Grid → ทุกใบสูงเท่ากันเสมอ (แก้ปัญหาการ์ดสูงไม่เท่ากัน/ช่องว่างไม่สมมาตร)
    cols: จำนวนคอลัมน์เท่ากัน หรือ template: เช่น '1fr 2fr'"""
    tpl = template or f"repeat({cols or len(items)},minmax(0,1fr))"
    return f'<div class="cis-grid" style="grid-template-columns:{tpl};{style}">{"".join(items)}</div>'


def page_title(title, subtitle):
    st.html(f"""<div style="margin:0 0 2px 0;">
        <div class="module-title" style="font-size:22px;font-weight:800;color:{INK};letter-spacing:0.3px;line-height:1.25;">{title}</div>
        <div class="module-subtitle" style="font-size:14px;color:{MUTED};margin-top:2px;line-height:1.5;">{subtitle}</div></div>""")


def section_title(text, sub="", mb=8):
    """หัวข้อย่อยรูปแบบเดียวทั้งแอป (คำอธิบายเสริมต่อท้ายตัวเล็ก ตัดบรรทัดได้ ไม่ดันความสูงจนไม่เท่ากัน)"""
    sub_html = f'<span style="font-size:12.5px;font-weight:400;color:{FAINT};margin-left:6px;">{sub}</span>' if sub else ""
    return (f'<div style="font-size:13.5px;font-weight:800;color:{INK2};letter-spacing:0.3px;margin-bottom:{mb}px;'
            f'line-height:1.45;">{text}{sub_html}</div>')


def chart_header(text, sub="", lines=1):
    """หัวข้อเหนือกราฟที่อยู่เคียงกันหลายกราฟ — กำหนดความสูงคงที่ ให้กราฟทุกตัวเริ่มที่บรรทัดเดียวกัน"""
    h = 22 * lines
    st.html(f'<div style="min-height:{h}px;">{section_title(text, sub, mb=0)}</div>')


def kpi(label, value, sub="", color=INK, size=22, grey=False):
    """การ์ดตัวเลขหลัก (KPI) รูปแบบเดียวทั้งแอป — ใช้คู่กับ grid() เพื่อให้ทุกใบสูงเท่ากัน"""
    bg = f"background:{SOFT};" if grey else ""
    c = FAINT if grey else color
    return (f'<div class="cis-card" style="height:100%;{bg}">'
            f'<div style="font-size:12.5px;font-weight:700;color:{MUTED};letter-spacing:0.2px;">{label}</div>'
            f'<div style="font-size:{size}px;font-weight:800;color:{c};margin-top:2px;line-height:1.3;">{value}</div>'
            f'<div style="font-size:12.5px;color:{MUTED};margin-top:3px;line-height:1.5;">{sub}</div></div>')


def tile(label, value, sub="", color=INK, size=17):
    """กล่องย่อยพื้นเทาอ่อน (ใช้ภายในการ์ด)"""
    return (f'<div style="{TILE}"><div style="font-size:12.5px;color:{MUTED};font-weight:600;">{label}</div>'
            f'<div style="font-size:{size}px;font-weight:800;color:{color};margin-top:2px;line-height:1.3;">{value}</div>'
            f'<div style="font-size:12px;color:{MUTED};margin-top:2px;line-height:1.45;">{sub}</div></div>')


def badge(lab, size=12.5):
    """ป้ายสี จาก dict ที่ได้จาก labels.*_label()"""
    return (f'<span style="display:inline-block;background:{lab["bg"]};color:{lab["color"]};border:1px solid {lab["color"]};'
            f'border-radius:14px;padding:1px 10px;font-size:{size}px;font-weight:700;white-space:nowrap;">'
            f'{lab["th"]} · {lab["en"]}</span>')


def ring(score, color, center=None, sub="/100", size=92):
    """วงแหวนคะแนน 0-100 (score None → วงเทา)"""
    pct = 0 if L.is_missing(score) else max(0.0, min(100.0, float(score)))
    center = (NA if L.is_missing(score) else f"{float(score):.0f}") if center is None else center
    inner = size - 14
    return f"""<div style="margin:0 auto;width:{size}px;height:{size}px;border-radius:50%;
        background:conic-gradient({color} 0% {pct}%,{LINE} {pct}% 100%);display:flex;align-items:center;justify-content:center;">
        <div style="width:{inner}px;height:{inner}px;border-radius:50%;background:#FFFFFF;display:flex;flex-direction:column;
        align-items:center;justify-content:center;"><span style="font-size:{int(size/4.2)}px;font-weight:800;color:{INK};line-height:1;">{center}</span>
        <span style="font-size:11.5px;color:{MUTED};">{sub}</span></div></div>"""


def scale_bar(score, color, marks=(50, 65, 75), labels_txt=None):
    """แถบ 0-100 พร้อมขีดบอกเส้นเกณฑ์ (ใช้ในการ์ดคำแนะนำ)"""
    pct = 0 if L.is_missing(score) else max(0.0, min(100.0, float(score)))
    ticks = "".join(f'<div style="position:absolute;left:{m}%;top:-4px;height:16px;border-left:2px dashed #475569;"></div>'
                    f'<div style="position:absolute;left:{m}%;top:14px;transform:translateX(-50%);font-size:11px;color:{MUTED};">{m}</div>'
                    for m in marks)
    return f"""<div style="position:relative;height:8px;background:{LINE};border-radius:6px;margin:8px 0 20px 0;">
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
    return (f'<div style="background:rgba(148,163,184,0.10);border:1px dashed {color};border-radius:10px;padding:12px 14px;'
            f'color:#475569;font-size:14px;line-height:1.6;box-sizing:border-box;">{text}</div>')


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
    # timeout 60 วินาที: ถ้ามีอีกคนกำลังเขียนฐานข้อมูลอยู่ ให้รอแทนที่จะ error "database is locked"
    return create_engine("sqlite:///cis_database.db", connect_args={"timeout": 60})


@st.cache_resource
def _build_lock():
    """[v17.3] กุญแจตัวเดียวที่ทุก session ใช้ร่วมกัน — บน Streamlit Cloud ถ้ามีผู้ใช้ 2 คน (หรือกดรีเฟรช)
    ระหว่างที่ระบบสร้างฐานข้อมูลครั้งแรก จะไม่สร้างซ้อนกัน 2 รอบ (สาเหตุ error "table ... already exists")"""
    import threading
    return threading.Lock()


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
    if database_is_ready():
        return True
    with st.spinner("⏳ กำลังประมวลผลข้อมูลครั้งแรก (import + calculate scores)... อาจใช้เวลาสักครู่"):
        with _build_lock():
            # เช็คซ้ำหลังได้กุญแจ: ถ้าอีก session สร้างเสร็จไปแล้วระหว่างที่รอ ก็ไม่ต้องสร้างใหม่
            if database_is_ready():
                st.cache_data.clear()
                return True
            try:
                build_database()
                st.cache_data.clear()
            except Exception as build_err:
                st.error(f"⚠️ สร้างฐานข้อมูลอัตโนมัติไม่สำเร็จ: {build_err}\n\n"
                         f"กรุณาตรวจสอบว่าโฟลเดอร์ `Dataset/` ถูกอัปโหลดขึ้น GitHub ครบถ้วน "
                         f"แล้วกด Reboot app ใน Streamlit Cloud (เมนู Manage app)")
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
# 6. UI ส่วนกลาง: Sidebar + Header Bar + เลื่อนขึ้นบนสุดเมื่อเปลี่ยนหน้า
# ============================================================================
def scroll_to_top_on_page_change(page):
    """[v17.4] เปลี่ยนหน้าแล้วเลื่อนจอขึ้นบนสุดของหน้าใหม่อัตโนมัติ
    หลักการ: ฝังสคริปต์เล็ก ๆ (iframe สูง 0 px ใน sidebar) ที่มีชื่อหน้าอยู่ในเนื้อหา
    - เปลี่ยนหน้า → เนื้อหาสคริปต์เปลี่ยน → Streamlit โหลด iframe ใหม่ → สคริปต์สั่งเลื่อนพื้นที่เนื้อหาขึ้นบนสุด
    - อยู่หน้าเดิม (เช่น กดเปลี่ยนช่วงเวลาของกราฟ / เปลี่ยนหุ้น) → เนื้อหาเหมือนเดิม → ไม่เลื่อน ตำแหน่งที่อ่านอยู่ไม่หาย"""
    import streamlit.components.v1 as components
    safe_page = str(page).replace("<", "").replace(">", "").strip()
    script = f"""<script>
    /* page: {safe_page} */
    (function () {{
      var d = window.parent.document;
      var sel = ['[data-testid="stMain"]', 'section.stMain', '[data-testid="stAppViewContainer"]',
                 'section.main', '.main', '[data-testid="stAppScrollToBottomContainer"]'];
      function goTop() {{
        sel.forEach(function (s) {{
          d.querySelectorAll(s).forEach(function (el) {{
            try {{ el.scrollTo({{ top: 0, behavior: 'auto' }}); }} catch (e) {{ el.scrollTop = 0; }}
          }});
        }});
        try {{ window.parent.scrollTo(0, 0); }} catch (e) {{}}
      }}
      goTop(); setTimeout(goTop, 80); setTimeout(goTop, 300); setTimeout(goTop, 700);
    }})();
    </script>"""
    with st.sidebar:
        components.html(script, height=0)


def render_sidebar(scores_df):
    """วาด sidebar (โลโก้, เมนู navigation, dropdown เลือกหุ้น) แล้ว return (nav_page, selected_ticker)"""
    st.sidebar.markdown(f"""
    <div style="padding: 4px 0 6px 0;">
        <div style="display: flex; align-items: flex-start; gap: 10px; min-width: 0;">
            <div style="width: 26px; height: 26px; flex-shrink: 0; border-radius: 7px; background:{INK}; display:flex; align-items:center; justify-content:center;">
                <span style="font-size: 13px; font-weight:800; color:#FFFFFF;">CI</span>
            </div>
            <span style="font-size: 15px; font-weight: 800; color: {INK}; letter-spacing: -0.1px; line-height: 1.3; min-width: 0; word-break: break-word; overflow-wrap: break-word;">
                Comprehensive Investment System
            </span>
        </div>
        <div style="font-size: 12px; color: {FAINT}; margin-top: 4px; padding-left: 36px; letter-spacing: 0.3px; font-weight: 600;">
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
        f"<div style='font-size:12px; font-weight:700; color:{MUTED}; "
        "margin-bottom:4px; letter-spacing:0.5px;'>COMPANY</div>",
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
        key="nav_page",
        label_visibility="collapsed",
    )

    active_color = PAGE_COLORS.get(selected_page, "#3B82F6")

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
            background-color: {active_color}12 !important;
            border: 1px solid {active_color}30 !important;
            box-shadow: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {{
            color: {active_color} !important;
            font-weight: 700 !important;
        }}

        /* =========================================================
           RESPONSIVE / MOBILE (≤ 768px)
           ========================================================= */
        @media (max-width: 768px) {{
            [data-testid="stMainBlockContainer"], .stMainBlockContainer, .main .block-container {{
                width: 100% !important; max-width: 100% !important; box-sizing: border-box !important;
                padding: 2.6rem 0.8rem 1.5rem 0.8rem !important;
            }}
            html, body, .stApp {{ width: 100% !important; max-width: 100vw !important; overflow-x: hidden !important; }}
            [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
                width: 100% !important; max-width: 100% !important; overflow-x: hidden !important; box-sizing: border-box !important;
            }}
            /* แถวการ์ด (CSS Grid) → 1 คอลัมน์ */
            .cis-grid {{ grid-template-columns: 1fr !important; }}
            .cis-card {{ max-width: 100% !important; }}
            /* คอลัมน์ Streamlit → เรียงลงมาทีละคอลัมน์ */
            [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 0.75rem !important; }}
            [data-testid="column"], [data-testid="stColumn"] {{
                width: 100% !important; max-width: 100% !important; min-width: 0 !important;
                flex: 1 1 100% !important; box-sizing: border-box !important;
            }}
            .cis-header {{ flex-direction: column !important; align-items: flex-start !important; gap: 8px !important; padding: 12px 14px !important; }}
            .cis-header-info {{ width: 100% !important; display: flex !important; flex-wrap: wrap !important; gap: 4px 10px !important; font-size: 13px !important; }}
            .cis-header-divider {{ display: none !important; }}
            .module-title {{ font-size: 19px !important; }}
            .module-subtitle {{ font-size: 13px !important; }}
            .cis-table-wrap {{ overflow-x: auto !important; }}
            [data-testid="stDataFrame"], .js-plotly-plot, .plot-container, .plotly, [data-testid="stPlotlyChart"] {{
                width: 100% !important; max-width: 100% !important; box-sizing: border-box !important;
            }}
        }}

        /* =========================================================
           iPad / Tablet (769px - 1100px)
           ========================================================= */
        @media (min-width: 769px) and (max-width: 1100px) {{
            [data-testid="stMainBlockContainer"], .stMainBlockContainer, .main .block-container {{
                max-width: 100% !important; padding: 2.6rem 1.2rem 1.5rem 1.2rem !important;
            }}
            /* แถวการ์ดตั้งแต่ 4 ใบขึ้นไป → แถวละ 2-3 ใบ แทนการบีบจนข้อความตกบรรทัด */
            .cis-grid.wrap-md {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important; }}
            [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) {{
                flex-wrap: wrap !important; row-gap: 0.75rem !important;
            }}
            [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"],
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) > [data-testid="column"] {{
                flex: 1 1 calc(50% - 0.75rem) !important; min-width: 220px !important;
            }}
            .cis-table-wrap {{ overflow-x: auto !important; }}
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
    div = f'<span class="cis-header-divider" style="margin:0 10px;color:#CBD5E1;">|</span>'
    st.html(f"""
    <div class="cis-header" style="display:flex;justify-content:space-between;align-items:center;gap:12px;background:#FFFFFF;
         padding:10px 18px;border-radius:12px;border:1px solid {LINE};">
        <div style="flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            <span style="font-size:21px;font-weight:800;color:{INK};">{ctx.selected_ticker}</span>
            <span style="color:{MUTED};font-size:13px;margin-left:8px;">{COMPANY_NAMES.get(ctx.selected_ticker, '').replace(' PCL', '')} · {info.get('sector','-')}</span>
        </div>
        <div class="cis-header-info" style="flex:0 0 auto;font-size:14px;color:{MUTED};white-space:nowrap;">
            ราคา: <b style="color:{INK};font-size:17px;">{ctx.current_price:.2f}</b> บาท
            <span style="color:{ctx.change_color};font-weight:700;margin-left:4px;">({ctx.change_sign}{ctx.change_pct:.2f}%) {ctx.arrow_sign}</span>
            {div}P/E ({fy_txt}): <b style="color:{INK};">{pe_txt}</b>
            {div}ROE ({fy_txt}): <b style="color:{INK};">{roe_txt}</b>
            {div}ข้อมูล ณ: <b style="color:#475569;">{info.get('latest_date','-')}</b>
        </div>
    </div>
    """)
