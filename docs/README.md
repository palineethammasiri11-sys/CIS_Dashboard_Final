# CIS — Comprehensive Investment System

Dashboard วิเคราะห์หุ้นกลุ่มเทคโนโลยีใน SET100 (8 หุ้น: ADVANC, CCET, DELTA, HANA, JMART, KCE, THCOM, TRUE)
เพื่อสนับสนุนการตัดสินใจลงทุน สร้างด้วย Streamlit — ข้อมูลทั้งหมดในหน้าจอคำนวณจากไฟล์ Dataset จริง **ไม่มีค่าจำลอง/สุ่มหลงเหลืออยู่**

> **v17.4 (10 ต.ค. 2569):** แก้ข้อความสรุปของ Entry Timing ให้ตรงกับ "ความพร้อม" + ปรับ UX/UI ทั้งแอป
> (เลื่อนขึ้นบนสุดเมื่อเปลี่ยนหน้า, กระชับขึ้น, การ์ดสูงเท่ากัน, กราฟไม่ทับกัน) — ดู `docs/CHANGES_v17.md` หัวข้อ 5.5

## โครงสร้างไฟล์ (เวอร์ชันแยกโมดูล — พร้อมแบ่งงานทีม)

```
cis-dashboard-main/
├── .streamlit/config.toml       # ธีมสว่าง (base="light") — บังคับธีมเดียวกันทุกเครื่อง แม้เบราว์เซอร์ตั้งโหมดมืด
├── Dataset/                     # ไฟล์ CSV ต้นทางทั้ง 5 ไฟล์
├── import_data.py               # นำเข้า CSV -> SQLite (cis_database.db)
├── calculate_scores.py          # ★ Orchestrator — วนลูปหุ้น เรียกโมดูลคำนวณ บันทึกผลลง DB (ไม่มีสูตรอยู่ในนี้แล้ว)
├── calculate_modules/            # ★ สูตร/การคำนวณ 1 ไฟล์ต่อ 1 โมดูล — แบ่งงานทีมตรงนี้
│   ├── common.py                 #   clean_float(), SECTOR_MAP ใช้ร่วมกันทุกโมดูล
│   ├── labels.py                 #   ป้าย/สี/เกณฑ์ชุดเดียวทั้งระบบ
│   ├── company_health.py
│   ├── fair_value.py
│   ├── entry_timing.py
│   ├── ai_prediction.py
│   ├── risk_analysis.py
│   └── industry_benchmark.py     #   จัดอันดับ/รวมคะแนน (รอผลจาก 5 โมดูลอื่นก่อน)
├── common.py                     # ★ CSS/ธีมกลาง (Design tokens), helper functions, การโหลดข้อมูล, PageContext, sidebar/header (ฝั่ง UI)
├── chart_notes.py                # คำอธิบาย "ⓘ วิธีอ่านกราฟและเทคนิค" ของทุกกราฟ
├── app.py                        # ★ Entry point — แค่ประกอบร่าง + routing ไม่มี logic หน้าจอ
├── pages_content/                 # ★ 1 ไฟล์ต่อ 1 โมดูล (ฝั่ง UI) — แบ่งงานทีมตรงนี้
│   ├── overview.py
│   ├── company_health.py
│   ├── fair_value.py
│   ├── entry_timing.py
│   ├── ai_prediction.py
│   ├── risk_analysis.py
│   └── industry_benchmark.py
├── preview_my_page.py           # ★ ไฟล์ให้แต่ละคน preview หน้าตัวเองแบบเดี่ยว ไม่ต้องรอทีม
├── cis_database.db              # ฐานข้อมูลที่ประมวลผลไว้แล้ว (พร้อมใช้งานทันที)
├── scripts/                     # สคริปต์ทดสอบ/วิเคราะห์เพิ่มเติม (รันจากโฟลเดอร์หลัก)
├── docs/                        # เอกสารทีม (TEAM_ROLES, GIT_WORKFLOW, EDGE_CASES, CHANGES_v17 ฯลฯ)
├── run_tests.py                 # ★ รันตรวจสอบทั้งระบบด้วยคำสั่งเดียว (Data Contract + หน้าจอ + ปุ่ม + preview)
└── requirements.txt
```

**หมายเหตุ:** มี `common.py` สองไฟล์ที่ทำหน้าที่ต่างกัน — `common.py` (root) เป็นของฝั่ง UI/Streamlit
ส่วน `calculate_modules/common.py` เป็นของฝั่งสูตรคำนวณ ไม่ใช่ไฟล์เดียวกัน อย่าสับสน

