"""Nigeria EWS run: fetch every source, stamp its freshness, apply rules + hysteresis, write status.json.

Run:  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 ews/pipeline.py
A failed or stale source is reported as such and contributes nothing — it is never filled in.
"""
from __future__ import annotations
import datetime as dt, json, sys, traceback
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
from eeinit import ee
import rules, wn3

STATE = HERE / "state.json"   # hysteresis memory between runs
OUT = HERE / "status.json"

# site facts measured in the 4 Oct 2026 study (layers/*.geojson)
FLOOD_SITES = {
    "mokwa":  dict(exposed_builtup_ha=116.7, s1=None),   # WorldCover built-up on HAND<=6 m valley floor
    "osogbo": dict(exposed_builtup_ha=185.8, s1=dict(lon=4.5624, lat=7.7827, r=9000, orbit=95, baseline_ha=0.5)),
}
EROSION_SITES = ["okigwe", "ideato"]
RESERVES = {"Oban Group": "oban", "Omo": "omo", "Okomu": "okomu"}


def now_utc():
    return dt.datetime.now(dt.UTC)


def src_wn3():
    init, counts = wn3.runs()
    series = wn3.fetch(init, max_h=96)
    days = {}
    for k, ser in series.items():
        d = wn3.daily(ser)
        days[k] = [v | {"date": day} for day, v in sorted(d.items()) if v["hours"] == 24][:3]
    return {"time": init, "days": days}


def src_imerg():
    IM = ee.ImageCollection("NASA/GPM_L3/IMERG_V07").select("precipitation")
    last = ee.Date(IM.filterDate(ee.Date(now_utc().isoformat()[:19]).advance(-10, "day"), ee.Date(now_utc().isoformat()[:19]))
                   .aggregate_max("system:time_start"))
    t = last.format("YYYY-MM-dd'T'HH:mm:ss'Z'").getInfo()
    obs = {}
    for k, s in wn3.SITES.items():
        g = ee.Geometry.Point(s["lon"], s["lat"]).buffer(s["r"])
        v = IM.filterDate(last.advance(-7, "day"), last).sum().multiply(0.5).reduceRegion(ee.Reducer.mean(), g, 11132).get("precipitation").getInfo()
        obs[k] = round(v or 0, 1)
    return {"time": t, "last7d_mm": obs}


def src_s1():
    out = {}
    for k, f in FLOOD_SITES.items():
        cfg = f["s1"]
        if not cfg:
            continue
        aoi = ee.Geometry.Point(cfg["lon"], cfg["lat"]).buffer(cfg["r"]).bounds()
        mh = ee.Image("MERIT/Hydro/v1_0_1")
        near = mh.select("upa").gt(50).selfMask().fastDistanceTransform(30).sqrt().multiply(ee.Image.pixelArea().sqrt()).lt(600)
        fp = mh.select("hnd").lte(5).And(near)
        col = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(aoi)
               .filter(ee.Filter.eq("relativeOrbitNumber_start", cfg["orbit"])).sort("system:time_start", False))
        img = ee.Image(col.first())
        t = img.date().format("YYYY-MM-dd'T'HH:mm:ss'Z'").getInfo()
        vv = img.select("VV").focal_median(30, "circle", "meters")
        ha = ee.Number(vv.lt(-18).And(fp).multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(), aoi, 10, maxPixels=1e9).get("VV")).divide(1e4).getInfo()
        out[k] = {"time": t, "water_ha": round(ha, 2), "baseline_ha": cfg["baseline_ha"]}
    return out


def src_radd():
    R = ee.ImageCollection("projects/radar-wur/raddalert/v1").filter(ee.Filter.eq("layer", "alerts"))
    ids = sorted(i for i in R.aggregate_array("system:index").getInfo() if i.startswith("africa_"))
    latest = ids[-1]
    img = R.filter(ee.Filter.eq("system:index", latest)).first()
    d = dt.datetime.strptime(latest.split("_")[1], "%Y%m%d").replace(tzinfo=dt.UTC)
    since = d - dt.timedelta(days=30)
    yydoy = (since.year % 100) * 1000 + since.timetuple().tm_yday
    nf = ee.ImageCollection("projects/nature-trace/assets/forest_typology/natural_forest_2020_v1_0_collection").mosaic().select("B0").gte(130)   # B0 = probability x 250; 130 = 0.52
    new = img.select("Date").gte(yydoy).And(img.select("Alert").gte(2)).And(nf)
    wd = ee.FeatureCollection("WCMC/WDPA/current/polygons").filter(ee.Filter.eq("ISO3", "NGA")).filter(ee.Filter.eq("DESIG_ENG", "Forest Reserve"))
    out = {}
    for name, key in RESERVES.items():
        g = wd.filter(ee.Filter.eq("NAME", name)).geometry()
        ha = ee.Number(new.multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(), g, 10, maxPixels=1e10, tileScale=4).values().get(0)).divide(1e4).getInfo()
        out[key] = round(ha, 1)
    return {"time": d.isoformat().replace("+00:00", "Z"), "image": latest, "new_30d_ha": out}


