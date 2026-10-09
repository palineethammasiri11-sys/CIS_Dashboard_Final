# TEAM_ROLES.md — คู่มือบทบาทหน้าที่ทีม 11 คน

เอกสารนี้คือ **จุดเริ่มต้นเดียว** ที่ทุกคนในทีมควรเปิดอ่านก่อนเริ่มงาน บอกว่าแต่ละคนรับผิดชอบอะไร
ต้องรู้/อ่านข้อมูลไหนก่อนเริ่ม และต้องส่งอะไรให้ใครต่อ ไฟล์อื่น (`README.md`, `DATA_FORMULA_AUDIT.md`,
`EDGE_CASES.md`, `GIT_WORKFLOW.md`) มีรายละเอียดเชิงลึกเฉพาะเรื่อง แต่ไฟล์นี้คือแผนที่รวมที่ชี้ไปหาไฟล์เหล่านั้น
**ไม่ต้องเปิดหลายไฟล์พร้อมกันเพื่อหาว่าตัวเองต้องทำอะไร — อ่านไฟล์นี้ไฟล์เดียวพอ**

---

## 0. แผนที่เอกสาร (เปิดไฟล์ไหนตอนไหน)

| อยากรู้เรื่อง... | เปิดไฟล์ |
|---|---|
| ใครรับผิดชอบอะไร ต้องอ่านอะไร ส่งงานให้ใคร (ภาพรวมทั้งทีม) | **ไฟล์นี้ (TEAM_ROLES.md)** |
| โครงสร้างโปรเจกต์ทั้งหมด มีไฟล์อะไรบ้าง เก็บไว้ตรงไหน | `README.md` |
| สูตรคำนวณของแต่ละโมดูล ที่มา น่าเชื่อถือแค่ไหน | `DATA_FORMULA_AUDIT.md` |
| เคสขอบที่เคยเจอจริง/ต้องระวังเป็นพิเศษต่อโมดูล | `EDGE_CASES.md` |
| ขั้นตอน Git, การเปิด PR, ลำดับการ merge | `GIT_WORKFLOW.md` |
| ตรวจสอบว่างานตัวเองพังไหมก่อนส่ง | รัน `python run_tests.py` |
| ดูหน้าตัวเองแบบเดี่ยว ไม่ต้องรอทีม | รัน `streamlit run preview_my_page.py` |

---

## 1. ภาพรวมทีม (ตารางสรุป)

| # | บทบาท | จำนวนคน | ไฟล์หลักที่ดูแล | ส่งงานให้ |
|---|---|---|---|---|
| 1-6 | เจ้าของโมดูล (คนละ 1 โมดูล) | 6 | `pages_content/<โมดูล>.py` + `calculate_modules/<โมดูล>.py` | คนที่ 8/9 (ตรวจสูตร), คนที่ 10 (ตรวจ Layout) |
| 7 | Overview Owner | 1 | `pages_content/overview.py` | คนที่ 10 (ตรวจ Layout), คนที่ 11 (รวมงาน) |
| 8 | Formula/Number Auditor (กลุ่มการเงิน) | 1 | ตรวจ `calculate_modules/company_health.py`, `fair_value.py`, `entry_timing.py` | คนที่ 1-3 (แจ้งแก้), คนที่ 11 (สรุปผล) |
| 9 | Formula/Number Auditor (กลุ่มควอนต์/สถิติ) | 1 | ตรวจ `calculate_modules/ai_prediction.py`, `risk_analysis.py`, `industry_benchmark.py` | คนที่ 4-6 (แจ้งแก้), คนที่ 11 (สรุปผล) |
| 10 | Layout/Design Lead | 1 | `common.py` (root, CSS/ธีมกลาง) + ตรวจ Layout ทุกหน้า | คนที่ 1-7 (แจ้งแก้ Layout), คนที่ 11 (สรุปผล) |
| 11 | Integration/QA Lead (เรา) | 1 | `app.py`, `calculate_scores.py`, `import_data.py`, `run_tests.py`, ไฟล์เอกสารทุกไฟล์, deploy | — (จุดสุดท้ายของ pipeline) |

