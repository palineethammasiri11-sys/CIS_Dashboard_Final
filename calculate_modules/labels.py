"""
calculate_modules/labels.py
---------------------------
ตารางป้ายและสีชุดเดียวของทั้งระบบ (Blueprint ฉบับที่ 2 หัวข้อ 5.4 ก, ข้อ D5)

ทุกหน้าและทุกการคำนวณที่ต้องแปลงคะแนนเป็นป้าย/สี ต้องเรียกฟังก์ชันในไฟล์นี้เท่านั้น
ห้ามเขียนเกณฑ์ซ้ำในหน้าใดหน้าหนึ่ง (เดิมแต่ละหน้าตั้งเกณฑ์เอง ทำให้หุ้นตัวเดียวได้ป้ายต่างกันในแต่ละหน้า)

ไฟล์นี้ไม่ import streamlit จึงใช้ได้ทั้งฝั่งคำนวณ (calculate_modules) และฝั่งหน้าจอ (pages_content)

ทุกฟังก์ชันคืน dict เดียวกัน: {'key', 'th', 'en', 'color', 'bg'}
    key   : รหัสสั้นสำหรับเทียบในโค้ด เช่น 'green' / 'yellow' / 'red' / 'grey'
    th    : ป้ายภาษาไทย
    en    : ป้ายภาษาอังกฤษ
    color : สีตัวอักษร/เส้น (hex)
    bg    : สีพื้นอ่อนสำหรับกล่อง/ป้าย (hex + alpha)

ที่มาของเกณฑ์: เส้น 50/65/75 ของคำแนะนำเป็นของเดิมที่ทีมกำหนด; Health และ Risk ใช้เส้นเดียวกับคำแนะนำ;
AI ใช้เส้นสมมาตรรอบ 50%; Entry Timing ใช้ 70/40 เดิม; Fair Value ใช้ Margin of Safety ±10% เดิม
ทุกเส้นเป็นการตัดสินใจของทีม ไม่มีแหล่งอ้างอิงภายนอก (ต้องเขียนไว้ในเล่ม)
"""

import math

GREEN = "#10B981"
YELLOW = "#F59E0B"
RED = "#EF4444"
GREY = "#94A3B8"

_BG = {GREEN: "rgba(16,185,129,0.10)", YELLOW: "rgba(245,158,11,0.10)",
       RED: "rgba(239,68,68,0.10)", GREY: "rgba(148,163,184,0.14)"}

# เกณฑ์ (แก้ที่นี่ที่เดียว)
OVERALL_STRONG_BUY = 75.0
OVERALL_BUY = 65.0
OVERALL_ACCUMULATE = 50.0
HEALTH_GOOD, HEALTH_MID = 65.0, 50.0
RISK_GOOD, RISK_MID = 65.0, 50.0
FV_BAND = 10.0                      # Margin of Safety ±10%
TIMING_BULL, TIMING_NEUTRAL = 70.0, 40.0
AI_UP, AI_DOWN = 65.0, 35.0         # โอกาสขึ้น (%)


def is_missing(v):
    """True ถ้าไม่มีค่า (None / NaN / สตริงว่าง)"""
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return str(v).strip() in ("", "nan", "None")


def _lab(key, th, en, color):
    return {"key": key, "th": th, "en": en, "color": color, "bg": _BG[color]}


def no_data(th="ข้อมูลไม่พอ", en="N/A"):
    return _lab("grey", th, en, GREY)


def overall_label(score):
    """คะแนนรวม → คำแนะนำ"""
    if is_missing(score):
        return no_data()
    s = float(score)
    if s >= OVERALL_STRONG_BUY:
        return _lab("green", "ซื้อแรง", "STRONG BUY", GREEN)
    if s >= OVERALL_BUY:
        return _lab("green", "ซื้อ", "BUY", GREEN)
    if s >= OVERALL_ACCUMULATE:
        return _lab("yellow", "ทยอยซื้อ", "ACCUMULATE", YELLOW)
    return _lab("red", "ลดสัดส่วน / ขาย", "REDUCE / SELL", RED)


def recommendation_code(score):
    """ค่าที่เก็บในคอลัมน์ recommendation (ใช้ชื่อเดิมของระบบ)"""
    if is_missing(score):
        return "ข้อมูลไม่พอ"
    return overall_label(score)["en"]


