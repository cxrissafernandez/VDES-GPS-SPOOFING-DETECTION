import pandas as pd
import os
import random
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_scenarios")

def create_scenarios():
    """
    Generates 3 synthetic satellite telemetry CSV files for closed-loop testing.
    Each file mocks what an A*STAR VDES payload log would contain:
    satellite lat/lon at moment of AIS signal reception, paired with MMSI.

    1_all_secure.csv   - satellite near every ship  → all SECURE
    2_all_spoofed.csv  - satellite in Alaska        → all SPOOFED
    3_mixed.csv        - half secure, half spoofed
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    live_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_ship_data.csv")
    if not os.path.exists(live_path):
        raise FileNotFoundError("live_ship_data.csv not found. Run a live scan first.")

    df = pd.read_csv(live_path)
    df.columns = [c.lower().strip() for c in df.columns] 
    df = df.rename(columns={'userid': 'mmsi', 'source_mmsi': 'mmsi', 'latitude': 'lat', 'longitude': 'lon'})
    df = df.drop_duplicates(subset=['mmsi'], keep='last').dropna(subset=['lat', 'lon', 'mmsi'])

    # SCENARIO 1: ALL SECURE 
    rows1 = [{"mmsi": str(r['mmsi']),
              "lat": round(float(r['lat']) + random.uniform(-0.005, 0.005), 6),
              "lon": round(float(r['lon']) + random.uniform(-0.005, 0.005), 6),
              "time_utc": str(r.get('time_utc', datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))} for _, r in df.iterrows()]
    pd.DataFrame(rows1).to_csv(os.path.join(OUTPUT_DIR, "1_all_secure.csv"), index=False)

    # SCENARIO 2: ALL SPOOFED 
    rows2 = [{"mmsi": str(r['mmsi']),
              "lat": round(64.0 + random.uniform(-0.5, 0.5), 6),
              "lon": round(-150.0 + random.uniform(-0.5, 0.5), 6),
              "time_utc": str(r.get('time_utc', datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))} for _, r in df.iterrows()]
    pd.DataFrame(rows2).to_csv(os.path.join(OUTPUT_DIR, "2_all_spoofed.csv"), index=False)

    # SCENARIO 3: MIXED
    rows3 = []
    for i, (_, r) in enumerate(df.iterrows()):
        if i % 2 == 0:
            s_lat = round(float(r['lat']) + random.uniform(-0.005, 0.005), 6)
            s_lon = round(float(r['lon']) + random.uniform(-0.005, 0.005), 6)
        else:
            s_lat = round(64.0  + random.uniform(-0.5, 0.5), 6)
            s_lon = round(-150.0 + random.uniform(-0.5, 0.5), 6)
        rows3.append({"mmsi": str(r['mmsi']), "lat": s_lat, "lon": s_lon,
                      "time_utc": str(r.get('time_utc', datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))})
    pd.DataFrame(rows3).to_csv(os.path.join(OUTPUT_DIR, "3_mixed.csv"), index=False)

    return OUTPUT_DIR