---

## 2. Workflow ภาพรวม — ใครส่งงานต่อใคร

```
คนที่ 1-6 (เขียนโมดูล)  ──┬──►  คนที่ 8 หรือ 9 (ตรวจสูตร/ตัวเลข)  ──┐
                          │                                          │
                          └──►  คนที่ 10 (ตรวจ Layout)  ─────────────┤
                                                                       ▼
คนที่ 7 (Overview)  ───────────►  คนที่ 10 (ตรวจ Layout)  ───►  คนที่ 11 (รวมโค้ด + test + deploy)
```

**อธิบายสั้นๆ:** โมดูล 1-6 ทำงานเสร็จ → เปิด PR → **ต้องผ่านการตรวจ 2 ทาง** คือ (ก) ตรวจสูตร/ตัวเลขจาก 8 หรือ 9
แล้วแต่ว่าโมดูลอยู่กลุ่มไหน และ (ข) ตรวจ Layout จาก 10 → พอผ่านทั้งสองทางแล้ว คนที่ 11 ถึงจะ merge เข้า main
คนที่ 7 (Overview) รอผลจากคนอื่นก่อน แล้วให้ 10 ตรวจ Layout อย่างเดียว (ไม่มีสูตรของตัวเองให้ 8/9 ตรวจ)

รายละเอียดขั้นตอน Git/PR/ลำดับ merge แบบเป๊ะๆ ดูที่ `GIT_WORKFLOW.md`

---

## 3. รายละเอียดแต่ละบทบาท

### บทบาทที่ 1-6: เจ้าของโมดูล (คนละ 1 โมดูล)

| โมดูล | ไฟล์ที่ดูแล | สี/emoji |
|---|---|---|
| 💚 Company Health | `pages_content/company_health.py` + `calculate_modules/company_health.py` | `#10B981` |
| ⚖️ Fair Value | `pages_content/fair_value.py` + `calculate_modules/fair_value.py` | `#F59E0B` |
| ⏱️ Entry Timing | `pages_content/entry_timing.py` + `calculate_modules/entry_timing.py` | `#38BDF8` |
| 🔮 AI Prediction | `pages_content/ai_prediction.py` + `calculate_modules/ai_prediction.py` | `#A855F7` |
| 🛡️ Risk Analysis | `pages_content/risk_analysis.py` + `calculate_modules/risk_analysis.py` | `#FB923C` |
| 📊 Industry Benchmark | `pages_content/industry_benchmark.py` + `calculate_modules/industry_benchmark.py` | `#2DD4BF` |

**ความรับผิดชอบ:**
- คำนวณคะแนน/ตัวชี้วัดของโมดูลตัวเอง (แก้/ปรับปรุงสูตรใน `calculate_modules/`)
- ออกแบบหน้าตาแสดงผลของโมดูลตัวเอง (`pages_content/`)
- ทดสอบตัวเองก่อนส่งงาน (ทั้งตัวเลขถูกไหม และหน้าจอพังไหม)

**ต้องอ่าน/รู้ก่อนเริ่ม:**
- `DATA_FORMULA_AUDIT.md` หัวข้อของโมดูลตัวเอง (มีสูตรปัจจุบัน + จัดระดับว่าอันไหนมาตรฐาน อันไหนกำหนดเอง)
- `EDGE_CASES.md` หัวข้อของโมดูลตัวเอง (มีเคสจริงที่เจอแล้ว เช่น EPS ติดลบสำหรับ Fair Value)
- Docstring หัวไฟล์ `calculate_modules/<โมดูลตัวเอง>.py` (Data Contract — ต้อง return key อะไรบ้าง)
- ไฟล์ CSV ที่เกี่ยวข้องใน `Dataset/` (ต้องรู้ว่าคอลัมน์ที่ใช้มาจากไหน)

