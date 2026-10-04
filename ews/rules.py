"""Pure decision logic for the Nigeria EWS (no network) — so it can be unit-tested.

Thresholds come from the back-tests run on 4 Oct 2026:
  * Rain-only trigger on 700 Groundsource floods vs 2,100 controls: AUC 0.59 -> rain alone may
    only raise a WATCH, never a WARNING.
  * WeatherNext 3 upper envelope (sum of hourly p90) >= 40 mm: caught 12-13 of ~20 heavy-rain
    days 1-3 days ahead, false alarms 20-30 % -> WATCH.
  * WeatherNext 3 IMERG-flavour mean >= 20 mm, next 24 h: 16/23 hits, 9/115 false alarms -> WARNING
    only where the site has built-up land on the floodplain.
  * Observed open water (Sentinel-1) well above the site's own baseline -> ALERT.
"""
from __future__ import annotations
import datetime as dt

LEVELS = ["none", "watch", "warning", "alert"]

# freshness limits (hours) — past these a source is STALE and is never used silently
MAX_AGE_H = {"wn3": 30, "imerg": 96, "s1": 24 * 7, "radd": 24 * 14}
S1_ALERT_MAX_AGE_H = 72                        # "alert" means danger NOW: radar older than this only informs

FLOOD = dict(env_watch_mm=40.0, mean_warning_mm=20.0, water_ratio_alert=3.0, water_min_ha=2.0)
FOREST = dict(new_ha_watch=10.0, new_ha_warning=50.0)
EROSION = dict(rain3d_watch_mm=50.0)          # provisional: not yet back-tested
DOWNGRADE_AFTER = 2                            # consecutive quieter runs before a level drops


def age_hours(iso: str | None, now: dt.datetime) -> float | None:
    if not iso:
        return None
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.UTC)
    return (now - t).total_seconds() / 3600


def fresh(source: str, iso: str | None, now: dt.datetime) -> bool:
    a = age_hours(iso, now)
    return a is not None and a <= MAX_AGE_H[source]


def daily_totals(hourly: dict[str, float]) -> dict[str, float]:
    """Sum 1-hour accumulations into UTC days. Requires the FULL hourly series:
    sampling 3-hourly and summing under-reports by ~2/3 (bug found in the Pakistan app)."""
    out: dict[str, float] = {}
    for vt, mm in hourly.items():
        out[vt[:10]] = out.get(vt[:10], 0.0) + mm
    return out


def flood_level(wn3_days: list[dict] | None, exposed_builtup_ha: float,
                water_ha: float | None, water_baseline_ha: float | None,
                wn3_ok: bool, s1_ok: bool, s1_age_h: float | None = 0.0) -> tuple[str, list[str]]:
    """wn3_days: next days ordered, each {'mean','imerg_mean','hi_env'} in mm."""
    level, why = "none", []
    if s1_ok and water_ha is not None and water_baseline_ha is not None:
        base = max(water_baseline_ha, 0.5)
        if water_ha >= FLOOD["water_min_ha"] and water_ha / base >= FLOOD["water_ratio_alert"]:
            msg = f"radar: {water_ha:.1f} ha open water vs {water_baseline_ha:.1f} ha baseline"
            if s1_age_h is not None and s1_age_h <= S1_ALERT_MAX_AGE_H:
                return "alert", [msg]
            why.append(msg + f" — observed {s1_age_h:.0f} h ago, too old to call an alert; awaiting next pass")
    if wn3_ok and wn3_days:
        d1 = wn3_days[0]
        if d1.get("imerg_mean", 0) >= FLOOD["mean_warning_mm"] and exposed_builtup_ha > 0:
            level = "warning"
            why.append(f"WN3 next-24h mean {d1['imerg_mean']:.0f} mm on a site with {exposed_builtup_ha:.0f} ha built-up floodplain")
        env = max(d.get("hi_env", 0) for d in wn3_days[:3])
        if env >= FLOOD["env_watch_mm"] and level == "none":
            level = "watch"
            why.append(f"WN3 upper envelope {env:.0f} mm within 3 days")
    return level, why


def forest_level(new_ha: float | None, radd_ok: bool) -> tuple[str, list[str]]:
    if not radd_ok or new_ha is None:
        return "none", []
    if new_ha >= FOREST["new_ha_warning"]:
        return "warning", [f"{new_ha:.0f} ha new radar forest-loss alerts in reserve (last 30 d)"]
    if new_ha >= FOREST["new_ha_watch"]:
        return "watch", [f"{new_ha:.0f} ha new radar forest-loss alerts in reserve (last 30 d)"]
    return "none", []


def erosion_level(wn3_days: list[dict] | None, wn3_ok: bool) -> tuple[str, list[str]]:
    if not wn3_ok or not wn3_days:
        return "none", []
    r3 = sum(d.get("mean", 0) for d in wn3_days[:3])
    if r3 >= EROSION["rain3d_watch_mm"]:
        return "watch", [f"WN3 3-day rain {r3:.0f} mm on an active gully (provisional rule)"]
    return "none", []


def apply_hysteresis(prev: dict | None, new_level: str) -> dict:
    """Raise at once; lower only after DOWNGRADE_AFTER consecutive quieter runs.
    Stops a level flickering day to day (lesson from the GLOF alert fixes)."""
    prev = prev or {"level": "none", "quiet_runs": 0}
    p, n = LEVELS.index(prev["level"]), LEVELS.index(new_level)
    if n >= p:
        return {"level": new_level, "quiet_runs": 0}
    q = prev.get("quiet_runs", 0) + 1
    if q >= DOWNGRADE_AFTER:
        return {"level": new_level, "quiet_runs": 0}
    return {"level": prev["level"], "quiet_runs": q, "held": True}