def run():
    now = now_utc()
    sources, errors = {}, {}
    for name, fn in [("wn3", src_wn3), ("imerg", src_imerg), ("s1", src_s1), ("radd", src_radd)]:
        try:
            sources[name] = fn()
        except Exception as e:  # report, never fill
            errors[name] = f"{type(e).__name__}: {e}"[:300]
            traceback.print_exc()
    wn3_ok = "wn3" in sources and rules.fresh("wn3", sources["wn3"]["time"], now)
    radd_ok = "radd" in sources and rules.fresh("radd", sources["radd"]["time"], now)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    sites = {}

    def put(key, kind, level, why, extra):
        h = rules.apply_hysteresis(state.get(key), level)
        state[key] = h
        sites[key] = {"kind": kind, "level": h["level"], "raw_level": level, "held": h.get("held", False), "why": why} | extra

    for k, f in FLOOD_SITES.items():
        days = sources.get("wn3", {}).get("days", {}).get(k)
        s1 = sources.get("s1", {}).get(k)
        s1_ok = bool(s1) and rules.fresh("s1", s1["time"], now)
        age = rules.age_hours(s1["time"], now) if s1 else None
        lvl, why = rules.flood_level(days, f["exposed_builtup_ha"], s1 and s1["water_ha"], s1 and s1["baseline_ha"], wn3_ok, s1_ok, age)
        put(f"flood:{k}", "flood", lvl, why, {"wn3_days": days, "s1": s1, "s1_fresh": s1_ok})
    for k in EROSION_SITES:
        days = sources.get("wn3", {}).get("days", {}).get(k)
        lvl, why = rules.erosion_level(days, wn3_ok)
        put(f"erosion:{k}", "erosion", lvl, why, {"wn3_days": days})
    for name, k in RESERVES.items():
        ha = sources.get("radd", {}).get("new_30d_ha", {}).get(k)
        lvl, why = rules.forest_level(ha, radd_ok)
        put(f"forest:{k}", "forest", lvl, why, {"new_30d_ha": ha})

    fresh_tbl = {}
    for name in ["wn3", "imerg", "radd"]:
        t = sources.get(name, {}).get("time")
        fresh_tbl[name] = {"time": t, "age_h": None if t is None else round(rules.age_hours(t, now), 1),
                           "fresh": t is not None and rules.fresh(name, t, now), "error": errors.get(name)}
    for k, s1 in sources.get("s1", {}).items():
        fresh_tbl[f"s1:{k}"] = {"time": s1["time"], "age_h": round(rules.age_hours(s1["time"], now), 1), "fresh": rules.fresh("s1", s1["time"], now)}
    if "s1" in errors:
        fresh_tbl["s1"] = {"time": None, "fresh": False, "error": errors["s1"]}
    status = {"run_utc": now.isoformat()[:19] + "Z", "freshness": fresh_tbl, "sites": sites,
              "imerg_last7d_mm": sources.get("imerg", {}).get("last7d_mm"),
              "radd_image": sources.get("radd", {}).get("image"),
              "rules": {"flood": rules.FLOOD, "forest": rules.FOREST, "erosion": rules.EROSION,
                        "downgrade_after_runs": rules.DOWNGRADE_AFTER, "max_age_h": rules.MAX_AGE_H}}
    STATE.write_text(json.dumps(state, indent=1))
    OUT.write_text(json.dumps(status, indent=1))
    return status


if __name__ == "__main__":
    s = run()
    print("run", s["run_utc"])
    for k, v in s["freshness"].items():
        print(f"  {k:12s} fresh={v['fresh']!s:5s} time={v.get('time')} age_h={v.get('age_h')} {('ERR ' + v['error']) if v.get('error') else ''}")
    for k, v in s["sites"].items():
        print(f"  {k:18s} {v['level'].upper():8s} {'; '.join(v['why'])}")