**ต้องส่งให้ใคร:**
- เปิด PR (ดูขั้นตอนใน `GIT_WORKFLOW.md`) แท็ก **คนที่ 8 หรือ 9** (ตามกลุ่ม — ดูตารางข้อ 1) ให้ตรวจสูตร/ตัวเลข
- แท็ก **คนที่ 10** ให้ตรวจ Layout
- ถ้าเพิ่ม key ใหม่ในผลลัพธ์ หรือเปลี่ยนสูตรจากที่มีอยู่ — เขียนสรุปใน PR description สั้นๆ ว่าเปลี่ยนอะไร ทำไม (auditor จะเอาไปอัปเดต `DATA_FORMULA_AUDIT.md`)

**Definition of Done ก่อนเปิด PR:**
- [ ] `streamlit run preview_my_page.py` ผ่านครบ 8 หุ้น ไม่มี error
- [ ] ถ้าแก้ `calculate_modules/` แล้ว กดปุ่ม "🔄 คำนวณคะแนนใหม่" ใน preview และเช็คตัวเลขสมเหตุสมผล
- [ ] เช็ค `EDGE_CASES.md` ของโมดูลตัวเองว่าเคสที่เคยเจอยังจัดการถูกอยู่ไหม (โดยเฉพาะ HANA/JMART)
- [ ] Data Contract ยัง return key ครบ (ไม่ลบ/เปลี่ยนชื่อ key เดิม)

---

### บทบาทที่ 7: Overview Owner

**ไฟล์ที่ดูแล:** `pages_content/overview.py`

**ความรับผิดชอบ:**
- หน้า Overview คือหน้าที่รวมผลจากทั้ง 6 โมดูลมาแสดง (6 วงคะแนน, Overall Score, Recommendation, Key Highlights)
- **ไม่มีสูตรคำนวณของตัวเอง** (ไม่มีไฟล์ใน `calculate_modules/` คู่กัน) — ดึงผลจากที่โมดูลอื่นคำนวณไว้แล้วในตาราง `cis_summary_scores` มาแสดงเท่านั้น
- ต้องรอโมดูล 1-6 มีผลลัพธ์ก่อนถึงจะทดสอบหน้าตัวเองได้ครบ

**ต้องอ่าน/รู้ก่อนเริ่ม:**
- `DATA_FORMULA_AUDIT.md` หัวข้อ 7 (Overall Score & Recommendation) — เข้าใจว่าน้ำหนักถ่วงมาจากไหน (ปัจจุบัน v17.1: Health 25 : Valuation 25 : Timing 15 : Risk 15 — AI และ Industry ไม่นับ)
- โครงสร้าง `PageContext` ใน `common.py` (root) — รู้ว่า `ctx.stock_info` มี key อะไรให้ใช้ได้บ้าง (มาจากทุกโมดูลรวมกัน)
- ไม่จำเป็นต้องอ่าน Dataset CSV โดยตรง เพราะไม่ได้คำนวณอะไรเอง

**ต้องส่งให้ใคร:**
- เปิด PR แท็ก **คนที่ 10** ให้ตรวจ Layout (ไม่ต้องแท็ก 8/9 เพราะไม่มีสูตรของตัวเอง แต่ถ้าตัวเลขที่โชว์ดูแปลกๆ ให้แจ้ง 8/9 ช่วยดูว่าต้นตอมาจากโมดูลไหน)
- ส่งให้ **คนที่ 11** ตอนพร้อม merge

**Definition of Done:**
- [ ] `streamlit run preview_my_page.py` (ตั้ง `MODULE_NAME = "overview"`) ผ่านครบ 8 หุ้น
- [ ] ควรรอให้ครบ/เกือบครบ 6 โมดูลจาก main ก่อน ถึงจะเห็นภาพรวมที่สมจริง — ถ้าโมดูลไหนยังไม่ merge ค่าที่โชว์อาจเป็นเวอร์ชันเก่า ไม่ใช่บั๊ก
- [ ] เช็คว่า 6 วงคะแนน + Recommendation ตรงกับตัวเลขจริงใน `cis_summary_scores`

---

### บทบาทที่ 8: Formula/Number Auditor — กลุ่มการเงิน (Company Health, Fair Value, Entry Timing)

