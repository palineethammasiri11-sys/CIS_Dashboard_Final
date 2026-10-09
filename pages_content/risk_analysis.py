"""
pages_content/risk_analysis.py — หน้า 5 Risk Analysis
------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.5 (R1-R10)
- ทุกตัวเลขในหน้านี้ใช้ช่วง 3 ปีล่าสุดชุดเดียวกัน (TRUE เริ่ม 3 มี.ค. 2023 หลังควบรวม) และอ่านจากหลังบ้านเท่านั้น
  (เดิมหน้าจอคิด Max Drawdown / Calmar เองจากข้อมูล 11 ปี ทำให้ ADVANC แสดง −48.6% แทน −14.8%)
- ที่มาของ Risk Score แสดงเป็นตาราง 5 มิติที่ใช้คิดจริง (D13); VaR, Sharpe ฯลฯ แสดงเป็นอันดับเทียบ 8 หุ้น (D14)
- ตัดออก: การ์ด 6 มิติที่ไม่ใช่ส่วนประกอบของคะแนน (เก็บ D/E และ Current Ratio เป็นค่าจริง), ข้อความตายตัวที่ไม่ได้มาจากข้อมูล
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, NA, badge, fmt_num, fmt_pct, html, json_list, num, page_title, rank_text, render_nav_footer,
                    ring, section_title, show_chart)

PAGE = " Risk Analysis"


def _thai_date(d):
    try:
        return pd.Timestamp(d).strftime("%d/%m/%Y")
    except Exception:
        return "-"


def _real_value(dim, d, info):
    v = d.get("real_value")
    if dim == "tail":
        return fmt_pct(v, 2)
    if dim == "drawdown":
        rec = "ยังไม่ฟื้น (+10)" if not num(info.get("recovered")) else f"ฟื้นใน {int(info['recovery_days'])} วัน (+{num(info.get('recovery_penalty')) or 0:.0f})"
        return f"{fmt_pct(v, 1)} · {rec}"
    if dim == "volatility":
        return fmt_pct(v, 1)
    if dim == "market":
        return fmt_num(v, 2)
    return NA if v is None else f"PSR {float(v):.1f}%"


RULES = {"tail": "CVaR × 10", "drawdown": "Max DD × 1.5 + โทษฟื้นช้า", "volatility": "ความผันผวน × 1.3",
         "market": "Beta × 40", "quality": "100 − PSR"}


def _metric_box(title, value, rank, desc):
    return (f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:12px;">'
            f'<div style="font-size:13.5px;font-weight:800;color:#0F172A;">{title}</div>'
            f'<div style="font-size:21px;font-weight:800;color:#0F172A;margin:3px 0;">{value}</div>'
            f'<div style="font-size:12.5px;color:#475569;">{rank}</div>'
            f'<div style="font-size:12px;color:#64748B;margin-top:4px;line-height:1.5;">{desc}</div></div>')


def render(ctx):
    info, df = ctx.stock_info, ctx.scores_df
    d0, d1 = _thai_date(info.get("risk_window_start")), _thai_date(info.get("risk_window_end"))
    page_title("RISK ANALYSIS", f"ถือหุ้นนี้แล้วเจ็บได้แค่ไหน · ข้อมูลราคา {d0} ถึง {d1} (3 ปีล่าสุด) · ทุกตัวเลขในหน้านี้ใช้ช่วงนี้")

    score = num(info.get("risk_score"))
    lab = L.risk_label(score)
    bd = json_list(info.get("risk_breakdown"))
    top = max([d for d in bd if d.get("deduction") is not None], key=lambda d: d["deduction"], default=None)

    # ---------------- R2 + R3 ----------------
    c1, c2 = st.columns([1, 2.3])
    with c1:
        html(f"""<div style="{CARD}text-align:center;height:100%;">{section_title('RISK SCORE', 'ยิ่งสูงยิ่งปลอดภัย')}
            {ring(score, lab['color'], size=120)}
            <div style="margin-top:10px;">{badge(lab, 14)}</div>
            <div style="font-size:12.5px;color:#64748B;margin-top:8px;">≥ 65 เสี่ยงต่ำ · 50-64.9 ปานกลาง · &lt; 50 เสี่ยงสูง</div>
            <div style="font-size:12.5px;color:#64748B;margin-top:4px;">{rank_text(info, 'risk_score')} · คิดจาก {int(info.get('risk_dims_used') or 0)}/5 มิติ</div></div>""")
    with c2:
        rows = ""
        for d in bd:
            hi = top is not None and d["dim"] == top["dim"]
            bg = "background:rgba(239,68,68,0.07);" if hi else ""
            w = d.get("weight_used")
            rows += (f'<tr style="border-top:1px solid #F1F5F9;{bg}"><td style="padding:7px 8px;">{d["name"]}'
                     f'<div style="font-size:11.5px;color:#94A3B8;">{RULES[d["dim"]]} · ตัดที่ 5-95</div></td>'
                     f'<td style="padding:7px 8px;text-align:right;">{_real_value(d["dim"], d, info)}</td>'
                     f'<td style="padding:7px 8px;text-align:right;">{fmt_num(d.get("hazard"), 1)}</td>'
                     f'<td style="padding:7px 8px;text-align:right;">{NA if w is None else f"{w * 100:.0f}%"} '
                     f'<span style="color:#94A3B8;font-size:12px;">({d["weight_nominal"] * 100:.0f}%)</span></td>'
                     f'<td style="padding:7px 8px;text-align:right;font-weight:800;color:{L.RED if hi else "#0F172A"};">{fmt_num(d.get("deduction"), 1)}</td></tr>')
        html(f"""<div style="{CARD}">{section_title('ที่มาของ Risk Score (5 มิติ)', 'Risk Score = 100 − ผลรวม “หักคะแนน” · แถวสีแดง = สาเหตุหลักของความเสี่ยง')}
            <table style="width:100%;border-collapse:collapse;font-size:14px;"><tr style="color:#64748B;font-size:12.5px;">
            <th style="padding:6px 8px;text-align:left;">มิติ</th><th style="padding:6px 8px;text-align:right;">ค่าจริง</th>
            <th style="padding:6px 8px;text-align:right;">คะแนนอันตราย</th><th style="padding:6px 8px;text-align:right;">น้ำหนักที่ใช้ (ตั้งต้น)</th>
            <th style="padding:6px 8px;text-align:right;">หักคะแนน</th></tr>{rows}
            <tr style="border-top:2px solid #E2E8F0;"><td colspan="4" style="padding:7px 8px;text-align:right;font-weight:700;">Risk Score = 100 − {sum(d['deduction'] for d in bd if d.get('deduction') is not None):.1f}</td>
            <td style="padding:7px 8px;text-align:right;font-weight:800;color:{lab['color']};">{fmt_num(score, 1)}</td></tr></table>
            <div style="font-size:12px;color:#94A3B8;margin-top:6px;">โทษฟื้นช้า: ฟื้นเกิน 180 วัน +3 · เกิน 365 วัน +7 · ยังไม่ฟื้น +10 ·
            มิติที่ไม่มีข้อมูลไม่นับและปรับน้ำหนักที่เหลือให้รวม 100% · ตัวคูณและน้ำหนักเป็นค่าที่ทีมกำหนด</div></div>""")

    # ---------------- R4 + R5 + R6 ----------------
    c3, c4, c5 = st.columns(3)
    with c3:
        b = df[["ticker", "beta"]].copy()
        b["beta"] = pd.to_numeric(b["beta"], errors="coerce")
        b = b.dropna().sort_values("beta")
        colors = ["#EF4444" if t == ctx.selected_ticker else "#CBD5E1" for t in b["ticker"]]
        fig = go.Figure(go.Bar(x=b["beta"], y=b["ticker"], orientation="h", marker_color=colors,
                               text=[f"{v:.2f}" for v in b["beta"]], textposition="outside",
                               hovertemplate="%{y}: Beta %{x:.2f}<extra></extra>"))
        fig.add_vline(x=1.0, line_dash="dash", line_color="#475569", annotation_text="ตลาด = 1.0", annotation_position="top")
        fig.update_layout(height=320, margin=dict(l=10, r=30, t=30, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          xaxis=dict(title="Beta (เทียบ TDEX)", gridcolor="#F1F5F9"), yaxis=dict(title=""))
        html(section_title("BETA เทียบ 8 หุ้น", f"{ctx.selected_ticker} = {fmt_num(info.get('beta'), 2)}"))
        show_chart(fig, key="risk_beta")
        r2 = num(info.get("beta_r2"))
        warn = (f'<div style="color:{L.YELLOW};font-size:12.5px;margin-top:4px;">⚠ R² ต่ำกว่า 0.3: Beta อธิบายการเคลื่อนไหวของหุ้นนี้ได้น้อย</div>'
                if (r2 is not None and r2 < 0.3) else "")
        html(f"""<div style="font-size:13px;color:#475569;line-height:1.6;">Beta {fmt_num(info.get('beta'), 2)} · Downside Beta {fmt_num(info.get('downside_beta'), 2)}
            · R² {fmt_num(r2, 2)} · ดัชนี: TDEX (ETF อ้างอิง SET50)<br>Beta 2.0 = เมื่อตลาดขยับ 1% หุ้นขยับไปทางเดียวกันราว 2% <b>โดยเฉลี่ย</b>;
            R² = สัดส่วนการขยับของหุ้นที่ตลาดอธิบายได้{warn}</div>""")
    rh = ctx.risk_hist_df
    rh = rh[rh["ticker"] == ctx.selected_ticker].sort_values("date") if not rh.empty else rh
    with c4:
        html(section_title("ความผันผวน 30 วัน", f"ทั้งช่วง 3 ปี = {fmt_pct(info.get('volatility'))} ต่อปี"))
        if rh.empty:
            html("ไม่มีข้อมูล")
        else:
            fig = go.Figure(go.Scatter(x=rh["date"], y=rh["rolling_vol_30d"], mode="lines", line=dict(color="#F59E0B", width=2),
                                       hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1f}% ต่อปี<extra></extra>"))
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                              xaxis=dict(title="วันที่ (ปลายสัปดาห์)"), yaxis=dict(title="ความผันผวนต่อปี (%)", gridcolor="#F1F5F9"))
            show_chart(fig, key="risk_volatility")
    with c5:
        rec = "ยังไม่ฟื้น" if not num(info.get("recovered")) else f"ฟื้นใน {int(info['recovery_days'])} วัน"
        html(section_title("DRAWDOWN", f"Max Drawdown 3 ปี = −{fmt_num(info.get('max_drawdown'), 1)}% · {rec}"))
        if rh.empty:
            html("ไม่มีข้อมูล")
        else:
            fig = go.Figure(go.Scatter(x=rh["date"], y=rh["drawdown_pct"], mode="lines", line=dict(color="#EF4444", width=1.5),
                                       fill="tozeroy", fillcolor="rgba(239,68,68,0.15)",
                                       hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1f}% จากจุดสูงสุด<extra></extra>"))
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                              xaxis=dict(title="วันที่"), yaxis=dict(title="% ต่ำกว่าจุดสูงสุดก่อนหน้า", gridcolor="#F1F5F9"))
            show_chart(fig, key="risk_drawdown")

    # ---------------- R7 + R8 ----------------
    boxes = "".join([
        _metric_box("VaR 95%", fmt_pct(info.get("var_95"), 2), rank_text(info, "var_95", False) + " (ยิ่งต่ำยิ่งดี)",
                    "ใน 95 วันจาก 100 วัน ขาดทุนไม่เกินค่านี้ต่อวัน (Historical)"),
        _metric_box("CVaR 95%", fmt_pct(info.get("cvar_95"), 2), rank_text(info, "cvar_95", False) + " (ยิ่งต่ำยิ่งดี)",
                    "ใน 5 วันที่แย่ที่สุด ขาดทุนเฉลี่ยวันละเท่านี้"),
        _metric_box("Sharpe", fmt_num(info.get("sharpe_ratio"), 2), rank_text(info, "sharpe_ratio", False) + " (ยิ่งสูงยิ่งดี)",
                    "(ผลตอบแทนต่อปี − 1.66%) ÷ ความผันผวนต่อปี"),
        _metric_box("Sortino", fmt_num(info.get("sortino_ratio"), 2), rank_text(info, "sortino_ratio", False) + " (ยิ่งสูงยิ่งดี)",
                    "เหมือน Sharpe แต่นับเฉพาะความผันผวนขาลง"),
        _metric_box("Calmar", fmt_num(info.get("calmar_ratio"), 2), rank_text(info, "calmar_ratio", False) + " (ยิ่งสูงยิ่งดี)",
                    f"ผลตอบแทนเฉลี่ยต่อปี ({fmt_pct(info.get('annual_return'), 1, sign=True)}) ÷ Max Drawdown"),
        _metric_box("PSR", fmt_pct(info.get("psr"), 1), rank_text(info, "psr", False) + " (ยิ่งสูงยิ่งดี)",
                    "โอกาสที่ Sharpe จริงมากกว่า 0 (Bailey & López de Prado)"),
    ])
    html(f"""<div style="{CARD}margin-top:14px;">{section_title('ขาดทุนในวันแย่ ๆ และผลตอบแทนเทียบความเสี่ยง', 'ไม่ตั้งเกณฑ์ดี/ไม่ดีเอง ใช้อันดับเทียบ 8 หุ้น · ช่วงข้อมูลเดียวกันทุกตัว')}
        <div style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;">{boxes}</div></div>""")

    # ---------------- R9 + R10 ----------------
    c6, c7 = st.columns([1, 1.6])
    with c6:
        de = num(info.get("de_ratio"))
        de_txt = NA if de is None else (f"{de:.2f} (ทุนติดลบ)" if de < 0 else f"{de:.2f} เท่า")
        html(f"""<div style="{CARD}height:100%;">{section_title('ความเสี่ยงจากงบการเงิน', 'ไม่นับใน Risk Score')}
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            {_metric_box('D/E', de_txt, rank_text(info, 'de_ratio', False) + ' (ยิ่งต่ำยิ่งดี)', 'หนี้สินรวม ÷ ส่วนผู้ถือหุ้น')}
            {_metric_box('Current Ratio', fmt_num(info.get('current_ratio'), 2, ' เท่า'), rank_text(info, 'current_ratio', False),
                         'ต่ำกว่า 1 = หนี้ระยะสั้นมากกว่าสินทรัพย์หมุนเวียน')}</div></div>""")
    with c7:
        top_txt = top["name"] if top else NA
        summary = (f"{ctx.selected_ticker} มี Risk Score {fmt_num(score, 1)} ({lab['th']}) มิติที่หักคะแนนมากที่สุดคือ "
                   f"<b>{top_txt}</b> · Beta {fmt_num(info.get('beta'), 2)} · ความผันผวน {fmt_pct(info.get('volatility'))} ต่อปี · "
                   f"Max Drawdown −{fmt_num(info.get('max_drawdown'), 1)}% ({rec}) · ข้อมูล {d0} ถึง {d1}")
        html(f"""<div style="{CARD}height:100%;">{section_title('สรุปความเสี่ยง')}
            <div style="font-size:15px;color:#334155;line-height:1.8;">{summary}</div></div>""")

    render_nav_footer(ctx, PAGE)
