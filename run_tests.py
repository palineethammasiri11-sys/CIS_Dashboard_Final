"""
run_tests.py — สคริปต์ตรวจสอบ Dashboard ทั้งระบบด้วยคำสั่งเดียว
----------------------------------------------------------------
สำหรับ QA/Integration Lead (หรือใครก็ได้) รันก่อน merge โค้ดทุกครั้ง เพื่อเช็คว่า:

    1. Data Contract  — ทุกโมดูลใน calculate_modules/ ยัง return key ครบตามที่ตกลงกันไว้
                         (ถ้าใครลบ/พิมพ์ชื่อ key ผิดโดยไม่ตั้งใจ จะจับได้ทันทีจากตรงนี้)
    2. Pipeline        — import_data.py + calculate_scores.py รันจบไม่มี error, ทุกตารางมีข้อมูล
    3. หน้าจอทุกหน้า    — ทั้ง 7 หน้า x 8 หุ้น (56 ชุด) เปิดได้ไม่มี exception
    4. ปุ่มนำทาง        — หน้าก่อนหน้า/หน้าหลัก/หน้าถัดไป กดแล้ว sidebar sync ถูกต้องทุกหน้า
    5. ปุ่มขยายกราฟ      — ทุกกราฟหลักเปิด dialog ได้ไม่มี error
    6. preview_my_page.py — สลับได้ครบทั้ง 7 โมดูล ไม่มี error

วิธีใช้:
    python run_tests.py

ผลลัพธ์: พิมพ์สรุป PASS/FAIL ทีละหมวด จบด้วยสรุปรวม
    - ถ้าทุกอย่างผ่าน: exit code 0 (ใช้เชื่อมกับ CI/GitHub Actions ได้)
    - ถ้ามีจุดไหนพัง: exit code 1 พร้อม print รายละเอียดว่าพังตรงไหน หน้าไหน หุ้นไหน
"""

import sys
import time
import traceback

PASS = "✅"
FAIL = "❌"

# ต้องตรงกับ common.PAGES (ลำดับใหม่ตาม Blueprint D18) — เดิมใช้ชื่อมี emoji ซึ่งไม่ตรงกับเมนูจริง
PAGES = [
    " Industry Benchmark", " Stock Overview", " Company Health", " Fair Value",
    " Risk Analysis", " Entry Timing", " AI Prediction"
]
TICKERS = ['ADVANC', 'CCET', 'DELTA', 'HANA', 'JMART', 'KCE', 'THCOM', 'TRUE']

# Data Contract ของแต่ละโมดูล (ต้องตรงกับ docstring ในไฟล์ calculate_modules/<โมดูล>.py)
# ถ้าทีมตกลงเพิ่ม/ลด key ในสัญญา ต้องแก้ตรงนี้ให้ตรงกันด้วย ไม่งั้น run_tests.py จะ false-positive
CONTRACT_KEYS = {
    'company_health':     ['health_score', 'roe', 'roa', 'de_ratio', 'current_ratio',
                            's_profitability', 's_liquidity', 's_debt'],
    'fair_value':         ['valuation_score', 'fair_value', 'dcf_fair_value', 'pe_fair_value',
                            'margin_of_safety', 'pe_ratio', 'pb_ratio', 'market_cap_mb', 'eps',
                            'price_to_value', 'confidence_level', 'wacc_used', 'target_pe_used'],
    'entry_timing':       ['timing_score', 'rsi', 'macd', 'adx', 'ema20', 'ema50', 'ma200',
                            'trend_signal', 'resistance_60d', 'support_60d', 'atr14', 'stop_loss',
                            'readiness', 'summary_short'],
    'ai_prediction':      ['ai_score', 'prob_up', 'accuracy', 'precision', 'recall',
                            'f1_score', 'roc_auc', 'ai_signal'],
    'risk_analysis':      ['risk_score', 'volatility', 'volatility_calc', 'max_drawdown',
                            'var_95', 'beta', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'risk_breakdown'],
    'industry_benchmark': ['industry_score', 'overall_score', 'sector_rank', 'overall_rank', 'recommendation',
                           'modules_used', 'rank_health_score'],
}