**ไฟล์ที่ตรวจ:** `calculate_modules/company_health.py`, `calculate_modules/fair_value.py`, `calculate_modules/entry_timing.py`
(และหน้า `pages_content/` คู่กัน เพื่อเช็คว่าตัวเลขที่โชว์บนจอตรงกับที่คำนวณจริง)

**ความรับผิดชอบ:**
- ตรวจสอบว่าสูตรที่คนที่ 1-3 เขียน **คำนวณถูกต้องตามที่ตั้งใจ** (ไม่ใช่แค่รันไม่ error แต่ตัวเลขต้องสมเหตุสมผล)
- ตรวจสอบว่าตัวเลขที่แสดงบนหน้าจอตรงกับที่คำนวณในฐานข้อมูลจริง (ไม่มีจุดไหนพิมพ์ผิด/อ้างผิดคอลัมน์)
- ตรวจสอบ**ความสอดคล้องข้ามโมดูล** ในกลุ่มนี้ เช่น ตัวเลข ROE ที่โชว์ในหน้า Company Health ต้องตรงกับที่ใช้คำนวณ Fair Value (P/E) และ Overview
- อัปเดต `DATA_FORMULA_AUDIT.md` และ `EDGE_CASES.md` เมื่อเจอสูตรใหม่/เคสใหม่จากการตรวจ

**ต้องอ่าน/รู้ก่อนเริ่ม:**
- `DATA_FORMULA_AUDIT.md` หัวข้อ 1, 2, 3 (Company Health, Fair Value, Entry Timing) ทั้งหมดโดยละเอียด
- `EDGE_CASES.md` หัวข้อเดียวกัน
- ไฟล์ `Dataset/master_all_8_stocks_financials.csv`, `Dataset/stock_cleaned_data_2023_2025.csv` (เปิดด้วย Excel เพื่อคำนวณเทียบด้วยมือ)
- Docstring/Data Contract ในไฟล์ `calculate_modules/` ทั้ง 3 ไฟล์ที่ตัวเองตรวจ

**วิธีตรวจ (แนะนำ):**
1. เลือกหุ้น 2-3 ตัว คำนวณสูตรด้วยมือ/Excel เทียบกับที่ Dashboard โชว์ (ดูสูตรจาก `DATA_FORMULA_AUDIT.md`)
2. รัน `streamlit run preview_my_page.py` (ตั้ง `MODULE_NAME` เป็นโมดูลที่กำลังตรวจ) ไล่ดูทั้ง 8 หุ้น
3. เช็ค PR ของคนที่ 1-3 ผ่าน GitHub — ดู diff ว่ามีจุดไหนเปลี่ยนสูตรที่ควรถามเหตุผลไหม

**ต้องส่งให้ใคร:**
- Comment/Request Changes บน PR ของคนที่ 1-3 ถ้าเจอปัญหา (พร้อมอธิบายว่าเจออะไร คำนวณเทียบยังไงถึงรู้ว่าผิด)
- **Approve** PR บน GitHub เมื่อตรวจผ่านแล้ว (นี่คือสัญญาณให้คนที่ 11 รู้ว่า merge ได้)
- ส่งสรุปสั้นๆ ให้คนที่ 11 ว่าโมดูลไหนตรวจผ่านแล้วบ้าง (เช่น ทุกสัปดาห์ หรือก่อน merge รอบใหญ่)

**Definition of Done ก่อน Approve:**
- [ ] คำนวณด้วยมือเทียบแล้วตรงกับ Dashboard อย่างน้อย 2 หุ้นต่อโมดูล
- [ ] ตรวจ Data Contract ว่า key ที่ return ยังครบ ไม่มีอะไรหายไปเงียบๆ
- [ ] เช็คเคสขอบใน `EDGE_CASES.md` ว่ายังจัดการถูกอยู่ (โดยเฉพาะ HANA/JMART สำหรับ Fair Value)

---

### บทบาทที่ 9: Formula/Number Auditor — กลุ่มควอนต์/สถิติ (AI Prediction, Risk Analysis, Industry Benchmark)

**ไฟล์ที่ตรวจ:** `calculate_modules/ai_prediction.py`, `calculate_modules/risk_analysis.py`, `calculate_modules/industry_benchmark.py`

