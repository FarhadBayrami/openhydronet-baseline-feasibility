# Environment and Setup Log

Technical log for running Google's OpenHydroNet (`google-research/flood-forecasting`, Apache 2.0) on the Reno at Casalecchio. For the summary and results, see [`README.md`](README.md).

**Status:** stopped at step 5 (static attributes). The data buckets are not accessible to outside accounts. See [Blockers](#blockers).

## Folder Layout

| Path | Purpose |
|---|---|
| `setup_env.bat` | Run once to set up the environment |
| `ENVIRONMENT.md` | This file |
| `env_lock.txt` | `pip freeze` output written by `setup_env.bat` |
| `flood-forecasting/` | Clone of `google-research/flood-forecasting` (git-ignored) |
| `flood-forecasting/.venv/` | Virtual environment created by `setup_env.bat` (git-ignored) |
| `data/raw_hydrosheds/` | HydroSHEDS D8 raster (git-ignored) |
| `data/tiles_5deg/` | HydroSHEDS D8 flow-direction tiles (`.npy`) for delineation (git-ignored) |
| `data/casalecchio/` | Basin-specific outputs (catchment boundary) |

## Setup Log

| Step | Status | Notes |
|---|---|---|
| Write `setup_env.bat` | ✅ done | Clones the repo, creates `.venv`, installs dependencies, freezes versions to `env_lock.txt` |
| Run `setup_env.bat` | ✅ done | Upstream pinned at commit `0112654` |
| Download HydroSHEDS Europe D8 raster | ✅ done | `eu_dir_3s.tif` (~800 MB, HydroSHEDS v1.1 "Europe and Middle East" 3 arc-second DIR layer) in `data/raw_hydrosheds/`; reusable for other basins in the region |
| Install runtime dependencies | ✅ done | `pip install -e .` installs **no** dependencies (`install_requires=[]` in `setup.py`; the repo assumes conda). This showed up as `ModuleNotFoundError: shapely` mid-run. Fixed by pip-installing the package list from `environments/conda.yml`; `setup_env.bat` now does this automatically. |
| Slice raster into 5° × 5° tiles (`scripts/slice_continental_dems.py`) | ✅ done | 108 non-empty tiles in `data/tiles_5deg/` |
| Delineate catchment (`delineate-catchment`, lat 44.483 / lon 11.283) | ✅ done | `data/casalecchio/casalecchio_425.geojson`; area **1,050.1 km²** vs. 1,053 km² reference (0.3 % off) |
| Static attributes (`extract-caravan-static`, HydroATLAS via `gs://open-multimet/...`) | ⛔ blocked | Bucket denies access to outside accounts |
| Meteorological forcing (`gs://caravan-multimet/v1.1`) | ⛔ blocked | Same access restriction |
| Inference with pretrained weights (`run infer`) | ⏸ not reached | Pretrained model and scaler are downloadable from GitHub |

## Blockers

- **`open-multimet` bucket is private.** It holds the HydroATLAS mirror, the ERA5 climate indices and the meteorological forcing. It refused every outside account tested, including authenticated ones, so this is an access restriction and not a local network problem.
- **Four `*_ERA5_LAND` climate static attributes** have no accessible precomputed source.
- **Recomputing them** needs about 40 years of raw hourly ERA5-Land data from the Copernicus Climate Data Store, which is a multi-hour to multi-day download. That is disproportionate for one extra baseline.

## Resuming

To pick this up again, the order would be:

| # | Task |
|---|---|
| 1 | Compute the four `*_ERA5_LAND` climate attributes from Copernicus CDS ERA5-Land |
| 2 | Rebuild HydroATLAS static attributes from the public HydroATLAS release |
| 3 | Build the forcing extract for the basin |
| 4 | Run `run infer` with the pretrained weights |
