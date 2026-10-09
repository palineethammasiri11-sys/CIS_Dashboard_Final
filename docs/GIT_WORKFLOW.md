# คู่มือ Git Workflow — ทีม 11 คน

เอกสารนี้บอกวิธีใช้ Git ร่วมกันทั้ง 11 คน ให้แก้โค้ดพร้อมกันได้โดยไม่ทับ/conflict กันเอง
อ่านคู่กับ `TEAM_ROLES.md` (ใครรับผิดชอบอะไร ต้องอ่าน/ส่งอะไรให้ใคร — รายละเอียดเต็มอยู่ที่นั่น)
และ `README.md` (โครงสร้างไฟล์ทั้งหมด)

---

## 1. ตั้ง Branch ตามนี้

```
main                              ← โค้ดที่ deploy จริง ห้าม push ตรงเด็ดขาด
├── feature/company-health        ← คนที่ 1
├── feature/fair-value            ← คนที่ 2
├── feature/entry-timing          ← คนที่ 3
├── feature/ai-prediction         ← คนที่ 4
├── feature/risk-analysis         ← คนที่ 5
├── feature/industry-benchmark    ← คนที่ 6
├── feature/overview              ← คนที่ 7
└── feature/layout                ← คนที่ 10 (Layout Lead ใช้ตอนแก้ common.py หรือปรับ Layout ให้คนอื่นโดยตรง)
```

**คนที่ 8 และ 9 (Formula/Number Auditor) ไม่ต้องมี feature branch ของตัวเอง** — งานหลักคือ**รีวิว PR ของคนอื่นบน GitHub**
(Comment / Request Changes / Approve) ถ้าเจอบั๊กแล้วอยากแก้เอง ให้สร้าง branch เล็กๆ ชื่อ `fix/<คำอธิบายสั้นๆ>`
เช่น `fix/pe-ratio-nan-display` แล้วเปิด PR แยก โดยแท็กเจ้าของโมดูลนั้นให้มา review ด้วย

**คนที่ 11 (Integration/QA Lead)** ทำงานบน `main` โดยตรง + ดูแล branch รวมตอน merge ไม่ต้องมี feature branch ของตัวเอง

**คำสั่งเริ่มต้น (รันครั้งเดียวตอนเริ่มงาน — สำหรับคนที่ 1-7, 10):**
```bash
git clone <repo-url>
cd cis-dashboard-main
git checkout -b feature/company-health   # เปลี่ยนชื่อ branch ตามโมดูลของตัวเอง
```

---

## 2. กติกาการแก้ไฟล์ — ใครแตะไฟล์ไหนได้บ้าง

| ไฟล์ | ใครแก้ได้ | หมายเหตุ |
|---|---|---|
| `pages_content/<โมดูลตัวเอง>.py` | เจ้าของโมดูล (คนที่ 1-6) | แก้อิสระ ไม่กระทบคนอื่น |
| `calculate_modules/<โมดูลตัวเอง>.py` | เจ้าของโมดูล (คนที่ 1-6) | แก้อิสระ แต่ห้ามลบ/เปลี่ยนชื่อ key ใน Data Contract โดยไม่แจ้งทีม |
| `pages_content/overview.py` | คนที่ 7 | ไม่มีไฟล์คำนวณคู่กัน (ดึงผลจากโมดูลอื่น) |
| `common.py` (root, ฝั่ง UI/CSS) | คนที่ 10 (Layout Lead) | คนอื่นถ้าอยากแก้ ต้องเปิด PR แยกแล้วแท็ก Layout Lead review |
| `calculate_modules/common.py` | ใครก็ได้ แต่ต้องแจ้งทีมในกลุ่มแชทก่อน | กระทบทุกโมดูล (SECTOR_MAP, clean_float) — คนที่ 8/9 มีสิทธิ์ flag ให้แก้ได้เวลารีวิว |
| `calculate_scores.py` (orchestrator), `import_data.py`, `app.py` | คนที่ 11 (Integration Lead) | คนอื่นไม่ควรต้องแตะไฟล์นี้เลยถ้าทำตาม Data Contract ถูกต้อง |
| `Dataset/*.csv` | คนที่ 11 เท่านั้น | ถ้ามีข้อมูลอัปเดต แจ้งทุกคนให้ pull ใหม่ + รัน pipeline ใหม่ |
| `run_tests.py`, `README.md`, `GIT_WORKFLOW.md`, `TEAM_ROLES.md` | คนที่ 11 | อัปเดตตามที่ทีมแจ้งมา |
| `DATA_FORMULA_AUDIT.md`, `EDGE_CASES.md` | คนที่ 8/9 (เนื้อหา) + คนที่ 11 (โครงสร้างไฟล์) | 8/9 อัปเดตเนื้อหาตอนตรวจเจอสูตร/เคสใหม่ ได้โดยตรง |

**กฎทอง:** ถ้าไฟล์ไม่ได้เป็นของตัวเองตามตารางนี้ ห้าม push ตรงเข้า `main` เอง ต้องเปิด PR เสมอ

