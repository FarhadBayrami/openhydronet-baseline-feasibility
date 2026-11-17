# OpenHydroNet Baseline Feasibility — Reno at Casalecchio

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![Status](https://img.shields.io/badge/Status-Stopped%20(data%20access)-orange.svg)

A feasibility study: can Google's open-sourced flood-forecasting model, **OpenHydroNet** ([`google-research/flood-forecasting`](https://github.com/google-research/flood-forecasting)), be run as an external baseline on an Italian basin (the Reno river at Casalecchio di Reno) by someone outside Google?

**Short answer:** catchment delineation works and is accurate, but inference is blocked. The static attributes and meteorological forcing the model needs are served from Google Cloud Storage buckets that deny access to outside accounts.

> This repository does **not** contain OpenHydroNet's code. It holds only my setup script, notes and the delineated catchment. OpenHydroNet belongs to Google Research and is licensed under Apache 2.0.

---

## Table of Contents

- [Results](#results)
- [Pipeline and Status](#pipeline-and-status)
- [Why It Stopped](#why-it-stopped)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Lessons Learned](#lessons-learned)
- [Future Work](#future-work)
- [Credits and Licensing](#credits-and-licensing)
- [References](#references)
- [Author](#author)

---

## Results

| Item | Value |
|---|---|
| Outlet (lat / lon) | 44.483 / 11.283 |
| Flow-direction data | HydroSHEDS v1.1, Europe & Middle East, 3 arc-second D8 (`eu_dir_3s`) |
| Tiling | 108 non-empty 5° × 5° tiles |
| Delineated catchment area | **1,050.1 km²** |
| Reference area | 1,053 km² |
| Relative error | **0.3 %** |
| Output | [`data/casalecchio/casalecchio_425.geojson`](data/casalecchio/casalecchio_425.geojson) |

The outlet snapped cleanly to the river network. The 0.3 % area error means the polygon can be used as-is for extracting basin attributes.

---

## Pipeline and Status

| # | Step | Tool | Status |
|---|---|---|---|
| 1 | Clone repo, create venv, install dependencies | `setup_env.bat` | ✅ Done (upstream pinned at commit `0112654`) |
| 2 | Download HydroSHEDS Europe D8 raster (~800 MB) | manual | ✅ Done |
| 3 | Slice raster into 5° tiles | `scripts/slice_continental_dems.py` | ✅ Done |
| 4 | Delineate catchment | `delineate-catchment` | ✅ Done |
| 5 | Extract static attributes (HydroATLAS + ERA5-Land climate indices) | `extract-caravan-static` | ⛔ Blocked |
| 6 | Fetch meteorological forcing | `gs://caravan-multimet/v1.1` | ⛔ Blocked |
| 7 | Inference with pretrained weights | `run infer` | ⏸ Not reached (weights are available) |

---

## Why It Stopped

| Blocker | Detail |
|---|---|
| Private data bucket | `extract-caravan-static` streams HydroATLAS attributes and ERA5-Land climate indices from Google's `open-multimet` bucket. In my tests it refused every outside account, including authenticated ones, so the failure was an access restriction rather than a local network problem. |
| No public substitute for 4 attributes | The four `*_ERA5_LAND` climate static attributes have no accessible precomputed source. |
| Cost of recomputing | Rebuilding them means pulling about 40 years of hourly ERA5-Land data from the Copernicus Climate Data Store, which takes hours to days. That was out of proportion for a single extra baseline. |

**Takeaway:** for basins that aren't already in Google's prepared datasets, the published model weights are not enough to reproduce OpenHydroNet forecasts from outside Google. The data pipeline is the bottleneck.

---

## Getting Started

**Requirements:** Windows, Git, Python on `PATH`, about 5 GB of free disk space.

| Step | Action |
|---|---|
| 1 | Clone this repository |
| 2 | Run `setup_env.bat` from the repo root. It clones `google-research/flood-forecasting` into `flood-forecasting/`, creates `.venv`, installs dependencies and writes `env_lock.txt`. |
| 3 | Download the HydroSHEDS v1.1 Europe & Middle East 3s DIR layer to `data/raw_hydrosheds/` |
| 4 | Follow [`ENVIRONMENT.md`](ENVIRONMENT.md) for the tiling and delineation commands |

`pip install -e .` on the upstream repo installs **no** dependencies (`install_requires=[]`, because it expects conda). `setup_env.bat` installs the full dependency list from `environments/conda.yml` with pip instead.

---

## Project Structure

| Path | Description | In this repo |
|---|---|---|
| `setup_env.bat` | One-shot environment setup for Windows | ✅ |
| `env_lock.txt` | `pip freeze` of the working environment | ✅ |
| `ENVIRONMENT.md` | Step-by-step setup log and technical notes | ✅ |
| `data/casalecchio/casalecchio_425.geojson` | Delineated catchment polygon | ✅ |
| `flood-forecasting/` | Upstream clone, created by `setup_env.bat` | ❌ git-ignored |
| `data/raw_hydrosheds/` | HydroSHEDS raster (~800 MB) | ❌ git-ignored |
| `data/tiles_5deg/` | Sliced D8 tiles (~3.9 GB) | ❌ git-ignored |

---

## Lessons Learned

- Before committing to a pretrained model, check that you can get its **input data**. Having the weights is not the hard part.
- Pip-only installs of research repos that assume conda fail silently until runtime (here: `ModuleNotFoundError: shapely`).
- HydroSHEDS 3s D8 delineation gives an area within a fraction of a percent of the reference for a ~1,000 km² Apennine basin.

---

## Future Work

- [ ] Compute the four `*_ERA5_LAND` climate attributes locally from Copernicus CDS
- [ ] Rebuild the HydroATLAS static attributes from public HydroATLAS downloads
- [ ] Assemble forcing from ERA5-Land and run `run infer` with the pretrained weights
- [ ] Compare against basin-specific models for the same gauge

---

## Credits and Licensing

| Component | Owner | License |
|---|---|---|
| OpenHydroNet / `googlehydrology` (not included) | Google Research | Apache 2.0 |
| NeuralHydrology (upstream of OpenHydroNet) | NeuralHydrology developers | BSD-3-Clause |
| HydroSHEDS flow-direction data (used to derive the GeoJSON) | WWF / HydroSHEDS | HydroSHEDS License |
| Setup script, notes, catchment output | Farhad Bayrami | MIT (see [`LICENSE`](LICENSE)) |

This is an independent project. It is not affiliated with or endorsed by Google.

---

## References

1. Nearing, G. et al. (2024). *Global prediction of extreme floods in ungauged watersheds.* Nature. https://www.nature.com/articles/s41586-024-07145-1
2. Gauch, M. et al. (2025). *How to deal with missing input data.* Hydrology and Earth System Sciences, 29, 6221. https://hess.copernicus.org/articles/29/6221/2025/
3. Kratzert, F. et al. (2022). *NeuralHydrology — A Python library for Deep Learning research in hydrology.* Journal of Open Source Software, 7(71), 4050.
4. Lehner, B., Verdin, K., Jarvis, A. (2008). *New global hydrography derived from spaceborne elevation data.* Eos, 89(10), 93–94.
5. Google Research — flood-forecasting repository: https://github.com/google-research/flood-forecasting

---

## Author

**Farhad Bayrami** — ML Engineer, MSc in Artificial Intelligence (University of Bologna)

[GitHub](https://github.com/FarhadBayrami) · [ORCID](https://orcid.org/0009-0001-5786-3363)