**ความรับผิดชอบ:** เหมือนคนที่ 8 ทุกอย่าง แต่รับผิดชอบกลุ่มโมดูลที่เน้นสถิติ/Machine Learning/การจัดอันดับแทน
โดยเฉพาะ **Industry Benchmark ต้องตรวจเป็นพิเศษ** เพราะรอผลจากอีก 5 โมดูลก่อน การันตีว่าไม่ได้แค่ไม่ error
แต่การจัดอันดับ/เปอร์เซ็นไทล์ต้องสมเหตุสมผลจริง (เช่น เช็คเคส sector ที่มีสมาชิกตัวเดียวตามที่ระบุใน `EDGE_CASES.md`)

**ต้องอ่าน/รู้ก่อนเริ่ม:**
- `DATA_FORMULA_AUDIT.md` หัวข้อ 4, 5, 6 (AI Prediction, Risk Analysis, Industry Benchmark)
- `EDGE_CASES.md` หัวข้อเดียวกัน — **โดยเฉพาะเคส JMART sector เดี่ยว** ที่ทำให้ industry_score เพี้ยน ต้องตัดสินใจว่าจะแก้หรือปล่อยไว้
- ไฟล์ `Dataset/stock_risk_metrics.csv`, `Dataset/train_test/*.csv` (สำหรับเช็คโมเดล AI แยก train/test ถูกไหม)
- พื้นฐาน Random Forest, Sharpe/Sortino Ratio, VaR (ถ้าไม่คุ้น ให้อ่านคำอธิบายใน `DATA_FORMULA_AUDIT.md` ก่อน มีอธิบายไว้ครบ)

**วิธีตรวจ (แนะนำ):**
1. เช็คว่า train/test แบ่งถูก (2023-2024 = train, 2025 = test) ไม่มีการเอาอนาคตมาเทรน (data leakage)
2. เช็คว่า accuracy/precision/recall ที่โชว์ตรงกับที่ sklearn คำนวณจริง (ไม่ได้ถูกแก้ไขค่าที่อื่น)
3. เช็คการจัดอันดับ Industry Benchmark ว่า sector ไหนมีสมาชิกกี่ตัว มีเคสเปอร์เซ็นไทล์เพี้ยนแบบ JMART อีกไหม

**ต้องส่งให้ใคร:** เหมือนคนที่ 8 (Comment/Approve PR ของคนที่ 4-6, ส่งสรุปให้คนที่ 11)

**Definition of Done ก่อน Approve:** เหมือนคนที่ 8 แต่เพิ่ม:
- [ ] เช็ค `roc_auc` ของทุกหุ้นไม่ใช่ 0.5 เป๊ะทุกตัว (ถ้าใช่ อาจชน edge case test set มี class เดียว)
- [ ] เช็คว่า Industry Benchmark ไม่โชว์คำว่า "อันดับ 1" ให้หุ้นที่คะแนนจริงแย่ (เคส sector เดี่ยว)

---

### บทบาทที่ 10: Layout/Design Lead

**ไฟล์ที่ดูแล:** `common.py` (root — CSS/ธีมกลาง, sidebar, header bar) + ตรวจ Layout ของทุกไฟล์ใน `pages_content/`

**ความรับผิดชอบ:**
- ออกแบบ/ปรับปรุงธีมภาพรวม (สี, ฟอนต์, spacing, การจัดวางการ์ด) ให้สม่ำเสมอกันทุกหน้า
- ตรวจ PR ของคนที่ 1-7 ทุกคนในส่วน Layout (ก่อนที่คนที่ 11 จะ merge)
- ดูแลไม่ให้สี/emoji ของแต่ละโมดูลชนกัน (ดูตารางในข้อ 3 บทบาทที่ 1-6)
- เทียบกับภาพ mockup ต้นแบบ (ถ้ามี) ว่าหน้าตารวมยังตรงทิศทางเดิมไหม