results = []  # (section, passed: bool, detail: str)


def log(section, passed, detail=""):
    results.append((section, passed, detail))
    icon = PASS if passed else FAIL
    print(f"{icon} {section}" + (f"  — {detail}" if detail and not passed else ""))


def section_header(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


# ============================================================================
# 1. รัน Pipeline ใหม่ทั้งหมด (import_data.py + calculate_scores.py)
# ============================================================================
section_header("1/6 — Data Pipeline (import_data.py + calculate_scores.py)")
try:
    import import_data
    import calculate_scores
    from sqlalchemy import create_engine
    import pandas as pd

    engine = create_engine(f'sqlite:///{calculate_scores.DB_NAME}')
    import_data.import_all(engine)          # รวม valuation_params_2023_2025.csv (WACC / Target P/E)
    log("import_data.py รันจบไม่มี error", True)

    calculate_scores.run_full_pipeline()
    log("calculate_scores.py รันจบไม่มี error", True)

    df_scores = pd.read_sql("SELECT * FROM cis_summary_scores", engine)
    log(f"ตาราง cis_summary_scores มีข้อมูล {len(df_scores)} แถว", len(df_scores) == len(TICKERS),
        f"คาดว่าควรมี {len(TICKERS)} แถว (1 ต่อหุ้น) แต่มี {len(df_scores)}")
except Exception as e:
    log("Data Pipeline ล้มเหลว", False, str(e))
    traceback.print_exc()
    df_scores = None


# ============================================================================
# 2. Data Contract — เช็คว่าทุกโมดูล return key ครบตามที่ตกลงกันไว้
# ============================================================================
section_header("2/6 — Data Contract Check (คอลัมน์ในตาราง cis_summary_scores)")
if df_scores is not None:
    for module_name, required_keys in CONTRACT_KEYS.items():
        missing = [k for k in required_keys if k not in df_scores.columns]
        log(f"calculate_modules/{module_name}.py — contract ครบ {len(required_keys)} key",
            len(missing) == 0,
            f"ขาด key: {missing}")
else:
    log("ข้าม Data Contract Check เพราะ Pipeline ล้มเหลวไปแล้ว", False)


# ============================================================================
# 3. ทดสอบหน้าจอทุกหน้า x ทุกหุ้น (ผ่าน app.py)
# ============================================================================
section_header("3/6 — หน้าจอทุกหน้า x ทุกหุ้น (56 ชุด)")
try:
    from streamlit.testing.v1 import AppTest

    page_fail_count = 0
    for page in PAGES:
        for tk in TICKERS:
            at = AppTest.from_file('app.py', default_timeout=60)
            at.session_state['nav_page'] = page
            at.run()
            at.selectbox[0].set_value(tk).run()
            if at.exception:
                page_fail_count += 1
                log(f"หน้า '{page.strip()}' + หุ้น '{tk}'", False, str(at.exception[0]) if at.exception else "unknown")
    if page_fail_count == 0:
        log(f"ทุกหน้า x ทุกหุ้น ({len(PAGES)*len(TICKERS)} ชุด)", True)
except Exception as e:
    log("ทดสอบหน้าจอทุกหน้า ล้มเหลว", False, str(e))
    traceback.print_exc()


# ============================================================================
# 4. ปุ่มนำทาง (หน้าก่อนหน้า/หน้าหลัก/หน้าถัดไป) + sidebar sync
# ============================================================================
section_header("4/6 — ปุ่มนำทาง + Sidebar Sync")
try:
    nav_fail_count = 0
    for page in PAGES:
        for label_kw in ['ก่อนหน้า', 'หลัก', 'ถัดไป']:
            at = AppTest.from_file('app.py', default_timeout=60)
            at.session_state['nav_page'] = page
            at.run()
            btns = [b for b in at.button if label_kw in (b.label or '')]
            if not btns:
                continue
            btns[0].click().run()
            if at.exception:
                nav_fail_count += 1
                log(f"ปุ่ม '{label_kw}' จากหน้า '{page.strip()}'", False, str(at.exception[0]))
            elif at.session_state['nav_page'] != at.radio(key='nav_page').value:
                nav_fail_count += 1
                log(f"ปุ่ม '{label_kw}' จากหน้า '{page.strip()}'", False, "Sidebar ไม่ sync กับหน้าที่เปลี่ยนไป")
    if nav_fail_count == 0:
        log("ปุ่มนำทางทุกปุ่มทุกหน้า sync ถูกต้อง", True)
except Exception as e:
    log("ทดสอบปุ่มนำทาง ล้มเหลว", False, str(e))
    traceback.print_exc()


# ============================================================================
# 5. ปุ่มขยายกราฟ (🔍 ขยายกราฟ)
# ============================================================================
section_header("5/6 — ปุ่มขยายกราฟ (Dialog)")
try:
    chart_fail_count = 0
    total_chart_btns = 0
    for page in PAGES:
        at = AppTest.from_file('app.py', default_timeout=60)
        at.session_state['nav_page'] = page
        at.run()
        expand_btns = [b for b in at.button if 'ขยายกราฟ' in (b.label or '')]
        total_chart_btns += len(expand_btns)
        for i in range(len(expand_btns)):
            at2 = AppTest.from_file('app.py', default_timeout=60)
            at2.session_state['nav_page'] = page
            at2.run()
            btns2 = [bb for bb in at2.button if 'ขยายกราฟ' in (bb.label or '')]
            btns2[i].click().run()
            if at2.exception:
                chart_fail_count += 1
                log(f"ปุ่มขยายกราฟ #{i} ในหน้า '{page.strip()}'", False, str(at2.exception[0]))
    if chart_fail_count == 0:
        log(f"ปุ่มขยายกราฟทุกจุด ({total_chart_btns} ปุ่ม)", True)
except Exception as e:
    log("ทดสอบปุ่มขยายกราฟ ล้มเหลว", False, str(e))
    traceback.print_exc()


# ============================================================================
# 6. preview_my_page.py — สลับได้ครบทุกโมดูล
# ============================================================================
section_header("6/6 — preview_my_page.py (สลับได้ครบทุกโมดูล)")
try:
    import os
    module_names = ['overview', 'company_health', 'fair_value', 'entry_timing',
                     'ai_prediction', 'risk_analysis', 'industry_benchmark']
    with open('preview_my_page.py', encoding='utf-8') as f:
        original_content = f.read()

    preview_fail_count = 0
    for mod in module_names:
        import re
        tmp_content = re.sub(r'MODULE_NAME = "[a-z_]+"', f'MODULE_NAME = "{mod}"', original_content, count=1)
        with open('_run_tests_preview_tmp.py', 'w', encoding='utf-8') as f:
            f.write(tmp_content)
        at = AppTest.from_file('_run_tests_preview_tmp.py', default_timeout=90)
        at.run()
        if at.exception:
            preview_fail_count += 1
            log(f"preview_my_page.py (MODULE_NAME='{mod}')", False, str(at.exception[0]))
    os.remove('_run_tests_preview_tmp.py')
    if preview_fail_count == 0:
        log(f"preview_my_page.py ทุกโมดูล ({len(module_names)} โมดูล)", True)
except Exception as e:
    log("ทดสอบ preview_my_page.py ล้มเหลว", False, str(e))
    traceback.print_exc()
    if os.path.exists('_run_tests_preview_tmp.py'):
        os.remove('_run_tests_preview_tmp.py')


# ============================================================================
# สรุปผลรวม
# ============================================================================
section_header("สรุปผลรวม")
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

for section, ok, detail in results:
    icon = PASS if ok else FAIL
    print(f"{icon} {section}" + (f"\n     └─ {detail}" if detail and not ok else ""))

print(f"\n{'='*70}")
if failed == 0:
    print(f"{PASS} ผ่านทั้งหมด {passed}/{total} รายการ — พร้อม merge/deploy")
    sys.exit(0)
else:
    print(f"{FAIL} ผ่าน {passed}/{total} รายการ — มี {failed} รายการที่ต้องแก้ก่อน merge/deploy")
    sys.exit(1)
