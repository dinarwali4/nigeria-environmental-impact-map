# Nigeria Environmental Impact Map & Early Warning System

**Live site:** https://dinarwali4.github.io/nigeria-environmental-impact-map/

A satellite-verified risk map of Nigeria with three layers, plus a tested early-warning pipeline:

| Layer | Sites | Main evidence |
|---|---|---|
| 1 · Flash floods | Mokwa, Niger State (28–29 May 2025) · Osogbo, Osun State (29 Sep 2026) | Sentinel-2 flood scour, Sentinel-1 radar water, NASA GPM IMERG rainfall, Google Groundsource, Google Earth Pro VHR before/after |
| 2 · Gully erosion | Imo State: Obodo (Ideato North), Okigwe escarpment, brief point Obolo (Isiala Mbano) | Copernicus DEM incision + Sentinel-2 bare soil screen, VHR verification, NASA EMIT |
| 3 · Canopy loss | Oban (Cross River), Omo (Ogun), Okomu (Edo) forest reserves | UMD Hansen GFC v1.13, WUR RADD radar alerts, natural-forest and oil-palm masks, WDPA |

Designed by **Mr. Dinar Wali**, Geospatial Computational Researcher, [RegenX.eco](https://regenx.eco) ·
dinar.wali@regenx.eco · [LinkedIn](https://www.linkedin.com/in/dinar-wali-621954102/)

## Key findings (analysis of 4 Oct 2026)

- **Mokwa:** satellite rain was at most 34 mm in 48 h, below the annual-maximum day of every year 2001–2024
  (29–102 mm). Flood scour (78.3 ha) runs to the railway embankment; 26.5 ha of riparian woodland was cleared two
  months earlier. Infrastructure failure, not record rain, made it deadly.
- **Osogbo:** radar showed the Osun River out of its channel the day before the reported flood
  (6.5 ha open water vs under 1 ha normally). 186 ha of built-up land sits on the ≤3 m floodplain.
- **Imo:** no active gully near the brief coordinate; active gullies 28–30 km away, one growing from 9.5 ha (2016)
  to 26.0 ha (2024).
- **Forests:** natural-forest loss inside the Oban reserve rose from 592 ha (2011–15) to 7,619 ha (2021–25); a
  4.2 km road was cut into it in 2025–26; a 163 ha block was cleared inside Okomu reserve in 2025.

## Early warning: how reliable is it?

| Test | Result |
|---|---|
| Rain-only trigger, 700 Groundsource floods vs 2,100 control days | AUC **0.59**: rain alone is a weak trigger, so it may only raise a *Watch* |
| WeatherNext 3 vs IMERG, 6 sites, 20 Sep–2 Oct 2026 | Day-1 error 5.6 mm vs 8.6 mm for climatology; little skill by day 2–3 |
| Warning rule (≥20 mm next 24 h) | 16/23 heavy-rain days caught, 9/115 false alarms |
| Osogbo, 28 Sep 2026 (48 mm observed) | WN3 mean 24 mm at 1–2 days; upper envelope 48 mm already 6 days ahead |
| Google flood model, published Nigeria skill | Positive NSE at 2 of 7 northern gauges; none near these sites |

Rules (`ews/rules.py`): **Watch** = WN3 upper envelope ≥40 mm within 3 days · **Warning** = ≥20 mm next 24 h on a
site with built-up floodplain · **Alert** = radar open water ≥3× baseline, image <72 h old. Levels rise at once
and drop after two quieter runs; stale sources are flagged and never used.

**Google Flood Hub:** live forecasts require approval through Google's Flood Forecasting API pilot. Until then the
page shows the model's published skill scores only.

## Repository

```
index.html, data/, img/, s2_*.jpg   static site (GitHub Pages)
ews/                                 early-warning pipeline, rules, tests, latest results
gis/                                 GeoJSON layers, KML for Google Earth, forest statistics
analysis/                            research scripts as run for the study
```

## Run it

```bash
pip install -r requirements.txt
earthengine authenticate
export GOOGLE_CLOUD_PROJECT=<your-earth-engine-project>
python ews/wn3.py && python ews/pipeline.py && python ews/make_site_data.py
python -m pytest -q ews/test_ews.py
```

The `ews-run` GitHub workflow runs this daily once two repository secrets are set:
`EE_SERVICE_ACCOUNT_KEY` (a service account registered for Earth Engine) and `GOOGLE_CLOUD_PROJECT`.

## Limits

Osogbo has no post-flood image yet; the Mokwa path through the roofed town core is inferred; IMERG is a 10 km
product; gully areas come from colour thresholds on two sensors; RADD alerts lag cutting by 2–6 weeks and include
degradation; WeatherNext 3 publishes percentiles, not members, so daily "envelopes" are wider than the true spread;
the WN3 verification covers two weeks only.

## Licence

Code MIT. Derived layers CC BY 4.0 (attribution: Dinar Wali, RegenX.eco). Source data keep their own licences.
VHR imagery © Airbus, Maxar Technologies, CNES via Google Earth Pro. See `LICENSE`.
