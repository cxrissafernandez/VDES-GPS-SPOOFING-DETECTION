import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math
import requests
import os
from datetime import datetime, timezone

import decoder
from validator import calculate_haversine, fetch_single_sat_position

# --- CONFIGURATION ---
N2YO_API_KEY = "YOUR_N2YO_API_KEY_HERE"
SAT_ID = 58997  # YMIR-1 (AAC-AIS-SAT3)
SPOOF_THRESHOLD_KM = 50
LIVE_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_ship_data.csv")

# --- PAGE CONFIG ---
st.set_page_config(page_title="VDES-SAT Detection System", layout="wide")
st.title("⚓ VDES-SAT: GPS Spoofing Detection System")
st.markdown("---")

# --- HELPERS ---
def clean_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = [str(c).lower().strip() for c in df.columns]
    rename_map = {'latitude': 'lat', 'longitude': 'lon', 'userid': 'mmsi', 'source_mmsi': 'mmsi'}
    df = df.rename(columns=rename_map)
    if not all(col in df.columns for col in ['lat', 'lon']):
        return pd.DataFrame()
    try:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        if 'mmsi' in df.columns:
            df['mmsi'] = df['mmsi'].astype(str).str.replace(r'\.0$', '', regex=True)
        df = df.dropna(subset=['lat', 'lon'])
        if 'time_utc' not in df.columns:
            df['time_utc'] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return pd.DataFrame()
    return df

def parse_uploaded_file(uploaded_file):
    """Smart two-step parser: CSV first, then NMEA decode."""
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)
        df.columns = [str(c).lower().strip() for c in df.columns]
        df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon', 'userid': 'mmsi', 'source_mmsi': 'mmsi'})
        if 'lat' in df.columns and 'lon' in df.columns:
            return df
    except:
        pass
    uploaded_file.seek(0)
    try:
        return decoder.parse_nmea_file(uploaded_file)
    except Exception as e:
        st.error(f"File Error: {e}")
        return pd.DataFrame()

# --- SESSION STATE ---
if 'ais_data' not in st.session_state: st.session_state['ais_data'] = None
if 'sat_data' not in st.session_state: st.session_state['sat_data'] = None

# --- SIDEBAR ---
st.sidebar.header("CONTROL PANEL")

# --- INPUT 1: AIS SHIP DATA ---
st.sidebar.subheader("1. AIS Ship Data")
input_mode = st.sidebar.radio("Source:", ("Live Stream", "Upload File"), label_visibility="collapsed")

if input_mode == "Live Stream":
    scan_duration = st.sidebar.slider("Scan Duration (sec)", 30, 120, 60)
    if st.sidebar.button("🔴 START LIVE SCAN"):
        try:
            with st.spinner("Scanning AIS Frequencies..."):
                import data_collector
                data_collector.run_collector(scan_duration)
                df = pd.read_csv(LIVE_DATA_PATH)
                cleaned = clean_dataframe(df).drop_duplicates(subset=['mmsi'], keep='last')
                if cleaned.empty:
                    st.sidebar.warning("⚠️ No ships received. Try longer scan or check API key.")
                else:
                    st.session_state['ais_data'] = cleaned
                    st.sidebar.info(f"✅ Loaded {len(cleaned)} ships.")
        except ConnectionError as e:
            st.sidebar.error(f"🌐 Network Error: {e}")
            st.sidebar.info("💡 Try a mobile hotspot or use Upload File mode.")
        except Exception as e:
            st.sidebar.error(f"Scan Failed: {e}")
else:
    ship_file = st.sidebar.file_uploader("Upload AIS Data", type=["csv", "txt", "log"], key="ship_up")
    if ship_file:
        df = parse_uploaded_file(ship_file)
        cleaned = clean_dataframe(df).drop_duplicates(subset=['mmsi'], keep='last')
        if cleaned.empty:
            st.sidebar.warning("⚠️ No valid data found. File needs mmsi, lat, lon columns.")
        else:
            st.session_state['ais_data'] = cleaned
            st.sidebar.info(f"✅ Loaded {len(cleaned)} ships.")

st.sidebar.markdown("---")

# --- INPUT 2: PAYLOAD TELEMETRY ---
st.sidebar.subheader("2. Payload Telemetry")
st.sidebar.caption("Satellite position - the cross-validation reference")

use_demo = st.sidebar.toggle("🛠️ Enable Simulation Mode")

