"""
pages_content/company_health.py — หน้า 3 Company Health
--------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.3 (H1-H9)
- คะแนนคิดจาก 4 องค์ประกอบ (ROE 30%, ROA 25%, Current Ratio 20%, D/E 25%) และหน้าจอแสดงที่มาตรงกับสูตรจริง (D3)
- ROE / ROA ใช้ค่าในไฟล์ของทีมข้อมูลทุกแถว (D2)
- ตัวชี้วัดเสริม 4 ตัวไม่นับในคะแนน; จุดแข็ง/จุดอ่อนเทียบค่ากลางของ 8 หุ้น (D16); เทียบคู่แข่งแบบเลือกได้ (D15)
- ตัดออก: การ์ด 7 มิติพร้อมน้ำหนักที่ไม่ได้ใช้, เกณฑ์ตายตัว 15%/10%/1.5, แถบ "ค่าเรา ÷ คู่แข่ง × 50", ดาว

[v17.4] จัดหน้าใหม่ให้กระชับและสมมาตร:
    [คะแนน | กราฟรายปี] → ที่มาของคะแนน 4 ช่อง → [ตัวชี้วัดเสริม | สัญญาณเตือน + เทียบค่ากลาง] → [งบ 3 ปี | เทียบคู่แข่ง]
"""

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from calculate_modules import labels as L
from calculate_modules.company_health import (W_ROE, W_ROA, W_LIQ, W_DEBT, MULT_ROE, MULT_ROA, MULT_CR, MULT_DE,
                                              DE_CAP)
from common import (CARD, INK, MUTED, FAINT, LINE, NA, TOOLS_H, badge, card, centered_card, fmt_num, fmt_pct, grid, html, num,
                    page_title, rank_text, render_nav_footer, ring, section_title, show_chart, style_fig, tile,
                    COMPANY_NAMES)

PAGE = " Company Health"
TREND_H = 292
COMPONENTS = [  # (คีย์ค่า, คีย์คะแนนย่อย, ชื่อ, น้ำหนัก, คำอธิบายช่วงเต็ม, หน่วย)
    ("roe", "s_roe", "ROE", W_ROE, f"× {MULT_ROE} · เต็ม 100 เมื่อ ROE ≥ {100 / MULT_ROE:.1f}%", "%"),
    ("roa", "s_roa", "ROA", W_ROA, f"× {MULT_ROA:.0f} · เต็ม 100 เมื่อ ROA ≥ {100 / MULT_ROA:.1f}%", "%"),
    ("current_ratio", "s_liquidity", "Current Ratio", W_LIQ, f"× {MULT_CR:.0f} · เต็ม 100 เมื่อ ≥ {100 / MULT_CR:.1f} เท่า", "x"),
    ("de_ratio", "s_debt", "D/E", W_DEBT, f"({DE_CAP} − D/E) × {MULT_DE:.0f} · ไม่มีหนี้ = 100, ≥ {DE_CAP} = 0", "x"),
]
COMPARE = [  # (คอลัมน์งบ, ชื่อ, ยิ่งสูงยิ่งดี, หน่วย)
    ("roe", "ROE", True, "%"), ("roa", "ROA", True, "%"), ("net_margin", "อัตรากำไรสุทธิ", True, "%"),
    ("de_ratio", "D/E", False, "x"), ("current_ratio", "Current Ratio", True, "x"),
]
TH = f"padding:5px 8px;color:{MUTED};font-size:12px;font-weight:700;"
TD = "padding:6px 8px;"


def _fmt(v, unit):
    return fmt_pct(v, 2) if unit == "%" else fmt_num(v, 2, "x")


def _better(a, b, high_good):
    """True ถ้า a ดีกว่า b (D/E ติดลบ = แย่ที่สุด)"""
    if a is None or b is None:
        return None
    if not high_good:
        a = float("inf") if a < 0 else a
        b = float("inf") if b < 0 else b
        return a < b
    return a > b


