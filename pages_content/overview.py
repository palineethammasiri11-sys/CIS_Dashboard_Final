"""
pages_content/overview.py — หน้า 2 Stock Overview
--------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.2 (O1-O7)
- คำแนะนำและป้ายทุกโมดูลมาจาก calculate_modules/labels.py (ชุดเดียวกับทุกหน้า)
- ไม่มีดาว (D6), ไม่มีป้าย ATTRACTIVE/FAIR/CAUTION, คะแนนที่ไม่มีแสดง N/A (เลิกแทนด้วย 50)
- บอกว่าคะแนนรวมคิดจากกี่โมดูล และโมดูลไหนไม่นับ (D4)
"""

import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, COMPANY_NAMES, NA, badge, fmt_mb, fmt_num, fmt_pct, html, json_list, num, page_title,
                    rank_text, render_chart_note, render_nav_footer, ring, scale_bar, section_title)

PAGE = " Stock Overview"
COMP_NAMES = {"s_roe": "ROE", "s_roa": "ROA", "s_liquidity": "สภาพคล่อง (Current Ratio)", "s_debt": "หนี้สิน (D/E)"}
MISSING_REASON = {"Health": "งบไม่ครบ", "Fair Value": "ข้อมูลไม่พอ",
                  "Risk": "ข้อมูลราคาไม่พอ", "Entry Timing": "ข้อมูลราคาไม่พอ"}


def health_reason(info):
    comps = [(k, num(info.get(k))) for k in COMP_NAMES]
    comps = [(k, v) for k, v in comps if v is not None]
    if not comps:
        return "ข้อมูลงบไม่พอ"
    best = max(comps, key=lambda x: x[1])
    worst = min(comps, key=lambda x: x[1])
    return f"จุดแข็ง {COMP_NAMES[best[0]]} · จุดอ่อน {COMP_NAMES[worst[0]]}"


def fv_reason(info):
    p2v = num(info.get("price_to_value"))
    if p2v is None:
        return "ประเมินไม่ได้ (ขาดทุนทั้งกำไรและกระแสเงินสด)"
    diff = (p2v - 1) * 100
    return f"ราคาสูงกว่ามูลค่า {diff:.0f}%" if diff > 0 else f"ราคาต่ำกว่ามูลค่า {abs(diff):.0f}%"


def risk_reason(info):
    bd = [d for d in json_list(info.get("risk_breakdown")) if d.get("deduction") is not None]
    if not bd:
        return "ข้อมูลไม่พอ"
    top = max(bd, key=lambda d: d["deduction"])
    return f"ด้านที่หักคะแนนมากที่สุด: {top['name'].split(' (')[0]}"


def timing_reason(info):
    p = info.get("criteria_passed")
    if L.is_missing(p):
        return "ข้อมูลไม่พอ"
    veto = " · ราคาต่ำกว่า MA200" if num(info.get("trend_veto_applied")) else ""
    return f"ผ่าน {int(p)} จาก 6 เกณฑ์{veto}"


def module_cards(info):
    """O6: ข้อมูลของการ์ด 4 โมดูลที่นับในคะแนนรวม (v17.1: ไม่แสดง AI Prediction ในหน้านี้)"""
    return [
        ("Company Health", " Company Health", info.get("health_score"), L.health_label(info.get("health_score")), health_reason(info)),
        ("Fair Value", " Fair Value", info.get("valuation_score"), L.fair_value_label(info.get("margin_of_safety")), fv_reason(info)),
        ("Risk Analysis", " Risk Analysis", info.get("risk_score"), L.risk_label(info.get("risk_score")), risk_reason(info)),
        ("Entry Timing", " Entry Timing", info.get("timing_score"),
         L.timing_label(info.get("timing_score"), info.get("trend_veto_applied")), timing_reason(info)),
    ]