if use_demo:
    demo_mode = st.sidebar.radio(
        "Simulation Scenario:",
        ("✅ All Secure", "🔴 All Spoofed", "🕵️ Mixed")
    )
    if st.sidebar.button("EXECUTE DEMO SCENARIO"):
        if st.session_state['ais_data'] is not None and not st.session_state['ais_data'].empty:
            with st.spinner("Simulating satellite pass..."):
                ships = st.session_state['ais_data'].copy()
                sat_log = []
                for i, (_, row) in enumerate(ships.iterrows()):
                    mmsi_str = str(row['mmsi'])
                    ship_lat, ship_lon = row['lat'], row['lon']

                    # SCENARIO 1: All Secure
                    # Satellite at each ship's reported position → distance ≈ 0 → all SECURE
                    if demo_mode == "✅ All Secure":
                        s_lat, s_lon = ship_lat, ship_lon

                    # SCENARIO 2: All Spoofed
                    # Satellite in Alaska → all Singapore ships ~12,000km away → all SPOOFED
                    elif demo_mode == "🔴 All Spoofed":
                        s_lat, s_lon = 64.0, -150.0

                    # SCENARIO 3: Mixed
                    # Even index → satellite near ship (SECURE)
                    # Odd index  → satellite in Alaska (SPOOFED)
                    else:
                        if i % 2 == 0:
                            s_lat, s_lon = ship_lat, ship_lon
                        else:
                            s_lat, s_lon = 64.0, -150.0

                    sat_log.append({
                        "mmsi": mmsi_str, "sat_lat": s_lat, "sat_lon": s_lon,
                        "time_utc": str(row.get("time_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
                    })
                st.session_state['sat_data'] = pd.DataFrame(sat_log)
                st.rerun()
        else:
            st.sidebar.warning("⚠️ Load AIS ship data first.")

else:
    sat_source = st.sidebar.radio(
        "Telemetry Source:",
        ("📡 Live N2YO API", "📂 Upload Payload CSV"),
        label_visibility="collapsed"
    )

    if sat_source == "📡 Live N2YO API":
        if st.sidebar.button("CONNECT TO SATELLITE"):
            if st.session_state['ais_data'] is not None and not st.session_state['ais_data'].empty:
                with st.spinner("Fetching YMIR-1 position..."):
                    first_ship = st.session_state['ais_data'].iloc[0]
                    pos = fetch_single_sat_position(first_ship['lat'], first_ship['lon'])
                    if pos:
                        sat_log = [{
                            "mmsi": str(r['mmsi']),
                            "sat_lat": pos['satlatitude'],
                            "sat_lon": pos['satlongitude'],
                            "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        } for _, r in st.session_state['ais_data'].iterrows()]
                        st.session_state['sat_data'] = pd.DataFrame(sat_log)
                        st.sidebar.info(f"✅ Linked to YMIR-1 (ID: {SAT_ID})")
                    else:
                        st.sidebar.error("Could not fetch satellite position. Check N2YO API key.")
            else:
                st.sidebar.warning("⚠️ Load AIS ship data first.")

    else:
        st.sidebar.caption("Expected columns: lat, lon, time_utc, (optional) mmsi")
        payload_file = st.sidebar.file_uploader(
            "Upload Payload Telemetry CSV", type=["csv", "txt", "log"], key="sat_up"
        )
        if payload_file and st.sidebar.button("LOAD PAYLOAD"):
            df_sat = parse_uploaded_file(payload_file)
            df_sat = clean_dataframe(df_sat)
            if df_sat.empty:
                st.sidebar.error("Could not parse payload file. Check lat and lon columns.")
            else:
                df_sat = df_sat.rename(columns={'lat': 'sat_lat', 'lon': 'sat_lon'})
                if 'mmsi' in df_sat.columns:
                    # Per-ship matching - mocks inteded A*STAR payload log after implementation (MMSI co-logged per message)
                    st.session_state['sat_data'] = df_sat[['mmsi', 'sat_lat', 'sat_lon', 'time_utc']].copy()
                    st.sidebar.info(f"✅ Loaded {len(df_sat)} payload entries. Matching by MMSI.")
                else:
                    # No MMSI - broadcast single satellite position to all ships
                    if st.session_state['ais_data'] is not None and not st.session_state['ais_data'].empty:
                        first = df_sat.iloc[0]
                        sat_log = [{
                            "mmsi": str(r['mmsi']),
                            "sat_lat": first['sat_lat'], "sat_lon": first['sat_lon'],
                            "time_utc": first.get('time_utc', datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
                        } for _, r in st.session_state['ais_data'].iterrows()]
                        st.session_state['sat_data'] = pd.DataFrame(sat_log)
                        st.sidebar.info("✅ No MMSI column - satellite position applied to all ships.")
                    else:
                        st.sidebar.warning("⚠️ Load AIS ship data first, then reload payload.")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 GENERATE TEST SCENARIOS"):
    import scenario_builder
    folder = scenario_builder.create_scenarios()
    st.sidebar.success(f"Generated in: `{folder}`")

# --- ANALYSIS ENGINE ---
results = []
spoofed_count = secure_count = stale_count = 0
status_label = "WAITING"

ais_ok = st.session_state['ais_data'] is not None and not st.session_state['ais_data'].empty
sat_ok = st.session_state['sat_data'] is not None and not st.session_state['sat_data'].empty

if ais_ok and sat_ok:
    with st.spinner("🔍 Verifying ship positions against satellite telemetry..."):
        ais_lookup = st.session_state['ais_data'].set_index('mmsi').to_dict('index')
        sat_df = st.session_state['sat_data']

    for _, sat_row in sat_df.iterrows():
        mmsi = str(sat_row['mmsi']).replace('.0', '')
        if mmsi not in ais_lookup:
            continue
        try:
            ship = ais_lookup[mmsi]
            ship_lat = float(ship['lat'])
            ship_lon = float(ship['lon'])
            sat_lat  = float(sat_row['sat_lat'])
            sat_lon  = float(sat_row['sat_lon'])

            # UTC staleness check
            ship_time_raw = ship.get('time_utc', 'N/A')
            sat_time_raw  = sat_row.get('time_utc', 'N/A')
            time_diff_secs = 0
            is_stale = False
            if ship_time_raw != 'N/A' and sat_time_raw != 'N/A':
                try:
                    t_diff = abs((pd.to_datetime(sat_time_raw) - pd.to_datetime(ship_time_raw)).total_seconds())
                    time_diff_secs = t_diff
                    if t_diff > 300:
                        is_stale = True
                except:
                    pass

            # Distance check
            dist_km = calculate_haversine(ship_lat, ship_lon, sat_lat, sat_lon)
            is_spoofed = dist_km > SPOOF_THRESHOLD_KM

            # Verdict
            if is_stale:
                verdict = "⚪ STALE"
                reason  = f"UTC gap {int(time_diff_secs)}s > 300s threshold"
                stale_count += 1
            elif is_spoofed:
                verdict = "🔴 SPOOFED"
                reason  = f"Position {dist_km:,.1f}km from satellite - exceeds {SPOOF_THRESHOLD_KM}km threshold"
                spoofed_count += 1
            else:
                verdict = "🟢 SECURE"
                reason  = f"Verified within threshold ({dist_km:,.1f}km < {SPOOF_THRESHOLD_KM}km)"
                secure_count += 1

            results.append({
                "MMSI": mmsi,
                "Ship Lat": round(ship_lat, 5), "Ship Lon": round(ship_lon, 5),
                "Sat Lat": round(sat_lat, 5),   "Sat Lon": round(sat_lon, 5),
                "Distance (km)": round(dist_km, 2),
                "UTC Time": ship_time_raw, "Sync Gap": f"{int(time_diff_secs)}s",
                "Verdict": verdict, "Reason": reason,
                "_ship_lat": ship_lat, "_ship_lon": ship_lon,
                "_sat_lat": sat_lat,   "_sat_lon": sat_lon,
                "_spoofed": is_spoofed and not is_stale,
            })
        except:
            continue

    status_label = f"⚠️ {spoofed_count} SPOOFED" if spoofed_count > 0 else "✅ ALL SECURE"
    st.toast("✅ Analysis Complete")

# --- SIDEBAR METRICS ---
st.sidebar.metric("System Status", status_label)
c1, c2 = st.sidebar.columns(2)
c1.metric("🔴 Spoofed", spoofed_count)
c2.metric("🟢 Secure", secure_count)
st.sidebar.metric("⚪ Stale", stale_count)
st.sidebar.metric("Total Ships", len(st.session_state['ais_data']) if ais_ok else 0)

# --- MAIN DASHBOARD ---
col_map, col_table = st.columns([2, 1])
selected_mmsi = None

with col_table:
    st.subheader("Detection Report")
    if results:
        df_disp = pd.DataFrame(results)
        show_all = st.checkbox("Show all ships", value=True)
        if not show_all:
            df_disp = df_disp[df_disp["Verdict"] != "🟢 SECURE"]

        display_cols = ["MMSI","Ship Lat","Ship Lon","Sat Lat","Sat Lon",
                        "Distance (km)","UTC Time","Sync Gap","Verdict","Reason"]

        event = st.dataframe(
            df_disp[display_cols], on_select="rerun",
            selection_mode="single-row", use_container_width=True, hide_index=True
        )
        if len(event.selection.rows) > 0:
            selected_mmsi = df_disp.iloc[event.selection.rows[0]]["MMSI"]
            st.success(f"Tracking MMSI: {selected_mmsi}")
    else:
        st.info("Load AIS data and payload telemetry to run detection.")

with col_map:
    st.subheader("Global Threat Map")
    m = folium.Map(location=[1.25, 103.8], zoom_start=4)
    all_coords = []

    if results:
        ref = next((r for r in results if r["MMSI"] == str(selected_mmsi)), results[0])
        sat_pos = [ref["_sat_lat"], ref["_sat_lon"]]

        # 50km verification circle
        folium.Circle(
            location=sat_pos, radius=SPOOF_THRESHOLD_KM * 1000,
            color="blue", weight=2, fill=True, fill_opacity=0.08,
            tooltip=f"{SPOOF_THRESHOLD_KM}km verification radius"
        ).add_to(m)
        folium.Marker(
            sat_pos, icon=folium.Icon(color='blue', icon='satellite', prefix='fa'),
            tooltip="YMIR-1 Satellite Position"
        ).add_to(m)
        all_coords.append(sat_pos)

    for r in results:
        v_mmsi = r["MMSI"]
        s_mmsi = str(selected_mmsi) if selected_mmsi else None
        if s_mmsi and v_mmsi != s_mmsi:
            continue
        if not show_all and not r["_spoofed"] and s_mmsi != v_mmsi:
            continue

        ship_pos = [r["_ship_lat"], r["_ship_lon"]]
        color = 'red' if r["_spoofed"] else 'green'
        folium.Marker(
            ship_pos, icon=folium.Icon(color=color, icon='ship', prefix='fa'),
            tooltip=f"{'🔴 SPOOFED' if r['_spoofed'] else '🟢 SECURE'} | MMSI: {v_mmsi} | {r['Distance (km)']}km"
        ).add_to(m)
        all_coords.append(ship_pos)

        if r["_spoofed"]:
            sat_pos_r = [r["_sat_lat"], r["_sat_lon"]]
            folium.PolyLine(
                [ship_pos, sat_pos_r], color="red", weight=2, dash_array='6, 4',
                tooltip=f"{r['Distance (km)']}km"
            ).add_to(m)
            if sat_pos_r not in all_coords:
                all_coords.append(sat_pos_r)

    if all_coords:
        m.fit_bounds(all_coords, padding=(80, 80))

    st_folium(m, width=800, height=600, key=f"map_{selected_mmsi}_{spoofed_count}")

# --- SECURITY AUDIT PANEL ---
if selected_mmsi:
    r = next((x for x in results if x["MMSI"] == str(selected_mmsi)), None)
    if r:
        st.markdown("---")
        st.subheader(f"🛡️ Security Audit: MMSI {selected_mmsi}")
        if r["Verdict"] == "🔴 SPOOFED":
            st.error("SPOOFING DETECTED")
            st.write(f"""
**Satellite position at reception:** ({r['Sat Lat']}, {r['Sat Lon']})

**Ship's claimed AIS position:** ({r['Ship Lat']}, {r['Ship Lon']})

**Discrepancy:** {r['Distance (km)']} km - exceeds the {SPOOF_THRESHOLD_KM}km verification threshold.

At UTC **{r['UTC Time']}**, YMIR-1 received an AIS signal attributed to MMSI **{selected_mmsi}**. The ship's self-reported coordinates are inconsistent with the satellite telemetry. This vessel is flagged as a GPS spoofing candidate.
            """)
        elif r["Verdict"] == "⚪ STALE":
            st.warning("STALE - FORENSIC LINK UNRELIABLE")
            st.write(f"UTC timestamp gap of {r['Sync Gap']} exceeds the 300s threshold. Cannot reliably cross-reference AIS record with satellite telemetry.")
        else:
            st.success("SECURE - POSITION VERIFIED")
            st.write(f"Ship position is consistent with satellite telemetry. Distance to satellite reference: **{r['Distance (km)']}km** - within the {SPOOF_THRESHOLD_KM}km threshold.")
