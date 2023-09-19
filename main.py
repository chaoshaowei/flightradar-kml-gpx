import requests
import os
import csv
import json
import datetime
#-----------------------------
# Flags
#-----------------------------
DEBUG = False
SAVE_RESPONSE = True
CONTINUE_ID = True

# Run mode
FORCE_SEARCH = False

LIST_FLIGHT_BY_REG = 0
SEARCH_FLIGHT_BY_REG = 1
SEARCH_FLIGHT_BY_FLIGHT_ID = 2
SEARCH_FLIGHT_BY_FLIGHT_IDS = 3

RUN_MODE = SEARCH_FLIGHT_BY_FLIGHT_IDS

# Output options
OUTPUT_KML = True
OUTPUT_GPX = True

OUT_FLT_NUM = True

# Output filename timezone option
#
# TIMEZONE_UTC   : 2023-09-08T1230Z
# TIMEZONE_CUSTOM: 2023-09-08T2030+0800
#                  (use OUTPUT_TZ_NUM's timezone)
# TIMEZONE_AUTO  : 2023-09-08T2030+0800
#                  (use FR24 Destination's timezone)
TIMEZONE_UTC = 0
TIMEZONE_CUSTOM = 1
TIMEZONE_AUTO = 2

OUTPUT_TZ_NUM = +8

TIMEZONE_MODE = TIMEZONE_AUTO

COPY_TO_SPECIFIC_PATH = True

#-----------------------------
# directories
#-----------------------------


