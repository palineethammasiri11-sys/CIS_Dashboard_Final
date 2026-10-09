# CIS Dashboard — โปรเจกต์ฉบับเต็ม (สูตรคำนวณเวอร์ชัน 2026-10-05-v16)

โฟลเดอร์นี้คือโปรเจกต์ทั้งชุด ทั้งไฟล์ที่แก้แล้วและไม่ได้แก้ หน้าตา สี และ Layout เหมือนเดิมทุกอย่าง แก้เฉพาะส่วนการคำนวณ

## ไฟล์ไหนแก้ ไฟล์ไหนไม่แก้

| ไฟล์ | สถานะ |
|---|---|
| `calculate_modules/company_health.py` | แก้ (ROE/ROA จากงบจริง, เลิกค่าปลอม/เลิกบีบคะแนน) |
| `calculate_modules/fair_value.py` | แก้ (หนี้สุทธิไม่รวมเจ้าหนี้การค้า) |
| `calculate_modules/ai_prediction.py` | แก้ (feature สัดส่วน, purge, NO EDGE) |
| `calculate_modules/risk_analysis.py` | แก้ (Volatility จากราคาจริง, เลิกค่าปลอม) |
| `calculate_scores.py` | แก้ (ราคาปลอม 10 บาท, % กำไรผิดเครื่องหมาย, CALC_VERSION, ข้อมูลแถบหัวหน้า Entry Timing) |
| `calculate_modules/entry_timing.py` | ไฟล์ต้นฉบับ v2.3 ของทีม + แก้ 2 key ให้ตรงหน้าจอ (rr_status_reason, missing_fields) ตรรกะคำนวณไม่เปลี่ยน |
| `import_data.py` | แก้ (ROE/ROA คำนวณจากงบจริง, เลิกตัดราคาก่อนปี 2023 ทิ้ง — รับข้อมูล 2015-2025) |
| `Dataset/stock_cleaned_data_2015_2025.csv` | ใหม่ — ราคา 10 ปี แทนไฟล์ 2023-2025 |
| `compute_beta.py` | ใหม่ — คำนวณ Beta / Downside Beta เทียบดัชนี SET แล้วเขียน `stock_risk_metrics.csv` ใหม่ |
| `calculate_modules/risk_analysis.py` | เพิ่ม: Beta ที่คำนวณเองถือว่ายืนยันที่มาแล้ว + Downside Beta |
| `fetch_price_history.py` | ใหม่ — สคริปต์ดึงราคาจาก Yahoo Finance (ใช้ตอนอยากอัปเดตราคา) |
| `pages_content/entry_timing.py` | แก้เฉพาะตัวเลขน้ำหนักให้อ่านจาก backend (หน้าตาเหมือนเดิม) |
| `pages_content/ai_prediction.py`, `overview.py` | หุ้นที่โมเดล NO EDGE แสดง "N/A / NO EDGE" แทนคะแนน 50 ปลอม, จำนวนตัวชี้วัด 11, กราฟ Forecast ไม่แสดงทิศทางเมื่อ NO EDGE (หน้าตาเหมือนเดิม) |
| `pages_content/overview.py`, `entry_timing.py`, `industry_benchmark.py` | เพิ่มแถบ ⓘ ใต้กราฟที่ไม่ได้วาดผ่าน show_chart |
| `pages_content/industry_benchmark.py` | AI ของหุ้น NO EDGE ในตารางเปรียบเทียบขึ้น "No Edge" (เดิมขึ้น Bearish สีแดงผิด), การ์ด N/A โทนเดียวกับการ์ดอื่น |
| `pages_content/fair_value.py` | โมเดลที่คำนวณไม่ได้แสดง "N/A" แทน 0.00 THB, เลิกแต่งช่วง ±10%, ป้าย Blended ตามจริง (หน้าตาเหมือนเดิม) |
| `common.py` | แก้ `database_is_ready()` ให้รู้ว่า DB เก่า + เพิ่ม `render_chart_note()` แถบอธิบายใต้กราฟ |
| `chart_notes.py` | ใหม่ — คำอธิบายเทคนิคของกราฟทั้ง 11 ตัว (แก้ข้อความที่ไฟล์นี้ไฟล์เดียว) |
| `คำอธิบายกราฟ_สำหรับเล่ม.md` | ใหม่ — ข้อความชุดเดียวกันสำหรับใส่เล่มรายงาน |
| `rebuild_database.py`, `วิธีอัปเดต.md` | ใหม่ |
| ไฟล์อื่นทั้งหมด (`pages_content/` หน้าอื่น, `app.py`, `import_data.py`, `Dataset/` ฯลฯ) | ไม่แก้ |