**ต้องอ่าน/รู้ก่อนเริ่ม:**
- `common.py` (root) ทั้งไฟล์ — โดยเฉพาะส่วน CSS และฟังก์ชัน `show_chart`, `render_nav_footer`, `module_card` (ถ้ามี), `PageContext`
- ทุกไฟล์ใน `pages_content/` (อย่างน้อยไล่ดูโครงสร้าง HTML/CSS คร่าวๆ ของแต่ละหน้า)
- ภาพ mockup ต้นแบบของ Dashboard (ถ้าทีมมีเก็บไว้ในโปรเจกต์)
- **ไม่จำเป็นต้องเข้าใจสูตรคำนวณลึก** (เป็นหน้าที่ 8/9) แต่ควรรู้คร่าวๆ ว่าตัวเลขแต่ละจุดหมายถึงอะไร เพื่อจัด Layout ให้สื่อความหมายถูกต้อง (เช่น ตัวเลขสำคัญควรเด่นกว่าตัวเลขรอง)

**ต้องส่งให้ใคร:**
- Comment/Request Changes บน PR ของคนที่ 1-7 ถ้า Layout มีปัญหา (สี ฟอนต์เล็กไป จัดวางไม่สวย ฯลฯ)
- **Approve** PR ในส่วน Layout เมื่อผ่านแล้ว
- ถ้าแก้ `common.py` (root) เอง — ต้องแจ้งทีมในกลุ่มแชทก่อน (กระทบทุกหน้าพร้อมกัน) แล้วรัน `python run_tests.py` เช็คว่าไม่มีหน้าไหนพังหลังแก้

**Definition of Done ก่อน Approve:**
- [ ] ฟอนต์อ่านง่าย สีไม่กลืนพื้นหลัง (เคยมีบั๊กสีตัวหนังสือกลืนพื้นหลัง sidebar มาก่อน)
- [ ] Layout ไม่ล้น/ไม่บีบจนเบี้ยว (เคยมีบั๊กวงกลมเบี้ยวจากการปรับขนาดมาก่อน)
- [ ] สี/emoji ของโมดูลนั้นตรงกับที่ตกลงกันไว้ ไม่ชนกับโมดูลอื่น
- [ ] ปุ่ม/กราฟที่เพิ่มมาใหม่ (ถ้ามี) ใช้ `show_chart()` และ `render_nav_footer()` จาก `common.py` แทนการเขียนเอง

---

### บทบาทที่ 11: Integration/QA Lead (เรา)

**ไฟล์ที่ดูแล:** `app.py`, `calculate_scores.py` (orchestrator), `import_data.py`, `run_tests.py`,
`README.md`, `GIT_WORKFLOW.md`, `TEAM_ROLES.md`, `.streamlit/config.toml`, `requirements.txt`, `cis_database.db` (เวอร์ชัน deploy จริง)

**ความรับผิดชอบ:**
- รวมโค้ดจาก branch ของทุกคน (merge ตามลำดับใน `GIT_WORKFLOW.md`)
- รัน `python run_tests.py` หลัง merge ทุก branch — ถ้า FAIL ส่งกลับให้เจ้าของโมดูลแก้ ไม่ merge ต่อ
- เช็คหน้าตารวมทั้งระบบรอบสุดท้ายก่อนส่ง (ไล่ทุกหน้า ทุกหุ้น ด้วยตา อีกรอบนอกจาก automated test)
- Deploy ขึ้น Streamlit Cloud + ดูแลไม่ให้ deploy พัง (เช่น เคสที่เคยเจอ: `.gitignore` กันไฟล์ `.db`/`Dataset/` ไม่ให้ขึ้น repo)
- ดูแลไฟล์ส่วนกลางที่ไม่มีใครเป็นเจ้าของโดยตรง (`app.py` routing, orchestrator)
- เป็นจุดตัดสินใจสุดท้ายถ้ามีความเห็นขัดแย้งระหว่าง auditor (8/9) กับเจ้าของโมดูล (1-6) หรือระหว่าง Layout Lead (10) กับเจ้าของโมดูล