## สำหรับทีม 11 คน — วิธีแบ่งงาน

**รายละเอียดบทบาทแบบเต็ม (ใครรับผิดชอบอะไร ต้องอ่าน/ส่งอะไรให้ใคร) ดูที่ `TEAM_ROLES.md` — เป็นไฟล์หลักที่ควรอ่านก่อนเริ่มงาน**

**โครงสร้างทีม (สรุปย่อ):**
| # | บทบาท | ไฟล์ที่รับผิดชอบ |
|---|---|---|
| 1-6 | เจ้าของโมดูล คนละ 1 โมดูล | `pages_content/<โมดูล>.py` **+** `calculate_modules/<โมดูล>.py` (2 ไฟล์คู่กัน) |
| 7 | Overview Owner | `pages_content/overview.py` |
| 8 | Formula/Number Auditor (กลุ่มการเงิน) | ตรวจ Company Health, Fair Value, Entry Timing |
| 9 | Formula/Number Auditor (กลุ่มควอนต์) | ตรวจ AI Prediction, Risk Analysis, Industry Benchmark |
| 10 | Layout/Design Lead | `common.py` (root — CSS กลาง) + ตรวจ Layout ทุกหน้า |
| 11 | Integration/QA Lead | `app.py`, `calculate_scores.py`, `import_data.py`, `run_tests.py`, deploy |

**สิ่งที่แต่ละคน (1-6) ต้องทำ 3 ชั้น:**
1. **เช็ค/ปรับสูตร** — แก้ที่ `calculate_modules/<โมดูลของตัวเอง>.py` เทียบกับ `DATA_FORMULA_AUDIT.md`
   ทุกไฟล์มี **Data Contract** เขียนไว้ที่หัวไฟล์ (input ต้องมีอะไร, output ต้อง return key อะไรบ้าง) — **ห้ามลบ/เปลี่ยนชื่อ key เดิม เพิ่มใหม่ได้อิสระ**
2. **เช็คตัวเลข** — รัน `python calculate_scores.py` แล้วดู print สรุปท้ายผล หรือคำนวณด้วยมือจาก `Dataset/*.csv` เทียบกับที่ Dashboard โชว์ อย่างน้อย 2-3 หุ้น
3. **จัด Layout** — แก้เฉพาะไฟล์ `pages_content/<โมดูลของตัวเอง>.py` โดยใช้ helper กลางใน `common.py`
   (`kpi()`, `card()`, `grid()`, `tile()`, `section_title()`, `style_fig()`, `show_chart()`) เพื่อให้ทุกหน้าหน้าตาเหมือนกัน

**งานของคนที่ 1-6 ต้องผ่านการตรวจ 2 ทางก่อน merge** — Formula Auditor (คนที่ 8 หรือ 9 แล้วแต่กลุ่ม) ตรวจสูตร/ตัวเลข
และ Layout Lead (คนที่ 10) ตรวจหน้าตา ทั้งสองต้อง Approve PR บน GitHub ก่อน คนที่ 11 ถึงจะ merge ได้
รายละเอียดขั้นตอน PR/ลำดับ merge ดู `GIT_WORKFLOW.md`, checklist ก่อนส่งงานแต่ละบทบาทดู `TEAM_ROLES.md`

**ก่อน merge ทุกครั้ง (Integration Lead รันคำสั่งเดียว):**
```bash
python run_tests.py
```
ตรวจครบ: Data Contract ของทุกโมดูล, หน้าจอ 56 ชุด, ปุ่มนำทาง, ปุ่มขยายกราฟ, `preview_my_page.py` ทุกโมดูล — ผ่านหมดถึง merge/deploy ได้

**วิธี preview หน้าตัวเองแบบเดี่ยว (ไม่ต้องรอทีม — สำหรับคนที่ 1-7):**
```bash
# 1. เปิด preview_my_page.py แก้บรรทัด MODULE_NAME ให้ตรงกับโมดูลตัวเอง เช่น
#    MODULE_NAME = "company_health"
# 2. รัน
streamlit run preview_my_page.py
# 3. ไล่เปลี่ยนหุ้นใน dropdown ให้ครบทั้ง 8 ตัว
```

**ถ้าแก้แค่ Layout (`pages_content/<โมดูล>.py`)** — save ไฟล์แล้ว refresh หน้าเว็บได้เลย เห็นผลทันที

