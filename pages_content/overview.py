"""
pages_content/overview.py — หน้า 2 Stock Overview
--------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.2 (O1-O7)
- คำแนะนำและป้ายทุกโมดูลมาจาก calculate_modules/labels.py (ชุดเดียวกับทุกหน้า)
- ไม่มีดาว (D6), ไม่มีป้าย ATTRACTIVE/FAIR/CAUTION, คะแนนที่ไม่มีแสดง N/A (เลิกแทนด้วย 50)
- บอกว่าคะแนนรวมคิดจากกี่โมดูล และโมดูลไหนไม่นับ (D4)

[v17.4] จัดหน้าใหม่ให้กระชับและสมมาตร: การ์ดคำแนะนำ → [ข้อมูลหุ้น + กราฟราคา | การ์ด 4 โมดูล] → Key Highlights
"""

import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, COMPANY_NAMES, INK, MUTED, FAINT, LINE, NA, TOOLS_H, badge, card, fmt_mb, fmt_num, fmt_pct,
                    grid, html, json_list, num, page_title, rank_text, render_nav_footer, ring, scale_bar,
                    section_title, show_chart, style_fig, tile)

PAGE = " Stock Overview"
COMP_NAMES = {"s_roe": "ROE", "s_roa": "ROA", "s_liquidity": "สภาพคล่อง (Current Ratio)", "s_debt": "หนี้สิน (D/E)"}
MISSING_REASON = {"Health": "งบไม่ครบ", "Fair Value": "ข้อมูลไม่พอ",
                  "Risk": "ข้อมูลราคาไม่พอ", "Entry Timing": "ข้อมูลราคาไม่พอ"}
