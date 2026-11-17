@echo off
rem ============================================================
rem  OpenHydroNet (Google flood-forecasting) - environment setup
rem  Run this once from C:\Work\OpenHydroNet by double-clicking it,
rem  or from a cmd prompt opened in this folder.
rem ============================================================
setlocal
cd /d "%~dp0"

echo === OpenHydroNet environment setup ===
echo Working folder: %cd%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git not found on PATH. Install Git for Windows, then re-run this script.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python not found on PATH.
    pause
    exit /b 1
)

if not exist "flood-forecasting" (
    echo Cloning google-research/flood-forecasting ...
    git clone https://github.com/google-research/flood-forecasting
    if errorlevel 1 (
        echo ERROR: git clone failed. Check your internet connection and re-run.
        pause
        exit /b 1
    )
) else (
    echo flood-forecasting already cloned - skipping clone.
)

cd flood-forecasting

if not exist ".venv" (
    echo Creating virtual environment .venv ...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo.
echo Upgrading pip ...
python -m pip install --upgrade pip

echo.
echo Installing googlehydrology (editable) ...
pip install -e .
if errorlevel 1 (
    echo ERROR: "pip install -e ." failed - see the error above and fix before continuing.
    pause
    exit /b 1
)

echo.
echo NOTE: this repo's "pip install -e ." pulls in NO dependencies on its own
echo (install_requires is empty - it assumes you use the conda env file instead).
echo So install everything from environments\conda.yml by hand, via pip:
echo Installing runtime dependencies ...
pip install numpy pandas torch scipy xarray zarr dask h5py h5netcdf netcdf4 geopandas shapely pyproj pyogrio gcsfs rasterio google-cloud-storage pydantic ruamel.yaml tqdm more-itertools cachey pyarrow absl-py matplotlib seaborn bokeh
if errorlevel 1 (
    echo WARNING: one or more packages failed to install. rasterio/geopandas/pyproj
    echo sometimes need prebuilt wheels on Windows - if they keep failing, install
    echo just those via conda instead:
    echo     conda install -c conda-forge rasterio geopandas shapely pyproj pyogrio
    echo and then re-run this script ^(it will skip the clone/venv steps that worked^).
)

echo.
echo Freezing installed package versions for the record ...
pip freeze > ..\env_lock.txt

if not exist "..\data" mkdir "..\data"
if not exist "..\data\tiles_5deg" mkdir "..\data\tiles_5deg"
if not exist "..\data\casalecchio" mkdir "..\data\casalecchio"

echo.
echo === Done ===
echo Environment:      %cd%\.venv
echo Package versions: %cd%\..\env_lock.txt
echo Working data dir: %cd%\..\data
echo Tracking doc:      C:\Work\OpenHydroNet\ENVIRONMENT.md  (open and update as you go)
echo.
echo Next: activate it in any new cmd window with:
echo     C:\Work\OpenHydroNet\flood-forecasting\.venv\Scripts\activate.bat
pause
