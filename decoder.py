import pandas as pd
import io

# =========================================================
# helper functions
# =========================================================

def convert_ais_char(char):
    ascii_value = ord(char)
    val = ascii_value - 48
    if val > 40:
        val = val - 8
    return val

def extract_bits(binary_data, start_pos, bit_length):
    if start_pos + bit_length > len(binary_data):
        return None
    bit_string = binary_data[start_pos:start_pos + bit_length]
    return int(bit_string, 2)

def extract_signed_bits(binary_data, start_pos, bit_length):
    value = extract_bits(binary_data, start_pos, bit_length)
    if value is None:
        return None
    if value >= (1 << (bit_length - 1)):
        value = value - (1 << bit_length)
    return value

def convert_payload_to_binary(payload):
    result = ""
    for char in payload:
        six_bit_val = convert_ais_char(char)
        binary_str = format(six_bit_val, '06b')
        result += binary_str
    return result

def get_payload_from_nmea(sentence):
    if not sentence.startswith('!AIVDM') and not sentence.startswith('!AIVDO'):
        return None
    parts = sentence.strip().split(',')
    if len(parts) >= 6:
        return parts[5]
    return None

# =========================================================
# main decoder logic
# =========================================================
def decode_ais(nmea_sentence):
    payload = get_payload_from_nmea(nmea_sentence)
    if not payload: return None
        
    binary_data = convert_payload_to_binary(payload)
    if len(binary_data) < 38: return None
    
    msg_type = extract_bits(binary_data, 0, 6)
    mmsi = extract_bits(binary_data, 8, 30)
    
    # init variables
    longitude = latitude = sog = cog = heading = None
    
    # process position reports (types 1, 2, 3)
    if msg_type in [1, 2, 3] and len(binary_data) >= 168:
        sog_raw = extract_bits(binary_data, 50, 10)
        sog = f"{sog_raw / 10.0:.1f}" if sog_raw != 1023 else "0.0"
        
        lon_raw = extract_signed_bits(binary_data, 61, 28)
        lat_raw = extract_signed_bits(binary_data, 89, 27)
        
        if lon_raw != 0x6791AC0:
            longitude = lon_raw / 600000.0
        if lat_raw != 0x3412140:
            latitude = lat_raw / 600000.0
            
        cog_raw = extract_bits(binary_data, 116, 12)
        cog = f"{cog_raw / 10.0:.1f}" if cog_raw < 3600 else "360.0"
        
        hdg_raw = extract_bits(binary_data, 128, 9)
        heading = hdg_raw if hdg_raw != 511 else None

    return {
        "mmsi": mmsi,
        "lat": latitude,    
        "lon": longitude,   
        "speed": sog,
        "course": cog,
        "heading": heading,
        "type": msg_type
    }

# =========================================================
# file parsing function
# =========================================================
def parse_nmea_file(uploaded_file):
    decoded_list = []
    
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if not line: continue
        
        try:
            result = decode_ais(line)
            
            # check for valid coordinates
            if result and result['lat'] is not None and result['lon'] is not None:
                decoded_list.append(result)
                
        except Exception as e:
            continue

    return pd.DataFrame(decoded_list)