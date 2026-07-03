#!/usr/bin/env python3
"""Offline HTF OB/reaction marker for XAU structure research.

This is an offline marker/simulation, not an MT5 backtest.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
RATES_DIR = ROOT / "results" / "research" / "rates"


@dataclass
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class Zone:
    tf: str
    direction: int
    start: datetime
    end: datetime
    low: float
    high: float
    depart_time: datetime
    depart_close: float
    depart_atr: float
    base_bars: int
    score: float


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M")


def load_rates(path: Path) -> List[Bar]:
    rows = []  # type: List[Bar]
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                Bar(
                    time=parse_time(row["time"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return rows


def atr_values(bars: List[Bar], period: int = 14) -> List[float]:
    trs = []  # type: List[float]
    prev_close = None  # type: Optional[float]
    for b in bars:
        if prev_close is None:
            tr = b.high - b.low
        else:
            tr = max(b.high - b.low, abs(b.high - prev_close), abs(b.low - prev_close))
        trs.append(tr)
        prev_close = b.close
    atr = []  # type: List[float]
    for i in range(len(trs)):
        start = max(0, i - period + 1)
        atr.append(sum(trs[start : i + 1]) / (i - start + 1))
    return atr


def candle_body(b: Bar) -> float:
    return abs(b.close - b.open)


def detect_zones(bars: List[Bar], tf: str, base_min: int, base_max: int) -> List[Zone]:
    atr = atr_values(bars)
    zones = []  # type: List[Zone]
    for end_idx in range(base_min - 1, len(bars) - 3):
        for base_len in range(base_min, base_max + 1):
            start_idx = end_idx - base_len + 1
            if start_idx < 20:
                continue
            base = bars[start_idx : end_idx + 1]
            highs = [b.high for b in base]
            lows = [b.low for b in base]
            zone_high = max(highs)
            zone_low = min(lows)
            width = zone_high - zone_low
            cur_atr = atr[end_idx]
            if cur_atr <= 0:
                continue
            width_atr = width / cur_atr
            if width_atr > 8.0:
                continue
            body_sum = sum(candle_body(b) for b in base)
            range_sum = sum(max(0.0001, b.high - b.low) for b in base)
            body_ratio = body_sum / range_sum
            if body_ratio > 0.62:
                continue

            future = bars[end_idx + 1 : min(len(bars), end_idx + 8)]
            for j, fb in enumerate(future, start=end_idx + 1):
                up_break = fb.close > zone_high + 0.35 * cur_atr
                down_break = fb.close < zone_low - 0.35 * cur_atr
                if not up_break and not down_break:
                    continue
                direction = 1 if up_break else -1
                depart_dist = (fb.close - zone_high) if direction == 1 else (zone_low - fb.close)
                impulse = depart_dist / cur_atr
                if impulse < 0.35:
                    continue
                score = impulse + max(0.0, 8.0 - width_atr) * 0.15 + max(0.0, 0.62 - body_ratio)
                zones.append(
                    Zone(
                        tf=tf,
                        direction=direction,
                        start=base[0].time,
                        end=base[-1].time,
                        low=zone_low,
                        high=zone_high,
                        depart_time=fb.time,
                        depart_close=fb.close,
                        depart_atr=cur_atr,
                        base_bars=base_len,
                        score=score,
                    )
                )
                break
    return dedupe_zones(zones)


def dedupe_zones(zones: List[Zone]) -> List[Zone]:
    zones = sorted(zones, key=lambda z: (z.depart_time, -z.score))
    kept = []  # type: List[Zone]
    for z in zones:
        duplicate = False
        for k in kept[-30:]:
            overlap = min(z.high, k.high) - max(z.low, k.low)
            width = max(z.high, k.high) - min(z.low, k.low)
            if z.direction == k.direction and width > 0 and overlap / width > 0.72 and abs((z.depart_time - k.depart_time).total_seconds()) < 86400 * 10:
                duplicate = True
                break
        if not duplicate:
            kept.append(z)
    return kept


def first_touch_after(zone: Zone, bars: List[Bar], from_time: datetime, to_time: datetime) -> Optional[Bar]:
    for b in bars:
        if b.time <= from_time or b.time < zone.depart_time or b.time > to_time:
            continue
        if b.low <= zone.high and b.high >= zone.low:
            return b
    return None


def outcome_after(direction: int, bars: List[Bar], start_time: datetime, days: int) -> Tuple[float, float, Optional[float]]:
    future = [b for b in bars if start_time < b.time <= start_time + timedelta(days=days)]
    if not future:
        return 0.0, 0.0, None
    ref = future[0].open
    hi = max(b.high for b in future)
    lo = min(b.low for b in future)
    close = future[-1].close
    if direction == 1:
        return hi - ref, ref - lo, close - ref
    return ref - lo, hi - ref, ref - close


def wick_reject_score(direction: int, b: Bar) -> float:
    rng = max(0.0001, b.high - b.low)
    if direction == 1:
        lower = min(b.open, b.close) - b.low
        close_pos = (b.close - b.low) / rng
        return lower / rng + close_pos
    upper = b.high - max(b.open, b.close)
    close_pos = (b.high - b.close) / rng
    return upper / rng + close_pos


def fmt_dir(direction: int) -> str:
    return "需求" if direction == 1 else "供给"


def iter_months(spec: str) -> Iterable[Tuple[str, datetime, datetime]]:
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        start = datetime.strptime(item + ".01", "%Y.%m.%d")
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)
        yield item, start, end


def main() -> int:
    parser = argparse.ArgumentParser(description="离线标注大周期OB触达反应，不是MT5回测。")
    parser.add_argument("--prefix", default="xau_htf_20260618")
    parser.add_argument("--months", default="2025.05,2026.02,2026.05")
    parser.add_argument("--manual-zone", default="2025.12.01,2026.01.31,4270,4545,1")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    d1 = load_rates(RATES_DIR / (args.prefix + "_XAUUSDm_D1.csv"))
    h4 = load_rates(RATES_DIR / (args.prefix + "_XAUUSDm_H4.csv"))
    m15 = load_rates(RATES_DIR / (args.prefix + "_XAUUSDm_M15.csv"))

    zones = []  # type: List[Zone]
    zones.extend(detect_zones(d1, "D1", 5, 28))
    zones.extend(detect_zones(h4, "H4", 8, 48))

    manual = args.manual_zone.split(",")
    if len(manual) == 5:
        z_start = datetime.strptime(manual[0], "%Y.%m.%d")
        z_end = datetime.strptime(manual[1], "%Y.%m.%d")
        z_low = float(manual[2])
        z_high = float(manual[3])
        z_dir = int(manual[4])
        zones.append(
            Zone(
                tf="USER",
                direction=z_dir,
                start=z_start,
                end=z_end,
                low=z_low,
                high=z_high,
                depart_time=z_end,
                depart_close=z_high if z_dir == 1 else z_low,
                depart_atr=max(1.0, z_high - z_low),
                base_bars=0,
                score=99.0,
            )
        )

    print("HTF OB zones detected:", len(zones))
    for month, start, end in iter_months(args.months):
        events = []
        for z in zones:
            if z.end >= start:
                continue
            touch = first_touch_after(z, m15, start - timedelta(days=2), end)
            if not touch:
                continue
            if touch.time < start or touch.time >= end:
                continue
            favor1, adverse1, close1 = outcome_after(z.direction, m15, touch.time, 1)
            favor3, adverse3, close3 = outcome_after(z.direction, m15, touch.time, 3)
            favor10, adverse10, close10 = outcome_after(z.direction, m15, touch.time, 10)
            favor20, adverse20, close20 = outcome_after(z.direction, m15, touch.time, 20)
            wick = wick_reject_score(z.direction, touch)
            events.append((z.score + wick, z, touch, wick, favor1, adverse1, favor3, adverse3, favor10, adverse10, favor20, adverse20, close20))
        events.sort(key=lambda x: (-x[0], x[2].time))
        print("")
        print("MONTH", month, "events", len(events))
        for row in events[: args.top]:
            _, z, touch, wick, f1, a1, f3, a3, f10, a10, f20, a20, c20 = row
            print(
                "%s %s zone=%.1f-%.1f base=%s..%s depart=%s touch=%s wick=%.2f "
                "fav/adverse 1d=%.1f/%.1f 3d=%.1f/%.1f 10d=%.1f/%.1f 20d=%.1f/%.1f close20=%s"
                % (
                    z.tf,
                    fmt_dir(z.direction),
                    z.low,
                    z.high,
                    z.start.strftime("%Y.%m.%d"),
                    z.end.strftime("%Y.%m.%d"),
                    z.depart_time.strftime("%Y.%m.%d %H:%M"),
                    touch.time.strftime("%Y.%m.%d %H:%M"),
                    wick,
                    f1,
                    a1,
                    f3,
                    a3,
                    f10,
                    a10,
                    f20,
                    a20,
                    "" if c20 is None else "%.1f" % c20,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
