import csv
import math
import requests
from datetime import datetime, timezone

# --- CONFIGURATION ---
N2YO_API_KEY = "YOUR_N2YO_API_KEY_HERE"
SAT_ID = 58997  # YMIR-1 
THRESHOLD_KM = 50.0   # can be changed depending on operator needs

# File paths for standalone mode
LIVE_API_FILE = "live_ship_data.csv"
SATELLITE_FILE = "demo_sats_frozen.csv" 
OUTPUT_FILE = "final_validation_report.csv"

def calculate_haversine(lat1, lon1, lat2, lon2):
    """Mathematical model for checking"""
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def fetch_single_sat_position(observer_lat, observer_lon):
    """
    Fetches real-time telemetry from N2YO.
    Provides the 'Current Witness' position.
    """
    url = f"https://api.n2yo.com/rest/v1/satellite/positions/{SAT_ID}/{observer_lat}/{observer_lon}/0/1/&apiKey={N2YO_API_KEY}"
    try:
        response = requests.get(url, timeout=5).json()
        if 'positions' in response and len(response['positions']) > 0:
            pos = response['positions'][0]
            # provides the timestamp needed for the UTC Cross-Check
            pos['time_utc'] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return pos
    except Exception as e:
        print(f"API Error in validator: {e}")
    return None

def run_validation():
    """Standalone batch validator. Cross-checks AIS claims vs Satellite Witness logs."""
    print("--- STARTING TIME-SPACE CROSS-CHECK (LAYER 2) ---")
    
    api_data = {}
    try:
        with open(LIVE_API_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                api_data[row['mmsi']] = row
    except FileNotFoundError:
        print(f"Error: {LIVE_API_FILE} not found.")
        return

    with open(SATELLITE_FILE, 'r') as infile, open(OUTPUT_FILE, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        
        # Ensure 'time_utc' is in the fieldnames so it carries through to the Web App
        new_fields = ['api_lat', 'api_lon', 'diff_km', 'status']
        fieldnames = reader.fieldnames + [f for f in new_fields if f not in reader.fieldnames]
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            mmsi = row['mmsi']
            if mmsi in api_data:
                api_ship = api_data[mmsi]
                
                # Handle 'lat' vs 'latitude' naming from different data sources
                sat_lat_val = row.get('latitude') or row.get('lat')
                sat_lon_val = row.get('longitude') or row.get('lon')
                
                if sat_lat_val and sat_lon_val:
                    sat_lat = float(sat_lat_val)
                    sat_lon = float(sat_lon_val)
                    
                    if row.get('lat_hemisphere') == 'S': sat_lat = -abs(sat_lat)
                    if row.get('lon_hemisphere') == 'W': sat_lon = -abs(sat_lon)
                    
                    dist = calculate_haversine(sat_lat, sat_lon, float(api_ship['lat']), float(api_ship['lon']))
                    
                    row.update({
                        'api_lat': api_ship['lat'], 
                        'api_lon': api_ship['lon'], 
                        'diff_km': round(dist, 2), 
                        # Flag as SPOOFED if distance exceeds the 50 km threshold
                        'status': "SPOOFED" if dist > THRESHOLD_KM else "SECURE"
                    })
                writer.writerow(row)
    print("Batch validation complete. Report saved to final_validation_report.csv")

if __name__ == "__main__":
    run_validation()