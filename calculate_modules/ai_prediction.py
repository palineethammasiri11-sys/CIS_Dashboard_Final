"""
calculate_modules/ai_prediction.py
--------------------------------------
สูตรคำนวณโมดูล "AI Prediction" (🔮) — คู่กับ pages_content/ai_prediction.py

=== DATA CONTRACT (key เดิมครบ + key ใหม่) ===
train_and_predict_ai(df_price_ticker, ticker) คืน (metrics_dict, feature_importance_dict, backtest_df)
    metrics_dict key เดิม: ai_score, prob_up, accuracy, baseline_accuracy, precision, recall, f1_score,
                          roc_auc, ai_signal, is_fallback
    key ใหม่: model_has_edge, n_train, n_test, n_purged, ai_status
    backtest_df: [date, actual_close, predicted_up_prob]

=== CHANGELOG (รอบแก้ "ตัวเลขต้องถูกก่อน") ===
- [FIX-A1] เปลี่ยน Feature จาก "ระดับราคาเป็นบาท" (close, EMA20, EMA50, MACD) เป็น "ค่าสัดส่วน"
  เหตุผล: Random Forest แบ่งข้อมูลด้วยเกณฑ์ตัวเลขตายตัว เช่น "close > 145 บาท" ที่เรียนจากปี 2023-24
  พอราคาปี 2025 ออกนอกช่วงเดิม ทุกแถวจะตกกิ่งเดียวกัน ทำนายเหมือนกันหมด (ต้นไม้ extrapolate ไม่ได้)
  ค่าสัดส่วน (ราคาห่าง EMA กี่ %, ผลตอบแทนย้อนหลัง, Volume เทียบค่าเฉลี่ย) ใช้ได้ทุกช่วงราคา
- [FIX-A2] Purge รอยต่อ Train/Test: label ของแถวท้ายปี 2024 ใช้ราคาเดือน ม.ค. 2025 (อยู่ในชุด Test)
  → ตัดแถว Train ที่วันของ label อยู่ในปี 2025 ทิ้ง (ตามแนวคิด Purging ของ López de Prado, 2018)
- [FIX-A3] เลิกคืนค่าปลอมตอนข้อมูลไม่พอ (เดิม accuracy=75%, ai_score=65) → คืน None ทั้งหมด + is_fallback=True
- [FIX-A4] เลิก clip ai_score ที่ 30-95 → 0-100
- [v17 / D12] AI Score = prob_up เมื่อผ่านด่าน (เดิม prob_up × 0.7 + accuracy × 0.3); ป้ายจาก labels.ai_label
  (≥ 65% เอียงขึ้น · 35-64.9% ก้ำกึ่ง · < 35% เอียงลง) — ให้ตรงกับทุกหน้า
- [FIX-A5] ถ้าโมเดลไม่ชนะการเดาแบบง่าย (accuracy <= baseline หรือ ROC-AUC <= 0.5) → model_has_edge=False,
  ai_signal='NO EDGE', ai_score=None (ไม่ถูกนับในคะแนนรวม) เพื่อไม่ให้ Dashboard แสดง STRONG BUY
  จากโมเดลที่ทำนายได้ไม่ดีกว่าการเดา
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from calculate_modules.common import clean_float
from calculate_modules import labels as L

PREDICTION_HORIZON_DAYS = 10
TEST_START = '2025-01-01'

# FIX-A1: ชื่อ feature ที่จะโชว์ในกราฟ Feature Importance (หน้า UI ต้องแก้ข้อความ "6 ตัวชี้วัด" เป็นจำนวนนี้)
FEATURES = [
    'dist_ema20',      # close / EMA20 - 1        ราคาห่างเส้น EMA20 กี่ %
    'ema20_vs_ema50',  # EMA20 / EMA50 - 1        ความชันเทรนด์
    'macd_norm',       # MACD / close             MACD เทียบขนาดราคา
    'macd_hist_norm',  # MACD Histogram / close   แรงเร่งโมเมนตัม
    'RSI14',
    'ADX',
    'volume_ratio',    # volume / Volume Avg 20
    'ret_5d', 'ret_10d', 'ret_20d',   # ผลตอบแทนย้อนหลัง 5/10/20 วัน
    'vol_20d',         # ความผันผวนรายวัน 20 วัน (std ของผลตอบแทน)
]


def _build_features(df):
    """สร้าง feature เชิงสัดส่วนจากคอลัมน์ในตาราง stock_daily_prices"""
    num = lambda c: pd.to_numeric(df[c].apply(clean_float, default=np.nan), errors='coerce') \
        if c in df.columns else pd.Series(np.nan, index=df.index)
    close, ema20, ema50 = num('close'), num('EMA20'), num('EMA50')
    macd, hist = num('MACD'), num('macd_hist')
    volume, vol_avg = num('volume'), num('Volume Avg')

    f = pd.DataFrame(index=df.index)
    f['dist_ema20'] = close / ema20 - 1
    f['ema20_vs_ema50'] = ema20 / ema50 - 1
    f['macd_norm'] = macd / close
    f['macd_hist_norm'] = hist / close
    f['RSI14'] = num('RSI14')
    f['ADX'] = num('ADX')
    f['volume_ratio'] = volume / vol_avg.replace(0, np.nan)
    ret = close.pct_change()
    f['ret_5d'] = close.pct_change(5)
    f['ret_10d'] = close.pct_change(10)
    f['ret_20d'] = close.pct_change(20)
    f['vol_20d'] = ret.rolling(20).std()
    return f.replace([np.inf, -np.inf], np.nan), close


def _fallback(reason, n_train=0, n_test=0):
    """FIX-A3: ข้อมูลไม่พอ → ไม่สร้างตัวเลขขึ้นมาเอง"""
    metrics = {k: None for k in ['ai_score', 'prob_up', 'accuracy', 'baseline_accuracy', 'precision',
                                  'recall', 'f1_score', 'roc_auc']}
    metrics.update({'ai_signal': 'INSUFFICIENT DATA', 'is_fallback': True, 'model_has_edge': False,
                    'n_train': n_train, 'n_test': n_test, 'n_purged': 0, 'ai_status': reason})
    return (metrics, {f: 0.0 for f in FEATURES},
            pd.DataFrame(columns=['date', 'actual_close', 'predicted_up_prob']))


def train_and_predict_ai(df_price_ticker, ticker):
    """Module 4: AI Prediction (Train 2015-2024 (purged) / Test 2025)"""
    df = df_price_ticker.copy().sort_values(by='date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    feats, close = _build_features(df)
    df = pd.concat([df[['date']], feats], axis=1)
    df['close'] = close

    future_close = close.shift(-PREDICTION_HORIZON_DAYS)
    df['target'] = np.where(future_close.notna(), (future_close > close).astype(int), np.nan)
    df['label_date'] = df['date'].shift(-PREDICTION_HORIZON_DAYS)   # วันที่ที่ใช้ตัดสิน label

    df_model = df.dropna(subset=FEATURES + ['target'])
    test_start = pd.Timestamp(TEST_START)
    train_all = df_model[df_model['date'] < test_start]
    train_data = train_all[train_all['label_date'] < test_start]          # FIX-A2: purge
    n_purged = len(train_all) - len(train_data)
    test_data = df_model[df_model['date'] >= test_start]

    if len(train_data) < 50 or len(test_data) < 20:
        return _fallback(f'ข้อมูลไม่พอ (train={len(train_data)}, test={len(test_data)})',
                         len(train_data), len(test_data))

    X_train, y_train = train_data[FEATURES], train_data['target'].astype(int)
    X_test, y_test = test_data[FEATURES], test_data['target'].astype(int)
    baseline_acc = float(max(y_test.mean(), 1 - y_test.mean()) * 100)

    model = RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=10,
                                   random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    test_pred = model.predict(X_test)
    test_proba = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, test_pred) * 100
    prec = precision_score(y_test, test_pred, zero_division=0) * 100
    rec = recall_score(y_test, test_pred, zero_division=0) * 100
    f1 = f1_score(y_test, test_pred, zero_division=0) * 100
    auc = roc_auc_score(y_test, test_proba) if y_test.nunique() > 1 else None

    # ทำนายวันล่าสุด (ใช้แถวล่าสุดที่ feature ครบ — ไม่ต้องมี label)
    latest = df.dropna(subset=FEATURES)
    prob_up = float(model.predict_proba(latest[FEATURES].iloc[[-1]])[0][1] * 100) if not latest.empty else None

    has_edge = bool(auc is not None and auc > 0.5 and acc > baseline_acc)   # FIX-A5 (ด่าน "ต้องชนะการเดา")
    if prob_up is None:
        ai_score, sig = None, 'INSUFFICIENT DATA'
    elif not has_edge:
        ai_score, sig = None, 'NO EDGE'
    else:
        # v17 / D12: AI Score = โอกาสขึ้นตรง ๆ (ตัดสูตร 0.7 × โอกาส + 0.3 × ความแม่นยำ ที่ไม่มีที่มา)
        ai_score = round(float(prob_up), 1)
        sig = L.ai_label(prob_up, True)['en']

    feature_importance = {f: round(float(imp), 4) for f, imp in zip(FEATURES, model.feature_importances_)}
    backtest_df = pd.DataFrame({
        'date': test_data['date'].dt.strftime('%Y-%m-%d').values,
        'actual_close': test_data['close'].values,
        'predicted_up_prob': test_proba,
    })

    return ({
        'ai_score': ai_score,
        'prob_up': None if prob_up is None else round(prob_up, 1),
        'accuracy': round(float(acc), 1),
        'baseline_accuracy': round(baseline_acc, 1),
        'precision': round(float(prec), 1),
        'recall': round(float(rec), 1),
        'f1_score': round(float(f1), 1),
        'roc_auc': None if auc is None else round(float(auc), 3),
        'ai_signal': sig,
        'is_fallback': False,
        'model_has_edge': has_edge,
        'n_train': int(len(train_data)),
        'n_test': int(len(test_data)),
        'n_purged': int(n_purged),
        'ai_status': 'OK' if has_edge else 'โมเดลยังไม่ชนะการเดาแบบง่าย (baseline) บนข้อมูลปี 2025',
        'test_start': TEST_START, 'horizon_days': PREDICTION_HORIZON_DAYS,
        'train_start': str(train_data['date'].min().date()), 'train_end': str(train_data['date'].max().date()),
        'test_end': str(test_data['date'].max().date()),
    }, feature_importance, backtest_df)
