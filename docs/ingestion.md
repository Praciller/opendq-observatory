# Ingestion

The CLI is run from the repository root through the pipeline virtual environment:

```powershell
pipeline/.venv/Scripts/python.exe -m opendq migrate
pipeline/.venv/Scripts/python.exe -m opendq ingest open-meteo
pipeline/.venv/Scripts/python.exe -m opendq ingest usgs
pipeline/.venv/Scripts/python.exe -m opendq ingest all
```

Each run is inserted before source processing and always finalized with `SUCCESS`, `PARTIAL`, `FAILED`, or `NO_CHANGE`. `ingest all` attempts both adapters, prints one outcome per source, and exits non-zero if any source fails.

Open-Meteo uses a fixed Bangkok latitude/longitude and requests a compact hourly window. USGS uses the official all-day GeoJSON summary feed and stores the GeoJSON feature ID as the canonical event identity. Invalid records are rejected and counted; failures are classified with a small explicit taxonomy.

