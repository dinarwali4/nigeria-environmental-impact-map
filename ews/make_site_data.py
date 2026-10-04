"""Rebuild data/ews.json (read by index.html) from the pipeline outputs in ews/."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
L = lambda n: json.load(open(HERE / n))
status, wn, ver, osg, bt = L("status.json"), L("wn3_latest.json"), L("wn3_verification.json"), L("wn3_osogbo_test.json"), L("backtest_summary.json")
clim = defaultdict(list)
for r in ver: clim[r["site"]].append(r["obs"])
clim = {k: st.mean(v) for k, v in clim.items()}
vs = []
for lead in (1, 2, 3):
    R = [r for r in ver if r["lead"] == lead]
    ev, non = [r for r in R if r["obs"] >= 20], [r for r in R if r["obs"] < 20]
    vs.append(dict(lead=lead, n=len(R),
        mae_wn3=round(st.mean(abs(r["fc"] - r["obs"]) for r in R), 1),
        mae_wn3_imerg=round(st.mean(abs(r["fc_imerg"] - r["obs"]) for r in R), 1),
        mae_clim=round(st.mean(abs(clim[r["site"]] - r["obs"]) for r in R), 1),
        heavy_days=len(ev), non_heavy=len(non),
        warn_hits=sum(r["fc_imerg"] >= 20 for r in ev), warn_fa=sum(r["fc_imerg"] >= 20 for r in non),
        watch_hits=sum(r["hi_env"] >= 40 for r in ev), watch_fa=sum(r["hi_env"] >= 40 for r in non)))
# Published skill of Google's flood model at Nigerian GRDC gauges (Nearing et al. 2024, Zenodo 10397664, 1980-2021 hindcast)
fh = [("Hadejia at Wudil", 1837410, 0.42, 0.07, 0.42, 0.55), ("Jamaare at Katagum", 1837250, 0.15, 0.08, 0.15, 0.48),
      ("Jamaare at Bunga", 1837255, 0.02, 0.23, -0.20, 0.57), ("Kano at Chiromawa", 1837430, -0.19, 0.12, -0.15, 0.40),
      ("Challawa Gorge (dam)", 1837451, -0.69, -0.89, -0.01, -0.07), ("Kano at Tiga Dam", 1837431, -4.85, -11.79, -0.39, -1.39),
      ("Komadugu Gana at Dapchi", 1837200, -274.68, -1.04, -13.92, 0.21)]
fh = [dict(gauge=g, grdc=n, google_nse=a, glofas_nse=b, google_kge=c, glofas_kge=d) for g, n, a, b, c, d in fh]
out = dict(status=status,
           wn3={"init": wn["init"], "sites": {k: {"name": v["name"], "daily": [dict(date=d, **x) for d, x in sorted(v["daily"].items()) if x["hours"] == 24]} for k, v in wn["sites"].items()}},
           verification=vs, osogbo=osg, backtest=bt, floodhub=fh)
(HERE.parent / "data" / "ews.json").write_text(json.dumps(out, indent=1))
print("wrote data/ews.json")
