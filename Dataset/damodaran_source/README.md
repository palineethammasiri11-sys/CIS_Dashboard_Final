# ไฟล์ต้นทาง Damodaran (Emerging Markets) ที่ใช้สร้าง `Dataset/valuation_params_2023_2025.csv`

| ปีงบ | WACC | Target P/E | วันที่ในไฟล์ (Date updated) |
|---|---|---|---|
| 2023 | waccemerg23.xls | peemerg23.xls | 2024-01-05 |
| 2024 | waccemerg24.xls | peemerg24.xls | 2025-01-05 |
| 2025 | waccemerg_2026.xls | peemerg_2026.xls | 2026-01-05 |

- ไฟล์ปี 2023-2024: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html
- ไฟล์ปี 2025 (ฉบับปัจจุบัน): https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html
- ค่าที่ใช้: ชีต "Industry Averages" คอลัมน์ "Cost of Capital" (USD) และ "Aggregate Mkt Cap/ Trailing Net Income (only money making firms)"
- อุตสาหกรรม: Telecom (Wireless) = ADVANC · Telecom. Services = TRUE, THCOM · Electronics (General) = DELTA, HANA, KCE, CCET · Computer Services = JMART (จาก indname.xls ฉบับ ม.ค. 2026)
- WACC บาท = (1 + WACC USD) × 1.02 / 1.025 − 1
- การตรวจสอบ: วันที่ในไฟล์ WACC และ P/E ของปีเดียวกันตรงกัน · จำนวนบริษัทในแต่ละอุตสาหกรรมตรงกันทั้งสองไฟล์ · ค่าปี 2025 ที่ดึงใหม่ตรงกับไฟล์เดิมทุกหุ้น
