# VDES GPS Spoofing Detection System

NTU EEE Final Year Project 2026: Secure Monitoring of Ship Location using VDES Technology and Satellite Communication

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
