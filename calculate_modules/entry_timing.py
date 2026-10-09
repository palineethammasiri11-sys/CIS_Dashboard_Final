"""
calculate_modules/entry_timing.py — v17 (Blueprint ฉบับที่ 2)
--------------------------------------------------------------------
สูตรคำนวณโมดูล "Entry Timing" — คู่กับ pages_content/entry_timing.py

คะแนน (ไม่เปลี่ยนจาก v2.3):
    แนวโน้ม 60 แต้ม (ข้อละ 20): ราคา > EMA20 · EMA20 > EMA50 · ราคา > MA200 (ค่าเฉลี่ยธรรมดา 200 วัน)
    แรงส่ง 40 แต้ม (ข้อละ 13.3): MACD > 0 · ADX ≥ 25 (Wilder) · Volume วันล่าสุด ≥ ค่าเฉลี่ย 20 วันก่อนหน้า
    รวมแล้วปัดเป็นจำนวนเต็ม; ≥ 70 STRONG BUY · 40-69 NEUTRAL · < 40 BEARISH · ราคา < MA200 → BEARISH เสมอ (Trend Veto)
    ข้อที่ไม่มีข้อมูลได้ 0 และไม่ลดตัวหาร; ต้องมีข้อมูลอย่างน้อยครึ่งหนึ่งของเกณฑ์
    น้ำหนัก 60/40 และเส้น 70/40 เป็นค่าที่ทีมกำหนด (มีผลทดสอบความไวและ backtest ใน scripts/)

ระดับราคาอ้างอิง (v17 / D11 — แทน Stop Loss ต่ำสุด 30 วัน, Pivot, โซนซื้อ, Target และ Risk/Reward ที่ตัดออก):
    แนวต้าน = High สูงสุด 60 วันทำการ; แนวรับ = Low ต่ำสุด 60 วันทำการ
    ATR14 = ค่าเฉลี่ยแบบ Wilder ของ True Range 14 วัน
            (True Range = มากที่สุดของ High−Low, |High−ปิดวันก่อน|, |Low−ปิดวันก่อน|)
    Stop Loss = ราคา − 2 × ATR14  (ตัวคูณ 2 เป็นการตัดสินใจของผู้ออกแบบ ไม่มีแหล่งอ้างอิง)

[v17.4] ข้อความสรุปสั้น (summary_short) ใช้กติกาเดียวกับ "ความพร้อม" และป้ายสัญญาณ
    เดิมสรุปจากจำนวนข้อที่ผ่านอย่างเดียว ทำให้ ADVANC (คะแนน 73, พร้อม) ขึ้นว่า "รอการยืนยัน" และ
    DELTA (คะแนน 47, NEUTRAL) ขึ้นว่า "ควรงดเข้าซื้อ" ซึ่งขัดกับป้ายในหน้าเดียวกัน ตอนนี้:
        ราคา < MA200          → "ควรงดเข้าซื้อ · ราคาต่ำกว่า MA200"
        คะแนน ≥ 70           → "พร้อมเข้าซื้อ" (+ บอกข้อที่ยังไม่ผ่าน ถ้ามี)
        คะแนน 40-69          → "รอสัญญาณ · ยังไม่ผ่าน: ..."
        คะแนน < 40           → "ควรงดเข้าซื้อ · แนวโน้มและแรงส่งอ่อน"
    คะแนนและป้ายทุกตัวไม่เปลี่ยน
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from calculate_modules import labels as L


@dataclass(frozen=True)
class TimingConfig:
    trend_weight: float = 60.0
    momentum_weight: float = 40.0
    trend_criteria_count: int = 3
    momentum_criteria_count: int = 3
    adx_trend_threshold: float = 25.0
    macd_bull_threshold: float = 0.0
    volume_ratio_threshold: float = 1.0
    volume_lookback: int = 20
    bullish_threshold: float = L.TIMING_BULL
    neutral_threshold: float = L.TIMING_NEUTRAL
    min_bars_required: int = 20
    min_data_completeness: float = 0.50
    enable_trend_veto: bool = True
    level_window: int = 60
    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    ma_long_period: int = 200

    def tuned(self, **kwargs) -> "TimingConfig":
        return replace(self, **kwargs)


DEFAULT_CONFIG = TimingConfig()

CRITERIA = [  # (key, ชื่อไทย, กลุ่ม)
    ("k15", "ราคา > EMA20 (แนวโน้มสั้น)", "trend"),
    ("k16", "EMA20 > EMA50 (แนวโน้มกลาง)", "trend"),
    ("k17", "ราคา > MA200 (แนวโน้มยาว)", "trend"),
    ("k18", "MACD > 0 (แรงส่ง)", "momentum"),
    ("k19", "ADX ≥ 25 (ความแรงแนวโน้ม)", "momentum"),
    ("k20", "Volume ≥ ค่าเฉลี่ย 20 วัน (วอลุ่มยืนยัน)", "momentum"),
]


def _f(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def _col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    return None


def _last(df, *names):
    c = _col(df, *names)
    return (_f(df[c].iloc[-1]) if c else None)


def _r(v, d=2):
    return None if v is None else round(float(v), d)


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR แบบ Wilder: ค่าแรก = ค่าเฉลี่ย TR 14 วันแรก จากนั้น ATR_t = (ATR_{t-1} × 13 + TR_t) ÷ 14"""
    h = pd.to_numeric(df['high'], errors='coerce')
    lo = pd.to_numeric(df['low'], errors='coerce')
    c = pd.to_numeric(df['close'], errors='coerce')
    pc = c.shift(1)
    tr = pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def compute_price_levels(price, df, cfg: TimingConfig = DEFAULT_CONFIG) -> dict:
    out = {"resistance_60d": None, "support_60d": None, "atr14": None, "stop_loss": None,
           "resistance_pct": None, "support_pct": None, "stop_loss_pct": None,
           "at_resistance": 0, "levels_available": 0, "levels_reason": ""}
    if price is None or price <= 0 or not {'high', 'low', 'close'}.issubset(df.columns):
        out["levels_reason"] = "ไม่มีราคาหรือคอลัมน์ High/Low"
        return out
    win = df.tail(cfg.level_window)
    res = _f(pd.to_numeric(win['high'], errors='coerce').max())
    sup = _f(pd.to_numeric(win['low'], errors='coerce').min())
    atr = _f(wilder_atr(df, cfg.atr_period).iloc[-1]) if len(df) > cfg.atr_period else None
    stop = price - cfg.stop_atr_multiple * atr if atr is not None else None
    pct = lambda lvl: None if lvl is None else (lvl - price) / price * 100
    out.update({
        "resistance_60d": _r(res), "support_60d": _r(sup), "atr14": _r(atr, 3), "stop_loss": _r(stop),
        "resistance_pct": _r(pct(res), 1), "support_pct": _r(pct(sup), 1), "stop_loss_pct": _r(pct(stop), 1),
        "at_resistance": int(res is not None and price >= res - 1e-9),
        "levels_available": int(res is not None and sup is not None and stop is not None),
    })
    return out


