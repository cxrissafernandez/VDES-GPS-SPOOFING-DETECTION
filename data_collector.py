import asyncio
import websockets
import json
import csv
import time
from datetime import datetime

# configuration
API_KEY = "YOUR_AISSTREAM_API_KEY_HERE" 
import os
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_ship_data.csv")

# bounding box: malacca strait + singapore + south china sea
BOUNDING_BOX = [[-2.0, 95.0], [12.0, 115.0]] 

async def connect_ais_stream(duration=60):
    print(f"Connecting to AIS Stream for {duration} seconds...")
    
    collected_count = 0
    start_time = time.time()

    # open csv to write data
    with open(OUTPUT_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["mmsi", "lat", "lon", "time_utc"]) 
        
        async with websockets.connect("wss://stream.aisstream.io/v0/stream", open_timeout=60) as websocket:
            
            # subscribe message
            subscribe_message = {
                "APIKey": API_KEY,
                "BoundingBoxes": [BOUNDING_BOX],
                "FiltersShipMMSI": [], 
                "FilterMessageTypes": ["PositionReport"] 
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("Connected! Collecting data...")

            try:
                async for message_json in websocket:
                    
                    # check timer
                    if (time.time() - start_time) > duration:
                        break

                    message = json.loads(message_json)
                    
                    if "PositionReport" in message["Message"]:
                        report = message["Message"]["PositionReport"]
                        meta = message["MetaData"]

                        row = [
                            report["UserID"], 
                            report["Latitude"], 
                            report["Longitude"], 
                            meta["time_utc"][:19]
                        ]
                        
                        # write to file
                        writer.writerow(row)
                        file.flush()
                        collected_count += 1
                        
            except Exception as e:
                print(f"Error: {e}")
                
    return collected_count

# wrapper function
def run_collector(seconds=60):
    return asyncio.run(connect_ais_stream(seconds))

# standalone test
if __name__ == "__main__":
    count = run_collector(60)
    print(f"Done. Saved {count} ships.")



