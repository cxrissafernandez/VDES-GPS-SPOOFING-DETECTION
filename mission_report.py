import pandas as pd
import time
import requests
import os
from datetime import datetime, timezone
import data_collector

API_KEY = "YOUR_N2YO_API_KEY_HERE"
SAT_ID  = 58997  # YMIR-1 (AAC-AIS-SAT3)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SHIP_FILENAME = os.path.join(BASE_DIR, "demo_ships_frozen.csv")
SAT_FILENAME  = os.path.join(BASE_DIR, "demo_sats_frozen.csv")

def get_sat_position(lat, lon):
    url = f"https://api.n2yo.com/rest/v1/satellite/positions/{SAT_ID}/{lat}/{lon}/0/1/&apiKey={API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if 'positions' in r and r['positions']:
            return r['positions'][0]
    except Exception as e:
        print(f"   [!] API warning: {e}")
    return None

def run_mission():
    print("=" * 55)
    print("  VDES-SAT MISSION REPORT - FROZEN DATA COLLECTOR")
    print("=" * 55)

    # --- STEP 1: Collect live AIS ship data ---
    print("\n[1/2] Scanning AIS stream for 60 seconds...")
    data_collector.run_collector(60)

    live_path = os.path.join(BASE_DIR, "live_ship_data.csv")
    try:
        df = pd.read_csv(live_path)
        df.columns = [c.lower().strip() for c in df.columns]
        df = df.rename(columns={'userid': 'mmsi', 'latitude': 'lat', 'longitude': 'lon'})
        df = df.drop_duplicates(subset=['mmsi'], keep='last').dropna(subset=['lat', 'lon', 'mmsi'])
        print(f"    ✅ Captured {len(df)} vessels.")
    except FileNotFoundError:
        print("    ❌ Ship scan failed - live_ship_data.csv not found.")
        return

    # --- STEP 2: Fetch satellite position for each ship ---
    print(f"\n[2/2] Fetching YMIR-1 (ID: {SAT_ID}) position per ship...")
    sat_log = []
    for _, row in df.iterrows():
        mmsi = str(row['mmsi'])
        sat_pos = get_sat_position(row['lat'], row['lon'])
        if sat_pos:
            sat_log.append({
                "mmsi":     mmsi,
                "lat":      sat_pos['satlatitude'],
                "lon":      sat_pos['satlongitude'],
                "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })
            print(f"    -> synced satellite for MMSI {mmsi}")
            time.sleep(0.2)  # respect N2YO rate limit
        else:
            print(f"    [x] could not fetch for MMSI {mmsi}")

    if not sat_log:
        print("\n❌ Satellite sync failed. Check internet connection and N2YO API key.")
        return

    # --- SAVE ---
    df.to_csv(SHIP_FILENAME, index=False)
    pd.DataFrame(sat_log).to_csv(SAT_FILENAME, index=False)

    print("\n" + "=" * 55)
    print("✅ MISSION COMPLETE - Files saved:")
    print(f"   Ship data:      {os.path.basename(SHIP_FILENAME)}")
    print(f"   Satellite data: {os.path.basename(SAT_FILENAME)}")
    print("=" * 55)
    print("\nDemo instructions (Upload File mode):")
    print(f"   Input 1 (AIS Ship Data):     {os.path.basename(SHIP_FILENAME)}")
    print(f"   Input 2 (Payload Telemetry): {os.path.basename(SAT_FILENAME)}")
    print("=" * 55)

if __name__ == "__main__":
    run_mission()