def _volume_check(df, cfg):
    vc = _col(df, 'volume', 'Volume')
    if vc is None or len(df) < cfg.volume_lookback + 1:
        return None, None, None
    vol = pd.to_numeric(df[vc], errors='coerce')
    last = _f(vol.iloc[-1])
    avg = _f(vol.iloc[-(cfg.volume_lookback + 1):-1].mean())     # 20 วันก่อนหน้า ไม่รวมวันนี้
    if last is None or avg is None or avg <= 0:
        return None, None, None
    return last, avg, last / avg


def summary_text(total, veto, failing, cfg: TimingConfig = DEFAULT_CONFIG) -> str:
    """[v17.4] ข้อความสรุปสั้นที่สอดคล้องกับ "ความพร้อม" และป้ายสัญญาณเสมอ
    total   : คะแนน Entry Timing (0-100)
    veto    : True ถ้าราคาต่ำกว่า MA200
    failing : รายชื่อเกณฑ์ที่มีข้อมูลแต่ยังไม่ผ่าน (ชื่อสั้น)"""
    pending = (" · ยังไม่ผ่าน: " + ", ".join(failing)) if failing else ""
    if veto:
        return "ควรงดเข้าซื้อ · ราคาต่ำกว่า MA200"
    if total >= cfg.bullish_threshold:
        return "พร้อมเข้าซื้อ · ผ่านครบทุกเกณฑ์" if not failing else "พร้อมเข้าซื้อ" + pending
    if total >= cfg.neutral_threshold:
        return "รอสัญญาณ" + pending
    return "ควรงดเข้าซื้อ · แนวโน้มและแรงส่งอ่อน"


def _empty(reason, missing=None) -> dict:
    out = {"timing_score": None, "trend_score": None, "mom_score": None, "data_status": "INSUFFICIENT_DATA",
           "data_status_reason": reason, "is_evaluated": 0, "missing_fields": json.dumps(missing or [], ensure_ascii=False),
           "trend_signal": "N/A", "status_label": "ข้อมูลไม่พอ", "readiness": "NO_DATA", "trend_veto_applied": 0,
           "criteria_passed": None, "criteria_available": None, "summary_short": "ข้อมูลไม่เพียงพอ",
           "rsi": None, "macd": None, "adx": None, "ema20": None, "ema50": None, "ma200": None,
           "volume_last": None, "volume_avg": None, "volume_ratio": None}
    for k, _, _ in CRITERIA:
        out[f"{k}_ok"] = 0
        out[f"{k}_available"] = 0
    out.update(compute_price_levels(None, pd.DataFrame()))
    return out


