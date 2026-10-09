"""
pages_content/industry_benchmark.py — หน้า 1 Industry Benchmark (ภาพรวม 8 หุ้น)
---------------------------------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.1 (I1-I7)
- ตัวเลขทุกตัวอ่านจากตาราง cis_summary_scores (หลังบ้าน) ไม่คำนวณสูตรหลักซ้ำบนจอ
- ป้าย/สีทุกช่องมาจาก calculate_modules/labels.py ชุดเดียวกับทุกหน้า
- ตัดออกจากเวอร์ชันเดิม: ดาว, ป้าย LEADER/STRONG COMPETITOR ตามอันดับ, "Top x%", ตาราง Peer Comparison เฉพาะกลุ่ม,
  แกน Industry Score ในเรดาร์ (D6, D14)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, NA, badge, fmt_num, fmt_score, html, num, page_title, rank_text, render_nav_footer,
                    section_title, show_chart)

PAGE = " Industry Benchmark"
DIMS = [  # (คอลัมน์คะแนน, ชื่อ)
    ("health_score", "Health"), ("valuation_score", "Fair Value"), ("risk_score", "Risk"),
    ("timing_score", "Entry Timing"), ("ai_score", "AI"),
]


def _module_label(row, col):
    """ป้ายของแต่ละโมดูลจากตารางป้ายกลาง"""
    if col == "health_score":
        return L.health_label(row.get(col))
    if col == "valuation_score":
        return L.fair_value_label(row.get("margin_of_safety"))
    if col == "risk_score":
        return L.risk_label(row.get(col))
    if col == "timing_score":
        return L.timing_label(row.get(col), row.get("trend_veto_applied"))
    return L.ai_label(row.get("prob_up"), row.get("model_has_edge"))


def _chip(lab, score):
    s = NA if L.is_missing(score) else f"{float(score):.0f}"
    if lab["en"] == "NO EDGE":
        s = "NO EDGE"
    return (f'<span title="{lab["th"]}" style="display:inline-block;min-width:54px;text-align:center;background:{lab["bg"]};'
            f'color:{lab["color"]};border:1px solid {lab["color"]};border-radius:8px;padding:2px 6px;font-size:13px;'
            f'font-weight:700;">{s}</span>')


def _ranking_table(df, selected):
    """I2: ตารางจัดอันดับทั้ง 8 หุ้น"""
    rows = ""
    for _, r in df.sort_values(["overall_rank", "ticker"]).iterrows():
        rec = L.overall_label(r.get("overall_score"))
        sel = r["ticker"] == selected
        bg = "background:rgba(6,182,212,0.08);" if sel else ""
        bold = "font-weight:800;" if sel else ""
        chips = "".join(f'<td style="padding:8px 6px;text-align:center;">{_chip(_module_label(r, c), r.get(c))}</td>' for c, _ in DIMS)
        rank = NA if L.is_missing(r.get("overall_rank")) else int(r["overall_rank"])
        rows += f"""<tr style="border-top:1px solid #F1F5F9;{bg}">
            <td style="padding:8px 6px;text-align:center;{bold}">{rank}</td>
            <td style="padding:8px 6px;{bold}color:#0F172A;">{r['ticker']}{' ◀' if sel else ''}</td>
            <td style="padding:8px 6px;color:#64748B;font-size:13px;">{r.get('sector', '-')}</td>
            <td style="padding:8px 6px;text-align:center;font-weight:800;color:{rec['color']};">{fmt_num(r.get('overall_score'), 1)}</td>
            <td style="padding:8px 6px;"><span style="color:{rec['color']};font-weight:700;font-size:13.5px;">{rec['th']}</span></td>
            {chips}
            <td style="padding:8px 6px;text-align:center;color:#475569;">{int(r.get('modules_used') or 0)}/4</td></tr>"""
    head = "".join(f'<th style="padding:6px;text-align:center;">{n}</th>' for _, n in DIMS)
    return f"""<div style="{CARD}overflow-x:auto;">{section_title('ตารางจัดอันดับทั้ง 8 หุ้น', 'เรียงตามคะแนนรวม · ตัวเลขในช่อง = คะแนน 0-100 ของโมดูล · คอลัมน์ AI แสดงประกอบ ไม่นับในคะแนนรวม')}
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="color:#64748B;font-size:13px;"><th style="padding:6px;">อันดับ</th><th style="padding:6px;text-align:left;">หุ้น</th>
        <th style="padding:6px;text-align:left;">กลุ่ม</th><th style="padding:6px;">คะแนนรวม</th><th style="padding:6px;text-align:left;">คำแนะนำ</th>
        {head}<th style="padding:6px;">โมดูลที่นับ</th></tr>{rows}</table>
        <div style="font-size:12.5px;color:#64748B;margin-top:8px;line-height:1.6;">
        สีของช่องใช้เกณฑ์กลางของแต่ละโมดูล (Fair Value ใช้ Margin of Safety ±10%, Entry Timing ราคาต่ำกว่า MA200 = แดงเสมอ)
        · AI ที่โมเดลสอบไม่ผ่าน = NO EDGE และไม่นับในคะแนนรวม</div></div>"""


def _matrix(df, selected):
    """I3: Strategic Matrix (ตัดแกนที่ 50 ทั้งสองแกน — D17)"""
    fig = go.Figure()
    d = df.dropna(subset=["health_score", "overall_score"])
    for _, r in d.iterrows():
        sel = r["ticker"] == selected
        color = L.overall_label(r["overall_score"])["color"] if sel else "#94A3B8"
        fig.add_trace(go.Scatter(
            x=[r["health_score"]], y=[r["overall_score"]], mode="markers+text", text=[r["ticker"]],
            textposition="top center", textfont=dict(size=13 if sel else 11.5, color="#0F172A" if sel else "#64748B"),
            marker=dict(size=18 if sel else 12, color=color, line=dict(width=2 if sel else 0, color="#0F172A")),
            showlegend=False,
            hovertemplate=f"{r['ticker']}<br>Health %{{x:.1f}}<br>คะแนนรวม %{{y:.1f}}<extra></extra>"))
    for txt, x, y in [("Market Leader", 97, 97), ("Hidden Gem", 3, 97), ("Competitive", 97, 3), ("Value Trap", 3, 3)]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, font=dict(size=12, color="#94A3B8"),
                           xanchor="right" if x > 50 else "left", yanchor="top" if y > 50 else "bottom")
    fig.add_vline(x=50, line_dash="dash", line_color="#CBD5E1")
    fig.add_hline(y=50, line_dash="dash", line_color="#CBD5E1")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      xaxis=dict(title="Health Score (คุณภาพธุรกิจ)", range=[0, 100], gridcolor="#F1F5F9"),
                      yaxis=dict(title="คะแนนรวม (ความน่าลงทุน)", range=[0, 100], gridcolor="#F1F5F9"))
    return fig


def _peer_avg(df, info, col):
    """ค่าเฉลี่ยคู่แข่ง = หุ้นอื่นในกลุ่มเดียวกัน (ไม่รวมตัวเอง)
    ถ้ากลุ่มนี้ยังไม่มีหุ้นอื่น คืน None (ไม่เทียบ) · เมื่อเพิ่มหุ้นกลุ่มเดียวกันใน SECTOR_MAP จะเทียบให้เองทันที"""
    same = df[(df["ticker"] != info["ticker"]) & (df["sector"] == info["sector"])]
    v = pd.to_numeric(same[col], errors="coerce").dropna()
    return None if v.empty else float(v.mean())


def render(ctx):
    info, df = ctx.stock_info, ctx.scores_df.copy()
    page_title("INDUSTRY BENCHMARK", "ภาพรวมทั้ง 8 หุ้นที่ติดตาม และตำแหน่งของหุ้นที่เลือกเมื่อเทียบกับเพื่อน")

    # ---------------- ส่วนบน: ทั้ง 8 หุ้น ----------------
    html(_ranking_table(df, ctx.selected_ticker))
    html('<div style="margin-top:18px;"></div>' + section_title("STRATEGIC MATRIX", "แยก “บริษัทดี” ออกจาก “หุ้นน่าซื้อ” · เส้นแบ่งที่ 50 = เส้นทยอยซื้อของคำแนะนำ"))
    show_chart(_matrix(df, ctx.selected_ticker), key="industry_matrix")

    # ---------------- ส่วนล่าง: หุ้นที่เลือก ----------------
    html(f'<div style="font-size:18px;font-weight:800;color:#0F172A;margin:22px 0 10px 0;">หุ้นที่เลือก: {ctx.selected_ticker}</div>')
    n_all = len(df)
    overall = num(info.get("overall_score"))
    rank = info.get("overall_rank")
    top = pd.to_numeric(df["overall_score"], errors="coerce").max()
    med = pd.to_numeric(df["overall_score"], errors="coerce").median()
    sector_n = int(info.get("sector_n") or 1)
    sector_txt = (f"อันดับ {int(info['sector_rank'])} จาก {sector_n} ในกลุ่ม {info.get('sector')}" if sector_n > 1
                  else f"กลุ่ม {info.get('sector')} ยังไม่มีหุ้นอื่นในชุดข้อมูล จึงไม่เทียบในกลุ่ม")
    rec = L.overall_label(overall)
    gap_top = NA if overall is None else f"{overall - top:+.1f}"
    gap_med = NA if overall is None else f"{overall - med:+.1f}"

    c1, c2 = st.columns([1, 2.2])
    with c1:   # I4
        html(f"""<div style="{CARD}border:1.5px solid {rec['color']};height:100%;">
            {section_title('อันดับของหุ้นที่เลือก')}
            <div style="font-size:30px;font-weight:800;color:#0F172A;">อันดับ {NA if L.is_missing(rank) else int(rank)} <span style="font-size:17px;color:#64748B;">จาก {n_all}</span></div>
            <div style="font-size:14.5px;color:#475569;margin-top:4px;">{sector_txt}</div>
            <div style="margin-top:12px;font-size:14.5px;line-height:1.9;color:#334155;">
              คะแนนรวม <b style="color:{rec['color']};">{fmt_num(overall, 1)}</b> · {badge(rec, 12)}<br>
              ห่างจากอันดับ 1: <b>{gap_top}</b> คะแนน<br>
              ห่างจากค่ากลางของ 8 หุ้น ({med:.1f}): <b>{gap_med}</b> คะแนน</div></div>""")
    with c2:   # I5
        cards = ""
        for col, name in DIMS + [("revenue_growth_yoy", "การเติบโตของรายได้")]:
            v = info.get(col)
            if col == "ai_score" and L.is_missing(v):
                main, sub = "N/A (NO EDGE)", "โมเดลสอบไม่ผ่าน ไม่จัดอันดับ"
            else:
                main = rank_text(info, col, with_sector=False)
                sub = (f"ในกลุ่ม {int(info['srank_' + col])}/{sector_n}" if sector_n > 1 and not L.is_missing(info.get('srank_' + col))
                       else "กลุ่มนี้มีหุ้นเดียว")
            val = fmt_num(v, 1, "%" if col == "revenue_growth_yoy" else "", sign=(col == "revenue_growth_yoy"))
            cards += f"""<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:10px 12px;">
                <div style="font-size:13px;color:#64748B;font-weight:700;">{name}</div>
                <div style="font-size:16px;font-weight:800;color:#0F172A;margin-top:2px;">{main.replace('อันดับ ', '')}</div>
                <div style="font-size:12.5px;color:#64748B;">ค่า {val} · {sub}</div></div>"""
        html(f"""<div style="{CARD}height:100%;">{section_title('อันดับรายด้าน', 'อันดับ 1 = ดีที่สุดในด้านนั้น (Risk: ปลอดภัยที่สุด)')}
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">{cards}</div></div>""")

    # I6 + I7 — เทียบเฉพาะคู่แข่งในกลุ่มเดียวกัน · กลุ่มที่ยังไม่มีหุ้นอื่น → แสดงเฉพาะหุ้นนี้ ไม่เทียบ
    has_peers = sector_n > 1
    axes, mine, peers = [], [], []
    for col, name in DIMS:
        v = num(info.get(col))
        pv = _peer_avg(df, info, col) if has_peers else None
        if v is None or (has_peers and pv is None):
            continue       # AI ที่สอบไม่ผ่าน (หรือคู่แข่งไม่มีค่า) → ตัดแกนออก
        axes.append(name)
        mine.append(v)
        peers.append(pv)
    no_peer_msg = (f"กลุ่ม {info.get('sector')} ยังไม่มีหุ้นอื่นในชุดข้อมูลนี้ จึงไม่แสดงเส้นเปรียบเทียบ "
                   f"(เมื่อเพิ่มหุ้นในกลุ่มเดียวกัน ระบบจะเทียบให้อัตโนมัติ)")
    c3, c4 = st.columns([1.3, 1])
    with c3:
        if len(axes) >= 3:
            fig = go.Figure()
            if has_peers:
                fig.add_trace(go.Scatterpolar(r=peers + peers[:1], theta=axes + axes[:1], name="ค่าเฉลี่ยคู่แข่งในกลุ่ม",
                                              line=dict(color="#64748B", dash="dash"), fill=None))
            fig.add_trace(go.Scatterpolar(r=mine + mine[:1], theta=axes + axes[:1], name=ctx.selected_ticker,
                                          line=dict(color="#06B6D4", width=2), fill="toself", fillcolor="rgba(6,182,212,0.18)"))
            fig.update_layout(height=380, margin=dict(l=40, r=40, t=30, b=30), paper_bgcolor="#FFFFFF",
                              polar=dict(radialaxis=dict(range=[0, 100], tickfont=dict(size=11))),
                              legend=dict(orientation="h", y=-0.08), showlegend=True)
            if has_peers:
                html(section_title("RADAR: หุ้นที่เลือก เทียบค่าเฉลี่ยคู่แข่ง", "คู่แข่งในกลุ่ม (ไม่รวมตัวเอง)"))
            else:
                html(section_title("RADAR: คะแนน 5 ด้านของหุ้นที่เลือก", "ไม่มีคู่แข่งในกลุ่ม"))
            show_chart(fig, key="industry_radar")
            if not has_peers:
                html(f'<div style="font-size:13px;color:#64748B;margin-top:-4px;">{no_peer_msg}</div>')
        else:
            html(f'<div style="{CARD}">' + section_title("RADAR") + 'ข้อมูลไม่พอวาดเรดาร์</div>')
    with c4:
        items = ""
        dropped = [n for _, n in DIMS if n not in axes]
        drop_txt = f'<div style="font-size:12.5px;color:#94A3B8;margin-top:6px;">ไม่แสดง: {", ".join(dropped)} (ไม่มีคะแนน)</div>' if dropped else ""
        if has_peers:
            better = 0
            for name, v, pv in zip(axes, mine, peers):
                ok = v >= pv
                better += ok
                icon, colr = ("✓", L.GREEN) if ok else ("✗", L.RED)
                note = " (ปลอดภัยกว่า)" if name == "Risk" and ok else (" (เสี่ยงกว่า)" if name == "Risk" else "")
                items += (f'<div style="padding:6px 0;border-bottom:1px solid #F1F5F9;font-size:14.5px;">'
                          f'<b style="color:{colr};">{icon}</b> <b>{name}</b>{note}<br>'
                          f'<span style="color:#64748B;font-size:13.5px;">หุ้นนี้ {v:.1f} · ค่าเฉลี่ยคู่แข่ง {pv:.1f}</span></div>')
            head = (f"{ctx.selected_ticker} อยู่อันดับ {NA if L.is_missing(rank) else int(rank)} จาก {n_all} "
                    f"และดีกว่าค่าเฉลี่ยคู่แข่งในกลุ่ม {better} จาก {len(axes)} ด้าน")
        else:
            for name, v in zip(axes, mine):
                items += (f'<div style="padding:6px 0;border-bottom:1px solid #F1F5F9;font-size:14.5px;">'
                          f'<b>{name}</b> <span style="color:#64748B;font-size:13.5px;">· คะแนน {v:.1f}</span></div>')
            head = (f"{ctx.selected_ticker} อยู่อันดับ {NA if L.is_missing(rank) else int(rank)} จาก {n_all} · "
                    f"<b>ไม่มีคู่แข่งในกลุ่ม</b> จึงไม่สรุปจุดแข็ง-จุดอ่อน (ดูอันดับเทียบทั้ง {n_all} หุ้นได้ที่การ์ดอันดับรายด้าน)")
        html(f"""<div style="{CARD}">{section_title('จุดแข็ง-จุดอ่อนเทียบคู่แข่ง')}
            <div style="font-size:15px;color:#0F172A;margin-bottom:8px;line-height:1.6;">{head}</div>
            {items}{drop_txt}</div>""")

    render_nav_footer(ctx, PAGE)
