"""
pages_content/ai_prediction.py — หน้า 7 AI Prediction
------------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.7 (A1-A8)
- โมเดล Random Forest ทำนาย 10 วันทำการ ฝึกข้อมูลก่อน 2025 (ตัดรอยต่อ 10 วัน) ทดสอบปี 2025 (calculate_modules/ai_prediction.py)
- ด่าน "ต้องชนะการเดา": ความแม่นยำ > Baseline และ ROC-AUC > 0.5 → ไม่ผ่าน = NO EDGE: ทิศทาง/โอกาส/คะแนนเป็นสีเทา (D12)
- AI Score = โอกาสขึ้น (ตัดสูตร 0.7/0.3); แสดงผลสอบของโมเดลอย่างเปิดเผย (A3)
- ตัดออก: ประโยคตายตัวที่ไม่ได้มาจากโมเดล
"""

from math import sqrt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculate_modules import labels as L
from common import (CARD, NA, badge, fmt_num, fmt_pct, html, na_box, num, page_title, render_nav_footer, section_title,
                    show_chart)

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
Z80 = 1.2816
HORIZON = 10


def _kpi(t, v, s, c="#0F172A", grey=False):
    c = "#94A3B8" if grey else c
    return (f'<div style="{CARD}height:100%;{"background:#F1F5F9;" if grey else ""}"><div style="font-size:13px;font-weight:700;color:#64748B;">{t}</div>'
            f'<div style="font-size:22px;font-weight:800;color:{c};margin-top:4px;">{v}</div>'
            f'<div style="font-size:12.5px;color:#64748B;margin-top:2px;line-height:1.5;">{s}</div></div>')


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
    k = st.columns(5)
    with k[0]:
        html(_kpi("ราคาล่าสุด", f"{ctx.current_price:.2f}", f"บาท · {info.get('latest_date', '-')}"))
    with k[1]:
        html(_kpi("สถานะโมเดล", "ผ่านด่าน" if edge else "ไม่ผ่านด่าน (NO EDGE)",
                  "ชนะการเดาแบบง่ายบนข้อมูลปี 2025" if edge else "ไม่ชนะการเดาแบบง่าย จึงไม่ใช้ผลทำนาย",
                  L.GREEN if edge else L.RED))
    with k[2]:
        html(_kpi("ทิศทาง 10 วัน", ("ขาขึ้น" if (prob or 0) >= 50 else "ขาลง") if edge else NA,
                  "โอกาสขึ้น ≥ 50% = ขาขึ้น" if edge else hidden, L.GREEN if (prob or 0) >= 50 else L.RED, grey=not edge))
    with k[3]:
        html(_kpi("โอกาสขึ้น", fmt_pct(prob) if edge else NA, "ความน่าจะเป็นจากโมเดล" if edge else hidden, lab["color"], grey=not edge))
    with k[4]:
        html(_kpi("AI Score", fmt_num(info.get("ai_score"), 1) if edge else NA,
                  (f"{lab['th']} · ≥ 65 เอียงขึ้น · 35-64.9 ก้ำกึ่ง · &lt; 35 เอียงลง · ไม่นับในคะแนนรวม" if edge else hidden + " · ไม่นับในคะแนนรวม"),
                  lab["color"], grey=not edge))

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
    html(f"""<div style="{CARD}margin-top:14px;">{section_title('ผลสอบของโมเดล', 'ทดสอบกับข้อมูลที่โมเดลไม่เคยเห็น')}
        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;">
          <div><div style="font-size:12.5px;color:#64748B;">ความแม่นยำ (ปี 2025)</div><div style="font-size:20px;font-weight:800;">{fmt_pct(acc)}</div></div>
          <div><div style="font-size:12.5px;color:#64748B;">การเดาแบบง่าย (Baseline)</div><div style="font-size:20px;font-weight:800;">{fmt_pct(base)}</div>
               <div style="font-size:11.5px;color:#94A3B8;">เดาคำตอบที่พบบ่อยที่สุดของปี 2025 ทุกวัน</div></div>
          <div><div style="font-size:12.5px;color:#64748B;">ROC-AUC</div><div style="font-size:20px;font-weight:800;">{fmt_num(auc, 3)}</div>
               <div style="font-size:11.5px;color:#94A3B8;">0.5 = เท่าการโยนเหรียญ</div></div>
          <div><div style="font-size:12.5px;color:#64748B;">วันฝึก / วันทดสอบ</div><div style="font-size:20px;font-weight:800;">{int(num(info.get('n_train')) or 0):,} / {int(num(info.get('n_test')) or 0):,}</div>
               <div style="font-size:11.5px;color:#94A3B8;">ฝึก {info.get('train_start') or '-'} ถึง {info.get('train_end') or '-'} · ตัดรอยต่อ {int(num(info.get('n_purged')) or 0)} วัน</div></div>
          <div><div style="font-size:12.5px;color:#64748B;">เงื่อนไขผ่านด่าน</div>
               <div style="font-size:13.5px;line-height:1.8;">แม่นยำ &gt; Baseline: {mark(c1_ok)}<br>ROC-AUC &gt; 0.5: {mark(c2_ok)}</div></div>
        </div>
        <div style="font-size:14.5px;color:#334155;margin-top:10px;border-top:1px solid #F1F5F9;padding-top:8px;">{sent}</div>
        <div style="font-size:12px;color:#94A3B8;margin-top:4px;">ทดสอบตั้งแต่ {info.get('test_start') or '2025-01-01'} ถึง {info.get('test_end') or '-'}
        · ตัดแถวฝึกที่คำตอบ (ราคาอีก 10 วัน) ล้ำเข้าช่วงทดสอบ เพื่อไม่ให้โมเดลแอบเห็นคำตอบ (Purging, López de Prado 2018)</div></div>""")

    # ---------------- A4: กล่องผลทำนาย ----------------
    fi = ctx.feat_imp_df
    fi = fi[fi["ticker"] == ctx.selected_ticker].sort_values("importance", ascending=False) if not fi.empty else fi
    top3 = [FEATURE_TH.get(f, f) for f in fi["feature"].head(3)] if not fi.empty else []
    if edge and prob is not None:
        html(f"""<div style="{CARD}margin-top:14px;">{section_title('ผลทำนาย')}
            <div style="display:flex;height:22px;border-radius:8px;overflow:hidden;font-size:12.5px;font-weight:700;color:#fff;">
              <div style="width:{prob}%;background:{L.GREEN};padding-left:8px;line-height:22px;">ขึ้น {prob:.1f}%</div>
              <div style="width:{100 - prob}%;background:{L.RED};text-align:right;padding-right:8px;line-height:22px;">ลง {100 - prob:.1f}%</div></div>
            <div style="font-size:15px;color:#334155;margin-top:10px;line-height:1.7;">โมเดลประเมินว่า {ctx.selected_ticker} มีโอกาสขึ้น
            <b style="color:{lab['color']};">{prob:.1f}%</b> ใน 10 วันทำการ ({lab['th']}) โดยดูจาก {', '.join(top3) or '-'} มากที่สุด</div></div>""")
    else:
        html(f'<div style="margin-top:14px;">{na_box("โมเดลทำนายหุ้นนี้ไม่ได้ดีกว่าการเดา จึงไม่แสดงผลทำนาย")}</div>')

    # ---------------- A5: Forecast ----------------
    d = ctx.stock_daily.tail(150)
    last_date, price = d["date"].iloc[-1], float(d["close"].iloc[-1])
    vol = num(info.get("volatility"))
    c1, c2 = st.columns([1.5, 1])
    with c1:
        html(section_title("FORECAST 10 วันทำการ", "แถบ = ช่วงราคาราว 80% ของกรณี (บานทั้งขึ้นและลงเสมอ) · ทิศทางดูจากเส้นกลาง"))
        if vol is None:
            html("ไม่มีข้อมูลความผันผวน")
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
            fig.add_trace(go.Scatter(x=d["date"], y=d["close"], name="ราคาจริง", mode="lines", line=dict(color="#0F172A", width=1.6)))
            fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[price] + up + ([price] + dn)[::-1], fill="toself",
                                     fillcolor="rgba(168,85,247,0.15)", line=dict(width=0), name="ช่วงราคา 80%", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=xs, y=[price] + mid, name="เส้นกลาง" if edge else "ไม่มีมุมมองทิศทาง", mode="lines",
                                     line=dict(color="#A855F7", width=2, dash="dash")))
            if edge and prob is not None:
                fig.add_annotation(x=xs[-1], y=mid[-1], text=f"โอกาสขึ้น {prob:.0f}%", showarrow=True, arrowhead=2,
                                   font=dict(size=12, color=lab["color"]), ax=-40, ay=-30)
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                              xaxis=dict(title="วันที่"), yaxis=dict(title="ราคา (บาท)", gridcolor="#F1F5F9"),
                              legend=dict(orientation="h", y=1.08), hovermode="x unified")
            show_chart(fig, key="ai_forecast")
    # ---------------- A6 + A7 ----------------
    with c2:
        sub = "จากโมเดลที่ยังทำนายไม่ดีกว่าการเดา ไม่ควรตีความมาก" if not edge else "ตัวชี้วัดที่โมเดลใช้แยกวันขึ้น/ลงบ่อยที่สุด"
        html(section_title("ความสำคัญของตัวชี้วัด", sub))
        if fi.empty:
            html("ไม่มีข้อมูล")
        else:
            f2 = fi.sort_values("importance")
            fig2 = go.Figure(go.Bar(x=f2["importance"], y=[FEATURE_TH.get(f, f) for f in f2["feature"]], orientation="h",
                                    marker_color="#A855F7" if edge else "#CBD5E1",
                                    hovertemplate="%{y}<br>ความสำคัญ %{x:.3f}<extra></extra>"))
            fig2.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                               xaxis=dict(title="ความสำคัญ (Mean Decrease in Impurity)", gridcolor="#F1F5F9"),
                               yaxis=dict(tickfont=dict(size=11)))
            show_chart(fig2, key="ai_feature_importance")
    if top3:
        items = "".join(f"<li><b>{FEATURE_TH.get(f, f)}</b> <span style='color:#94A3B8;'>({f})</span></li>" for f in fi["feature"].head(3))
        html(f"""<div style="{CARD}margin-top:10px;">{section_title('สรุป Explainable AI')}
            <div style="font-size:14.5px;color:#334155;">ตัวชี้วัด 3 อันดับแรกที่โมเดลใช้ตัดสิน:</div>
            <ol style="margin:6px 0 0 20px;font-size:14.5px;line-height:1.8;color:#334155;">{items}</ol>
            <div style="font-size:12.5px;color:#64748B;">ความสำคัญบอกว่าโมเดล “ใช้อะไร” ตัดสิน ไม่ได้บอกว่าค่าสูงทำให้ขึ้นหรือลง
            {'· โมเดลนี้สอบไม่ผ่าน จึงไม่ควรตีความมาก' if not edge else ''}</div></div>""")

    render_nav_footer(ctx, PAGE)
