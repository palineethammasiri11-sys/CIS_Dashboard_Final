# วิธีเปิด CIS Dashboard ใน VS Code (สำหรับคนที่ไม่เคยใช้)

ทำครั้งแรกครั้งเดียว: ขั้นที่ 1-7 · ครั้งต่อไปทำแค่ขั้นที่ 4, 5, 8

## 1. ติดตั้ง Python
1. เข้า https://www.python.org/downloads/ กดปุ่มดาวน์โหลด Python (แนะนำรุ่น 3.12)
2. เปิดไฟล์ที่โหลดมา **ติ๊กช่อง "Add python.exe to PATH" ด้านล่างก่อน** แล้วกด Install Now
3. รอจนขึ้น Setup was successful แล้วกด Close

## 2. ติดตั้ง VS Code
1. เข้า https://code.visualstudio.com/ กด Download แล้วติดตั้งตามปกติ (กด Next ไปเรื่อย ๆ)
2. เปิด VS Code → กดไอคอนสี่เหลี่ยม 4 ช่องทางซ้าย (Extensions) → พิมพ์ `Python` → กด Install ที่ตัวของ Microsoft

## 3. แตกไฟล์ zip
1. คลิกขวาไฟล์ `CIS_ver1_v17.zip` → **Extract All...** → เลือกที่เก็บ เช่น `Documents` → Extract
2. จะได้ folder `CIS_ver1` ที่ข้างในมี `app.py`, `Dataset`, `pages_content` ฯลฯ
   (ห้ามเปิดไฟล์จากในตัว zip ตรง ๆ ต้องแตกก่อน)

## 4. เปิด folder ใน VS Code
1. VS Code → เมนู **File → Open Folder...**
2. เลือก folder `CIS_ver1` (ตัวที่มี `app.py` อยู่ข้างใน) → Select Folder
3. ถ้าถามว่า "Do you trust the authors..." กด **Yes, I trust the authors**

## 5. เปิดหน้าต่างพิมพ์คำสั่ง (Terminal)
- เมนู **Terminal → New Terminal** จะมีกล่องพิมพ์คำสั่งขึ้นด้านล่าง
- ทุกคำสั่งในขั้นถัดไป พิมพ์ (หรือวาง) ในกล่องนี้แล้วกด Enter

## 6. สร้างพื้นที่แยกของโปรเจกต์ (ทำครั้งเดียว)
Windows:
```
python -m venv .venv
.venv\Scripts\activate
```
Mac:
```
python3 -m venv .venv
source .venv/bin/activate
```
- สำเร็จแล้วบรรทัดคำสั่งจะขึ้นต้นด้วย `(.venv)`
- Windows ถ้าขึ้นตัวแดงว่า "running scripts is disabled" ให้พิมพ์
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` กด Enter ตอบ `Y` แล้วพิมพ์ `.venv\Scripts\activate` ใหม่

## 7. ติดตั้งโปรแกรมที่ Dashboard ใช้ (ทำครั้งเดียว ใช้เวลา 2-5 นาที)
```
python -m pip install -r requirements.txt
```
(Mac ใช้ `python3` แทน `python`)

## 8. เปิด Dashboard
```
python -m streamlit run app.py
```
- เบราว์เซอร์จะเปิดหน้า `http://localhost:8501` ให้เอง (ถ้าไม่เปิด ให้พิมพ์ที่อยู่นี้ในเบราว์เซอร์)
- **ครั้งแรกต้องรอราว 1-2 นาที** ระบบกำลังคำนวณฐานข้อมูลใหม่ (ฝึกโมเดล AI) จะเห็นข้อความ "กำลังประมวลผลข้อมูลครั้งแรก"
- ถ้าถามอีเมลในกล่องคำสั่ง ให้กด Enter ข้ามไปได้
- ปิด Dashboard: คลิกที่ Terminal แล้วกด **Ctrl + C**

## ครั้งต่อไปที่จะเปิด
1. เปิด VS Code → File → Open Folder → `CIS_ver1`
2. Terminal → New Terminal
3. `.venv\Scripts\activate` (Mac: `source .venv/bin/activate`)
4. `python -m streamlit run app.py`

## ตรวจระบบทั้งหมด (ไม่บังคับ)
```
python run_tests.py
```
ตรวจการคำนวณ, ข้อมูลที่แต่ละโมดูลส่งออกมา, ทุกหน้า × ทุกหุ้น และปุ่มนำทาง ใช้เวลาหลายนาที ผลสุดท้ายควรขึ้น "ผ่านทั้งหมด"

## ปัญหาที่เจอบ่อย
| อาการ | วิธีแก้ |
|---|---|
| `'python' is not recognized` | ตอนติดตั้ง Python ไม่ได้ติ๊ก Add to PATH → ติดตั้ง Python ใหม่แล้วติ๊ก หรือใช้คำสั่ง `py` แทน `python` |
| `No module named streamlit` | ยังไม่ได้ทำขั้นที่ 7 หรือยังไม่ได้ activate `.venv` (ดูว่ามี `(.venv)` หน้าบรรทัดไหม) |
| `Port 8501 is already in use` | มี Dashboard เปิดค้างอยู่ → ไปที่ Terminal เดิมกด Ctrl + C หรือใช้ `python -m streamlit run app.py --server.port 8502` |
| ตัวเลขบนจอไม่เปลี่ยนหลังแก้สูตร | ลบไฟล์ `cis_database.db` แล้วเปิดใหม่ หรือแก้เลข `CALC_VERSION` ใน `calculate_scores.py` |
| ขั้นที่ 7 ขึ้น error ยาว ๆ ติดตั้งไม่ผ่าน | มักเกิดกับ Python รุ่นใหม่มาก ให้ติดตั้ง Python 3.12 แล้วทำขั้นที่ 6-7 ใหม่ (ลบ folder `.venv` เดิมก่อน) |
| หน้าเว็บขึ้น error สีแดงเรื่องไฟล์ข้อมูล | ตรวจว่า folder `Dataset` มีไฟล์ CSV ครบ 5 ไฟล์ (รวม `valuation_params_2023_2025.csv`) |