def render(ctx):
    info = ctx.stock_info
    page_title("STOCK OVERVIEW", "สรุปหุ้นที่เลือกในจอเดียว: ควรทำอะไร เพราะอะไร และควรดูรายละเอียดหน้าไหนต่อ")

    # ---------------- O2: การ์ดสรุปการตัดสินใจ ----------------
    overall = num(info.get("overall_score"))
    rec = L.overall_label(overall)
    used = int(info.get("modules_used") or 0)
    missing = json_list(info.get("modules_missing"))
    miss_txt = ("ไม่นับ: " + ", ".join(f"{m} ({MISSING_REASON.get(m, 'ไม่มีคะแนน')})" for m in missing)) if missing else "นับครบทุกโมดูล"
    n_all = len(ctx.scores_df)
    rank = info.get("overall_rank")
    html(f"""<div style="background:#FFFFFF;border:2px solid {rec['color']};border-radius:16px;padding:20px 22px;margin-bottom:18px;">
      <div style="display:grid;grid-template-columns:minmax(260px,1.2fr) minmax(320px,1.6fr) minmax(200px,0.9fr);gap:22px;align-items:center;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#64748B;letter-spacing:0.6px;">คำแนะนำของระบบ</div>
          <div style="font-size:30px;font-weight:800;color:{rec['color']};line-height:1.25;margin-top:4px;">{rec['th']}</div>
          <div style="font-size:16px;font-weight:700;color:{rec['color']};">{rec['en']}</div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#64748B;">คะแนนรวม <b style="font-size:24px;color:#0F172A;margin-left:6px;">{fmt_num(overall, 1)}</b><span style="color:#94A3B8;"> / 100</span></div>
          {scale_bar(overall, rec['color'])}
          <div style="font-size:12.5px;color:#64748B;">&lt; 50 ลดสัดส่วน/ขาย · 50-64.9 ทยอยซื้อ · 65-74.9 ซื้อ · ≥ 75 ซื้อแรง</div>
        </div>
        <div style="border-left:1px solid #E2E8F0;padding-left:18px;">
          <div style="font-size:26px;font-weight:800;color:#0F172A;">อันดับ {NA if L.is_missing(rank) else int(rank)} <span style="font-size:15px;color:#64748B;">จาก {n_all} หุ้น</span></div>
          <div style="font-size:14px;color:#475569;margin-top:6px;">คิดจาก <b>{used} โมดูล</b></div>
          <div style="font-size:12.5px;color:#64748B;margin-top:2px;line-height:1.5;">{miss_txt}</div>
        </div>
      </div></div>""")

    # ---------------- O3-O5 + O6 ----------------
    col_left, col_right = st.columns([1.05, 2.4])
    with col_left:
        info_fy = info.get("health_fy")
        fy = f"FY{int(info_fy)}" if not L.is_missing(info_fy) else "FY"
        html(f"""<div style="{CARD}border-radius:12px 12px 0 0;border-bottom:none;padding-bottom:6px;">
            <div style="font-size:23px;font-weight:800;color:#0F172A;">{ctx.selected_ticker}</div>
            <div style="font-size:14px;color:#64748B;">{COMPANY_NAMES.get(ctx.selected_ticker, '-')}</div>
            <div style="margin-top:8px;"><span style="font-size:28px;font-weight:800;color:#0F172A;">{ctx.current_price:.2f}</span>
              <span style="font-size:14px;color:#64748B;"> บาท</span></div>
            <div style="font-size:15px;font-weight:700;color:{ctx.change_color};">{ctx.change_sign}{ctx.change_val:.2f} ({ctx.change_sign}{ctx.change_pct:.2f}%) {ctx.arrow_sign}</div>
            <div style="font-size:12.5px;color:#64748B;">ราคาปิด ณ {info.get('latest_date', '-')} (เทียบวันทำการก่อนหน้า)</div></div>""")
        spark = ctx.stock_daily.tail(90)
        fig = go.Figure(go.Scatter(x=spark["date"], y=spark["close"], mode="lines", line=dict(color="#3B82F6", width=1.6),
                                   fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
                                   hovertemplate="%{x|%d/%m/%Y}<br>ปิด %{y:.2f}<extra></extra>"))
        lo, hi = spark["close"].min(), spark["close"].max()
        fig.update_layout(height=125, margin=dict(l=8, r=8, t=4, b=0), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          xaxis=dict(showgrid=False, nticks=4, tickfont=dict(size=11, color="#64748B")),
                          yaxis=dict(showgrid=False, showticklabels=False, range=[lo * 0.97, hi * 1.03]))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="overview_spark_chart")
        render_chart_note("overview_spark")

        mcap = num(info.get("market_cap_mb"))
        fcf = num(info.get("free_cash_flow_latest"))
        fcf_yield = fcf / (mcap * 1e6) * 100 if (fcf is not None and mcap) else None
        pe = info.get("pe_ratio")
        pe_txt = "N/A (ขาดทุน)" if L.is_missing(pe) else f"{float(pe):.2f}x"

        def kv(k, v, color="#0F172A"):
            return (f'<div><div style="font-size:12.5px;color:#64748B;">{k}</div>'
                    f'<div style="font-size:15px;font-weight:700;color:{color};margin-top:2px;">{v}</div></div>')
        html(f"""<div style="{CARD}border-radius:0 0 12px 12px;border-top:none;padding-top:4px;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;border-top:1px solid #E2E8F0;padding-top:10px;">
            {kv('Market Cap', fmt_mb(mcap * 1e6 if mcap else None, 'ล้านบาท'))}
            {kv(f'P/E ({fy})', pe_txt)}
            {kv(f'P/B ({fy})', fmt_num(info.get('pb_ratio'), 2, 'x'))}
            {kv(f'FCF Yield ({fy})', fmt_pct(fcf_yield, 2), L.GREEN if (fcf_yield or 0) > 0 else L.RED)}
            {kv('กลุ่มอุตสาหกรรม', info.get('sector', '-'))}
            </div></div>""")

    with col_right:
        html(section_title(f"ผลจาก 4 โมดูล ({ctx.selected_ticker})", "สีแดง = ด้านที่ดึงคะแนนลง กดดูรายละเอียดของด้านนั้นก่อน"))
        cards = module_cards(info)
        cols = st.columns(len(cards))
        for col, (name, page, score, lab, reason) in zip(cols, cards):
            with col:
                html(f"""<div style="{CARD}text-align:center;padding:12px 10px;min-height:268px;">
                    <div style="font-size:14px;font-weight:800;color:#0F172A;margin-bottom:10px;">{name}</div>
                    {ring(score, lab['color'], size=86)}
                    <div style="margin-top:10px;color:{lab['color']};font-weight:800;font-size:14.5px;">{lab['th']}</div>
                    <div style="color:{lab['color']};font-size:12px;font-weight:700;">{lab['en']}</div>
                    <div style="font-size:13px;color:#475569;line-height:1.45;margin-top:6px;">{reason}</div></div>""")
                if st.button("ดูรายละเอียด", key=f"ov_go_{page.strip()}", use_container_width=True):
                    st.session_state["pending_nav"] = page
                    st.rerun()
        html(f"""<div style="{CARD}margin-top:10px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:14.5px;color:#475569;">อันดับในทั้ง 8 หุ้น (Industry Benchmark)</div>
            <div style="font-size:18px;font-weight:800;color:#0F172A;">{rank_text(info, 'overall_score')}</div></div>""")

    # ---------------- O7: Key Highlights ----------------
    fy = f"FY{int(info['health_fy'])}" if not L.is_missing(info.get("health_fy")) else "FY ล่าสุด"
    rev_g, ni_g = num(info.get("revenue_growth_yoy")), num(info.get("net_income_growth_yoy"))
    turn = bool(num(info.get("ni_turnaround")))
    ni_now = num(info.get("net_income_latest"))
    turn_txt = ("พลิกจากขาดทุนเป็นกำไร" if (ni_now or 0) > 0 else "พลิกจากกำไรเป็นขาดทุน") if turn else "เทียบปีก่อน"
    de = num(info.get("de_ratio"))
    sector_n = int(info.get("sector_n") or 1)
    srank = info.get("sector_rank")
    srank_txt = (f"{int(srank)} / {sector_n}" if sector_n > 1 and not L.is_missing(srank) else "กลุ่มนี้มีหุ้นเดียว")

    def hl(label, value, sub, color="#0F172A"):
        return (f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:10px 12px;">'
                f'<div style="font-size:12.5px;color:#64748B;">{label}</div>'
                f'<div style="font-size:17px;font-weight:800;color:{color};margin-top:2px;">{value}</div>'
                f'<div style="font-size:12px;color:#64748B;">{sub}</div></div>')
    gc = lambda v, good_high=True: "#0F172A" if v is None else (L.GREEN if (v >= 0) == good_high else L.RED)
    hls = "".join([
        hl(f"การเติบโตของรายได้ ({fy})", fmt_pct(rev_g, sign=True), "เทียบปีก่อน", gc(rev_g)),
        hl(f"การเติบโตของกำไรสุทธิ ({fy})", fmt_pct(ni_g, sign=True), turn_txt, gc(ni_g)),
        hl(f"ROE ({fy})", fmt_pct(info.get("roe"), 2), "ค่าในไฟล์งบการเงิน"),
        hl(f"Free Cash Flow ({fy})", fmt_mb(info.get("free_cash_flow_latest"), "ล้านบาท"), "กระแสเงินสดอิสระ",
           gc(num(info.get("free_cash_flow_latest")))),
        hl(f"D/E ({fy})", "N/A" if de is None else (f"{de:.2f} (ทุนติดลบ)" if de < 0 else f"{de:.2f}"), "ยิ่งต่ำยิ่งปลอดภัย"),
        hl("อันดับในกลุ่ม", srank_txt, info.get("sector", "-")),
    ])
    html(f"""<div style="{CARD}margin-top:16px;">{section_title('KEY HIGHLIGHTS', 'ตัวเลขการเงินสำคัญจากงบปีล่าสุด')}
        <div style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;">{hls}</div></div>""")

    render_nav_footer(ctx, PAGE)