**ต้องอ่าน/รู้:**
- ทุกไฟล์เอกสารในโปรเจกต์ (`README.md`, `DATA_FORMULA_AUDIT.md`, `EDGE_CASES.md`, `GIT_WORKFLOW.md`) — เพราะเป็นคนดูแล/อัปเดตไฟล์เหล่านี้ให้ทันสถานะล่าสุดของทีม
- โครงสร้าง `PageContext` ใน `common.py` และ orchestrator (`calculate_scores.py`) ละเอียดกว่าคนอื่น เพราะเป็นจุดต่อของทุกโมดูล

**รับ (ไม่ได้ส่งต่อ เพราะเป็นจุดสุดท้ายของ pipeline):**
- PR ที่ผ่านการ Approve จากทั้ง 8/9 (สูตร) และ 10 (Layout) แล้วเท่านั้น ถึงจะ merge เข้า `main`

**Checklist ก่อน Deploy จริงแต่ละรอบ:**
- [ ] `python run_tests.py` ผ่านครบ 13/13 (หรือมากกว่า ถ้ามีการเพิ่มเทสใหม่)
- [ ] ไล่ดูทุกหน้าด้วยตาอีกรอบ อย่างน้อย 2-3 หุ้นที่มีเคสขอบ (HANA, JMART)
- [ ] เช็คว่า `Dataset/` และ `cis_database.db` ถูก push ขึ้น GitHub ครบ (เช็คจากหน้า repo ตรงๆ ไม่ใช่แค่เชื่อ local)
- [ ] เช็ค `.gitignore` ไม่ได้ ignore ไฟล์ที่จำเป็น
- [ ] อัปเดต `README.md`/`DATA_FORMULA_AUDIT.md` ถ้ามีการเปลี่ยนแปลงจากรอบตรวจของ 8/9

---

## 4. คำถามที่พบบ่อย

**Q: ถ้าคนที่ 8/9 กับเจ้าของโมดูล (1-6) ความเห็นไม่ตรงกันเรื่องสูตร ใครตัดสิน?**
A: คุยกันก่อนใน PR comment ถ้าตกลงกันไม่ได้ ให้คนที่ 11 เป็นคนตัดสินใจสุดท้าย (ดูเหตุผลทั้งสองฝ่ายจาก `DATA_FORMULA_AUDIT.md` ประกอบ)

**Q: คนที่ 10 (Layout Lead) ต้องรู้สูตรคำนวณด้วยไหม?**
A: ไม่ต้องลึกเท่า 8/9 แต่ควรรู้ว่าตัวเลขแต่ละจุดสื่อความหมายอะไร (เช่น คะแนนสูง=ดี หรือ คะแนนสูง=เสี่ยงมาก) เพื่อเลือกสี/ไอคอนให้สื่อความหมายถูก ดูสรุปสั้นๆ ได้จากหัวข้อ "สรุป" ท้ายแต่ละโมดูลใน `DATA_FORMULA_AUDIT.md` พอ ไม่ต้องอ่านสูตรละเอียด

**Q: คนที่ 7 (Overview) ต้องรอให้ทุกโมดูล merge เสร็จก่อนถึงจะเริ่มงานได้ไหม?**
A: ไม่ต้องรอ เริ่มจัด Layout ได้เลยด้วยข้อมูลเท่าที่มี (`cis_database.db` ปัจจุบันมีข้อมูลจริงอยู่แล้วจากทุกโมดูล) พอโมดูลไหน merge เวอร์ชันใหม่เข้ามา ตัวเลขจะอัปเดตอัตโนมัติเพราะดึงจากฐานข้อมูลเดียวกัน

**Q: ต้องส่งไฟล์/ข้อความอะไรให้คนที่ 11 บ้างเป็นทางการ?**
A: ไม่ต้องส่งไฟล์แยก — ทุกอย่างสื่อสารผ่าน GitHub PR (เปิด PR, แท็ก reviewer ที่เกี่ยวข้อง, รอ Approve) คนที่ 11 จะเห็นสถานะทั้งหมดจากหน้า GitHub โดยตรง ไม่ต้องส่งสรุปแยกนอกระบบ ยกเว้นมีปัญหาเร่งด่วนให้แจ้งในกลุ่มแชท
