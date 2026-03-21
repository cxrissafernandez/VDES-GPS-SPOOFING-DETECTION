# VDES GPS Spoofing Detection System

NTU EEE Final Year Project 2026: Secure Monitoring of Ship Location using VDES Technology and Satellite Communication   
Author: Carissa Metta Fernandez

## Quick Start
1. pip install -r requirements.txt
2. Add API keys (see below)
3. py -m streamlit run app.py

## API Keys Required
- AISStream API key: Register free at https://aisstream.io
- N2YO API key: Register free at https://www.n2yo.com/api/

Replace the placeholders in:
- data_collector.py → API_KEY
- validator.py → N2YO_API_KEY
- mission_report.py → API_KEY
- app.py → N2YO_API_KEY

## Modules
- app.py               : Main Streamlit dashboard
- data_collector.py    : Live AIS stream collector
- decoder.py           : NMEA AIS decoder
- validator.py         : Haversine + N2YO satellite API
- scenario_builder.py  : Synthetic test data generator
- mission_report.py    : Offline demo workflow

## Testing
### Simulation Mode
Use the Simulation Mode toggle in the app to generate 
synthetic satellite positions on the fly from loaded 
AIS data. Three scenarios available: All Secure, 
All Spoofed, and Mixed.

### Test Scenario Files
Click GENERATE TEST SCENARIOS in the app to save 
3 reusable CSV files to disk:
- test_scenarios/1_all_secure.csv
- test_scenarios/2_all_spoofed.csv
- test_scenarios/3_mixed.csv

Upload these as Input 2 (Payload Telemetry) to 
reproduce each test scenario.

## Offline Demo
Run mission_report.py to pre-collect real AIS and 
satellite data, saving them as frozen files that 
can be uploaded into the app to demonstrate the 
system using actual live data:
- demo_ships_frozen.csv  → upload as Input 1
- demo_sats_frozen.csv   → upload as Input 2