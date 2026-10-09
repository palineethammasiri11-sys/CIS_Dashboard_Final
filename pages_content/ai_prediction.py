"""
pages_content/ai_prediction.py — หน้า 7 AI Prediction
------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.7 (A1-A8)
- โมเดล Random Forest ทำนาย 10 วันทำการ ฝึกข้อมูลก่อน 2025 (ตัดรอยต่อ 10 วัน) ทดสอบปี 2025 (calculate_modules/ai_prediction.py)
- ด่าน "ต้องชนะการเดา": ความแม่นยำ > Baseline และ ROC-AUC > 0.5 → ไม่ผ่าน = NO EDGE: ทิศทาง/โอกาส/คะแนนเป็นสีเทา (D12)
- AI Score = โอกาสขึ้น (ตัดสูตร 0.7/0.3); แสดงผลสอบของโมเดลอย่างเปิดเผย (A3)
- ตัดออก: ประโยคตายตัวที่ไม่ได้มาจากโมเดล

[v17.4] - จัดหน้า: KPI 5 ช่อง → ผลสอบของโมเดล → [Forecast | ความสำคัญของตัวชี้วัด] → [ผลทำนาย | สรุป Explainable AI]
        - ช่อง "ทิศทาง 10 วัน" ใช้ป้ายชุดเดียวกับ AI Score (เอียงขึ้น / ก้ำกึ่ง / เอียงลง) — เดิมโอกาส 49% ขึ้นว่า "ขาลง"
          ขณะที่ป้าย AI Score ขึ้นว่า "ก้ำกึ่ง"
"""

from math import sqrt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, INK, MUTED, FAINT, LINE, NA, TOOLS_H, badge, card, fmt_num, fmt_pct, grid, html, kpi,
                    na_box, num, page_title, render_nav_footer, section_title, show_chart, style_fig)

PAGE = " AI Prediction"
FEATURE_TH = {
    "dist_ema20": "ราคาห่างเส้น EMA20 กี่ %",
    "ema20_vs_ema50": "EMA20 สูงหรือต่ำกว่า EMA50 กี่ % (ความชันแนวโน้ม)",
    "macd_norm": "MACD เทียบขนาดราคา (แรงส่ง)",
    "macd_hist_norm": "MACD Histogram เทียบราคา (แรงส่งเร่งหรือแผ่ว)",
    "RSI14": "RSI 14 วัน (ซื้อมาก/ขายมากเกินไป)",
    "ADX": "ADX (ความแรงของแนวโน้ม)",
    "volume_ratio": "Volume เทียบค่าเฉลี่ย 20 วัน",
    "ret_5d": "ผลตอบแทนย้อนหลัง 5 วัน",
    "ret_10d": "ผลตอบแทนย้อนหลัง 10 วัน",
    "ret_20d": "ผลตอบแทนย้อนหลัง 20 วัน",
    "vol_20d": "ความผันผวนรายวัน 20 วัน",
}
FEATURE_SHORT = {   # ชื่อสั้นสำหรับแกนกราฟ (ชื่อเต็มอยู่ในการ์ดสรุปและ hover)
    "dist_ema20": "ราคาห่าง EMA20", "ema20_vs_ema50": "EMA20 เทียบ EMA50", "macd_norm": "MACD / ราคา",
    "macd_hist_norm": "MACD Hist / ราคา", "RSI14": "RSI 14 วัน", "ADX": "ADX", "volume_ratio": "Volume / เฉลี่ย 20 วัน",
    "ret_5d": "ผลตอบแทน 5 วัน", "ret_10d": "ผลตอบแทน 10 วัน", "ret_20d": "ผลตอบแทน 20 วัน", "vol_20d": "ความผันผวน 20 วัน",
}
Z80 = 1.2816
HORIZON = 10
CHART_H = 340


