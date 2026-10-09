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
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from calculate_modules.fair_value import BLUME_W, DCF_WEIGHT, FCF_NI_WARN, MARKET_ERP, MARKET_RF, PE_WEIGHT
from common import (CARD, NA, fmt_num, fmt_pct, html, num, page_title, rank_text, render_chart_note,
                    render_nav_footer, ring, section_title, show_chart)

PAGE = " Fair Value"
CONF_TH = {"High": ("สูง", L.GREEN), "Medium": ("ปานกลาง", L.YELLOW), "Low": ("ต่ำ", L.RED)}


def _kpi(label, value, sub, color="#0F172A"):
    return (f'<div style="{CARD}"><div style="font-size:13px;font-weight:700;color:#64748B;">{label}</div>'
            f'<div style="font-size:26px;font-weight:800;color:{color};margin-top:4px;">{value}</div>'
            f'<div style="font-size:13px;color:#64748B;margin-top:2px;line-height:1.5;">{sub}</div></div>')


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
    k = st.columns(4)
    with k[0]:
        html(_kpi("มูลค่าเหมาะสม", fmt_num(fair, 2), f"บาทต่อหุ้น · {methods}"))
    with k[1]:
        html(_kpi("ราคาปัจจุบัน", f"{price:.2f}", f"บาท · ราคาปิด {info.get('latest_date', '-')}"))
    with k[2]:
        html(_kpi("Margin of Safety", fmt_pct(mos, 1, sign=True),
                  "ราคา = " + (NA if p2v is None else f"{p2v:.2f} เท่าของมูลค่า") + " · บวก = ราคาต่ำกว่ามูลค่า", lab["color"]))
    with k[3]:
        html(_kpi("สถานะ", lab["th"], f"{lab['en']} · เกณฑ์ ±10% (ทีมกำหนด)", lab["color"]))
    if status == "NOT_RATED":
        html(f'<div style="{CARD}margin-top:10px;color:{L.RED};">ประเมินไม่ได้ (ขาดทุนทั้งกำไรและกระแสเงินสด) — คะแนน Fair Value = 0 ตามกติกา D4</div>')

    # ---------------- F3 + F4 ----------------
    c1, c2 = st.columns([1.6, 1])
    with c1:
        conf = info.get("confidence_level") or "Low"
        conf_th, conf_col = CONF_TH.get(conf, ("ต่ำ", L.RED))
        gap = num(info.get("method_gap_pct"))
        html(section_title("เทียบ 2 วิธี และความมั่นใจ", "สองจุดอยู่ใกล้กัน = ผลน่าเชื่อขึ้น · ราคาอยู่ซ้ายของมูลค่า = ราคาถูก"))
        pts = [("DCF", dcf, "#6366F1", "diamond"), ("P/E", pe, "#06B6D4", "square"),
               ("มูลค่าเหมาะสม", fair, lab["color"], "circle"), ("ราคาปัจจุบัน", price, "#0F172A", "line-ns-open")]
        fig = go.Figure()
        for name, v, colr, sym in pts:
            if v is None:
                continue
            fig.add_trace(go.Scatter(x=[v], y=[0], mode="markers+text", name=name, text=[f"{name}<br>{v:,.2f}"],
                                     textposition="top center", marker=dict(size=22 if sym == "line-ns-open" else 16, color=colr,
                                                                            symbol=sym, line=dict(width=3 if sym == "line-ns-open" else 0, color=colr)),
                                     hovertemplate=f"{name}: %{{x:,.2f}} บาท<extra></extra>"))
        vals = [v for _, v, _, _ in pts if v is not None]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.15 or hi * 0.1
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=30), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          showlegend=False, yaxis=dict(visible=False, range=[-0.6, 1.2]),
                          xaxis=dict(title="บาทต่อหุ้น", range=[max(0, lo - pad), hi + pad], gridcolor="#F1F5F9"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="fv_methods_chart")
        render_chart_note("fair_value_methods")
        html(f"""<div style="{CARD}display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;">
            <div><div style="font-size:12.5px;color:#64748B;">มูลค่าจาก DCF</div><div style="font-size:19px;font-weight:800;">{fmt_num(dcf, 2) if dcf is not None else 'คำนวณไม่ได้'}</div>
                 <div style="font-size:12px;color:#94A3B8;">{'' if dcf is not None else 'FCF ≤ 0 หรือหนี้สุทธิสูงกว่ามูลค่ากิจการ'}</div></div>
            <div><div style="font-size:12.5px;color:#64748B;">มูลค่าจาก P/E</div><div style="font-size:19px;font-weight:800;">{fmt_num(pe, 2) if pe is not None else 'คำนวณไม่ได้'}</div>
                 <div style="font-size:12px;color:#94A3B8;">{'' if pe is not None else 'EPS ≤ 0 (ขาดทุน)'}</div></div>
            <div><div style="font-size:12.5px;color:#64748B;">ส่วนต่างระหว่าง 2 วิธี</div><div style="font-size:19px;font-weight:800;">{fmt_pct(gap, 0)}</div>
                 <div style="font-size:12px;color:#94A3B8;">|DCF − P/E| ÷ ค่าเฉลี่ยของทั้งสอง</div></div>
            <div><div style="font-size:12.5px;color:#64748B;">ความมั่นใจ</div><div style="font-size:19px;font-weight:800;color:{conf_col};">{conf_th}</div>
                 <div style="font-size:12px;color:#64748B;">{info.get('confidence_reason') or ''}</div></div></div>
            <div style="font-size:12px;color:#94A3B8;margin-top:6px;">ความมั่นใจ: สูง = ต่างกัน ≤ 25% · ปานกลาง = 25-50% · ต่ำ = &gt; 50% หรือมีวิธีเดียว · มีคำเตือน FCF ลด 1 ระดับ (เส้น 25/50 ผู้ออกแบบกำหนด)</div>""")
    with c2:
        vs = num(info.get("valuation_score"))
        sc_col = L.score_color(vs)
        sub = ""
        for name, sk, mk, w in [("DCF", "dcf_score", "dcf_mos", DCF_WEIGHT), ("P/E", "pe_score", "pe_mos", PE_WEIGHT)]:
            s, m = num(info.get(sk)), num(info.get(mk))
            txt = (f"คำนวณไม่ได้ → นับ 0 คะแนน" if s is None else f"{s:.1f} (MOS ที่ใช้คิด {m:+.1f}%)")
            sub += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F1F5F9;font-size:14px;">'
                    f'<span>{name} × {w * 100:.0f}%</span><b>{txt}</b></div>')
        html(f"""<div style="{CARD}text-align:center;">{section_title('คะแนน FAIR VALUE')}
            {ring(vs, sc_col, size=112)}
            <div style="font-size:13px;color:#64748B;margin:8px 0;">50 = ราคาเท่ามูลค่าพอดี · สูงกว่า 50 = ถูกกว่ามูลค่า</div>
            <div style="text-align:left;">{sub}</div>
            <div style="font-size:12px;color:#94A3B8;text-align:left;margin-top:6px;line-height:1.5;">คะแนนแต่ละวิธี = 50 + Margin of Safety ของวิธีนั้น
            ตัดที่ 0-100 (ก่อนคิด มูลค่าถูกจำกัดไว้ 65%-185% ของราคา) · {rank_text(info, 'valuation_score')}</div></div>""")

    # ---------------- F5 + F6 ----------------
    implied, roe_avg, roe_last, gap_pts = (num(info.get(k)) for k in ("implied_roe", "roe_hist_avg", "roe_latest", "roe_gap"))
    html('<div style="margin-top:14px;"></div>' + section_title("ราคานี้คาดหวังอะไร (Market Expectation)", "ไม่ต้องเดาการเติบโต · ใช้กติกาเดียวกันทุกหุ้น"))
    if implied is None:
        html(f'<div style="{CARD}">N/A — {info.get("expectation_note") or "ข้อมูลไม่พอ"}</div>')
    else:
        ecol = info.get("expectation_color") or "#64748B"
        html(f"""<div style="{CARD}">
            <div style="font-size:16px;color:#0F172A;line-height:1.7;">ถ้าซื้อที่ราคา {price:.2f} บาท บริษัทต้องทำ ROE ได้ราว
            <b style="color:{ecol};">{implied:.1f}% ต่อปี</b> ไปเรื่อย ๆ</div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:10px;">
              <div style="background:#F8FAFC;border-radius:10px;padding:10px;"><div style="font-size:12.5px;color:#64748B;">ROE ที่ราคาคาดหวัง</div>
                <div style="font-size:21px;font-weight:800;">{implied:.1f}%</div>
                <div style="font-size:12px;color:#64748B;">Ke {fmt_num(info.get('ke_capm'), 2, '%')} · P/B {fmt_num(info.get('pb_current'), 2, 'x')}</div></div>
              <div style="background:#F8FAFC;border-radius:10px;padding:10px;"><div style="font-size:12.5px;color:#64748B;">ROE จริง (ค่าในไฟล์)</div>
                <div style="font-size:21px;font-weight:800;">{fmt_pct(roe_avg)}</div>
                <div style="font-size:12px;color:#64748B;">เฉลี่ย FY{info.get('roe_hist_years') or '-'} · ปีล่าสุด {fmt_pct(roe_last)}</div></div>
              <div style="background:#F8FAFC;border-radius:10px;padding:10px;"><div style="font-size:12.5px;color:#64748B;">ช่องว่าง (คาดหวัง − จริง)</div>
                <div style="font-size:21px;font-weight:800;color:{ecol};">{fmt_num(gap_pts, 1, ' จุด', sign=True)}</div>
                <div style="font-size:12.5px;color:{ecol};font-weight:700;">{info.get('expectation_label') or ''}</div></div></div>
            <div style="font-size:12px;color:#94A3B8;margin-top:8px;line-height:1.6;">ROE ที่คาดหวัง = Ke + (P/B − 1) × (Ke − g) ÷ (1 + g) ·
            Ke = Rf {MARKET_RF * 100:.2f}% + Beta ปรับ ({BLUME_W} × Beta + {1 - BLUME_W:.2f}; Beta {fmt_num(info.get('beta_used'), 2)}) × ERP {MARKET_ERP * 100:.2f}% · g 2%
            · ป้าย: ≤ −2 จุด ต่ำกว่าผลงาน · −2 ถึง +2 สอดคล้อง · +2 ถึง +10 สูงกว่า · &gt; +10 สูงกว่ามาก (เส้นเดิมของทีม)
            {('· ' + info.get('expectation_note')) if info.get('expectation_note') else ''}</div></div>""")
        render_chart_note("market_expectation")
    if num(info.get("fcf_quality_warning")):
        html(f"""<div style="background:rgba(245,158,11,0.10);border:1px solid {L.YELLOW};border-radius:10px;padding:12px 14px;margin-top:10px;
            font-size:14.5px;color:#92400E;line-height:1.6;">⚠ FCF สูงกว่ากำไรสุทธิราว {fmt_num(info.get('fcf_to_ni'), 1)} เท่า (เกณฑ์เตือน {FCF_NI_WARN} เท่า) —
            มูลค่า DCF อาจสูงเกินจริง ให้น้ำหนักกับมูลค่าแบบ P/E มากขึ้น ธุรกิจสื่อสารอาจบันทึกค่าเช่าโครงข่ายหรือค่าใบอนุญาต
            ไว้ในกระแสเงินสดจากการจัดหาเงิน จึงไม่ถูกหักออกจาก FCF</div>""")

    # ---------------- F9: กราฟย้อนหลัง ----------------
    fv = ctx.fair_value_yearly_df
    fv = fv[fv["ticker"] == ctx.selected_ticker].sort_values("year") if not fv.empty else fv
    html('<div style="margin-top:14px;"></div>' + section_title("มูลค่าเหมาะสมเทียบราคาย้อนหลัง", "มูลค่าเหมาะสมจากงบและ WACC / Target P/E ของปีนั้น เทียบราคาปิดสิ้นปี"))
    if fv.empty:
        html(f'<div style="{CARD}">ไม่มีข้อมูลย้อนหลัง</div>')
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
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                           yaxis=dict(title="บาทต่อหุ้น", gridcolor="#F1F5F9"), xaxis=dict(title="ปีงบการเงิน"),
                           legend=dict(orientation="h", y=1.1))
        show_chart(fig2, key="fair_value_hist")
        missing_years = [f"FY{int(y)}" for y, v in zip(fv["year"], fv["fair_value"]) if pd.isna(v)]
        if missing_years:
            html(f'<div style="font-size:12.5px;color:#64748B;">{", ".join(missing_years)}: ประเมินมูลค่าไม่ได้ทั้ง 2 วิธี '
                 '(EPS ≤ 0 และ FCF ≤ 0 หรือมูลค่า DCF หลังหักหนี้สุทธิ ≤ 0) จึงไม่มีจุดในปีนั้น</div>')
        html('<div style="font-size:12.5px;color:#64748B;">หมายเหตุ: งบปีใดประกาศจริงต้นปีถัดไป ตลาด ณ สิ้นปียังไม่เห็นงบนั้น</div>')

    render_nav_footer(ctx, PAGE)
