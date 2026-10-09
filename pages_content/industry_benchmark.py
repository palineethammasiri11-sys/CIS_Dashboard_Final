"""
pages_content/industry_benchmark.py — หน้า 1 Industry Benchmark (ภาพรวม 8 หุ้น)
---------------------------------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.1 (I1-I7)
- ตัวเลขทุกตัวอ่านจากตาราง cis_summary_scores (หลังบ้าน) ไม่คำนวณสูตรหลักซ้ำบนจอ
- ป้าย/สีทุกช่องมาจาก calculate_modules/labels.py ชุดเดียวกับทุกหน้า
- ตัดออกจากเวอร์ชันเดิม: ดาว, ป้าย LEADER/STRONG COMPETITOR ตามอันดับ, "Top x%", ตาราง Peer Comparison เฉพาะกลุ่ม,
  แกน Industry Score ในเรดาร์ (D6, D14)

[v17.4] จัดหน้าใหม่ให้กระชับ (เลื่อนน้อยลง) และสมมาตร
    แถว 1: ตารางจัดอันดับ 8 หุ้น | Strategic Matrix (วางคู่กัน สูงใกล้เคียงกัน)
    แถว 2: แถบสรุปหุ้นที่เลือก + อันดับรายด้าน 6 ช่อง (CSS Grid สูงเท่ากัน)
    แถว 3: Radar | จุดแข็ง-จุดอ่อน (สูงเท่ากัน)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, INK, MUTED, FAINT, LINE, NA, TOOLS_H, badge, card, fmt_num, grid, html, num, page_title,
                    rank_text, render_nav_footer, section_title, show_chart, style_fig, tile)

PAGE = " Industry Benchmark"
DIMS = [  # (คอลัมน์คะแนน, ชื่อ)
    ("health_score", "Health"), ("valuation_score", "Fair Value"), ("risk_score", "Risk"),
    ("timing_score", "Entry Timing"), ("ai_score", "AI"),
]
SECTOR_SHORT = {"Technology & Telecomm": "Tech & Telecom", "Electronic Components": "Electronics",
                "Commerce & Technology": "Commerce & Tech"}
TOP_ROW_H = 532     # ความสูงแถวบน (ตาราง | Matrix + แถบเครื่องมือ) ให้เท่ากัน
RADAR_H = 330


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
    return (f'<span title="{lab["th"]}" style="display:inline-block;min-width:46px;text-align:center;background:{lab["bg"]};'
            f'color:{lab["color"]};border:1px solid {lab["color"]};border-radius:7px;padding:1px 5px;font-size:12px;'
            f'font-weight:700;white-space:nowrap;">{s}</span>')


def _ranking_table(df, selected):
    """I2: ตารางจัดอันดับทั้ง 8 หุ้น"""
    rows = ""
    td = "padding:6px 5px;"
    for _, r in df.sort_values(["overall_rank", "ticker"]).iterrows():
        rec = L.overall_label(r.get("overall_score"))
        sel = r["ticker"] == selected
        bg = "background:rgba(6,182,212,0.09);" if sel else ""
        bold = "font-weight:800;" if sel else "font-weight:600;"
        chips = "".join(f'<td style="{td}text-align:center;">{_chip(_module_label(r, c), r.get(c))}</td>' for c, _ in DIMS)
        rank = NA if L.is_missing(r.get("overall_rank")) else int(r["overall_rank"])
        sector = SECTOR_SHORT.get(r.get("sector"), r.get("sector", "-"))
        rows += f"""<tr style="border-top:1px solid #F1F5F9;{bg}">
            <td style="{td}text-align:center;{bold}color:{INK};">{rank}</td>
            <td style="{td}"><div style="{bold}color:{INK};line-height:1.2;">{r['ticker']}{' ◀' if sel else ''}</div>
                <div style="font-size:11.5px;color:{FAINT};line-height:1.2;white-space:nowrap;">{sector}</div></td>
            <td style="{td}text-align:center;font-weight:800;color:{rec['color']};">{fmt_num(r.get('overall_score'), 1)}</td>
            <td style="{td}"><span style="color:{rec['color']};font-weight:700;font-size:12.5px;white-space:nowrap;">{rec['th']}</span></td>
            {chips}</tr>"""
    head = "".join(f'<th style="padding:4px 5px;text-align:center;font-weight:700;">{n}</th>' for _, n in DIMS)
    inner = f"""{section_title('ตารางจัดอันดับทั้ง 8 หุ้น', 'เรียงตามคะแนนรวม · ตัวเลข = คะแนน 0-100 ของโมดูล')}
        <div class="cis-table-wrap"><table style="width:100%;border-collapse:collapse;font-size:13.5px;">
        <tr style="color:{MUTED};font-size:12px;"><th style="padding:4px 5px;font-weight:700;">อันดับ</th>
        <th style="padding:4px 5px;text-align:left;font-weight:700;">หุ้น</th><th style="padding:4px 5px;font-weight:700;white-space:nowrap;">คะแนนรวม</th>
        <th style="padding:4px 5px;text-align:left;font-weight:700;">คำแนะนำ</th>{head}</tr>{rows}</table></div>
        <div style="font-size:12px;color:{MUTED};margin-top:8px;line-height:1.55;">
        คะแนนรวม = Health 25 : Fair Value 25 : Entry Timing 15 : Risk 15 (ทุกหุ้นนับครบ 4 โมดูล) ·
        สีช่องใช้เกณฑ์กลางของแต่ละโมดูล (Fair Value ใช้ Margin of Safety ±10%, Entry Timing ราคาต่ำกว่า MA200 = แดง) ·
        AI แสดงประกอบ ไม่นับในคะแนนรวม (สอบไม่ผ่าน = NO EDGE)</div>"""
    return card(inner, f"min-height:{TOP_ROW_H}px;")


def _label_positions(d):
    """วางชื่อหุ้นไม่ให้ทับกันเมื่อจุดอยู่ใกล้กัน: จุดแรกของกลุ่มใช้ป้ายด้านบน
    จุดถัดไปที่อยู่ใกล้ (ห่างไม่เกิน 12 แนวนอน / 10 แนวตั้ง) เลือกตำแหน่งที่เพื่อนบ้านยังไม่ใช้ (ขวา → ซ้าย → ล่าง)"""
    order = ["middle right", "middle left", "bottom center", "top center"]
    pts = list(zip(d["ticker"], d["health_score"].astype(float), d["overall_score"].astype(float)))
    pos = {}
    for i, (t, x, y) in enumerate(pts):
        near = [p[0] for p in pts[:i] if abs(p[1] - x) < 12 and abs(p[2] - y) < 10]
        if not near:
            pos[t] = "top center"
            continue
        used = {pos[n] for n in near}
        pos[t] = next((o for o in order if o not in used), "bottom center")
    return pos


def _matrix(df, selected):
    """I3: Strategic Matrix (ตัดแกนที่ 50 ทั้งสองแกน — D17)"""
    fig = go.Figure()
    d = df.dropna(subset=["health_score", "overall_score"]).sort_values("overall_score", ascending=False)
    pos = _label_positions(d)
    for _, r in d.iterrows():
        sel = r["ticker"] == selected
        color = L.overall_label(r["overall_score"])["color"] if sel else "#94A3B8"
        fig.add_trace(go.Scatter(
            x=[r["health_score"]], y=[r["overall_score"]], mode="markers+text", text=[r["ticker"]],
            textposition=pos[r["ticker"]], textfont=dict(size=12.5 if sel else 11, color=INK if sel else MUTED),
            marker=dict(size=16 if sel else 10, color=color, line=dict(width=2 if sel else 0, color=INK)),
            showlegend=False, cliponaxis=False,
            hovertemplate=f"{r['ticker']}<br>Health %{{x:.1f}}<br>คะแนนรวม %{{y:.1f}}<extra></extra>"))
    for txt, x, y in [("Market Leader", 98, 98), ("Hidden Gem", 2, 98), ("Competitive", 98, 2), ("Value Trap", 2, 2)]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, font=dict(size=11.5, color="#94A3B8"),
                           xanchor="right" if x > 50 else "left", yanchor="top" if y > 50 else "bottom")
    fig.add_vline(x=50, line_dash="dash", line_color="#CBD5E1", layer="below")
    fig.add_hline(y=50, line_dash="dash", line_color="#CBD5E1", layer="below")
    style_fig(fig, height=TOP_ROW_H - TOOLS_H, title="STRATEGIC MATRIX", sub="บริษัทดี ≠ หุ้นน่าซื้อ · เส้นแบ่งที่ 50")
    fig.update_layout(xaxis=dict(title="Health Score (คุณภาพธุรกิจ)", range=[0, 100]),
                      yaxis=dict(title="คะแนนรวม", range=[0, 100]))
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

    # ---------------- แถว 1: ทั้ง 8 หุ้น ----------------
    c1, c2 = st.columns([1.6, 1])
    with c1:
        html(_ranking_table(df, ctx.selected_ticker))
    with c2:
        show_chart(_matrix(df, ctx.selected_ticker), key="industry_matrix", compact_tools=True)

    # ---------------- แถว 2: หุ้นที่เลือก (แถบสรุป + อันดับรายด้าน) ----------------
    n_all = len(df)
    overall = num(info.get("overall_score"))
    rank = info.get("overall_rank")
    top = pd.to_numeric(df["overall_score"], errors="coerce").max()
    med = pd.to_numeric(df["overall_score"], errors="coerce").median()
    sector_n = int(info.get("sector_n") or 1)
    sector_txt = (f"อันดับ {int(info['sector_rank'])} จาก {sector_n} ในกลุ่ม {info.get('sector')}" if sector_n > 1
                  else f"กลุ่ม {info.get('sector')} ยังไม่มีหุ้นอื่นในชุดข้อมูล")
    rec = L.overall_label(overall)
    gap_top = NA if overall is None else f"{overall - top:+.1f}"
    gap_med = NA if overall is None else f"{overall - med:+.1f}"

    summary = card(f"""
        <div style="font-size:12.5px;font-weight:700;color:{MUTED};">หุ้นที่เลือก</div>
        <div style="font-size:24px;font-weight:800;color:{INK};line-height:1.25;margin-top:2px;">{ctx.selected_ticker}
          <span style="font-size:15px;color:{MUTED};font-weight:700;">อันดับ {NA if L.is_missing(rank) else int(rank)} จาก {n_all}</span></div>
        <div style="margin-top:6px;">{badge(rec, 12)}</div>
        <div style="font-size:13px;color:#475569;line-height:1.7;margin-top:6px;">
          คะแนนรวม <b style="color:{rec['color']};">{fmt_num(overall, 1)}</b> · ห่างอันดับ 1 <b>{gap_top}</b><br>
          ห่างค่ากลาง 8 หุ้น ({med:.1f}) <b>{gap_med}</b><br>{sector_txt}</div>""",
        f"border:1.5px solid {rec['color']};")

    tiles = []
    for col, name in DIMS + [("revenue_growth_yoy", "การเติบโตของรายได้")]:
        v = info.get(col)
        if col == "ai_score" and L.is_missing(v):
            main, sub = "N/A (NO EDGE)", "โมเดลสอบไม่ผ่าน ไม่จัดอันดับ"
        else:
            main = rank_text(info, col, with_sector=False).replace("อันดับ ", "")
            sub = (f"ในกลุ่ม {int(info['srank_' + col])}/{sector_n}" if sector_n > 1 and not L.is_missing(info.get('srank_' + col))
                   else "กลุ่มนี้มีหุ้นเดียว")
        val = fmt_num(v, 1, "%" if col == "revenue_growth_yoy" else "", sign=(col == "revenue_growth_yoy"))
        tiles.append(tile(name, main, f"ค่า {val} · {sub}", size=16))
    ranks = card(section_title("อันดับรายด้านของหุ้นที่เลือก", "อันดับ 1 = ดีที่สุดในด้านนั้น (Risk: ปลอดภัยที่สุด)")
                 + grid(tiles, cols=3, style="gap:8px;"))
    html(grid([summary, ranks], template="minmax(250px,1fr) minmax(0,2.6fr)"))

    # ---------------- แถว 3: Radar | จุดแข็ง-จุดอ่อน ----------------
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
    c3, c4 = st.columns([1, 1])
    with c3:
        if len(axes) >= 3:
            fig = go.Figure()
            if has_peers:
                fig.add_trace(go.Scatterpolar(r=peers + peers[:1], theta=axes + axes[:1], name="ค่าเฉลี่ยคู่แข่งในกลุ่ม",
                                              line=dict(color="#64748B", dash="dash"), fill=None))
            fig.add_trace(go.Scatterpolar(r=mine + mine[:1], theta=axes + axes[:1], name=ctx.selected_ticker,
                                          line=dict(color="#06B6D4", width=2), fill="toself", fillcolor="rgba(6,182,212,0.18)"))
            style_fig(fig, height=RADAR_H,
                      title="RADAR" + (": เทียบค่าเฉลี่ยคู่แข่งในกลุ่ม" if has_peers else ": คะแนน 5 ด้าน"),
                      sub="ไม่รวมตัวเอง" if has_peers else "ไม่มีคู่แข่งในกลุ่ม", margin=dict(l=60, r=60, t=58, b=40))
            # legend ไว้ใต้กราฟ (เดิมอยู่บนแล้วทับชื่อแกน Fair Value) · ตัวเลขแกนรัศมีวางทแยง 45° ไม่ทับแกนใด
            fig.update_layout(showlegend=True,
                              legend=dict(orientation="h", yanchor="top", y=-0.04, xanchor="center", x=0.5, font=dict(size=11.5)),
                              polar=dict(radialaxis=dict(range=[0, 100], angle=45, tickangle=45, tickvals=[25, 50, 75, 100],
                                                         tickfont=dict(size=10, color=FAINT)),
                                         angularaxis=dict(tickfont=dict(size=12.5, color=INK))))
            show_chart(fig, key="industry_radar")
        else:
            html(card(section_title("RADAR") + "ข้อมูลไม่พอวาดเรดาร์", f"min-height:{RADAR_H}px;"))
    with c4:
        items = ""
        dropped = [n for _, n in DIMS if n not in axes]
        drop_txt = (f'<div style="font-size:12px;color:{FAINT};margin-top:6px;">ไม่แสดง: {", ".join(dropped)} '
                    f'(ไม่มีคะแนน)</div>') if dropped else ""
        if has_peers:
            better = 0
            for name, v, pv in zip(axes, mine, peers):
                ok = v >= pv
                better += ok
                icon, colr = ("✓", L.GREEN) if ok else ("✗", L.RED)
                note = " (ปลอดภัยกว่า)" if name == "Risk" and ok else (" (เสี่ยงกว่า)" if name == "Risk" else "")
                items += (f'<div style="display:flex;justify-content:space-between;gap:8px;padding:6px 0;'
                          f'border-bottom:1px solid #F1F5F9;font-size:13.5px;">'
                          f'<span><b style="color:{colr};">{icon}</b> <b>{name}</b>{note}</span>'
                          f'<span style="color:{MUTED};white-space:nowrap;">หุ้นนี้ {v:.1f} · คู่แข่ง {pv:.1f}</span></div>')
            head = (f"{ctx.selected_ticker} ดีกว่าค่าเฉลี่ยคู่แข่งในกลุ่ม <b>{better} จาก {len(axes)}</b> ด้าน")
        else:
            for name, v in zip(axes, mine):
                items += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F1F5F9;'
                          f'font-size:13.5px;"><b>{name}</b><span style="color:{MUTED};">คะแนน {v:.1f}</span></div>')
            head = (f"{ctx.selected_ticker} <b>ไม่มีคู่แข่งในกลุ่ม</b> จึงไม่สรุปจุดแข็ง-จุดอ่อน "
                    f"(ดูอันดับเทียบทั้ง {n_all} หุ้นได้ที่การ์ดอันดับรายด้านด้านบน)")
        extra = f'<div style="font-size:12.5px;color:{MUTED};margin-top:8px;line-height:1.55;">{no_peer_msg}</div>' if not has_peers else ""
        html(card(f"""{section_title('จุดแข็ง-จุดอ่อนเทียบคู่แข่ง')}
            <div style="font-size:14px;color:{INK};margin-bottom:6px;line-height:1.6;">{head}</div>
            {items}{drop_txt}{extra}""", f"min-height:{RADAR_H + TOOLS_H}px;"))

    render_nav_footer(ctx, PAGE)