ไม่มี `cis_database.db` ในชุดนี้โดยตั้งใจ เพราะต้องสร้างใหม่ด้วยสูตรใหม่ (ขั้นตอนที่ 2)

## ขั้นตอน

1. `pip install -r requirements.txt`
2. `python rebuild_database.py` ต้องขึ้น ✅ ครบทุกข้อในขั้น [5/5]
3. `streamlit run app.py` (ถ้ามี streamlit เปิดค้างอยู่ ให้ปิดก่อนด้วย Ctrl+C)
4. Push ขึ้น GitHub รวม `cis_database.db` ด้วย แต่ไม่ต้อง push `cis_database_backup.db`

## ครั้งต่อไปที่แก้สูตร

เปลี่ยนค่า `CALC_VERSION` ใน `calculate_scores.py` แล้วรัน `python rebuild_database.py`

## คำนวณ Beta ใหม่ (แทนค่าในไฟล์ที่ไม่ทราบที่มา)

รันใน Colab หรือเครื่องที่ต่อเน็ต (ต้องมีโฟลเดอร์ `Dataset/` ที่มีไฟล์ราคาหุ้นอยู่ด้วย):
```
pip install yfinance
python compute_beta.py
```
ได้ไฟล์ 2 ไฟล์ใน `Dataset/` → อัปขึ้น GitHub ทั้งคู่:
- `stock_risk_metrics.csv` (Beta ใหม่)
- `set_index_2015_2025.csv` (ดัชนี SET ที่ใช้คำนวณ — หลักฐานตรวจสอบย้อนหลังได้)

## รอบ v13 (2026-10-04)

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `calculate_modules/risk_analysis.py` | ความเสี่ยงทุกตัว + กราฟ Rolling ใช้ 3 ปีล่าสุด (TRUE หลังควบรวม) ตัดวันหยุดปลอม — Daves et al. (2000) |
| `calculate_modules/industry_benchmark.py` | Industry Score ไม่ถูกนับซ้ำใน Overall Score แล้ว |
| `calculate_scores.py` | `CALC_VERSION = "2026-10-05-v16"` |
| `chart_notes.py` | คำอธิบายกราฟ Risk และ Strategic Matrix ตรงกับโค้ดใหม่ |
| `sensitivity_analysis.py` | ใหม่ — ทดสอบน้ำหนัก (Yeh & Liu, 2020) |
| `backtest_signals.py` | ใหม่ — Backtest สัญญาณ Entry Timing หักค่าธรรมเนียม (Anghel, 2022) |
| `tune_ai.py` | ใหม่ — ปรับจูน AI ด้วย TimeSeriesSplit (Wahyuddin et al., 2025) |

สคริปต์ 3 ตัวใหม่รันหลัง `rebuild_database.py` ได้ผลเป็นตาราง CSV สำหรับใส่เล่ม (tune_ai.py ใช้เวลาประมาณ 3 นาที)

## รอบ v15 (2026-10-05) — การ์ด "ราคานี้คาดหวังอะไร"

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `calculate_modules/fair_value.py` | เพิ่ม `market_expectation()` คำนวณ ROE ที่ราคาคาดหวัง (CAPM: Rf 1.66% ThaiBMA, ERP 6.30% Damodaran, Beta Blume, g 2%) + ธงเตือน FCF — DCF/P/E เดิมไม่เปลี่ยน |
| `calculate_scores.py` | ส่ง Beta ให้ Fair Value, `CALC_VERSION = "2026-10-05-v16"` |
| `pages_content/fair_value.py` | การ์ด "ราคานี้คาดหวังอะไร" + ป้าย "มูลค่าอ้างอิง ไม่ใช่ราคาเป้าหมาย" |
| `chart_notes.py` | คำอธิบายสูตรของการ์ดใหม่ |

## รอบ v16 (2026-10-05)

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `calculate_modules/common.py` | `RISK_FREE_RATE = 0.0166` ค่าเดียวทั้งระบบ (ThaiBMA พันธบัตร 10 ปี สิ้นปี 2568) |
| `calculate_modules/risk_analysis.py` | Sharpe/Sortino ใช้ Rf 1.66% (เดิม 2.0%) |
| `calculate_modules/fair_value.py` | ดึง Rf จาก common.py แทนการเขียนซ้ำ |
| `pages_content/risk_analysis.py` | ข้อความ Rf 1.66% + เอาปุ่ม "หน้าถัดไป" ออก (หน้าสุดท้าย) |
| `calculate_scores.py` | `CALC_VERSION = "2026-10-05-v16"` |
