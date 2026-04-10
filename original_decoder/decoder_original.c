/*
 * AIS Message Decoder for Final Year Project
 * Purpose: Decode different types of AIS messages from NMEA format
 * Output: CSV format with all the navigation fields
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAX_LINE_LENGTH 1024
#define MAX_PAYLOAD_LENGTH 256
#define MAX_BINARY_LENGTH 1536
#define MAX_TEXT_LENGTH 128

// Structure to hold decoded AIS data
typedef struct {
    int msg_type;
    int repeat_ind;
    uint32_t mmsi;
    int nav_status;
    char rot[16];
    char sog[16];
    int pos_accuracy;
    char longitude[32];
    char lon_hem[2];
    char latitude[32];
    char lat_hem[2];
    char cog[16];
    int heading;
    int utc_sec;
    int sync;
    int slot;
    int raim;
    char ship_name[MAX_TEXT_LENGTH];
    int ship_type;
    char callsign[MAX_TEXT_LENGTH];
    char destination[MAX_TEXT_LENGTH];
    char draught[16];
    uint32_t imo;
    int dim_a;
    int dim_b;
    int dim_c;
    int dim_d;
    int ais_version;
    int dte;
    int altitude;
    int aid_type;
    char name_extension[MAX_TEXT_LENGTH];
    int off_position;
    int gnss;
    int has_position;
} AISData;

// Convert AIS character to 6-bit value
int convert_ais_char(char c) {
    int val = (int)c - 48;
    if (val > 40) {
        val -= 8;
    }
    return val;
}

// Extract bits from binary string
int64_t extract_bits(const char *binary_data, int start_pos, int bit_length) {
    int len = strlen(binary_data);
    if (start_pos + bit_length > len) {
        return -1;
    }
    
    char bit_string[65];
    strncpy(bit_string, binary_data + start_pos, bit_length);
    bit_string[bit_length] = '\0';
    
    int64_t result = 0;
    for (int i = 0; i < bit_length; i++) {
        result = (result << 1) | (bit_string[i] - '0');
    }
    return result;
}

// Extract signed bits (for negative values)
int64_t extract_signed_bits(const char *binary_data, int start_pos, int bit_length) {
    int64_t value = extract_bits(binary_data, start_pos, bit_length);
    if (value == -1) {
        return -1;
    }
    
    // Check if negative (MSB is 1)
    if (value >= (1LL << (bit_length - 1))) {
        value = value - (1LL << bit_length);
    }
    return value;
}

// Convert payload to binary
void convert_payload_to_binary(const char *payload, char *binary_output) {
    binary_output[0] = '\0';
    char temp[7];
    
    for (int i = 0; payload[i] != '\0'; i++) {
        int six_bit_val = convert_ais_char(payload[i]);
        for (int j = 5; j >= 0; j--) {
            temp[5-j] = ((six_bit_val >> j) & 1) ? '1' : '0';
        }
        temp[6] = '\0';
        strcat(binary_output, temp);
    }
}

// Parse NMEA sentence to get payload
int get_payload_from_nmea(const char *sentence, char *payload) {
    if (strncmp(sentence, "!AIVDM", 6) != 0 && strncmp(sentence, "!AIVDO", 6) != 0) {
        return 0;
    }

    const char *p = sentence;
    int comma_count = 0;

    while (*p) {
        if (*p == ',') {
            comma_count++;
        } else if (comma_count == 5) {
            // start of payload
            const char *start = p;
            while (*p && *p != ',') p++;
            int len = p - start;
            strncpy(payload, start, len);
            payload[len] = '\0';
            return 1;
        }
        p++;
    }
    return 0;
}

// Format coordinates with hemisphere
void format_lat_lon(double coordinate, int is_lon, char *coord_str, char *hem_str) {
    if (is_lon) {
        if (coordinate >= 0) {
            strcpy(hem_str, "E");
        } else {
            strcpy(hem_str, "W");
        }
    } else {
        if (coordinate >= 0) {
            strcpy(hem_str, "N");
        } else {
            strcpy(hem_str, "S");
        }
    }
    sprintf(coord_str, "%.7f", fabs(coordinate));
}

// Extract text from 6-bit encoded field
void extract_text(const char *binary_data, int start_pos, int num_chars, char *output) {
    output[0] = '\0';
    char temp[2];
    temp[1] = '\0';
    
    for (int i = 0; i < num_chars; i++) {
        int64_t char_bits = extract_bits(binary_data, start_pos + (i * 6), 6);
        if (char_bits == -1) {
            break;
        }
        
        int ascii_char;
        if (char_bits < 32) {
            ascii_char = char_bits + 64;
        } else {
            ascii_char = char_bits;
        }
        
        if (ascii_char >= 32 && ascii_char <= 126) {
            temp[0] = (char)ascii_char;
            strcat(output, temp);
        } else {
            strcat(output, " ");
        }
    }
    
    // Trim trailing spaces
    int len = strlen(output);
    while (len > 0 && output[len-1] == ' ') {
        output[len-1] = '\0';
        len--;
    }
}

// Initialize AIS data structure
void init_ais_data(AISData *data) {
    data->msg_type = 0;
    data->repeat_ind = 0;
    data->mmsi = 0;
    data->nav_status = -1;
    strcpy(data->rot, "0");
    strcpy(data->sog, "0.0");
    data->pos_accuracy = 0;
    strcpy(data->longitude, "0");
    strcpy(data->lon_hem, "E");
    strcpy(data->latitude, "0");
    strcpy(data->lat_hem, "N");
    strcpy(data->cog, "0.0");
    data->heading = 511;
    data->utc_sec = 60;
    data->sync = 0;
    data->slot = 0;
    data->raim = 0;
    data->ship_name[0] = '\0';
    data->ship_type = 0;
    data->callsign[0] = '\0';
    data->destination[0] = '\0';
    strcpy(data->draught, "0");
    data->imo = 0;
    data->dim_a = 0;
    data->dim_b = 0;
    data->dim_c = 0;
    data->dim_d = 0;
    data->ais_version = 0;
    data->dte = 0;
    data->altitude = 0;
    data->aid_type = 0;
    data->name_extension[0] = '\0';
    data->off_position = 0;
    data->gnss = 0;
    data->has_position = 0;
}

// Main decode function
int decode_ais(const char *nmea_sentence, AISData *data) {
    char payload[MAX_PAYLOAD_LENGTH];
    char binary_data[MAX_BINARY_LENGTH];
    
    init_ais_data(data);
    
    if (!get_payload_from_nmea(nmea_sentence, payload)) {
        return 0;
    }
    
    convert_payload_to_binary(payload, binary_data);
    
    if (strlen(binary_data) < 38) {
        return 0;
    }
    
    // Get basic message info
    data->msg_type = (int)extract_bits(binary_data, 0, 6);
    data->repeat_ind = (int)extract_bits(binary_data, 6, 2);
    data->mmsi = (uint32_t)extract_bits(binary_data, 8, 30);
    
    // Only process valid AIS message types (1-27)
    if (data->msg_type < 1 || data->msg_type > 27) {
        return 0;
    }
    
    // Decode based on message type
    if ((data->msg_type >= 1 && data->msg_type <= 3) && strlen(binary_data) >= 168) {
        // Class A position reports
        data->nav_status = (int)extract_bits(binary_data, 38, 4);
        
        // Rate of turn calculation
        int64_t rot_raw = extract_signed_bits(binary_data, 42, 8);
        if (rot_raw == -128) {
            strcpy(data->rot, "-128.0");
        } else if (rot_raw == -127) {
            strcpy(data->rot, "-720.0");
        } else if (rot_raw == 127) {
            strcpy(data->rot, "+127.0");
        } else if (rot_raw == 0) {
            strcpy(data->rot, "+0.0");
        } else if (rot_raw > 0) {
            double rot_degrees = pow(rot_raw / 4.733, 2);
            sprintf(data->rot, "+%.1f", rot_degrees);
        } else {
            double rot_degrees = pow(fabs(rot_raw) / 4.733, 2);
            sprintf(data->rot, "-%.1f", rot_degrees);
        }
        
        // Speed over ground
        int64_t sog_raw = extract_bits(binary_data, 50, 10);
        if (sog_raw == 1023) {
            strcpy(data->sog, "0.0");
        } else {
            sprintf(data->sog, "%.1f", sog_raw / 10.0);
        }
        
        data->pos_accuracy = (int)extract_bits(binary_data, 60, 1);
        
        // Position decoding
        int64_t lon_raw = extract_signed_bits(binary_data, 61, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 89, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        // Course over ground
        int64_t cog_raw = extract_bits(binary_data, 116, 12);
        if (cog_raw >= 3600) {
            strcpy(data->cog, "360.0");
        } else {
            sprintf(data->cog, "%.1f", cog_raw / 10.0);
        }
        
        // True heading
        int64_t hdg_raw = extract_bits(binary_data, 128, 9);
        data->heading = (hdg_raw == 511) ? 511 : (int)hdg_raw;
        
        // UTC second
        int64_t utc_raw = extract_bits(binary_data, 137, 6);
        data->utc_sec = (utc_raw >= 60) ? 60 : (int)utc_raw;
        
        // Communication state
        data->raim = (int)extract_bits(binary_data, 148, 1);
        data->sync = (int)extract_bits(binary_data, 149, 2);
        data->slot = (int)extract_bits(binary_data, 151, 3);
        
    } else if (data->msg_type == 4 && strlen(binary_data) >= 168) {
        // Base station report
        data->pos_accuracy = (int)extract_bits(binary_data, 78, 1);
        int64_t lon_raw = extract_signed_bits(binary_data, 79, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 107, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        data->raim = (int)extract_bits(binary_data, 148, 1);
        
    } else if (data->msg_type == 5 && strlen(binary_data) >= 424) {
        // Static and voyage related data
        data->ais_version = (int)extract_bits(binary_data, 38, 2);
        data->imo = (uint32_t)extract_bits(binary_data, 40, 30);
        extract_text(binary_data, 70, 7, data->callsign);
        extract_text(binary_data, 112, 20, data->ship_name);
        data->ship_type = (int)extract_bits(binary_data, 232, 8);
        data->dim_a = (int)extract_bits(binary_data, 240, 9);
        data->dim_b = (int)extract_bits(binary_data, 249, 9);
        data->dim_c = (int)extract_bits(binary_data, 258, 6);
        data->dim_d = (int)extract_bits(binary_data, 264, 6);
        data->pos_accuracy = (int)extract_bits(binary_data, 270, 4);
        
        int64_t draught_raw = extract_bits(binary_data, 294, 8);
        if (draught_raw > 0) {
            sprintf(data->draught, "%.1f", draught_raw / 10.0);
        }
        
        extract_text(binary_data, 302, 20, data->destination);
        data->dte = (int)extract_bits(binary_data, 422, 1);
        
    } else if (data->msg_type == 9 && strlen(binary_data) >= 168) {
        // SAR aircraft position
        int64_t altitude_raw = extract_bits(binary_data, 38, 12);
        if (altitude_raw != 4095) {
            data->altitude = (int)altitude_raw;
        }
        
        int64_t sog_raw = extract_bits(binary_data, 50, 10);
        if (sog_raw == 1023) {
            strcpy(data->sog, "0.0");
        } else {
            sprintf(data->sog, "%.1f", sog_raw / 10.0);
        }
        
        data->pos_accuracy = (int)extract_bits(binary_data, 60, 1);
        
        int64_t lon_raw = extract_signed_bits(binary_data, 61, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 89, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        int64_t cog_raw = extract_bits(binary_data, 116, 12);
        if (cog_raw >= 3600) {
            strcpy(data->cog, "360.0");
        } else {
            sprintf(data->cog, "%.1f", cog_raw / 10.0);
        }
        
        data->utc_sec = (int)extract_bits(binary_data, 128, 6);
        data->dte = (int)extract_bits(binary_data, 142, 1);
        data->raim = (int)extract_bits(binary_data, 147, 1);
        
    } else if (data->msg_type == 11 && strlen(binary_data) >= 168) {
        // UTC and date response
        data->pos_accuracy = (int)extract_bits(binary_data, 78, 1);
        int64_t lon_raw = extract_signed_bits(binary_data, 79, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 107, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        data->raim = (int)extract_bits(binary_data, 148, 1);
        
    } else if (data->msg_type == 17 && strlen(binary_data) >= 80) {
        // DGNSS broadcast binary message
        int64_t lon_raw = extract_signed_bits(binary_data, 40, 18);
        int64_t lat_raw = extract_signed_bits(binary_data, 58, 17);
        
        if (lon_raw != 0x1A838) {
            double lon_degrees = lon_raw / 600.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0xD548) {
            double lat_degrees = lat_raw / 600.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
    } else if (data->msg_type == 18 && strlen(binary_data) >= 168) {
        // Class B position report
        int64_t sog_raw = extract_bits(binary_data, 46, 10);
        if (sog_raw == 1023) {
            strcpy(data->sog, "0.0");
        } else {
            sprintf(data->sog, "%.1f", sog_raw / 10.0);
        }
        
        data->pos_accuracy = (int)extract_bits(binary_data, 56, 1);
        
        int64_t lon_raw = extract_signed_bits(binary_data, 57, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 85, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        int64_t cog_raw = extract_bits(binary_data, 112, 12);
        if (cog_raw >= 3600) {
            strcpy(data->cog, "360.0");
        } else {
            sprintf(data->cog, "%.1f", cog_raw / 10.0);
        }
        
        int64_t hdg_raw = extract_bits(binary_data, 124, 9);
        data->heading = (hdg_raw == 511) ? 511 : (int)hdg_raw;
        
        int64_t utc_raw = extract_bits(binary_data, 133, 6);
        data->utc_sec = (utc_raw >= 60) ? 60 : (int)utc_raw;
        
        data->raim = (int)extract_bits(binary_data, 147, 1);
        data->sync = (int)extract_bits(binary_data, 149, 2);
        data->slot = (int)extract_bits(binary_data, 151, 3);
        
    } else if (data->msg_type == 19 && strlen(binary_data) >= 312) {
        // Extended Class B
        int64_t sog_raw = extract_bits(binary_data, 46, 10);
        if (sog_raw == 1023) {
            strcpy(data->sog, "0.0");
        } else {
            sprintf(data->sog, "%.1f", sog_raw / 10.0);
        }
        
        data->pos_accuracy = (int)extract_bits(binary_data, 56, 1);
        
        int64_t lon_raw = extract_signed_bits(binary_data, 57, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 85, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        int64_t cog_raw = extract_bits(binary_data, 112, 12);
        if (cog_raw >= 3600) {
            strcpy(data->cog, "360.0");
        } else {
            sprintf(data->cog, "%.1f", cog_raw / 10.0);
        }
        
        int64_t hdg_raw = extract_bits(binary_data, 124, 9);
        data->heading = (hdg_raw == 511) ? 511 : (int)hdg_raw;
        
        int64_t utc_raw = extract_bits(binary_data, 133, 6);
        data->utc_sec = (utc_raw >= 60) ? 60 : (int)utc_raw;
        
        extract_text(binary_data, 143, 20, data->ship_name);
        data->ship_type = (int)extract_bits(binary_data, 263, 8);
        data->dim_a = (int)extract_bits(binary_data, 271, 9);
        data->dim_b = (int)extract_bits(binary_data, 280, 9);
        data->dim_c = (int)extract_bits(binary_data, 289, 6);
        data->dim_d = (int)extract_bits(binary_data, 295, 6);
        
        data->raim = (int)extract_bits(binary_data, 305, 1);
        data->dte = (int)extract_bits(binary_data, 306, 1);
        
    } else if (data->msg_type == 21 && strlen(binary_data) >= 272) {
        // Aid to navigation
        data->aid_type = (int)extract_bits(binary_data, 38, 5);
        extract_text(binary_data, 43, 20, data->ship_name);
        data->pos_accuracy = (int)extract_bits(binary_data, 163, 1);
        
        int64_t lon_raw = extract_signed_bits(binary_data, 164, 28);
        int64_t lat_raw = extract_signed_bits(binary_data, 192, 27);
        
        if (lon_raw != 0x6791AC0) {
            double lon_degrees = lon_raw / 600000.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0x3412140) {
            double lat_degrees = lat_raw / 600000.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        data->dim_a = (int)extract_bits(binary_data, 219, 9);
        data->dim_b = (int)extract_bits(binary_data, 228, 9);
        data->dim_c = (int)extract_bits(binary_data, 237, 6);
        data->dim_d = (int)extract_bits(binary_data, 243, 6);
        
        data->utc_sec = (int)extract_bits(binary_data, 253, 6);
        data->off_position = (int)extract_bits(binary_data, 259, 1);
        data->raim = (int)extract_bits(binary_data, 268, 1);
        
        if (strlen(binary_data) >= 360) {
            extract_text(binary_data, 272, 14, data->name_extension);
        }
        
    } else if (data->msg_type == 24 && strlen(binary_data) >= 168) {
        // Static data report
        int part_num = (int)extract_bits(binary_data, 38, 2);
        
        if (part_num == 0) {
            // Part A - vessel name
            extract_text(binary_data, 40, 20, data->ship_name);
        } else if (part_num == 1) {
            // Part B - static data
            data->ship_type = (int)extract_bits(binary_data, 40, 8);
            extract_text(binary_data, 90, 7, data->callsign);
            data->dim_a = (int)extract_bits(binary_data, 132, 9);
            data->dim_b = (int)extract_bits(binary_data, 141, 9);
            data->dim_c = (int)extract_bits(binary_data, 150, 6);
            data->dim_d = (int)extract_bits(binary_data, 156, 6);
        }
        
    } else if (data->msg_type == 27 && strlen(binary_data) >= 96) {
        // Long range AIS
        data->pos_accuracy = (int)extract_bits(binary_data, 38, 1);
        data->raim = (int)extract_bits(binary_data, 39, 1);
        data->nav_status = (int)extract_bits(binary_data, 40, 4);
        
        int64_t lon_raw = extract_signed_bits(binary_data, 44, 18);
        int64_t lat_raw = extract_signed_bits(binary_data, 62, 17);
        
        if (lon_raw != 0x1A838) {
            double lon_degrees = lon_raw / 600.0;
            format_lat_lon(lon_degrees, 1, data->longitude, data->lon_hem);
            data->has_position = 1;
        }
        
        if (lat_raw != 0xD548) {
            double lat_degrees = lat_raw / 600.0;
            format_lat_lon(lat_degrees, 0, data->latitude, data->lat_hem);
        }
        
        int64_t sog_raw = extract_bits(binary_data, 79, 6);
        if (sog_raw == 63) {
            strcpy(data->sog, "0.0");
        } else {
            sprintf(data->sog, "%.1f", (double)sog_raw);
        }
        
        int64_t cog_raw = extract_bits(binary_data, 85, 9);
        if (cog_raw >= 360) {
            strcpy(data->cog, "360.0");
        } else {
            sprintf(data->cog, "%.1f", (double)cog_raw);
        }
        
        data->gnss = (int)extract_bits(binary_data, 94, 1);
    }
    
    return 1;
}

// Convert decoded data to CSV line
void make_csv_line(const AISData *data, char *output) {
    sprintf(output, "%d,%d,%u,%d,%s,%s,%d,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%s,%d,%s,%s,%s,%u,%d,%d,%d,%d,%d,%d,%d,%d,%s,%d,%d",
            data->msg_type,
            data->repeat_ind,
            data->mmsi,
            data->nav_status,
            data->rot,
            data->sog,
            data->pos_accuracy,
            data->longitude,
            data->lon_hem,
            data->latitude,
            data->lat_hem,
            data->cog,
            data->heading,
            data->utc_sec,
            data->sync,
            data->slot,
            data->raim,
            data->ship_name,
            data->ship_type,
            data->callsign,
            data->destination,
            data->draught,
            data->imo,
            data->dim_a,
            data->dim_b,
            data->dim_c,
            data->dim_d,
            data->ais_version,
            data->dte,
            data->altitude,
            data->aid_type,
            data->name_extension,
            data->off_position,
            data->gnss);
}

// Function to process the input file and generate statistics
void process_ais_file(const char *input_filename, const char *output_filename) {
    FILE *input_file = NULL;
    FILE *output_file = NULL;
    char line[MAX_LINE_LENGTH];
    char csv_line[MAX_LINE_LENGTH * 3]; // Increased size to be safe for a long CSV line
    AISData data;

    // Statistics variables
    int total_messages = 0;
    int decoded_messages = 0;
    int invalid_messages = 0;
    int message_types[28] = {0}; // Index 1-27 for message types
    int invalid_types[256] = {0}; // Track invalid types
    int messages_with_position = 0;
    int valid_without_position = 0;

    // File opening
    input_file = fopen(input_filename, "r");
    if (input_file == NULL) {
        printf("Error: Could not find file %s\n", input_filename);
        return;
    }

    output_file = fopen(output_filename, "w");
    if (output_file == NULL) {
        printf("Error: Could not open output file %s\n", output_filename);
        fclose(input_file);
        return;
    }

    // Write header
    const char *header = "message_type,repeat_indicator,mmsi,navigation_status,rate_of_turn,speed_over_ground,position_accuracy,longitude,lon_hemisphere,latitude,lat_hemisphere,course_over_ground,true_heading,utc_second,sync_state,slot_timeout,raim_flag,ship_name,ship_type,callsign,destination,draught,imo,dim_a,dim_b,dim_c,dim_d,ais_version,dte,altitude,aid_type,name_extension,off_position,gnss";
    fprintf(output_file, "%s\n", header);

    // Process file line by line
    while (fgets(line, sizeof(line), input_file) != NULL) {
        // Remove trailing newline/carriage return
        line[strcspn(line, "\r\n")] = '\0';

        if (strlen(line) == 0) {
            continue;
        }

        total_messages++;

        // Initial check for message type
        char payload_check[MAX_PAYLOAD_LENGTH];
        char binary_data_check[MAX_BINARY_LENGTH];
        int msg_type_check = -1;

        if (get_payload_from_nmea(line, payload_check)) {
            convert_payload_to_binary(payload_check, binary_data_check);
            if (strlen(binary_data_check) >= 6) {
                msg_type_check = (int)extract_bits(binary_data_check, 0, 6);
            }
        }
        
        // Skip message if type is non-standard/invalid (similar to Python logic)
        if (msg_type_check != -1 && (msg_type_check < 1 || msg_type_check > 27)) {
            invalid_messages++;
            if (msg_type_check >= 0 && msg_type_check < 256) {
                invalid_types[msg_type_check]++;
            }
            continue;
        }

        // Decode the message
        if (decode_ais(line, &data)) {
            if (data.msg_type >= 1 && data.msg_type <= 27) {
                // Tally message type
                message_types[data.msg_type]++;

                // Check for position data
                if (data.has_position) { // has_position is set to 1 in decode_ais if a valid coordinate is found
                    messages_with_position++;
                } else {
                    valid_without_position++;
                }

                // Write to CSV
                make_csv_line(&data, csv_line);
                fprintf(output_file, "%s\n", csv_line);
                decoded_messages++;
            }
        }
    }

    // Close files
    fclose(input_file);
    fclose(output_file);

    // Print summary (similar to Python)
    printf("Total messages processed: %d\n", total_messages);
    printf("Successfully decoded: %d\n", decoded_messages);
    printf("Invalid/non-standard message types: %d\n", invalid_messages);
    
    printf("\nValid messages with position data: %d\n", messages_with_position);
    printf("Valid messages without position data: %d\n", valid_without_position);
    
    printf("\nValid message type summary:\n");
    for (int i = 1; i <= 27; i++) {
        if (message_types[i] > 0) {
            printf("  Type %d: %d messages\n", i, message_types[i]);
        }
    }

    int invalid_found = 0;
    for (int i = 0; i < 256; i++) {
        if (invalid_types[i] > 0) {
            invalid_found = 1;
            break;
        }
    }
    
    if (invalid_found) {
        printf("\nInvalid/non-standard message types found:\n");
        for (int i = 0; i < 256; i++) {
            if (invalid_types[i] > 0) {
                printf("  Type %d: %d messages\n", i, invalid_types[i]);
            }
        }
    }

    printf("\nDecoded data saved to: %s\n", output_filename);
}

// Debug function for single message (optional but good for testing)
void debug_single_message(const char *nmea_msg) {
    char payload[MAX_PAYLOAD_LENGTH];
    char binary[MAX_BINARY_LENGTH];
    
    if (!get_payload_from_nmea(nmea_msg, payload)) {
        printf("Could not parse NMEA message\n");
        return;
    }

    convert_payload_to_binary(payload, binary);
    printf("Payload: %s\n", payload);
    printf("Binary length: %zu bits\n", strlen(binary));
    
    int msg_type = (int)extract_bits(binary, 0, 6);
    int repeat = (int)extract_bits(binary, 6, 2);
    uint32_t mmsi = (uint32_t)extract_bits(binary, 8, 30);
    
    printf("Message type: %d\n", msg_type);
    printf("Repeat: %d\n", repeat);
    printf("MMSI: %u\n", mmsi);
    
    if (msg_type >= 1 && msg_type <= 3) {
        printf("Class A position report detected\n");
        int nav_stat = (int)extract_bits(binary, 38, 4);
        int64_t rot_raw = extract_signed_bits(binary, 42, 8);
        int64_t sog_raw = extract_bits(binary, 50, 10);
        int pos_acc = (int)extract_bits(binary, 60, 1);
        int64_t lon_raw = extract_signed_bits(binary, 61, 28);
        int64_t lat_raw = extract_signed_bits(binary, 89, 27);
        
        printf("Navigation status: %d\n", nav_stat);
        printf("ROT raw: %lld\n", (long long)rot_raw);
        printf("SOG raw: %lld\n", (long long)sog_raw);
        printf("Position accuracy: %d\n", pos_acc);
        printf("Longitude raw: %lld\n", (long long)lon_raw);
        printf("Latitude raw: %lld\n", (long long)lat_raw);
    }
}


int main(void) {
    // Test with sample message
    const char *test_nmea = "!AIVDM,1,1,,A,38IFDN0Ohj7JvbN0fABtpbJ401w@,0*69";
    printf("Testing decoder with sample message:\n");
    printf("Input: %s\n", test_nmea);
    
    debug_single_message(test_nmea);
    
    AISData data;
    if (decode_ais(test_nmea, &data)) {
        char csv_line[MAX_LINE_LENGTH];
        make_csv_line(&data, csv_line);
        printf("Decoded result: %s\n", csv_line);
    } else {
        printf("Decoding failed!\n");
    }
    
    printf("\n============================================================\n\n");
    
    // Process full file - Update these paths as needed
    const char *input_path = "your_input_file.txt";
    const char *output_path = "your_output_file.txt";
    
    printf("Processing AIS messages from: %s\n", input_path);
    process_ais_file(input_path, output_path);
    
    printf("\nPress Enter to Exit");
    getchar();

    return 0;
}  