MODULE_CARD_H = 232


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
    miss_txt = ("ไม่นับ: " + ", ".join(f"{m} ({MISSING_REASON.get(m, 'ไม่มีคะแนน')})" for m in missing)) if missing else "นับครบทุกโมดูล (AI แสดงประกอบ ไม่นับ)"
    n_all = len(ctx.scores_df)
    rank = info.get("overall_rank")
    html(f"""<div class="cis-card" style="border:2px solid {rec['color']};padding:14px 20px;">
      <div class="cis-grid" style="grid-template-columns:minmax(220px,1fr) minmax(300px,1.7fr) minmax(200px,0.9fr);gap:20px;align-items:center;">
        <div>
          <div style="font-size:12.5px;font-weight:700;color:{MUTED};letter-spacing:0.4px;">คำแนะนำของระบบ</div>
          <div style="font-size:27px;font-weight:800;color:{rec['color']};line-height:1.25;margin-top:2px;">{rec['th']}</div>
          <div style="font-size:14px;font-weight:700;color:{rec['color']};">{rec['en']}</div>
        </div>
        <div>
          <div style="font-size:12.5px;font-weight:700;color:{MUTED};">คะแนนรวม <b style="font-size:22px;color:{INK};margin-left:6px;">{fmt_num(overall, 1)}</b><span style="color:{FAINT};"> / 100</span></div>
          {scale_bar(overall, rec['color'])}
          <div style="font-size:12px;color:{MUTED};">&lt; 50 ลดสัดส่วน/ขาย · 50-64.9 ทยอยซื้อ · 65-74.9 ซื้อ · ≥ 75 ซื้อแรง</div>
        </div>
        <div style="border-left:1px solid {LINE};padding-left:18px;">
          <div style="font-size:23px;font-weight:800;color:{INK};">อันดับ {NA if L.is_missing(rank) else int(rank)} <span style="font-size:14px;color:{MUTED};">จาก {n_all} หุ้น</span></div>
          <div style="font-size:13.5px;color:#475569;margin-top:4px;">คิดจาก <b>{used} โมดูล</b></div>
          <div style="font-size:12px;color:{MUTED};margin-top:2px;line-height:1.5;">{miss_txt}</div>
        </div>
      </div></div>""")

    # ---------------- O3-O5 + O6 ----------------
    col_left, col_right = st.columns([1.05, 2.35])
    with col_left:
        info_fy = info.get("health_fy")
        fy = f"FY{int(info_fy)}" if not L.is_missing(info_fy) else "FY"
        mcap = num(info.get("market_cap_mb"))
        fcf = num(info.get("free_cash_flow_latest"))
        fcf_yield = fcf / (mcap * 1e6) * 100 if (fcf is not None and mcap) else None
        pe = info.get("pe_ratio")
        pe_txt = "N/A (ขาดทุน)" if L.is_missing(pe) else f"{float(pe):.2f}x"

        def kv(k, v, color=INK):
            return (f'<div style="min-width:0;"><div style="font-size:12px;color:{MUTED};">{k}</div>'
                    f'<div style="font-size:14.5px;font-weight:700;color:{color};margin-top:1px;">{v}</div></div>')
        html(card(f"""
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
              <div style="min-width:0;"><div style="font-size:21px;font-weight:800;color:{INK};line-height:1.2;">{ctx.selected_ticker}</div>
                <div style="font-size:12.5px;color:{MUTED};">{COMPANY_NAMES.get(ctx.selected_ticker, '-')}</div></div>
              <div style="text-align:right;white-space:nowrap;"><span style="font-size:23px;font-weight:800;color:{INK};">{ctx.current_price:.2f}</span>
                <span style="font-size:12.5px;color:{MUTED};"> บาท</span>
                <div style="font-size:13.5px;font-weight:700;color:{ctx.change_color};">{ctx.change_sign}{ctx.change_val:.2f} ({ctx.change_sign}{ctx.change_pct:.2f}%) {ctx.arrow_sign}</div></div>
            </div>
            <div style="font-size:12px;color:{FAINT};margin-top:2px;">ราคาปิด ณ {info.get('latest_date', '-')} (เทียบวันทำการก่อนหน้า)</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;border-top:1px solid {LINE};margin-top:10px;padding-top:10px;">
            {kv('Market Cap', fmt_mb(mcap * 1e6 if mcap else None, 'ล้านบาท'))}
            {kv(f'P/E ({fy})', pe_txt)}
            {kv(f'P/B ({fy})', fmt_num(info.get('pb_ratio'), 2, 'x'))}
            {kv(f'FCF Yield ({fy})', fmt_pct(fcf_yield, 2), L.GREEN if (fcf_yield or 0) > 0 else L.RED)}
            </div>"""))
        spark = ctx.stock_daily.tail(90)
        fig = go.Figure(go.Scatter(x=spark["date"], y=spark["close"], mode="lines", line=dict(color="#3B82F6", width=1.6),
                                   fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
                                   hovertemplate="%{x|%d/%m/%Y}<br>ปิด %{y:.2f}<extra></extra>"))
        lo, hi = spark["close"].min(), spark["close"].max()
        style_fig(fig, height=150, title="ราคา 90 วันทำการล่าสุด", margin=dict(b=6))
        fig.update_layout(xaxis=dict(showgrid=False, nticks=4), yaxis=dict(showgrid=False, range=[lo * 0.97, hi * 1.03]))
        show_chart(fig, key="overview_spark", expandable=False)

    with col_right:
        cards = module_cards(info)
        cols = st.columns(len(cards))
        for col, (name, page, score, lab, reason) in zip(cols, cards):
            with col:
                html(card(f"""<div style="text-align:center;">
                    <div style="font-size:13.5px;font-weight:800;color:{INK};margin-bottom:8px;">{name}</div>
                    {ring(score, lab['color'], size=82)}
                    <div style="margin-top:8px;color:{lab['color']};font-weight:800;font-size:14px;line-height:1.3;">{lab['th']}</div>
                    <div style="color:{lab['color']};font-size:11.5px;font-weight:700;">{lab['en']}</div>
                    <div style="font-size:12.5px;color:#475569;line-height:1.45;margin-top:6px;">{reason}</div></div>""",
                          f"min-height:{MODULE_CARD_H}px;padding:12px 10px;"))
                if st.button("ดูรายละเอียด ➜", key=f"ov_go_{page.strip()}", use_container_width=True):
                    st.session_state["pending_nav"] = page
                    st.rerun()
        html(card(f"""<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
            <div style="font-size:13.5px;color:#475569;">อันดับในทั้ง 8 หุ้น (Industry Benchmark) · สีแดง = ด้านที่ดึงคะแนนลง</div>
            <div style="font-size:16px;font-weight:800;color:{INK};">{rank_text(info, 'overall_score')}</div></div>""",
                  "padding:10px 16px;"))
        html(card(f"""<div style="font-size:12.5px;color:{MUTED};line-height:1.6;">
            <b style="color:{INK};">อ่านการ์ดอย่างไร:</b> วงแหวน = คะแนน 0-100 ของโมดูล · ป้ายสีใช้เกณฑ์กลางชุดเดียวทุกหน้า
            (เขียว = ดี · เหลือง = ปานกลาง · แดง = ควรระวัง) · ประโยคใต้ป้าย = เหตุผลหลักของคะแนนนั้น ·
            กด "ดูรายละเอียด" เพื่อดูที่มาของตัวเลขทั้งหมดในหน้าของโมดูลนั้น</div>""", "padding:10px 16px;"))

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
    gc = lambda v, good_high=True: INK if v is None else (L.GREEN if (v >= 0) == good_high else L.RED)
    hls = [
        tile(f"การเติบโตของรายได้ ({fy})", fmt_pct(rev_g, sign=True), "เทียบปีก่อน", gc(rev_g)),
        tile(f"การเติบโตของกำไรสุทธิ ({fy})", fmt_pct(ni_g, sign=True), turn_txt, gc(ni_g)),
        tile(f"ROE ({fy})", fmt_pct(info.get("roe"), 2), "ค่าในไฟล์งบการเงิน"),
        tile(f"Free Cash Flow ({fy})", fmt_mb(info.get("free_cash_flow_latest"), "ล้านบาท"), "กระแสเงินสดอิสระ",
             gc(num(info.get("free_cash_flow_latest")))),
        tile(f"D/E ({fy})", "N/A" if de is None else (f"{de:.2f} (ทุนติดลบ)" if de < 0 else f"{de:.2f}"), "ยิ่งต่ำยิ่งปลอดภัย"),
        tile("อันดับในกลุ่ม", srank_txt, info.get("sector", "-")),
    ]
    html(card(section_title("KEY HIGHLIGHTS", "ตัวเลขการเงินสำคัญจากงบปีล่าสุด") + grid(hls, cols=6, style="gap:8px;")
              .replace('class="cis-grid"', 'class="cis-grid wrap-md"')))

    render_nav_footer(ctx, PAGE)
