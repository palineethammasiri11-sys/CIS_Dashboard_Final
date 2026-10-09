"""
pages_content/entry_timing.py — หน้า 6 Entry Timing
----------------------------------------------------
Blueprint ฉบับที่ 2 หัวข้อ 6.6 (T1-T9)
- คะแนนและเกณฑ์ 6 ข้ออ่านจากหลังบ้าน (calculate_modules/entry_timing.py) ไม่คำนวณซ้ำบนจอ
- กราฟ: แท่งเทียน + EMA20 + EMA50 + MA200 + เส้นแนวต้าน/แนวรับ 60 วัน + Stop Loss (ราคา − 2 × ATR14)
  ช่อง Volume และช่อง MACD (MACD, Signal, Histogram, เส้น 0) — D10, D11
- ตัวเลือกช่วงเวลาเป็นภาษาไทย มีผลเฉพาะกราฟ (T4)
- ตัดออก: Risk/Reward, Pivot, โซนเข้าซื้อ/เฝ้าดู, Target 1-2, Stop Loss ต่ำสุด 30 วัน

[v17.4] - "สรุปสั้น" ใช้กติกาเดียวกับ "ความพร้อม" (หลังบ้าน summary_short) — เดิม ADVANC ขึ้น "พร้อม" คู่กับ "รอการยืนยัน"
        - จัดหน้า: KPI 4 ช่อง → [คะแนน+เกณฑ์ 6 ข้อ | กราฟ] สูงเท่ากัน → [ระดับราคาอ้างอิง | วิธีให้คะแนน]
                   → เหตุผล 3 ข้อ → สรุป (กราฟกว้างขึ้น อ่านง่ายขึ้น และไม่มีคอลัมน์แคบที่ข้อความตกบรรทัดยาว)
        - กราฟ: ชื่อช่องย่อยย้ายไปเป็นชื่อแกน (เดิมทับกับ legend), ป้ายเส้นระดับราคาไม่ล้นขอบ
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from calculate_modules import labels as L
from calculate_modules.entry_timing import CRITERIA, DEFAULT_CONFIG as CFG
from common import (CARD, INK, MUTED, FAINT, LINE, NA, TOOLS_H, badge, card, centered_card, fmt_num, fmt_pct, grid, html, json_list,
                    kpi, na_box, num, page_title, render_nav_footer, ring, section_title, show_chart, style_fig)

PAGE = " Entry Timing"
PTS = {"trend": CFG.trend_weight / CFG.trend_criteria_count, "momentum": CFG.momentum_weight / CFG.momentum_criteria_count}
CHART_H = 540
RADIO_H = 26
ROW_H = RADIO_H + 12 + CHART_H + TOOLS_H      # ความสูงรวมของคอลัมน์กลาง → ใช้ตั้งความสูงคอลัมน์ซ้าย/ขวาให้เท่ากัน


def _state(info, k):
    if not num(info.get(f"{k}_available")):
        return "--", FAINT
    return ("✓", L.GREEN) if num(info.get(f"{k}_ok")) else ("✕", L.RED)


def render(ctx):
    info = ctx.stock_info
    page_title("ENTRY TIMING", "ตอนนี้กราฟราคาเอื้อให้เข้าซื้อหรือยัง ด้วยเกณฑ์ 6 ข้อที่ตรวจได้จากกราฟ และระดับราคาอ้างอิงที่อธิบายได้ทุกเส้น")

    score = num(info.get("timing_score"))
    if score is None or not num(info.get("is_evaluated")):      # T9
        missing = json_list(info.get("missing_fields"))
        html(na_box(f"<b>ข้อมูลไม่เพียงพอสำหรับประเมินจังหวะ</b><br>เหตุผล: {info.get('data_status_reason') or '-'}"
                    + (f"<br>ข้อมูลที่ขาด: {', '.join(missing)}" if missing else "")))
        render_nav_footer(ctx, PAGE)
        return

    veto = bool(num(info.get("trend_veto_applied")))
    lab = L.timing_label(score, veto)
    ready = info.get("readiness") == "READY"
    passed = int(info.get("criteria_passed") or 0)
    advice = {"green": "แนวโน้มและแรงส่งสนับสนุนการซื้อ", "yellow": "แกว่งตัว รอสัญญาณยืนยัน",
              "red": "เทรนด์หลักเป็นขาลง หลีกเลี่ยงการซื้อสวนแนวโน้ม" if veto else "แนวโน้มและแรงส่งอ่อน ควรหลีกเลี่ยง"}[lab["key"]]
    summary = info.get("summary_short") or "-"

    # ---------------- T2: KPI 4 ช่อง ----------------
    html(grid([
        kpi("ความพร้อม", "พร้อม" if ready else "รอ", "พร้อม = คะแนน ≥ 70 และราคาไม่ต่ำกว่า MA200", L.GREEN if ready else L.YELLOW),
        kpi("สัญญาณ", lab["en"], advice, lab["color"]),
        kpi("เกณฑ์ที่ผ่าน", f"{passed} จาก 6", "นับข้อที่ผ่าน (ไม่ใช่ความมั่นใจทางสถิติ)"),
        kpi("สรุปสั้น", summary, "ใช้กติกาเดียวกับความพร้อมและสัญญาณ · ข้อที่ยังไม่ผ่าน = สิ่งที่ต้องรอ", lab["color"], size=15.5),
    ], template="minmax(0,0.8fr) minmax(0,1fr) minmax(0,0.8fr) minmax(0,1.6fr)").replace('class="cis-grid"', 'class="cis-grid wrap-md"'))

    left, center = st.columns([1, 2.75])

    # ---------------- T3: มาตรคะแนน + เกณฑ์ 6 ข้อ ----------------
    with left:
        rows, last_group = "", None
        for key, name, group in CRITERIA:
            if group != last_group:
                gname = "แนวโน้ม (60 แต้ม)" if group == "trend" else "แรงส่ง (40 แต้ม)"
                rows += f'<div style="font-size:11.5px;font-weight:700;color:{FAINT};margin-top:8px;">{gname}</div>'
                last_group = group
            icon, colr = _state(info, key)
            got = PTS[group] if icon == "✓" else 0
            short, why = (name.split(" (") + [""])[:2]
            rows += (f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;padding:4px 0;'
                     f'border-bottom:1px solid #F1F5F9;font-size:13px;" title="{why.rstrip(")")}">'
                     f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"><b style="color:{colr};">{icon}</b> {short}</span>'
                     f'<b style="color:{colr};">{got:.1f}</b></div>')
        veto_html = (f'<div style="font-size:12px;color:{L.RED};margin-top:6px;line-height:1.5;">Trend Veto: ราคาต่ำกว่า MA200 → BEARISH เสมอ '
                     f'(แม้คะแนนรวมเป็น {score:.0f})</div>' if veto else "")
        html(centered_card(section_title('TIMING SCORE', 'เกณฑ์ 6 ข้อ'), f"""
            <div style="text-align:center;">{ring(score, lab['color'], size=104)}<div style="margin-top:8px;">{badge(lab, 12.5)}</div>
            <div style="font-size:12px;color:{MUTED};margin:6px 0;">แนวโน้ม {fmt_num(info.get('trend_score'), 1)}/60 · แรงส่ง {fmt_num(info.get('mom_score'), 1)}/40</div></div>
            {rows}{veto_html}
            <div style="font-size:11.5px;color:{FAINT};margin-top:6px;">-- = ไม่มีข้อมูล (ได้ 0 และไม่ลดตัวหาร)</div>""",
                  f"min-height:{ROW_H}px;"))

    # ---------------- T4 + T5: กราฟ ----------------
    with center:
        px = ctx.stock_daily.copy()
        px["MA200"] = pd.to_numeric(px["close"], errors="coerce").rolling(CFG.ma_long_period).mean()
        y0, y1 = px["date"].min().year, px["date"].max().year
        options = {"1 เดือน": 22, "3 เดือน": 66, "6 เดือน": 132, "1 ปี": 252, "2 ปี": 504, f"ทั้งหมด ({y0}-{y1})": len(px)}
        tf = st.radio("ช่วงเวลาของกราฟ", list(options), index=2, horizontal=True, key="timing_tf_th",
                      label_visibility="collapsed",
                      help="1 เดือน ≈ 22 วันทำการ · 3 เดือน ≈ 66 · 6 เดือน ≈ 132 · 1 ปี ≈ 252 · 2 ปี ≈ 504 · ทั้งหมด = ทุกวันในไฟล์")
        d = px.tail(min(options[tf], len(px)))
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.6, 0.15, 0.25])
        fig.add_trace(go.Candlestick(x=d["date"], open=d["open"], high=d["high"], low=d["low"], close=d["close"], name="ราคา",
                                     increasing_line_color=L.GREEN, decreasing_line_color=L.RED), row=1, col=1)
        for col, name, colr in [("EMA20", "EMA20", "#F59E0B"), ("EMA50", "EMA50", "#3B82F6"),
                                ("MA200", "MA200", "#8B5CF6")]:
            fig.add_trace(go.Scatter(x=d["date"], y=d[col], name=name, mode="lines", line=dict(color=colr, width=1.4)), row=1, col=1)
        for key, name, colr, dash in [("resistance_60d", "แนวต้าน", "#64748B", "dash"),
                                      ("support_60d", "แนวรับ", L.GREEN, "dash"),
                                      ("stop_loss", "Stop Loss", L.RED, "dot")]:
            v = num(info.get(key))
            if v is not None:
                fig.add_hline(y=v, line_dash=dash, line_color=colr, line_width=1.4, row=1, col=1,
                              annotation_text=f"{name} {v:,.2f}", annotation_position="right",
                              annotation_font=dict(size=11, color=colr))
        vcol = [L.GREEN if c >= o else L.RED for c, o in zip(d["close"], d["open"])]
        fig.add_trace(go.Bar(x=d["date"], y=d["volume"], marker_color=vcol, name="Volume", showlegend=False), row=2, col=1)
        if "macd_hist" in d.columns:
            hcol = [L.GREEN if (h or 0) >= 0 else L.RED for h in d["macd_hist"]]
            fig.add_trace(go.Bar(x=d["date"], y=d["macd_hist"], marker_color=hcol, name="Histogram", showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=d["date"], y=d["MACD"], name="MACD", mode="lines", line=dict(color=INK, width=1.3)), row=3, col=1)
        if "macd_signal" in d.columns:
            fig.add_trace(go.Scatter(x=d["date"], y=d["macd_signal"], name="Signal", mode="lines",
                                     line=dict(color="#F97316", width=1.2)), row=3, col=1)
        fig.add_hline(y=0, line_color="#94A3B8", line_width=1, row=3, col=1)
        style_fig(fig, height=CHART_H, legend=True, title="ราคา · Volume · MACD",
                  sub="ช่วงเวลามีผลเฉพาะกราฟ คะแนนคิดจากข้อมูลล่าสุดเสมอ", margin=dict(r=118))
        fig.update_layout(hovermode="x unified", xaxis_rangeslider_visible=False)
        fig.update_yaxes(title_text="ราคา (บาท)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        show_chart(fig, key="timing_main", expand_height=820)

    # ---------------- T6 + T7: ระดับราคาอ้างอิง | วิธีให้คะแนน ----------------
    price = ctx.current_price

    def lvl(name, key, pct_key, colr):
        v = num(info.get(key))
        return (f'<div style="display:flex;justify-content:space-between;gap:6px;padding:5px 0;border-bottom:1px solid #F1F5F9;font-size:13.5px;">'
                f'<span style="color:{colr};">{name}</span><b style="color:{colr};white-space:nowrap;">{fmt_num(v, 2)} '
                f'<span style="font-weight:400;font-size:12px;">({fmt_pct(info.get(pct_key), 1, sign=True)})</span></b></div>')
    at_res = (f'<div style="font-size:12px;color:{L.YELLOW};margin-top:6px;">ราคาอยู่ที่แนวต้านพอดี (จุดสูงสุด 60 วัน)</div>'
              if num(info.get("at_resistance")) else "")
    levels = card(f"""{section_title('ระดับราคาอ้างอิง', '% = ระยะจากราคาปัจจุบัน')}
        <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #F1F5F9;font-size:13.5px;">
          <span>ราคาปัจจุบัน</span><b>{price:,.2f}</b></div>
        {lvl('แนวต้าน 60 วัน', 'resistance_60d', 'resistance_pct', '#475569')}
        {lvl('แนวรับ 60 วัน', 'support_60d', 'support_pct', L.GREEN)}
        {lvl('Stop Loss', 'stop_loss', 'stop_loss_pct', L.RED)}
        <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:13.5px;"><span>ATR14</span><b>{fmt_num(info.get('atr14'), 3)}</b></div>
        {at_res}
        <div style="font-size:11.5px;color:{FAINT};margin-top:6px;line-height:1.5;">แนวต้าน = High สูงสุด 60 วันทำการ · แนวรับ = Low ต่ำสุด 60 วัน
        · ATR14 = ค่าเฉลี่ยแบบ Wilder ของ True Range 14 วัน · Stop Loss = ราคา − 2 × ATR14 (ตัวคูณ 2 ผู้ออกแบบกำหนด)</div>""")
    method = card(f"""{section_title('ⓘ วิธีให้คะแนน')}
        <div style="font-size:13px;color:#334155;line-height:1.75;">
        <b>แนวโน้ม 60 แต้ม</b> (ข้อละ 20): ราคา &gt; EMA20 · EMA20 &gt; EMA50 · ราคา &gt; MA200<br>
        <b>แรงส่ง 40 แต้ม</b> (ข้อละ 13.3): MACD &gt; 0 · ADX ≥ 25 (Wilder) · Volume ≥ ค่าเฉลี่ย 20 วันก่อนหน้า<br>
        รวมแล้วปัดเป็นจำนวนเต็ม · ≥ 70 STRONG BUY · 40-69 NEUTRAL · &lt; 40 BEARISH<br>
        <b>Trend Veto:</b> ราคาต่ำกว่า MA200 → BEARISH เสมอ<br>
        <b>ความพร้อม:</b> พร้อม = คะแนน ≥ 70 และราคาไม่ต่ำกว่า MA200 · สรุปสั้นใช้กติกาเดียวกัน</div>
        <div style="font-size:11.5px;color:{FAINT};margin-top:6px;">น้ำหนัก 60/40 และเส้น 70/40 ทีมกำหนด (มีผลทดสอบความไวและ backtest ใน scripts/)</div>""")
    html(grid([levels, method], template="minmax(0,1fr) minmax(0,1fr)"))

    # ---------------- T8: เหตุผล 3 ข้อ ----------------
    names = {k: n.split(" (")[0] for k, n, _ in CRITERIA}

    def group_card(title, keys, desc_ok, desc_bad):
        states = [(k, _state(info, k)[0]) for k in keys]
        avail = [s for _, s in states if s != "--"]
        fails = [names[k] for k, s in states if s == "✕"]
        if not avail:
            icon, colr, txt = "--", FAINT, "ไม่มีข้อมูล"
        elif all(s == "✓" for s in avail) and len(avail) == len(keys):
            icon, colr, txt = "✓", L.GREEN, desc_ok
        elif any(s == "✓" for s in avail):
            icon, colr, txt = "◐", L.YELLOW, "ผ่านบางส่วน — ยังไม่ผ่าน: " + ", ".join(fails)
        else:
            icon, colr, txt = "✕", L.RED, desc_bad + " (" + ", ".join(fails) + ")"
        return card(f'<div style="font-size:14.5px;font-weight:800;color:{INK};">'
                    f'<span style="color:{colr};font-size:17px;">{icon}</span> {title}</div>'
                    f'<div style="font-size:13px;color:#475569;margin-top:4px;line-height:1.6;">{txt}</div>')
    cards = [
        group_card("แนวโน้ม", ["k15", "k16", "k17"], "ราคาอยู่เหนือ EMA20 > EMA50 และเหนือ MA200 = ขาขึ้นทุกระยะ",
                   "ยังไม่ผ่านเกณฑ์แนวโน้ม"),
        group_card("แรงส่ง", ["k18", "k19"], "MACD เหนือ 0 และ ADX ≥ 25 = มีแรงส่งและแนวโน้มแข็งแรง", "แรงส่งยังอ่อน"),
        group_card("วอลุ่ม", ["k20"], f"วอลุ่มวันล่าสุดเป็น {fmt_num(info.get('volume_ratio'), 2)} เท่าของค่าเฉลี่ย 20 วัน",
                   f"วอลุ่มยังไม่ยืนยัน ({fmt_num(info.get('volume_ratio'), 2)} เท่าของค่าเฉลี่ย)"),
    ]
    concl = card(f'<div style="font-size:14px;color:#334155;line-height:1.6;">สรุป: <b style="color:{lab["color"]};">{lab["en"]}</b> — '
                 f'{advice} · ผ่าน {passed} จาก 6 เกณฑ์ · {summary}</div>', "padding:10px 16px;")
    html(grid(cards, cols=3).replace('class="cis-grid"', 'class="cis-grid wrap-md"'))
    html(concl)

    render_nav_footer(ctx, PAGE)