def health_label(score):
    if is_missing(score):
        return no_data()
    s = float(score)
    if s >= HEALTH_GOOD:
        return _lab("green", "แข็งแรง", "STRONG", GREEN)
    if s >= HEALTH_MID:
        return _lab("yellow", "ปานกลาง", "MODERATE", YELLOW)
    return _lab("red", "อ่อนแอ", "WEAK", RED)


def risk_label(score):
    """Risk Score ยิ่งสูงยิ่งปลอดภัย"""
    if is_missing(score):
        return no_data()
    s = float(score)
    if s >= RISK_GOOD:
        return _lab("green", "เสี่ยงต่ำ", "LOW RISK", GREEN)
    if s >= RISK_MID:
        return _lab("yellow", "เสี่ยงปานกลาง", "MODERATE RISK", YELLOW)
    return _lab("red", "เสี่ยงสูง", "HIGH RISK", RED)


def fair_value_label(mos):
    """Margin of Safety (%) → สถานะราคาเทียบมูลค่า"""
    if is_missing(mos):
        return no_data("ประเมินไม่ได้", "NOT RATED")
    m = float(mos)
    if m > FV_BAND:
        return _lab("green", "ต่ำกว่ามูลค่า", "UNDERVALUED", GREEN)
    if m >= -FV_BAND:
        return _lab("yellow", "ใกล้เคียงมูลค่า", "FAIR VALUE", YELLOW)
    return _lab("red", "สูงกว่ามูลค่า", "OVERVALUED", RED)


def timing_label(score, trend_veto=False):
    """Entry Timing: ราคา < MA200 (Trend Veto) → BEARISH เสมอ"""
    if is_missing(score):
        return no_data()
    if trend_veto and not is_missing(trend_veto) and bool(int(float(trend_veto))):
        return _lab("red", "ขาลง (ราคาต่ำกว่า MA200)", "BEARISH", RED)
    s = float(score)
    if s >= TIMING_BULL:
        return _lab("green", "จังหวะซื้อ", "STRONG BUY", GREEN)
    if s >= TIMING_NEUTRAL:
        return _lab("yellow", "รอสัญญาณ", "NEUTRAL", YELLOW)
    return _lab("red", "ขาลง", "BEARISH", RED)


def ai_label(prob_up, has_edge):
    """AI: ถ้าโมเดลไม่ผ่านด่าน (ไม่ชนะการเดา) → NO EDGE สีเทา ไม่ว่าโอกาสจะเป็นเท่าไร"""
    edge = (not is_missing(has_edge)) and bool(int(float(has_edge)))
    if not edge:
        return no_data("โมเดลสอบไม่ผ่าน", "NO EDGE")
    if is_missing(prob_up):
        return no_data()
    p = float(prob_up)
    if p >= AI_UP:
        return _lab("green", "เอียงขึ้น", "LEAN UP", GREEN)
    if p >= AI_DOWN:
        return _lab("yellow", "ก้ำกึ่ง", "UNCLEAR", YELLOW)
    return _lab("red", "เอียงลง", "LEAN DOWN", RED)


def score_color(score, good=65.0, mid=50.0):
    """สีของคะแนน 0-100 ทั่วไป (เส้นเดียวกับ Health / Risk)"""
    if is_missing(score):
        return GREY
    s = float(score)
    return GREEN if s >= good else (YELLOW if s >= mid else RED)


# ตารางสรุปสำหรับแสดงในหน้าจอ/เล่ม (ใช้ในคำอธิบาย ⓘ)
LEGEND_ROWS = [
    ("คะแนนรวม → คำแนะนำ", "≥ 75 ซื้อแรง / 65-74.9 ซื้อ", "50-64.9 ทยอยซื้อ", "< 50 ลดสัดส่วน / ขาย"),
    ("Company Health", "≥ 65 แข็งแรง", "50-64.9 ปานกลาง", "< 50 อ่อนแอ"),
    ("Fair Value (Margin of Safety)", "> +10% ต่ำกว่ามูลค่า", "−10% ถึง +10% ใกล้เคียงมูลค่า", "< −10% สูงกว่ามูลค่า"),
    ("Risk", "≥ 65 เสี่ยงต่ำ", "50-64.9 เสี่ยงปานกลาง", "< 50 เสี่ยงสูง"),
    ("Entry Timing", "≥ 70 STRONG BUY", "40-69 NEUTRAL", "< 40 หรือราคา < MA200 = BEARISH"),
    ("AI (โอกาสขึ้น)", "≥ 65% เอียงขึ้น", "35-64.9% ก้ำกึ่ง", "< 35% เอียงลง (ไม่ผ่านด่าน = NO EDGE)"),
]
