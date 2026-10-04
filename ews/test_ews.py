"""Run: /opt/miniconda3/bin/python -m pytest -q ews/test_ews.py"""
import datetime as dt, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rules

NOW = dt.datetime(2026, 10, 4, 12, tzinfo=dt.UTC)


# --- freshness: stale data is never used -------------------------------------
def test_fresh_and_stale():
    assert rules.fresh("wn3", "2026-10-04T00:00:00Z", NOW)
    assert not rules.fresh("wn3", "2026-10-02T00:00:00Z", NOW)
    assert not rules.fresh("radd", None, NOW)


def test_stale_wn3_cannot_raise_flood_level():
    days = [{"mean": 90, "imerg_mean": 90, "hi_env": 200}]
    assert rules.flood_level(days, 100, None, None, wn3_ok=False, s1_ok=False)[0] == "none"


# --- daily totals must use every hourly step ---------------------------------
def test_daily_totals_full_hourly_series():
    hourly = {f"2026-10-05T{h:02d}:00:00Z": 1.0 for h in range(24)}
    assert rules.daily_totals(hourly)["2026-10-05"] == 24.0
    thinned = {k: v for i, (k, v) in enumerate(hourly.items()) if i % 3 == 0}
    assert rules.daily_totals(thinned)["2026-10-05"] == 8.0   # the 2/3 under-report this guards against


# --- flood rules ----------------------------------------------------------------
def test_osogbo_28_sep_radar_is_alert():
    assert rules.flood_level(None, 186, 6.5, 0.5, wn3_ok=False, s1_ok=True)[0] == "alert"


def test_old_radar_cannot_make_alert():
    lvl, why = rules.flood_level(None, 186, 6.5, 0.5, wn3_ok=False, s1_ok=True, s1_age_h=147)
    assert lvl == "none" and "too old" in why[0]


def test_normal_water_is_not_alert():
    assert rules.flood_level(None, 186, 0.6, 0.5, wn3_ok=False, s1_ok=True)[0] == "none"


def test_envelope_only_gives_watch():
    days = [{"mean": 10, "imerg_mean": 10, "hi_env": 45}]
    assert rules.flood_level(days, 186, None, None, True, False)[0] == "watch"


def test_warning_needs_exposed_builtup():
    days = [{"mean": 25, "imerg_mean": 25, "hi_env": 60}]
    assert rules.flood_level(days, 186, None, None, True, False)[0] == "warning"
    assert rules.flood_level(days, 0, None, None, True, False)[0] == "watch"


def test_osogbo_forecast_of_27_sep_would_have_been_watch():
    # WN3 init 2026-09-26 00Z for 28 Sep: mean 23.9, IMERG-flavour 23.5, envelope 56.2 (lead 2 d)
    days = [{"mean": 5, "imerg_mean": 5, "hi_env": 20}, {"mean": 23.9, "imerg_mean": 23.5, "hi_env": 56.2}]
    assert rules.flood_level(days, 186, None, None, True, False)[0] == "watch"


# --- hysteresis -------------------------------------------------------------------
def test_hysteresis_raises_at_once_and_drops_slowly():
    s = rules.apply_hysteresis(None, "warning")
    assert s["level"] == "warning"
    s = rules.apply_hysteresis(s, "none")
    assert s["level"] == "warning" and s["held"]
    s = rules.apply_hysteresis(s, "none")
    assert s["level"] == "none"


def test_hysteresis_resets_on_new_rise():
    s = rules.apply_hysteresis({"level": "watch", "quiet_runs": 1}, "alert")
    assert s == {"level": "alert", "quiet_runs": 0}


# --- forest rules -------------------------------------------------------------------
def test_forest_levels():
    assert rules.forest_level(60, True)[0] == "warning"
    assert rules.forest_level(12, True)[0] == "watch"
    assert rules.forest_level(60, False)[0] == "none"


# --- regression: published numbers still follow from the layer files ------------------
def _layer(name):
    return json.load(open(HERE.parent / "gis" / name))


def test_published_numbers_regression():
    from shapely.geometry import shape
    import pyproj
    from shapely.ops import transform
    l3 = _layer("L3_forest.geojson")["features"]
    okomu = [f for f in l3 if f["properties"]["kind"] == "new_clearance"]
    assert len(okomu) == 1 and okomu[0]["properties"]["ha"] == 163.0
    road = [f for f in l3 if f["properties"]["kind"] == "new_road"][0]
    assert 4500 <= road["properties"]["length_m"] <= 5000
    l1 = _layer("L1_hydromet.geojson")["features"]
    scour = [f for f in l1 if f["properties"]["kind"] == "observed_scour"][0]
    utm = pyproj.Transformer.from_crs(4326, 32631, always_xy=True).transform
    ha = transform(utm, shape(scour["geometry"])).area / 1e4
    assert abs(ha - 78.3) < 1.0
    summ = json.load(open(HERE.parent / "gis" / "forest_summary.json"))
    assert round(summ["oban"]["inside_reserve"]["natloss_2021_25"]) == 7619


def test_backtest_summary_present_and_weak_rain_skill_recorded():
    b = json.load(open(HERE / "backtest_summary.json"))
    assert b["n_events"] == 700 and 0.55 <= b["auc_r1"] <= 0.65