if __name__ == '__main__':
    #-----------------------------
    # Constants
    #-----------------------------
    REG_ID = 'B-16340'
    FLIGHT_ID = '31d5273a'#
    FLIGHT_IDS = ['32160cb5', '32167408']

    #-----------------------------
    # target url
    #-----------------------------
    REG_URL_TEMPLATE = 'https://api.flightradar24.com/common/v1/flight/list.json?query=[REG_ID]&fetchBy=reg&filterBy=historic'
    FLIGHT_URL_TEMPLATE = 'https://api.flightradar24.com/common/v1/flight-playback.json?flightId=[FLIGHT_ID]&timestamp=[TIMESTAMP]'

    OUTPUT_TZ = datetime.timezone(datetime.timedelta(hours=OUTPUT_TZ_NUM))

    #-----------------------------
    # directories
    #-----------------------------
    WORKING_DIR = os.path.dirname(os.path.realpath(__file__))

    RESPONSE_DIR = os.path.join(WORKING_DIR, 'Responses')
    RESPONSE1_FILE = os.path.join(RESPONSE_DIR, f'List_{REG_ID}.json')
    HEADERS_FILE = os.path.join(WORKING_DIR, f'headers.json')
    
    KML_TEMPLATE_FILE = os.path.join(WORKING_DIR, 'kml_template.xml')
    with open (KML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        KML_TEMPLATE = ''.join(f.readlines())

    GPX_TEMPLATE_FILE = os.path.join(WORKING_DIR, 'gpx_template.xml')
    with open (GPX_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        GPX_TEMPLATE = ''.join(f.readlines())

    SPECIFIC_GPX_PATH = os.path.join(WORKING_DIR, 'Ian', 'GPXs')
    SPECIFIC_KML_PATH = os.path.join(WORKING_DIR, 'Ian', 'KMLs')
    if COPY_TO_SPECIFIC_PATH:
        os.makedirs(SPECIFIC_GPX_PATH, exist_ok=True)
        os.makedirs(SPECIFIC_KML_PATH, exist_ok=True)

    #-----------------------------
    # main
    #-----------------------------
    with open(HEADERS_FILE, 'r', encoding='utf-8') as f1:
        headers = json.load(f1)

    os.makedirs(RESPONSE_DIR, exist_ok=True)

    s = requests.Session()

    #-----------------------------
    # List Reg
    #-----------------------------
    def list_flights(reg_id: str):
        print(f"Listing Flight of [{reg_id}]")
        
        # Generate URL
        reg_url = REG_URL_TEMPLATE.replace('[REG_ID]', reg_id)

        # Getting Data
        r = s.get(reg_url, headers=headers)
        if r.status_code!=200:
            print(f'Error code {r.status_code}')
            return []

        # Saving Data
        if SAVE_RESPONSE:
            with open(RESPONSE1_FILE, 'w', encoding='utf-8') as f:
                f.write(r.text)

        list_dict = json.loads(r.text)
        ids = [list_dict['result']['response']['data'][i]['identification']['id'] for i in range(len(list_dict['result']['response']['data']))]
        print(f'  {len(ids):2d} results found:')
        print(f'    {ids[0]}')
        print(f'      ....')
        print(f'    {ids[-1]}\n')
        return ids

    #-----------------------------
    # Search Flight
    #-----------------------------
    def search_flight(flight_id: str):
        print(f"Searching Flight: {flight_id}")

        if not FORCE_SEARCH and False:
            print("  Will not be searched")

        # Generate URL
        flight_url = FLIGHT_URL_TEMPLATE.replace('[FLIGHT_ID]', flight_id).replace('[TIMESTAMP]', str(int(datetime.datetime.now().timestamp())))
        print(flight_url)

        # Getting Data
        r = s.get(flight_url, headers=headers)
        if r.status_code!=200:
            print(f'Error code {r.statuscode}')
            return

        # Saving Data
        full_dict = json.loads(r.text)

        reg = full_dict['result']['response']['data']['flight']['aircraft']['identification']['registration']
        eventTimestamp = full_dict['result']['response']['data']['flight']['status']['generic']['eventTime']['utc']
        try:
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)
        except TypeError:
            eventTimestamp = full_dict['result']['response']['data']['flight']['track'][-1]['timestamp']
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)

        if full_dict['result']['response']['data']['flight']['status']['generic']['status']['text'] in ['landed', 'diverted']:
            print(f"  {reg}, {full_dict['result']['response']['data']['flight']['status']['generic']['status']['text']}")
            if SAVE_RESPONSE:
                os.makedirs(os.path.join(WORKING_DIR, 'Responses', reg), exist_ok=True)
                RESPONSE2_FILE = os.path.join(WORKING_DIR, 'Responses', reg, f'{eventTime.astimezone(tz=OUTPUT_TZ).isoformat(timespec="minutes").replace(":","")}_{flight_id}.json')
                with open(RESPONSE2_FILE, 'w', encoding='utf-8') as f:
                    f.write(r.text)
        else:
            print(f"  {reg}, {full_dict['result']['response']['data']['flight']['status']['generic']['status']['text']}, json will not be saved")

        
        return full_dict['result']['response']['data']['flight']

    def outputKML(flight_dict: dict):
        if flight_dict == None:
            return
        track_list = flight_dict['track']

        coords_str = '\n'.join([f'          {point["longitude"]},{point["latitude"]},{point["altitude"]["meters"]}' for point in track_list])
        
        reg = flight_dict['aircraft']['identification']['registration']
        eventTimestamp = flight_dict['status']['generic']['eventTime']['utc']
        try:
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)
        except TypeError:
            eventTimestamp = flight_dict['track'][-1]['timestamp']
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)

        if flight_dict["identification"]["number"]["default"]:
            flt_num = flight_dict["identification"]["number"]["default"]
        else:
            flt_num = flight_dict["identification"]["callsign"]
        
        # Handle timezone option
        if TIMEZONE_MODE == TIMEZONE_UTC:
            time_str = eventTime.isoformat(timespec="minutes").replace("+00:00", "Z").replace(":","")
        elif TIMEZONE_MODE == TIMEZONE_CUSTOM:
            time_str = eventTime.astimezone(tz=OUTPUT_TZ).isoformat(timespec="minutes").replace(":","")
        elif TIMEZONE_MODE == TIMEZONE_AUTO:
            output_tzinfo = datetime.timezone(datetime.timedelta(seconds=flight_dict['airport']['destination']['timezone']['offset']))
            time_str = eventTime.astimezone(tz=output_tzinfo).isoformat(timespec="minutes").replace(":","")
        
        # Handle output filename
        kml_filename = time_str
        if OUT_FLT_NUM:
            if flight_dict["identification"]["number"]["default"]:
                kml_filename += f'_{flt_num}'
            else:
                kml_filename += f'_{flt_num}'
        kml_filename += f'_{reg}_{flight_id}.kml'

        os.makedirs(os.path.join(WORKING_DIR, 'KMLs', reg), exist_ok=True)
        # Default kml output
        kml_file_list = [os.path.join(WORKING_DIR, 'KMLs', reg, kml_filename)]
        if COPY_TO_SPECIFIC_PATH:
            kml_file_list.append(os.path.join(SPECIFIC_KML_PATH, kml_filename))
        for kml_file in kml_file_list:
            with open(kml_file, 'w', encoding='utf-8') as f:
                trk_name_str = 'Flight'
                if OUT_FLT_NUM:
                    trk_name_str += f' {flt_num}'
                trk_name_str += f' of {reg} at {eventTime.strftime("%Y-%m-%dZ")}'
                f.write(KML_TEMPLATE.replace('[COORDS]', coords_str).replace('[TRK_NAME]', trk_name_str).replace('[TRK_DSCRP]', f'{trk_name_str}, {flight_id}@FR24'))

    def outputGPX(flight_dict: dict):
        if flight_dict == None:
            return
        track_list = flight_dict['track']

        coords_str = ''
        for trkpt_dict in track_list:
            trkptTime = datetime.datetime.fromtimestamp(trkpt_dict['timestamp'], tz=datetime.timezone.utc)
            trkpt_time_str = trkptTime.isoformat()
            coords_str += f'      <trkpt lat="{trkpt_dict["latitude"]}" lon="{trkpt_dict["longitude"]}">\n        <ele>{trkpt_dict["altitude"]["meters"]}</ele>\n        <time>{trkpt_time_str}</time>\n      </trkpt>\n'
        
        reg = flight_dict['aircraft']['identification']['registration']
        eventTimestamp = flight_dict['status']['generic']['eventTime']['utc']
        try:
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)
        except TypeError:
            eventTimestamp = flight_dict['track'][-1]['timestamp']
            eventTime = datetime.datetime.fromtimestamp(eventTimestamp, tz=datetime.timezone.utc)

        # Getting FLT NUM (eg. BR265). If null, get callsign (eg. EVA265)
        if flight_dict["identification"]["number"]["default"]:
            flt_num = flight_dict["identification"]["number"]["default"]
        else:
            flt_num = flight_dict["identification"]["callsign"]

        # Handle timezone option
        if TIMEZONE_MODE == TIMEZONE_UTC:
            time_str = eventTime.isoformat(timespec="minutes").replace("+00:00", "Z").replace(":","")
        elif TIMEZONE_MODE == TIMEZONE_CUSTOM:
            time_str = eventTime.astimezone(tz=OUTPUT_TZ).isoformat(timespec="minutes").replace(":","")
        elif TIMEZONE_MODE == TIMEZONE_AUTO:
            output_tzinfo = datetime.timezone(datetime.timedelta(seconds=flight_dict['airport']['destination']['timezone']['offset']))
            time_str = eventTime.astimezone(tz=output_tzinfo).isoformat(timespec="minutes").replace(":","")
        
        # Handle output filename
        gpx_filename = time_str
        if OUT_FLT_NUM:
            gpx_filename += f'_{flt_num}'
        gpx_filename += f'_{reg}_{flight_id}.gpx'

        os.makedirs(os.path.join(WORKING_DIR, 'GPXs', reg), exist_ok=True)
        # Default gpx output
        gpx_file_list = [os.path.join(WORKING_DIR, 'GPXs', reg, gpx_filename)]
        if COPY_TO_SPECIFIC_PATH:
            gpx_file_list.append(os.path.join(SPECIFIC_GPX_PATH, gpx_filename))
        for gpx_file in gpx_file_list:
            with open(gpx_file, 'w', encoding='utf-8') as f:
                trk_name_str = 'Flight'
                if OUT_FLT_NUM:
                    trk_name_str += f' {flt_num}'
                trk_name_str += f' of {reg} at {eventTime.strftime("%Y-%m-%dZ")}'
                f.write(GPX_TEMPLATE.replace('[COORDS]', coords_str).replace('[TIME]', eventTime.astimezone(tz=OUTPUT_TZ).isoformat(timespec="minutes").replace(":","")).replace('[TRK_NAME]', trk_name_str))

    
    if RUN_MODE == SEARCH_FLIGHT_BY_FLIGHT_ID:
        ids = [FLIGHT_ID]
    elif RUN_MODE == SEARCH_FLIGHT_BY_FLIGHT_IDS:
        ids = FLIGHT_IDS
    elif RUN_MODE == SEARCH_FLIGHT_BY_REG or RUN_MODE == LIST_FLIGHT_BY_REG:
        ids = list_flights(reg_id=REG_ID)
    
    if RUN_MODE == SEARCH_FLIGHT_BY_REG or RUN_MODE == SEARCH_FLIGHT_BY_FLIGHT_ID or RUN_MODE == SEARCH_FLIGHT_BY_FLIGHT_IDS:
        for flight_id in ids:
            flight_dict = search_flight(flight_id)
            if OUTPUT_KML:
                outputKML(flight_dict)
            if OUTPUT_GPX:
                outputGPX(flight_dict)
    
    exit()
