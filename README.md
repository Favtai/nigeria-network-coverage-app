# Spectrum — National Coverage Verifier

> Verifies mobile network coverage (2G/3G/4G) for coordinates across Nigeria.

Project structure
- `app.py` — Streamlit application UI and geospatial logic
- `buffered_towers.gpkg` — coverage geometries (GeoPackage layer `buffered_towers`)
- `gadm41_NGA_1.geojson` — Nigerian administrative boundaries
- `requirements.txt` — Python dependencies

Quickstart

1. Create and activate a virtual environment (Windows CMD):

```bash
python -m venv venv
venv\Scripts\activate.bat
```

Or PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Upgrade pip and install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Run the app with Streamlit:

```bash
streamlit run app.py
```

Notes
- The app expects `buffered_towers.gpkg` and `gadm41_NGA_1.geojson` to be present in the project root.
- If data files are large, Streamlit may take a few seconds to initialize.


Development tips
- Use the `st.cache_data` decorator to speed repeated data loads while developing.
- If you change geospatial files, ensure they use `EPSG:4326` or the app will reproject them.

Contact
- Made by Group B for the GIC competition. Maintainer: Favour Taiwo — https://www.linkedin.com/in/favour-taiwo-57232023a/

License
- Check with the dataset providers for redistribution terms. Code here is provided for demonstration.
