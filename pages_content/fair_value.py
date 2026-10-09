"""
pages_content/fair_value.py — หน้า 4 Fair Value
-----------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.4 (F1-F7, F9)
- ทุกตัวเลขอ่านจากหลังบ้าน (calculate_modules/fair_value.py) ไม่คำนวณมูลค่าซ้ำบนจอ
- WACC และ Target P/E จาก Damodaran ผ่าน Dataset/valuation_params_2023_2025.csv (D8 ทาง ก) · กราฟย้อนหลังใช้ค่ารายปี
- สถานะใช้ Margin of Safety ±10% ตัวเดียวทั้งหน้า, คะแนน 50 = ราคาเท่ามูลค่า (D7), ความมั่นใจจากความสอดคล้อง 2 วิธี (D9)
- ตัดออก: การ์ดช่วงมูลค่า 2 ใบ, Valuation Drivers, Detail Breakdown, Confidence แบบ |MOS|, ป้าย +10/−5, ดาว,
  g ตามกลุ่ม + 1.5% ปีแรก, ตาราง WACC ±1%
- v17.1: ตัดตาราง "สมมติฐานและแหล่งที่มา" (F7) ออกจากหน้าจอ · หัวข้อ KPI ใช้ "มูลค่าเหมาะสม"

[v17.4] - กราฟเทียบ 2 วิธี: ราคาปัจจุบันเป็นเส้นตั้ง + ป้ายชื่อสลับบน/ล่างอัตโนมัติ (เดิมป้ายทับกันเมื่อมูลค่าใกล้ราคา)
        - จัดหน้า: KPI 4 ช่อง → [กราฟเทียบ 2 วิธี | คะแนน] → แถบ 4 ช่อง (มูลค่าแต่ละวิธี/ส่วนต่าง/ความมั่นใจ)
                   → [Market Expectation | กราฟย้อนหลัง] (สูงเท่ากัน)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from calculate_modules.fair_value import BLUME_W, DCF_WEIGHT, FCF_NI_WARN, MARKET_ERP, MARKET_RF, PE_WEIGHT
from common import (CARD, INK, MUTED, FAINT, LINE, NA, TOOLS_H, card, fmt_num, fmt_pct, grid, html, kpi, num,
                    page_title, rank_text, render_chart_note, render_nav_footer, ring, section_title, show_chart,
                    style_fig, tile)

PAGE = " Fair Value"
CONF_TH = {"High": ("สูง", L.GREEN), "Medium": ("ปานกลาง", L.YELLOW), "Low": ("ต่ำ", L.RED)}
METHODS_H = 236
HIST_H = 372


def _methods_chart(dcf, pe, fair, price, fair_color):
    """มูลค่า 2 วิธี + มูลค่าเหมาะสม (จุด) และราคาปัจจุบัน (เส้นตั้ง) บนแกนเดียวกัน
    ป้ายชื่อของจุดที่อยู่ใกล้กันจะสลับบน/ล่าง เพื่อไม่ให้ตัวหนังสือทับกัน"""
    single = (dcf is None) != (pe is None)          # ประเมินได้วิธีเดียว → มูลค่าเหมาะสม = วิธีนั้น (แสดงจุดเดียว)
    fair_name = ("มูลค่าเหมาะสม (= " + ("DCF" if dcf is not None else "P/E") + ")") if single else "มูลค่าเหมาะสม"
    pts = [(n, v, c, s) for n, v, c, s in [("DCF", None if single else dcf, "#6366F1", "diamond"),
                                            ("P/E", None if single else pe, "#06B6D4", "square"),
                                            (fair_name, fair, fair_color, "circle")] if v is not None]
    vals = [v for _, v, _, _ in pts] + [price]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or abs(hi) * 0.2 or 1.0
    pad = span * 0.18
    fig = go.Figure()
    side, last_x = {}, {"top": None, "bottom": None}
    for name, v, _, _ in sorted(pts, key=lambda p: p[1]):
        # ใกล้ราคาปัจจุบัน (ป้ายราคาอยู่ด้านบน) หรือใกล้จุดก่อนหน้าที่อยู่ด้านบน → ย้ายลงล่าง
        near_price = abs(v - price) < span * 0.16
        near_top = last_x["top"] is not None and abs(v - last_x["top"]) < span * 0.22
        pos = "bottom" if (near_price or near_top) else "top"
        if pos == "bottom" and last_x["bottom"] is not None and abs(v - last_x["bottom"]) < span * 0.22:
            pos = "top"
        side[name] = pos
        last_x[pos] = v
    x0, x1 = max(0, lo - pad), hi + pad
    for name, v, colr, sym in pts:
        rel = (v - x0) / ((x1 - x0) or 1)
        horiz = "right" if rel < 0.18 else ("left" if rel > 0.82 else "center")   # ใกล้ขอบ → ป้ายหันเข้าใน ไม่ถูกตัด
        fig.add_trace(go.Scatter(x=[v], y=[0], mode="markers+text", name=name, text=[f"{name} {v:,.2f}"],
                                 textposition=f"{side[name]} {horiz}", textfont=dict(size=12, color=INK),
                                 marker=dict(size=15, color=colr, symbol=sym, line=dict(width=1, color="#FFFFFF")),
                                 cliponaxis=False, hovertemplate=f"{name}: %{{x:,.2f}} บาท<extra></extra>"))
    fig.add_vline(x=price, line_color=INK, line_width=2.5, layer="below")
    fig.add_annotation(x=price, y=1, yref="paper", text=f"<b>ราคาปัจจุบัน {price:,.2f}</b>", showarrow=False,
                       yanchor="bottom", font=dict(size=12, color=INK), bgcolor="rgba(255,255,255,0.9)")
    style_fig(fig, height=METHODS_H, title="เทียบ 2 วิธี", sub="จุดใกล้กัน = ผลน่าเชื่อขึ้น · ราคาอยู่ซ้ายของมูลค่า = ราคาถูก",
              margin=dict(t=66, b=8))
    fig.update_layout(yaxis=dict(visible=False, range=[-1, 1]),
                      xaxis=dict(title="บาทต่อหุ้น", range=[x0, x1], showgrid=True))
    return fig


def render(ctx):
    info = ctx.stock_info
    price = ctx.current_price
    page_title("FAIR VALUE", "ราคาตอนนี้ถูกหรือแพงเทียบมูลค่าจากงบ ด้วย 2 วิธี (DCF และ P/E) และตัวเลขนี้เชื่อได้แค่ไหน")

    fair, dcf, pe = num(info.get("fair_value")), num(info.get("dcf_fair_value")), num(info.get("pe_fair_value"))
    mos, p2v = num(info.get("margin_of_safety")), num(info.get("price_to_value"))
    lab = L.fair_value_label(mos)
    status = info.get("valuation_status")
    methods = ("DCF 55% + P/E 45%" if (dcf is not None and pe is not None)
               else ("ใช้ DCF อย่างเดียว (P/E คำนวณไม่ได้: EPS ≤ 0)" if dcf is not None
                     else ("ใช้ P/E อย่างเดียว (DCF คำนวณไม่ได้: FCF ≤ 0)" if pe is not None else "ประเมินไม่ได้")))

    # ---------------- F2: KPI 4 ช่อง ----------------
    html(grid([
        kpi("มูลค่าเหมาะสม", fmt_num(fair, 2), f"บาทต่อหุ้น · {methods}"),
        kpi("ราคาปัจจุบัน", f"{price:.2f}", f"บาท · ราคาปิด {info.get('latest_date', '-')}"),
        kpi("Margin of Safety", fmt_pct(mos, 1, sign=True),
            "ราคา = " + (NA if p2v is None else f"{p2v:.2f} เท่าของมูลค่า") + " · บวก = ราคาต่ำกว่ามูลค่า", lab["color"]),
        kpi("สถานะ", lab["th"], f"{lab['en']} · เกณฑ์ ±10% (ทีมกำหนด)", lab["color"]),
    ]).replace('class="cis-grid"', 'class="cis-grid wrap-md"'))
    if status == "NOT_RATED":
        html(card(f'<span style="color:{L.RED};">ประเมินไม่ได้ (ขาดทุนทั้งกำไรและกระแสเงินสด) — คะแนน Fair Value = 0 ตามกติกา D4</span>'))

    # ---------------- F3 + F4 ----------------
    c1, c2 = st.columns([1.65, 1])
    with c1:
        show_chart(_methods_chart(dcf, pe, fair, price, lab["color"]), key="fair_value_methods")
    with c2:
        vs = num(info.get("valuation_score"))
        sc_col = L.score_color(vs)
        sub = ""
        for name, sk, mk, w in [("DCF", "dcf_score", "dcf_mos", DCF_WEIGHT), ("P/E", "pe_score", "pe_mos", PE_WEIGHT)]:
            s, m = num(info.get(sk)), num(info.get(mk))
            txt = (f"คำนวณไม่ได้ → นับ 0" if s is None else f"{s:.1f} (MOS ที่ใช้คิด {m:+.1f}%)")
            sub += (f'<div style="display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid #F1F5F9;font-size:13px;">'
                    f'<span>{name} × {w * 100:.0f}%</span><b>{txt}</b></div>')
        html(card(f"""{section_title('คะแนน FAIR VALUE', rank_text(info, 'valuation_score'))}
            <div style="display:flex;align-items:center;gap:14px;">
              <div style="flex:0 0 auto;">{ring(vs, sc_col, size=96)}</div>
              <div style="font-size:12.5px;color:{MUTED};line-height:1.55;">50 = ราคาเท่ามูลค่าพอดี<br>สูงกว่า 50 = ถูกกว่ามูลค่า<br>ต่ำกว่า 50 = แพงกว่ามูลค่า</div>
            </div>
            <div style="margin-top:8px;">{sub}</div>
            <div style="font-size:11.5px;color:{FAINT};margin-top:6px;line-height:1.5;">คะแนนแต่ละวิธี = 50 + Margin of Safety ของวิธีนั้น
            ตัดที่ 0-100 (ก่อนคิด มูลค่าถูกจำกัดไว้ 65%-185% ของราคา)</div>""", f"min-height:{METHODS_H + TOOLS_H}px;"))

    conf = info.get("confidence_level") or "Low"
    conf_th, conf_col = CONF_TH.get(conf, ("ต่ำ", L.RED))
    gap = num(info.get("method_gap_pct"))
    html(card(grid([
        tile("มูลค่าจาก DCF", fmt_num(dcf, 2) if dcf is not None else "คำนวณไม่ได้",
             "บาทต่อหุ้น" if dcf is not None else "FCF ≤ 0 หรือหนี้สุทธิสูงกว่ามูลค่ากิจการ"),
        tile("มูลค่าจาก P/E", fmt_num(pe, 2) if pe is not None else "คำนวณไม่ได้",
             "บาทต่อหุ้น" if pe is not None else "EPS ≤ 0 (ขาดทุน)"),
        tile("ส่วนต่างระหว่าง 2 วิธี", fmt_pct(gap, 0), "|DCF − P/E| ÷ ค่าเฉลี่ยของทั้งสอง"),
        tile("ความมั่นใจ", conf_th, info.get("confidence_reason") or "", conf_col),
    ], style="gap:8px;").replace('class="cis-grid"', 'class="cis-grid wrap-md"')
        + f'<div style="font-size:12px;color:{FAINT};margin-top:8px;">ความมั่นใจ: สูง = ต่างกัน ≤ 25% · ปานกลาง = 25-50% · '
          f'ต่ำ = &gt; 50% หรือมีวิธีเดียว · มีคำเตือน FCF ลด 1 ระดับ (เส้น 25/50 ผู้ออกแบบกำหนด)</div>'))

    # ---------------- F5 + F6 | F9 ----------------
    c3, c4 = st.columns([1, 1])
    with c3:
        implied, roe_avg, roe_last, gap_pts = (num(info.get(k)) for k in ("implied_roe", "roe_hist_avg", "roe_latest", "roe_gap"))
        head = section_title("ราคานี้คาดหวังอะไร (Market Expectation)", "ใช้กติกาเดียวกันทุกหุ้น")
        if implied is None:
            body = f'<div style="font-size:13.5px;">N/A — {info.get("expectation_note") or "ข้อมูลไม่พอ"}</div>'
        else:
            ecol = info.get("expectation_color") or MUTED
            body = f"""<div style="font-size:14.5px;color:{INK};line-height:1.6;">ถ้าซื้อที่ราคา {price:.2f} บาท บริษัทต้องทำ ROE ได้ราว
                <b style="color:{ecol};">{implied:.1f}% ต่อปี</b> ไปเรื่อย ๆ</div>
                <div class="cis-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px;">
                  {tile('ROE ที่ราคาคาดหวัง', f'{implied:.1f}%', f"Ke {fmt_num(info.get('ke_capm'), 2, '%')} · P/B {fmt_num(info.get('pb_current'), 2, 'x')}")}
                  {tile('ROE จริง (ค่าในไฟล์)', fmt_pct(roe_avg), f"เฉลี่ย FY{info.get('roe_hist_years') or '-'} · ปีล่าสุด {fmt_pct(roe_last)}")}
                  {tile('ช่องว่าง (คาดหวัง − จริง)', fmt_num(gap_pts, 1, ' จุด', sign=True), info.get('expectation_label') or '', ecol)}
                </div>
                <div style="font-size:11.5px;color:{FAINT};margin-top:8px;line-height:1.55;">ROE ที่คาดหวัง = Ke + (P/B − 1) × (Ke − g) ÷ (1 + g) ·
                Ke = Rf {MARKET_RF * 100:.2f}% + Beta ปรับ ({BLUME_W} × Beta + {1 - BLUME_W:.2f}; Beta {fmt_num(info.get('beta_used'), 2)}) × ERP {MARKET_ERP * 100:.2f}% · g 2%
                · ป้าย: ≤ −2 จุด ต่ำกว่าผลงาน · −2 ถึง +2 สอดคล้อง · +2 ถึง +10 สูงกว่า · &gt; +10 สูงกว่ามาก (เส้นเดิมของทีม)
                {('· ' + info.get('expectation_note')) if info.get('expectation_note') else ''}</div>"""
        warn = ""
        if num(info.get("fcf_quality_warning")):
            warn = f"""<div style="background:rgba(245,158,11,0.10);border:1px solid {L.YELLOW};border-radius:10px;padding:8px 12px;margin-top:10px;
                font-size:13px;color:#92400E;line-height:1.55;">⚠ FCF สูงกว่ากำไรสุทธิราว {fmt_num(info.get('fcf_to_ni'), 1)} เท่า (เกณฑ์เตือน {FCF_NI_WARN} เท่า) —
                มูลค่า DCF อาจสูงเกินจริง ให้น้ำหนักกับมูลค่าแบบ P/E มากขึ้น ธุรกิจสื่อสารอาจบันทึกค่าเช่าโครงข่ายหรือค่าใบอนุญาต
                ไว้ในกระแสเงินสดจากการจัดหาเงิน จึงไม่ถูกหักออกจาก FCF</div>"""
        html(card(head + body + warn, f"min-height:{HIST_H}px;"))
        render_chart_note("market_expectation")
    with c4:
        fv = ctx.fair_value_yearly_df
        fv = fv[fv["ticker"] == ctx.selected_ticker].sort_values("year") if not fv.empty else fv
        if fv.empty:
            html(card(section_title("มูลค่าเหมาะสมเทียบราคาย้อนหลัง") + "ไม่มีข้อมูลย้อนหลัง", f"min-height:{HIST_H}px;"))
        else:
            x = [f"FY{int(y)}" for y in fv["year"]]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=x, y=fv["price"], name="ราคาปิดสิ้นปี", marker_color="#CBD5E1",
                                  hovertemplate="%{x}<br>ราคา %{y:,.2f}<extra></extra>"))
            has_params = {"wacc_used", "target_pe_used"} <= set(fv.columns)
            fig2.add_trace(go.Scatter(x=x, y=fv["fair_value"], name="มูลค่าเหมาะสม", mode="lines+markers",
                                      line=dict(color="#F59E0B", width=3), marker=dict(size=10),
                                      customdata=fv[["wacc_used", "target_pe_used"]].values if has_params else None,
                                      hovertemplate=("%{x}<br>มูลค่า %{y:,.2f}<br>WACC %{customdata[0]:.2f}% · Target P/E %{customdata[1]:.2f}<extra></extra>"
                                                     if has_params else "%{x}<br>มูลค่า %{y:,.2f}<extra></extra>")))
            missing_years = [f"FY{int(y)}" for y, v in zip(fv["year"], fv["fair_value"]) if pd.isna(v)]
            sub = "บาทต่อหุ้น · WACC / Target P/E ของปีนั้น"
            if missing_years:
                sub += f" · {', '.join(missing_years)} ประเมินไม่ได้"
            style_fig(fig2, height=HIST_H, legend=True, title="มูลค่าเหมาะสมเทียบราคาย้อนหลัง", sub=sub)
            fig2.update_layout(yaxis=dict(title=None), xaxis=dict(title=None), bargap=0.35)
            show_chart(fig2, key="fair_value_hist")

    render_nav_footer(ctx, PAGE)