def render(ctx):
    info = ctx.stock_info
    fy = info.get("health_fy")
    fy_txt = f"FY{int(fy)}" if not L.is_missing(fy) else "ปีล่าสุด"
    page_title("COMPANY HEALTH", f"ความแข็งแรงทางการเงินจากงบจริง · ประเมินจากงบการเงิน {fy_txt}")

    score = num(info.get("health_score"))
    lab = L.health_label(score)
    used = int(info.get("health_components_used") or 0)

    # ---------------- H2 + H4 + H5 ----------------
    c1, c2 = st.columns([1, 1.75])
    with c1:
        comps = [(name, num(info.get(sk))) for _, sk, name, _, _, _ in COMPONENTS]
        comps_ok = [(n, v) for n, v in comps if v is not None]
        best = max(comps_ok, key=lambda x: x[1])[0] if comps_ok else NA
        worst = min(comps_ok, key=lambda x: x[1])[0] if comps_ok else NA
        note = "" if used == 4 else (f'<div style="font-size:12px;color:{L.YELLOW};margin-top:4px;">คิดจาก {used} องค์ประกอบ '
                                     f'(ปรับน้ำหนักให้รวม 100%)</div>' if used == 3 else "")
        de = num(info.get("de_ratio"))
        sentence = (f"ใน {fy_txt} บริษัทมี ROE {fmt_pct(info.get('roe'), 2)}, อัตรากำไรสุทธิ {fmt_pct(info.get('net_margin'), 2)}, "
                    f"D/E {'ติดลบ (ส่วนผู้ถือหุ้นติดลบ)' if (de is not None and de < 0) else fmt_num(de, 2, ' เท่า')} และ Current Ratio "
                    f"{fmt_num(info.get('current_ratio'), 2, ' เท่า')} — องค์ประกอบที่ได้คะแนนสูงสุดคือ <b>{best}</b> "
                    f"ต่ำสุดคือ <b>{worst}</b>")
        html(centered_card(section_title('HEALTH SCORE', fy_txt), f"""
            <div style="display:flex;align-items:center;gap:16px;">
              <div style="flex:0 0 auto;">{ring(score, lab['color'], size=108)}</div>
              <div style="min-width:0;"><div>{badge(lab, 13)}</div>{note}
                <div style="font-size:12px;color:{MUTED};margin-top:6px;">≥ 65 แข็งแรง · 50-64.9 ปานกลาง · &lt; 50 อ่อนแอ</div>
                <div style="font-size:12.5px;color:{MUTED};margin-top:2px;">{rank_text(info, 'health_score')}</div></div>
            </div>
            <div style="font-size:13.5px;color:#334155;line-height:1.7;margin-top:12px;border-top:1px solid #F1F5F9;padding-top:10px;">{sentence}</div>""",
                  f"min-height:{TREND_H + TOOLS_H}px;"))
    with c2:
        hy = ctx.health_yearly_df
        hy = hy[hy["ticker"] == ctx.selected_ticker].sort_values("year") if not hy.empty else hy
        if hy.empty:
            html(card(section_title("แนวโน้มคะแนน Health รายปี") + "ไม่มีข้อมูลรายปี", f"min-height:{TREND_H}px;"))
        else:
            colors = [L.health_label(v)["color"] for v in hy["health_score"]]
            xs = [f"FY{int(y)}" for y in hy["year"]]
            fig = go.Figure(go.Scatter(x=xs, y=hy["health_score"], mode="lines+markers",
                                       line=dict(color="#10B981", width=2.5), marker=dict(size=11, color=colors),
                                       cliponaxis=False, hovertemplate="%{x}<br>Health %{y:.1f}<extra></extra>"))
            for x, v in zip(xs, hy["health_score"]):      # ป้ายตัวเลขมีพื้นขาว อ่านได้แม้ทับเส้นเกณฑ์ 50 / 65
                if pd.notna(v):
                    fig.add_annotation(x=x, y=v, text=f"<b>{v:.1f}</b>", showarrow=False, yshift=16,
                                       font=dict(size=12, color=INK), bgcolor="rgba(255,255,255,0.92)", borderpad=1)
            fig.add_hline(y=65, line_dash="dot", line_color=L.GREEN, annotation_text="65 แข็งแรง", annotation_position="right",
                          annotation_font=dict(size=11, color=L.GREEN))
            fig.add_hline(y=50, line_dash="dot", line_color=L.YELLOW, annotation_text="50 ปานกลาง", annotation_position="right",
                          annotation_font=dict(size=11, color=L.YELLOW))
            style_fig(fig, height=TREND_H, title="แนวโน้มคะแนน Health รายปี", sub="สูตรเดียวกันทุกปี",
                      margin=dict(r=78))
            fig.update_layout(xaxis=dict(title="ปีงบการเงิน"), yaxis=dict(title="Health Score", range=[0, 108]))
            show_chart(fig, key="health_trend")

    # ---------------- H3: ที่มาของคะแนน ----------------
    avail_w = sum(w for _, sk, _, w, _, _ in COMPONENTS if num(info.get(sk)) is not None) or 1.0
    cards = []
    for vk, sk, name, w, rule, unit in COMPONENTS:
        v, s = num(info.get(vk)), num(info.get(sk))
        w_used = w / avail_w if s is not None else None
        pts = s * w_used if s is not None else None
        colr = L.score_color(s)
        disp = _fmt(v, unit) if not (vk == "de_ratio" and v is not None and v < 0) else f"{v:.2f}x (ทุนติดลบ)"
        cards.append(f"""<div style="background:#F8FAFC;border:1px solid {LINE};border-radius:10px;padding:10px 12px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;gap:6px;">
              <span style="font-size:13.5px;font-weight:800;color:{INK};">{name}</span>
              <span style="font-size:19px;font-weight:800;color:{INK};">{disp}</span></div>
            <div style="font-size:12.5px;color:#475569;line-height:1.6;margin-top:2px;">คะแนนย่อย <b style="color:{colr};">{fmt_num(s, 1)}</b>/100
            · น้ำหนัก <b>{'N/A' if w_used is None else f'{w_used * 100:.0f}%'}</b> · ได้จริง <b>{fmt_num(pts, 1)}</b></div>
            <div style="height:6px;background:{LINE};border-radius:4px;margin-top:6px;"><div style="width:{0 if s is None else s}%;height:100%;background:{colr};border-radius:4px;"></div></div>
            <div style="font-size:11.5px;color:{FAINT};margin-top:4px;">{rule}</div></div>""")
    html(card(section_title('ที่มาของคะแนน 4 องค์ประกอบ', f'ค่าจริง → คะแนนย่อย 0-100 → น้ำหนัก → คะแนนที่ได้ · รวม = {fmt_num(score, 1)}')
              + grid(cards, cols=4, style="gap:8px;").replace('class="cis-grid"', 'class="cis-grid wrap-md"')
              + f'<div style="font-size:12px;color:{FAINT};margin-top:8px;">ROE / ROA ใช้ค่าในไฟล์งบการเงินของทีม · '
                'ตัวคูณและน้ำหนักเป็นค่าที่ทีมกำหนด (ผ่านการทดสอบความไวแล้ว)</div>'))

    # ---------------- H6 + H8: ตัวชี้วัดเสริม | สัญญาณเตือน + เทียบค่ากลาง ----------------
    supp = [
        ("revenue_growth_yoy", "การเติบโตของรายได้", fmt_pct(info.get("revenue_growth_pct"), 1, sign=True), "สูงดี"),
        ("asset_turnover", "Asset Turnover", fmt_num(info.get("asset_turnover"), 2, " เท่า"), "สูงดี (ใช้สินทรัพย์สร้างรายได้เก่ง)"),
        ("accrual_ratio", "Accrual Ratio", fmt_num(info.get("accrual_ratio"), 3), "ต่ำหรือติดลบดี (กำไรมาจากเงินสดจริง)"),
        ("interest_coverage", "Interest Coverage", fmt_num(info.get("interest_coverage"), 2, " เท่า"), "สูงดี (จ่ายดอกเบี้ยไหว)"),
    ]
    sc = [tile(n, val, f"{good}<br><span style='color:#475569;'>{rank_text(info, rk, with_sector=False)}</span>")
          for rk, n, val, good in supp]
    supp_card = card(section_title('ตัวชี้วัดเสริม', 'ไม่นับในคะแนน Health · ดูสิ่งที่คะแนนหลักมองไม่เห็น')
                     + grid(sc, cols=2, style="gap:8px;")
                     + f'<div style="font-size:11.5px;color:{FAINT};margin-top:8px;line-height:1.5;">การเติบโต = (รายได้ปีล่าสุด − ปีก่อน) ÷ |ปีก่อน| · '
                       'Asset Turnover = รายได้รวม ÷ สินทรัพย์รวม (Soliman 2008) · Accrual Ratio = (กำไรสุทธิ − เงินสดจากการดำเนินงาน) ÷ '
                       'สินทรัพย์รวม (Sloan 1996) · Interest Coverage = คอลัมน์ในไฟล์งบ</div>')

    warns = []
    ni = num(info.get("net_income_latest"))
    if ni is not None and ni < 0:
        warns.append("ขาดทุนสุทธิในปีล่าสุด")
    if num(info.get("equity_negative")):
        warns.append("ส่วนผู้ถือหุ้นติดลบ")
    cr = num(info.get("current_ratio"))
    if cr is not None and cr < 1:
        warns.append("Current Ratio ต่ำกว่า 1 (หนี้ระยะสั้นมากกว่าสินทรัพย์หมุนเวียน — บางธุรกิจ เช่น ธุรกิจสื่อสาร เป็นแบบนี้ได้ตามปกติ)")
    if num(info.get("revenue_down_2y")):
        warns.append("รายได้ลดลง 2 ปีติดกัน")
    warn_html = ("".join(f'<div style="padding:3px 0;color:{L.RED};font-size:13.5px;line-height:1.5;">⚠ {w}</div>' for w in warns)
                 if warns else f'<div style="color:{L.GREEN};font-size:13.5px;">✓ ไม่พบสัญญาณเตือน</div>')
    vs = ""
    for col, name, high_good, unit in COMPARE:
        v, med = num(info.get(col)), num(info.get(f"median_{col}"))
        b = _better(v, med, high_good) if (v is not None and med is not None and round(v, 2) != round(med, 2)) else None
        icon = "–" if b is None else ("✓" if b else "✗")
        colr = FAINT if b is None else (L.GREEN if b else L.RED)
        vs += (f'<div style="display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid #F1F5F9;font-size:13.5px;">'
               f'<span><b style="color:{colr};">{icon}</b> {name}</span><span style="color:#475569;white-space:nowrap;">{_fmt(v, unit)} · ค่ากลาง {_fmt(med, unit)}</span></div>')
    warn_card = card(f"""{section_title('สัญญาณเตือน')}{warn_html}
        <div style="margin-top:12px;">{section_title('เทียบกับ 8 หุ้นที่ติดตาม', '✓ = ดีกว่าค่ากลาง (มัธยฐาน)')}</div>{vs}
        <div style="font-size:11.5px;color:{FAINT};margin-top:6px;">ค่ากลางมาจาก 8 บริษัทต่างอุตสาหกรรม · D/E ยิ่งต่ำยิ่งดี</div>""")
    html(grid([supp_card, warn_card], template="minmax(0,1.25fr) minmax(0,1fr)"))

    # ---------------- H7 + H9: งบ 3 ปี | เทียบคู่แข่ง ----------------
    c3, c4 = st.columns([1.25, 1])
    fin = ctx.fin_stock.sort_values("year")
    with c3:
        years = [int(y) for y in fin["year"]]
        head = "".join(f'<th style="{TH}text-align:right;">FY{y}</th>' for y in years)
        body = ""
        for col, name, _, unit in COMPARE:
            cells = "".join(f'<td style="{TD}text-align:right;">{_fmt(num(v), unit)}</td>' for v in fin[col])
            body += f'<tr style="border-top:1px solid #F1F5F9;"><td style="{TD}">{name}</td>{cells}</tr>'
        html(card(f"""{section_title('ตารางงบการเงินสำคัญ', 'คอลัมน์ขวาสุด = ปีที่ใช้คิดคะแนน')}
            <div class="cis-table-wrap"><table style="width:100%;border-collapse:collapse;font-size:13.5px;"><tr>
            <th style="{TH}text-align:left;">ตัวชี้วัด</th>{head}</tr>{body}</table></div>""", "min-height:322px;"))
    with c4:
        df = ctx.scores_df
        same = sorted(df[(df["sector"] == info["sector"]) & (df["ticker"] != ctx.selected_ticker)]["ticker"])
        other = sorted(df[(df["sector"] != info["sector"])]["ticker"])
        options = (["— ไม่เทียบ —"] if not same else []) + same + other
        comp = st.selectbox("เทียบคู่แข่งรายตัว (เปลี่ยนเฉพาะตารางนี้)", options, index=0, key=f"health_comp_{ctx.selected_ticker}",
                            format_func=lambda t: t if t.startswith("—") else (f"{t} — {COMPANY_NAMES.get(t, '')}" + ("" if t in same else " (ต่างกลุ่ม)")))
        if comp.startswith("—"):
            html(card(f'<div style="color:#475569;font-size:13.5px;line-height:1.6;">{ctx.selected_ticker} ไม่มีคู่แข่งในกลุ่ม {info["sector"]} ที่ติดตาม '
                      'จึงไม่เทียบโดยอัตโนมัติ เลือกบริษัทต่างกลุ่มจากรายการได้ (การเทียบข้ามอุตสาหกรรมมีความหมายน้อย)</div>',
                      "min-height:238px;"))
        else:
            f_me = ctx.fin_stock.sort_values("year").iloc[-1] if not ctx.fin_stock.empty else None
            f_c = ctx.fin_df[ctx.fin_df["ticker"] == comp].sort_values("year")
            f_c = f_c.iloc[-1] if not f_c.empty else None
            rows = ""
            for col, name, high_good, unit in COMPARE:
                a = num(f_me[col]) if f_me is not None else None
                b = num(f_c[col]) if f_c is not None else None
                w = _better(a, b, high_good) if (a is not None and b is not None and round(a, 2) != round(b, 2)) else None
                ca = f'<b style="color:{L.GREEN};">✓</b> ' if w is True else ""
                cb = f'<b style="color:{L.GREEN};">✓</b> ' if w is False else ""
                rows += (f'<tr style="border-top:1px solid #F1F5F9;"><td style="{TD}">{name}</td>'
                         f'<td style="{TD}text-align:right;">{ca}{_fmt(a, unit)}</td>'
                         f'<td style="{TD}text-align:right;">{cb}{_fmt(b, unit)}</td></tr>')
            yr_note = ""
            if f_me is not None and f_c is not None and int(f_me["year"]) != int(f_c["year"]):
                yr_note = f'<div style="font-size:12px;color:{L.YELLOW};">หมายเหตุ: ใช้งบคนละปี (FY{int(f_me["year"])} กับ FY{int(f_c["year"])})</div>'
            tag = "" if comp in same else ' <span style="font-size:11.5px;color:#F59E0B;">(ต่างกลุ่ม)</span>'
            html(card(f"""<table style="width:100%;border-collapse:collapse;font-size:13.5px;">
                <tr><th style="{TH}text-align:left;">ตัวชี้วัด (งบปีล่าสุด)</th>
                <th style="{TH}text-align:right;">{ctx.selected_ticker}</th><th style="{TH}text-align:right;">{comp}{tag}</th></tr>
                {rows}</table>{yr_note}<div style="font-size:11.5px;color:{FAINT};margin-top:6px;">✓ อยู่ฝั่งที่ดีกว่าในแต่ละแถว (D/E ยิ่งต่ำยิ่งดี)</div>"""))

    render_nav_footer(ctx, PAGE)