def calculate_timing_module(df_price_ticker: Optional[pd.DataFrame], config: Optional[TimingConfig] = None,
                            **overrides) -> dict:
    cfg = (config or DEFAULT_CONFIG)
    if overrides:
        cfg = cfg.tuned(**overrides)
    df = df_price_ticker
    if df is None or df.empty or _col(df, 'close') is None:
        return _empty("ไม่มีข้อมูลราคา")
    df = df.reset_index(drop=True)
    if len(df) < cfg.min_bars_required:
        return _empty(f"มีข้อมูลเพียง {len(df)} วัน (ต้องการอย่างน้อย {cfg.min_bars_required} วัน)")
    close = pd.to_numeric(df['close'], errors='coerce')
    price = _f(close.iloc[-1])
    if price is None or price <= 0:
        return _empty("ราคาปิดล่าสุดไม่ถูกต้อง")

    ema20 = _last(df, 'EMA20')
    ema50 = _last(df, 'EMA50')
    rsi = _last(df, 'RSI14')
    macd = _last(df, 'MACD')
    adx = _last(df, 'ADX', 'ADX14')
    ma200 = _f(close.tail(cfg.ma_long_period).mean()) if close.notna().sum() >= cfg.ma_long_period else None
    vol_last, vol_avg, vol_ratio = _volume_check(df, cfg)

    avail = {"k15": ema20 is not None, "k16": ema20 is not None and ema50 is not None, "k17": ma200 is not None,
             "k18": macd is not None, "k19": adx is not None, "k20": vol_ratio is not None}
    ok = {"k15": avail["k15"] and price > ema20, "k16": avail["k16"] and ema20 > ema50,
          "k17": avail["k17"] and price > ma200, "k18": avail["k18"] and macd > cfg.macd_bull_threshold,
          "k19": avail["k19"] and adx >= cfg.adx_trend_threshold,
          "k20": avail["k20"] and vol_ratio >= cfg.volume_ratio_threshold}
    missing = [n for (k, n, _) in CRITERIA if not avail[k]]
    n_avail = sum(avail.values())
    if n_avail / len(CRITERIA) < cfg.min_data_completeness:
        return _empty(f"ตัวชี้วัดพร้อมใช้เพียง {n_avail}/{len(CRITERIA)}", missing)

    trend_score = round(sum(ok[k] for k in ("k15", "k16", "k17")) * cfg.trend_weight / cfg.trend_criteria_count, 1)
    mom_score = round(sum(ok[k] for k in ("k18", "k19", "k20")) * cfg.momentum_weight / cfg.momentum_criteria_count, 1)
    total = float(round(np.clip(trend_score + mom_score, 0, 100)))
    veto = bool(cfg.enable_trend_veto and avail["k17"] and not ok["k17"])
    lab = L.timing_label(total, veto)
    readiness = "READY" if (total >= cfg.bullish_threshold and not veto) else "WAIT"

    passed = sum(ok.values())
    failing = [n.split(" (")[0] for (k, n, _) in CRITERIA if avail[k] and not ok[k]]
    summary = summary_text(total, veto, failing, cfg)            # v17.4: ตามกติกาเดียวกับความพร้อม/ป้าย

    out = {
        "data_status": "OK", "data_status_reason": "", "is_evaluated": 1,
        "missing_fields": json.dumps(missing, ensure_ascii=False),
        "timing_score": total, "trend_score": trend_score, "mom_score": mom_score,
        "trend_signal": lab["en"], "status_label": lab["en"], "readiness": readiness,
        "trend_veto_applied": int(veto), "criteria_passed": int(passed), "criteria_available": int(n_avail),
        "summary_short": summary,
        "rsi": _r(rsi, 1), "macd": _r(macd, 3), "adx": _r(adx, 1),
        "ema20": _r(ema20), "ema50": _r(ema50), "ma200": _r(ma200),
        "volume_last": _r(vol_last, 0), "volume_avg": _r(vol_avg, 0), "volume_ratio": _r(vol_ratio, 3),
    }
    for k, _, _ in CRITERIA:
        out[f"{k}_ok"] = int(bool(ok[k]))
        out[f"{k}_available"] = int(bool(avail[k]))
    out.update(compute_price_levels(price, df, cfg))
    return out