---

## 3. Workflow รายวัน (ทำระหว่างพัฒนา — สำหรับคนที่ 1-7, 10)

```bash
# ก่อนเริ่มงานทุกครั้ง ดึงโค้ดล่าสุดจาก main มาก่อน กัน branch ตัวเองเก่าเกินไป
git checkout main
git pull origin main
git checkout feature/company-health
git merge main          # เอาโค้ดล่าสุดจาก main มารวมกับ branch ตัวเอง

# แก้โค้ด ทดสอบด้วย preview_my_page.py ให้ผ่านก่อนทุกครั้ง
streamlit run preview_my_page.py

# commit เป็นชุดเล็กๆ บ่อยๆ (ไม่ใช่รวบยอด commit เดียวตอนจบ)
git add pages_content/company_health.py calculate_modules/company_health.py
git commit -m "company_health: ปรับน้ำหนัก ROE ให้เข้ม + แก้ layout การ์ด 7 มิติ"
git push origin feature/company-health
```

**ทำไมต้อง `git merge main` บ่อยๆ:** เพราะไฟล์กลาง (`common.py`, `calculate_scores.py`) อาจถูก
คนที่ 10 หรือ 11 อัปเดตระหว่างทาง ถ้าไม่ merge บ่อยๆ ตอนรวมสุดท้ายจะเจอ conflict ก้อนใหญ่

---

## 4. เปิด Pull Request (PR) ตอนงานเสร็จ

**Checklist ก่อนเปิด PR (Definition of Done):**
- [ ] รัน `streamlit run preview_my_page.py` ผ่านครบทั้ง 8 หุ้น ไม่มี error สีแดง
- [ ] ถ้าแก้ `calculate_modules/` แล้ว — กดปุ่ม "🔄 คำนวณคะแนนใหม่" ใน preview และเช็คตัวเลขสมเหตุสมผล
- [ ] Data Contract ยัง return key ครบ (เทียบ docstring หัวไฟล์ `calculate_modules/<โมดูล>.py`)
- [ ] เช็ค `EDGE_CASES.md` ของโมดูลตัวเองว่ายังจัดการถูกอยู่
- [ ] ถ้าเพิ่ม key ใหม่ในผลลัพธ์ หรือเปลี่ยนสูตร — เขียนสรุปสั้นๆ ใน PR description ว่าเปลี่ยนอะไร ทำไม
- [ ] ไม่ได้แก้ไฟล์ของคนอื่น (เช็คด้วย `git diff main --stat` ว่ามีแต่ไฟล์ของตัวเอง)

**คำสั่งเปิด PR:**
```bash
git push origin feature/company-health
# แล้วไปเปิด Pull Request บน GitHub: feature/company-health → main
```

**หัวข้อ PR แนะนำ:** `[Company Health] เพิ่ม X, แก้สูตร Y` — ระบุโมดูลในวงเล็บเสมอ ให้ reviewer กรอง PR ได้ง่าย

**ต้องแท็กใคร review (ดูรายละเอียดเต็มใน `TEAM_ROLES.md` ข้อ 2):**

| PR จากโมดูล | แท็ก Formula Auditor | แท็ก Layout |
|---|---|---|
| Company Health, Fair Value, Entry Timing | คนที่ 8 | คนที่ 10 |
| AI Prediction, Risk Analysis, Industry Benchmark | คนที่ 9 | คนที่ 10 |
| Overview | (ไม่มี — ไม่มีสูตรของตัวเอง) | คนที่ 10 |

**PR จะ merge ได้ก็ต่อเมื่อได้ Approve ครบทั้ง 2 ทาง** (Formula Auditor ที่เกี่ยวข้อง + Layout Lead) คนที่ 11 ถึงจะ merge เข้า `main`

---

## 5. ลำดับการ Merge (สำคัญมาก — มีโมดูลที่ต้องรอกัน)

Industry Benchmark (`calculate_modules/industry_benchmark.py`) และหน้า Overview
**คำนวณ/แสดงผลจากอีก 5 โมดูล** ดังนั้นควร merge ตามลำดับนี้:

```
1. merge feature/company-health       → main   (ผ่าน Approve: คนที่ 8 + คนที่ 10)
2. merge feature/fair-value           → main   (ผ่าน Approve: คนที่ 8 + คนที่ 10)
3. merge feature/entry-timing         → main   (ผ่าน Approve: คนที่ 8 + คนที่ 10)
4. merge feature/ai-prediction        → main   (ผ่าน Approve: คนที่ 9 + คนที่ 10)
5. merge feature/risk-analysis        → main   (ผ่าน Approve: คนที่ 9 + คนที่ 10)
6. merge feature/industry-benchmark   → main   (ผ่าน Approve: คนที่ 9 + คนที่ 10) ← ทำหลังสุดในกลุ่มโมดูล เพราะต้องมีผลลัพธ์ 5 โมดูลก่อนถึงจะเทสต์ Ranking ได้จริง
7. merge feature/overview             → main   (ผ่าน Approve: คนที่ 10) ← รวมทีหลังสุด เพราะ Overview ต้องมีคะแนนครบทุกโมดูลถึงจะโชว์ถูก
8. merge feature/layout (ถ้ามีการแก้ common.py เพิ่มเติม) → main
```