**ถ้าแก้สูตร (`calculate_modules/<โมดูล>.py`)** — save ไฟล์แล้วต้อง **กดปุ่ม "🔄 คำนวณคะแนนใหม่จากสูตรล่าสุด"** ที่มุมขวาบนของหน้า `preview_my_page.py` ก่อนเสมอ เพราะตัวเลขที่เห็นมาจาก `cis_database.db` ที่คำนวณไว้ล่วงหน้า ไม่ได้คำนวณสดทุกครั้ง — กดปุ่มนี้จะรัน `calculate_scores.py` ใหม่ทั้งหมดด้วยสูตรล่าสุดของคุณ แล้วโหลดผลลัพธ์ใหม่ให้ทันที (มีบอกเวลาที่คำนวณล่าสุดกำกับไว้ใต้ปุ่ม เผื่อสงสัยว่าข้อมูลเก่าหรือใหม่)

**คนที่ 8/9 (Formula/Number Auditor)** ใช้ `preview_my_page.py` ตั้ง `MODULE_NAME` เป็นโมดูลที่กำลังตรวจได้เหมือนกัน
เพื่อดูตัวเลข/หน้าตาจริงประกอบการตรวจ ไม่ต้องแก้ไฟล์ใดๆ เอง (ยกเว้นเจอบั๊กแล้วอยากแก้เอง — ดู `GIT_WORKFLOW.md` ข้อ 1)

**กติกาสำคัญ:**
- ห้ามแก้ `st.session_state["nav_page"]` / `"pending_nav"` logic ใน `common.py` (root) โดยไม่ปรึกษาทีม (เคยเป็นบั๊ก sidebar ไม่ sync มาก่อน)
- ห้ามแก้ `calculate_modules/common.py` (SECTOR_MAP, clean_float) โดยไม่แจ้งทีม เพราะทุกโมดูลใช้ร่วมกัน
- Industry Benchmark (`calculate_modules/industry_benchmark.py`) **ต้องรอ 5 โมดูลอื่นคำนวณเสร็จก่อน** เพราะจัดอันดับจากผลรวมทุกหุ้น — คนที่ดูแลโมดูลนี้ควรเริ่มจาก Layout ก่อน แล้วรอของจริงตอนรวมทีม
- สีประจำหน้า (เมนูด้านซ้าย): Industry `#06B6D4` | Overview `#3B82F6` | Health `#10B981` | Fair Value `#F59E0B` | Risk `#EF4444` | Timing `#6366F1` | AI `#A855F7`

## วิธีรันในเครื่อง (Local)

```bash
pip install -r requirements.txt

# ไม่บังคับ: แอปสร้างฐานข้อมูล cis_database.db ให้เองตอนเปิดครั้งแรก
# (หรือเมื่อ CALC_VERSION ใน calculate_scores.py เปลี่ยน) ถ้าต้องการสั่งเอง:
python import_data.py
python calculate_scores.py

streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501`

สคริปต์ใน `scripts/` ต้องรันจาก folder หลัก เช่น `python scripts/rebuild_database.py`, `python scripts/sensitivity_analysis.py`

เทียบโมเดล AI: `python scripts/model_comparison.py` (ทดสอบปี 2025) และ `python scripts/walk_forward_models.py` (ทดสอบย้อนหลังรายปี 2016–2025 ประมาณ 1-2 นาที) ผลสรุปอยู่ใน `docs/AI_เทียบโมเดลและวิเคราะห์Error.md`

## วิธี Deploy บน Streamlit Community Cloud

