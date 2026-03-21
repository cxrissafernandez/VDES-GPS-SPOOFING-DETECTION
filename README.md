# VDES GPS Spoofing Detection System

NTU EEE Final Year Project 2026: Secure Monitoring of Ship Location using VDES Technology and Satellite Communication

## Quick Start
1. pip install -r requirements.txt
2. Add API keys to data_collector.py, validator.py, mission_report.py
3. py -m streamlit run app.py

## Modules
- app.py               : Main Streamlit dashboard
- data_collector.py    : Live AIS stream collector  
- decoder.py           : NMEA AIS decoder
- validator.py         : Haversine + N2YO satellite API
- scenario_builder.py  : Synthetic test data generator
- mission_report.py    : Offline demo workflow