คนที่ 6 (Industry Benchmark) และคนที่ 7 (Overview) **ไม่ต้องรอเฉยๆ** — ระหว่างรอ ให้ทำ Layout
ของหน้าตัวเองไปก่อนด้วยข้อมูลของคนอื่นที่ merge ไปแล้วบางส่วน (ทดสอบผ่าน `preview_my_page.py`
จะเห็นข้อมูลจริงเท่าที่ merge มาแล้ว ค่อยๆ ดีขึ้นเรื่อยๆ ตามลำดับ merge)

คนที่ 8/9 (Auditor) ก็ไม่ต้องรอเฉยๆ เช่นกัน — ระหว่างที่โมดูลอื่นยังไม่เปิด PR สามารถเริ่มตรวจสอบสูตร
เทียบกับ `Dataset/*.csv` ล่วงหน้าได้เลยจากโค้ดปัจจุบันใน `main`

---

## 6. ขั้นตอนรวมทีม (Integration Lead ทำ — คนที่ 11)

```bash
git checkout main
git pull origin main

# ก่อน merge แต่ละ branch เช็คว่า PR นั้นได้ Approve ครบทั้ง Formula Auditor + Layout Lead แล้ว
git merge feature/company-health --no-ff
python calculate_scores.py    # รันเช็คว่ายัง import/รันผ่าน หลัง merge ทุกครั้ง
python run_tests.py           # รัน regression test เต็มชุด

# ถ้าผ่าน ไป merge branch ถัดไป ทำซ้ำแบบนี้จนครบทุก branch
git merge feature/fair-value --no-ff
python run_tests.py
# ... ทำซ้ำจนครบตามลำดับในข้อ 5
```

**ถ้า `run_tests.py` แจ้ง FAIL** — อ่าน error message (บอกชัดว่าโมดูลไหน/หน้าไหน/หุ้นไหนพัง)
แล้วส่งกลับให้เจ้าของโมดูลนั้นแก้ ไม่ต้อง merge ต่อจนกว่าจะแก้เสร็จ

**หลัง merge ครบทุก branch แล้ว:**
```bash
python run_tests.py           # รันรอบสุดท้ายให้แน่ใจ 100%
git push origin main          # deploy จริง
```

---

## 7. การแก้ Conflict (ถ้าเกิดขึ้น)

เพราะแยกไฟล์ตามโมดูลแล้ว **conflict ไม่ควรเกิดขึ้นบ่อย** ยกเว้น 2 กรณี:

**กรณี A: 2 คนแก้ `calculate_modules/common.py` หรือ `common.py` (root) พร้อมกัน**
→ ป้องกันได้ด้วยการไม่แก้ไฟล์นี้เองตั้งแต่แรก (ดูตารางข้อ 2) ถ้าจำเป็นต้องแก้ ให้ประกาศในกลุ่มแชทก่อนว่า "ขอแก้ common.py ช่วงเวลานี้" กันชนกัน

**กรณี B: `calculate_scores.py` (orchestrator) ถูกแก้พร้อมกับที่มีคน merge branch ใหม่เข้ามา**
→ ปกติไฟล์นี้ควรนิ่ง ไม่มีใครแก้บ่อย ถ้า conflict เกิดขึ้นจริง คนที่ 11 เป็นคนตัดสินใจว่าจะเก็บเวอร์ชันไหน

**คำสั่งแก้ conflict ทั่วไป:**
```bash
git status                     # ดูว่าไฟล์ไหน conflict
# เปิดไฟล์ที่ conflict แก้ส่วนที่มี <<<<<<< / ======= / >>>>>>> ด้วยมือ
git add <ไฟล์ที่แก้แล้ว>
git commit
python run_tests.py            # เช็คว่าแก้แล้วยังทำงานถูกต้อง
```

---

## 8. สรุปสั้นๆ แจกทีม

> **ก่อนแก้:** `git pull` + `git merge main` เข้า branch ตัวเอง
> **ระหว่างแก้:** แตะแค่ไฟล์ของตัวเอง (`pages_content/xxx.py` + `calculate_modules/xxx.py`), เทสด้วย `preview_my_page.py`
> **ก่อนเปิด PR:** เช็ค Definition of Done ในข้อ 4 + แท็ก Formula Auditor (8 หรือ 9) และ Layout Lead (10) ตามตาราง
> **ตอนรวมทีม:** merge ตามลำดับในข้อ 5 (ต้อง Approve ครบก่อน), รัน `python run_tests.py` หลัง merge ทุก branch
> **รายละเอียดบทบาทเต็ม:** ดู `TEAM_ROLES.md`