1. อัปโหลดทั้งโฟลเดอร์นี้ขึ้น GitHub repository (รวมไฟล์ `cis_database.db` และโฟลเดอร์ `.streamlit/` เพื่อให้แอปพร้อมใช้ทันทีโดยไม่ต้องรัน pipeline ตอน deploy)
2. ไปที่ [share.streamlit.io](https://share.streamlit.io) → New app → เลือก repo นี้ → Main file path: `app.py`
3. กด Deploy (ถ้าแอปเดิมเปิดอยู่แล้ว กด Reboot app ใน Manage app หลัง push)

ถ้าต้องการให้ระบบประมวลผลข้อมูลใหม่ทุกครั้งที่ deploy แทนการแนบ `cis_database.db` ไปด้วย ให้เพิ่มคำสั่งใน `app.py` หรือใช้ GitHub Actions ให้รัน `import_data.py` และ `calculate_scores.py` ก่อน build — แต่โดยทั่วไปแนบไฟล์ `.db` ที่ประมวลผลไว้แล้วไปเลยจะเสถียรและเร็วกว่า

## หลักการคำนวณ (สรุป) — v17 ตาม Blueprint ฉบับที่ 2

| โมดูล | แหล่งข้อมูล | วิธีคำนวณ (ย่อ) |
|---|---|---|
| Company Health | `stock_financials` (ROE / ROA ค่าในไฟล์, D/E, Current Ratio) | ROE × 3.5 (30%) + ROA × 7 (25%) + Current Ratio × 45 (20%) + (2.5 − D/E) × 40 (25%) ตัดที่ 0-100, ต้องมี 3 ใน 4 |
| Fair Value | `stock_financials` + `valuation_params` (Damodaran ม.ค. 2024-2026 รายปี) | DCF (FCF เฉลี่ย 2 ปี, WACC รายอุตสาหกรรม, g 2%) 55% + EPS × Target P/E 45%; คะแนนแต่ละวิธี = 50 + Margin of Safety |
| Risk Analysis | ราคา 3 ปีล่าสุด + Beta เทียบ TDEX | 100 − ค่าเฉลี่ยถ่วงน้ำหนักของ CVaR × 10 (30%), Max DD × 1.5 + โทษฟื้นช้า (25%), Volatility × 1.3 (20%), Beta × 40 (15%), 100 − PSR (10%) |
| Entry Timing | `stock_daily_prices` | แนวโน้ม 60 (ราคา > EMA20, EMA20 > EMA50, ราคา > MA200) + แรงส่ง 40 (MACD > 0, ADX ≥ 25, Volume ≥ เฉลี่ย 20 วัน); ราคา < MA200 = BEARISH |
| AI Prediction | `stock_daily_prices` (11 ตัวชี้วัดแบบสัดส่วน) | Random Forest ฝึกก่อน 2025 ทดสอบปี 2025 ทำนาย 10 วัน; ต้องชนะการเดาและ ROC-AUC > 0.5; AI Score = โอกาสขึ้น |
| Industry Benchmark | ผลของ 4 โมดูล (AI แสดงประกอบ ไม่นับ) | คะแนนรวม = ค่าเฉลี่ยถ่วงน้ำหนัก Health 25 : Fair Value 25 : Timing 15 : Risk 15 (= 31.25/31.25/18.75/18.75%) หารด้วยผลรวมน้ำหนักของโมดูลที่มีคะแนน; ≥ 75 ซื้อแรง · ≥ 65 ซื้อ · ≥ 50 ทยอยซื้อ · < 50 ลดสัดส่วน/ขาย |

ป้ายและสีของทุกโมดูลอยู่ใน `calculate_modules/labels.py` ไฟล์เดียว ทุกหน้าใช้ชุดเดียวกัน
รายละเอียดการเปลี่ยนแปลงรอบนี้ดูที่ `docs/CHANGES_v17.md`

โมเดล AI (Random Forest) และตัวเลข Feature Importance / Accuracy / Precision / Recall / ROC-AUC ที่แสดงในหน้า "AI Prediction"
ล้วนมาจากการเทรนโมเดลจริงในขั้นตอน `calculate_scores.py` (ไม่ใช่ตัวเลขคงที่)

## หมายเหตุสำคัญที่แก้ไขจากเวอร์ชันก่อนหน้า

1. **แก้บั๊ก**: `app.py` เดิมอ้างอิงตาราง `stock_daily` แต่ `import_data.py` สร้างตารางชื่อ `stock_daily_prices` ทำให้แอป error ตอนเปิด — แก้ไขให้ตรงกันแล้ว
2. **เอา `yfinance` ออก**: ตามที่ตกลงกัน ราคาทั้งหมดอ้างอิงจาก Dataset (CSV) เป็นหลัก ไม่พึ่งพา internet ตอน deploy เพื่อความเสถียร
3. **ลบค่าจำลอง/สุ่มทั้งหมด**: Market Cap, P/E, P/B, Revenue Growth, Net Profit Growth, FCF, D/E, Industry Rank, กราฟแท่งเทียน, RSI/MACD/ADX, Key Levels (Support/Resistance), Signal History, Beta/Volatility/Drawdown trend, SHAP-style Feature Importance, Peer Comparison, Radar Chart, Strategic Matrix — **คำนวณจากข้อมูลจริงทั้งหมด**
4. Feature Importance ใช้ `model.feature_importances_` ของ Random Forest จริง (ไม่ใช่ SHAP เนื่องจากไม่ได้ติดตั้งไลบรารี `shap` แต่ให้ผลการตีความลักษณะเดียวกัน)

## การทดสอบ

รัน `python run_tests.py` (ต้องติดตั้ง requirements.txt ครบ) เพื่อตรวจ pipeline, data contract และทุกหน้า × ทุกหุ้น (56 ชุด) ด้วย `streamlit.testing.v1.AppTest`