def render(ctx):
    info = ctx.stock_info
    page_title("AI PREDICTION", "โอกาสที่ราคาจะสูงขึ้นใน 10 วันทำการ และโมเดลของหุ้นนี้เชื่อได้หรือไม่")

    if num(info.get("is_fallback")) or L.is_missing(info.get("accuracy")):          # A8
        html(na_box(f"<b>ข้อมูลไม่พอฝึกหรือทดสอบโมเดล</b><br>{info.get('ai_status') or ''}<br>"
                    "ต้องมีข้อมูลฝึกอย่างน้อย 50 วันและข้อมูลทดสอบอย่างน้อย 20 วัน จึงไม่แสดงตัวเลขใด ๆ", L.RED))
        render_nav_footer(ctx, PAGE)
        return

    edge = bool(num(info.get("model_has_edge")))
    prob = num(info.get("prob_up"))
    lab = L.ai_label(prob, edge)
    acc, base, auc = num(info.get("accuracy")), num(info.get("baseline_accuracy")), num(info.get("roc_auc"))
    hidden = "ไม่แสดง เพราะโมเดลสอบไม่ผ่าน"

    # ---------------- A2 ----------------
    html(grid([
        kpi("ราคาล่าสุด", f"{ctx.current_price:.2f}", f"บาท · {info.get('latest_date', '-')}"),
        kpi("สถานะโมเดล", "ผ่านด่าน" if edge else "ไม่ผ่านด่าน",
            "ชนะการเดาแบบง่ายบนข้อมูลปี 2025" if edge else "NO EDGE · ไม่ชนะการเดาแบบง่าย จึงไม่ใช้ผลทำนาย",
            L.GREEN if edge else L.RED),
        kpi("ทิศทาง 10 วัน", lab["th"] if edge else NA,
            "≥ 65% เอียงขึ้น · 35-64.9% ก้ำกึ่ง · &lt; 35% เอียงลง" if edge else hidden, lab["color"], grey=not edge),
        kpi("โอกาสขึ้น", fmt_pct(prob) if edge else NA, "ความน่าจะเป็นจากโมเดล" if edge else hidden, lab["color"], grey=not edge),
        kpi("AI Score", fmt_num(info.get("ai_score"), 1) if edge else NA,
            (f"{lab['th']} · ไม่นับในคะแนนรวม" if edge else hidden + " · ไม่นับในคะแนนรวม"), lab["color"], grey=not edge),
    ]).replace('class="cis-grid"', 'class="cis-grid wrap-md"'))

    # ---------------- A3: ผลสอบของโมเดล ----------------
    c1_ok = acc is not None and base is not None and acc > base
    c2_ok = auc is not None and auc > 0.5
    mark = lambda ok: f'<b style="color:{L.GREEN if ok else L.RED};">{"ผ่าน ✓" if ok else "ไม่ผ่าน ✕"}</b>'
    if edge:
        sent = (f"{ctx.selected_ticker}: แม่นยำ {acc:.1f}% สูงกว่าการเดา {base:.1f}% และ ROC-AUC {auc:.3f} มากกว่า 0.5 "
                "จึงใช้ผลของโมเดลได้ (ยังเป็นผลทดสอบปีเดียว)")
    else:
        why = []
        if not c1_ok:
            why.append(f"แม่นยำ {fmt_num(acc, 1)}% ไม่สูงกว่าการเดา {fmt_num(base, 1)}%")
        if not c2_ok:
            why.append(f"ROC-AUC {fmt_num(auc, 3)} ไม่เกิน 0.5")
        sent = f"{ctx.selected_ticker}: " + " และ ".join(why) + " จึงไม่ใช้ผลของโมเดล"

    def cell(label, value, sub=""):
        return (f'<div style="min-width:0;"><div style="font-size:12px;color:{MUTED};">{label}</div>'
                f'<div style="font-size:18px;font-weight:800;color:{INK};line-height:1.35;">{value}</div>'
                f'<div style="font-size:11.5px;color:{FAINT};line-height:1.45;">{sub}</div></div>')
    html(card(f"""{section_title('ผลสอบของโมเดล', 'ทดสอบกับข้อมูลที่โมเดลไม่เคยเห็น (ปี 2025)')}
        <div class="cis-grid wrap-md" style="grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;">
          {cell('ความแม่นยำ (ปี 2025)', fmt_pct(acc))}
          {cell('การเดาแบบง่าย (Baseline)', fmt_pct(base), 'เดาคำตอบที่พบบ่อยที่สุดของปี 2025 ทุกวัน')}
          {cell('ROC-AUC', fmt_num(auc, 3), '0.5 = เท่าการโยนเหรียญ')}
          {cell('วันฝึก / วันทดสอบ', f"{int(num(info.get('n_train')) or 0):,} / {int(num(info.get('n_test')) or 0):,}",
                f"ฝึก {info.get('train_start') or '-'} ถึง {info.get('train_end') or '-'} · ตัดรอยต่อ {int(num(info.get('n_purged')) or 0)} วัน")}
          <div style="min-width:0;"><div style="font-size:12px;color:{MUTED};">เงื่อนไขผ่านด่าน</div>
               <div style="font-size:13px;line-height:1.75;">แม่นยำ &gt; Baseline: {mark(c1_ok)}<br>ROC-AUC &gt; 0.5: {mark(c2_ok)}</div></div>
        </div>
        <div style="font-size:14px;color:#334155;margin-top:10px;border-top:1px solid #F1F5F9;padding-top:8px;">{sent}</div>
        <div style="font-size:11.5px;color:{FAINT};margin-top:4px;">ทดสอบตั้งแต่ {info.get('test_start') or '2025-01-01'} ถึง {info.get('test_end') or '-'}
        · ตัดแถวฝึกที่คำตอบ (ราคาอีก 10 วัน) ล้ำเข้าช่วงทดสอบ เพื่อไม่ให้โมเดลแอบเห็นคำตอบ (Purging, López de Prado 2018)</div>"""))

    # ---------------- A5 + A6: Forecast | ความสำคัญของตัวชี้วัด ----------------
    fi = ctx.feat_imp_df
    fi = fi[fi["ticker"] == ctx.selected_ticker].sort_values("importance", ascending=False) if not fi.empty else fi
    top3 = [FEATURE_TH.get(f, f) for f in fi["feature"].head(3)] if not fi.empty else []
    d = ctx.stock_daily.tail(150)
    last_date, price = d["date"].iloc[-1], float(d["close"].iloc[-1])
    vol = num(info.get("volatility"))
    c1, c2 = st.columns([1.5, 1])
    with c1:
        if vol is None:
            html(card(section_title("FORECAST 10 วันทำการ") + "ไม่มีข้อมูลความผันผวน", f"min-height:{CHART_H}px;"))
        else:
            sigma = vol / 100 / sqrt(252)
            drift = ((prob - 50) / 50 * sigma * HORIZON) if (edge and prob is not None) else 0.0
            fut = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=HORIZON)
            t = list(range(1, HORIZON + 1))
            mid = [price * (1 + drift * i / HORIZON) for i in t]
            up = [m + Z80 * price * sigma * sqrt(i) for m, i in zip(mid, t)]
            dn = [m - Z80 * price * sigma * sqrt(i) for m, i in zip(mid, t)]
            xs = [last_date] + list(fut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d["date"], y=d["close"], name="ราคาจริง", mode="lines", line=dict(color=INK, width=1.6)))
            fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[price] + up + ([price] + dn)[::-1], fill="toself",
                                     fillcolor="rgba(168,85,247,0.15)", line=dict(width=0), name="ช่วงราคา 80%", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=xs, y=[price] + mid, name="เส้นกลาง" if edge else "ไม่มีมุมมองทิศทาง", mode="lines",
                                     line=dict(color="#A855F7", width=2, dash="dash")))
            if edge and prob is not None:
                fig.add_annotation(x=xs[-1], y=mid[-1], text=f"โอกาสขึ้น {prob:.0f}%", showarrow=True, arrowhead=2,
                                   font=dict(size=12, color=lab["color"]), ax=-50, ay=-34, bgcolor="rgba(255,255,255,0.9)")
            style_fig(fig, height=CHART_H, legend=True, title="FORECAST 10 วันทำการ",
                      sub="แถบ = ช่วงราคาราว 80% ของกรณี · ทิศทางดูจากเส้นกลาง")
            fig.update_layout(xaxis=dict(title=None), yaxis=dict(title="ราคา (บาท)"), hovermode="x unified")
            show_chart(fig, key="ai_forecast")
    with c2:
        if fi.empty:
            html(card(section_title("ความสำคัญของตัวชี้วัด") + "ไม่มีข้อมูล", f"min-height:{CHART_H}px;"))
        else:
            f2 = fi.sort_values("importance")
            fig2 = go.Figure(go.Bar(x=f2["importance"], y=[FEATURE_SHORT.get(f, f) for f in f2["feature"]], orientation="h",
                                    marker_color="#A855F7" if edge else "#CBD5E1",
                                    customdata=[FEATURE_TH.get(f, f) for f in f2["feature"]],
                                    hovertemplate="%{customdata}<br>ความสำคัญ %{x:.3f}<extra></extra>"))
            style_fig(fig2, height=CHART_H, title="ความสำคัญของตัวชี้วัด",
                      sub="โมเดลสอบไม่ผ่าน ไม่ควรตีความมาก" if not edge else "ตัวที่ใช้แยกวันขึ้น/ลงบ่อยที่สุด")
            fig2.update_layout(xaxis=dict(title="Mean Decrease in Impurity"), yaxis=dict(tickfont=dict(size=11)), bargap=0.3)
            show_chart(fig2, key="ai_feature_importance")

    # ---------------- A4 + A7: ผลทำนาย | Explainable AI ----------------
    if edge and prob is not None:
        pred = card(f"""{section_title('ผลทำนาย')}
            <div style="display:flex;height:22px;border-radius:8px;overflow:hidden;font-size:12px;font-weight:700;color:#fff;">
              <div style="width:{prob}%;background:{L.GREEN};padding-left:8px;line-height:22px;white-space:nowrap;">ขึ้น {prob:.1f}%</div>
              <div style="width:{100 - prob}%;background:{L.RED};text-align:right;padding-right:8px;line-height:22px;white-space:nowrap;">ลง {100 - prob:.1f}%</div></div>
            <div style="font-size:14px;color:#334155;margin-top:10px;line-height:1.7;">โมเดลประเมินว่า {ctx.selected_ticker} มีโอกาสขึ้น
            <b style="color:{lab['color']};">{prob:.1f}%</b> ใน 10 วันทำการ ({lab['th']}) โดยดูจาก {', '.join(top3) or '-'} มากที่สุด</div>""")
    else:
        pred = card(section_title('ผลทำนาย') + na_box("โมเดลทำนายหุ้นนี้ไม่ได้ดีกว่าการเดา (ไม่ผ่านด่าน) จึงไม่แสดงผลทำนาย "
                                                      "— ดูเหตุผลได้ที่การ์ด “ผลสอบของโมเดล” ด้านบน"))
    if top3:
        items = "".join(f"<li><b>{FEATURE_TH.get(f, f)}</b> <span style='color:{FAINT};'>({f})</span></li>" for f in fi["feature"].head(3))
        xai = card(f"""{section_title('สรุป Explainable AI')}
            <div style="font-size:13.5px;color:#334155;">ตัวชี้วัด 3 อันดับแรกที่โมเดลใช้ตัดสิน:</div>
            <ol style="margin:4px 0 0 20px;padding:0;font-size:13.5px;line-height:1.75;color:#334155;">{items}</ol>
            <div style="font-size:12px;color:{MUTED};margin-top:4px;">ความสำคัญบอกว่าโมเดล “ใช้อะไร” ตัดสิน ไม่ได้บอกว่าค่าสูงทำให้ขึ้นหรือลง
            {'· โมเดลนี้สอบไม่ผ่าน จึงไม่ควรตีความมาก' if not edge else ''}</div>""")
        html(grid([pred, xai], template="minmax(0,1fr) minmax(0,1fr)"))
    else:
        html(pred)

    render_nav_footer(ctx, PAGE)
