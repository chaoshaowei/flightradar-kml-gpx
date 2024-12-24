import requests
import os
import argparse, textwrap
import json
import datetime, time
#-----------------------------
# Flags
#-----------------------------
SAVE_HEX2DATE_INFO = True
ID_SAMPLES = ['10000000', '11B63080', '1CC20400', '20000000', '30000000']

# Output options
OUT_FLT_NUM = True

COPY_TO_SPECIFIC_PATH = False

if __name__ == '__main__':
    #-----------------------------
    # directories
    #-----------------------------
    WORKING_DIR = os.path.dirname(os.path.realpath(__file__))

    RESPONSE_DIR = os.path.join(WORKING_DIR, 'Responses')
    RESPONSE_ERROR_DIR = os.path.join(WORKING_DIR, 'Responses_Error')
    HEADERS_FILE = os.path.join(WORKING_DIR, 'Templates', 'headers.json')

    FR24_HEX_DATE_FILE = os.path.join(WORKING_DIR, 'fr24_hex_date.csv')
    FLEET_LIST_FILE = os.path.join(WORKING_DIR, 'fleet_list.txt')
    COOKIE_FILE = os.path.join(WORKING_DIR, 'cookie.txt')
    TOKEN_FILE = os.path.join(WORKING_DIR, 'token.txt')
    
    HEX_DIR = os.path.join(WORKING_DIR, 'HEXs')
    if not os.path.exists(HEX_DIR):
        os.makedirs(HEX_DIR)
    
    KML_TEMPLATE_FILE = os.path.join(WORKING_DIR, 'Templates', 'kml_template.xml')
    with open (KML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        KML_TEMPLATE = ''.join(f.readlines())

    GPX_TEMPLATE_FILE = os.path.join(WORKING_DIR, 'Templates', 'gpx_template.xml')
    with open (GPX_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        GPX_TEMPLATE = ''.join(f.readlines())
    
    HELP_TEXT_FILE = os.path.join(WORKING_DIR, 'Templates', 'help.txt')
    with open(HELP_TEXT_FILE, 'r', encoding='utf-8') as f:
        HELP_TEXT = ''.join(f.readlines())

    #-----------------------------
    # Constants
    #-----------------------------
    REG_URL_TEMPLATE = 'https://api.flightradar24.com/common/v1/flight/list.json?query=[REG_ID]&fetchBy=reg&limit=100&token=[TOKEN]&page=[PAGE]'
    FLIGHT_URL_TEMPLATE = 'https://api.flightradar24.com/common/v1/flight-playback.json?flightId=[FLIGHT_ID]&timestamp=[TIMESTAMP]'

    #-----------------------------
    # Utilities
    #-----------------------------
    def multiple_requests(s: requests.Session, url: str, method: str = 'GET', headers: dict = {}):
        r = s.request(method=method, url=url, headers=headers)
        while r.status_code in [402, 520]:
            print('    Too many requests, cooling down')
            time.sleep(30)
            r = s.request(method=method, url=url, headers=headers)
        return r

    class Flight_Summary:
        def __init__(self, hex_id: str):
            self.hex_id: str = hex_id
            self.timestamp: int = 0
            self.callsign: str = ''
            self.origin: str = 'XXX'
            self.real_dest: str = 'XXX'
        
        @classmethod
        def from_dict(self, raw_summary: dict):
            if raw_summary.keys() != set(['hex_id', 'timestamp', 'callsign', 'origin', 'real_dest']):
                return None
            summary = Flight_Summary(raw_summary['hex_id'])
            summary.timestamp = raw_summary['timestamp']
            summary.callsign = raw_summary['callsign']
            summary.origin = raw_summary['origin']
            summary.real_dest = raw_summary['real_dest']
            return summary
        
        def __jsonencode__(self):
            return {
                'hex_id': self.hex_id,
                'timestamp': self.timestamp,
                'callsign': self.callsign,
                'origin': self.origin,
                'real_dest': self.real_dest
                }

    # A class for encoding object into JSON
    class AdvancedJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, '__jsonencode__'):
                return obj.__jsonencode__()

            if isinstance(obj, set):
                return list(obj)
            return json.JSONEncoder.default(self, obj)
    #-----------------------------
    # Main functions
    #-----------------------------
    # List flights' hex ids from reg
    def list_flights(reg_id: str, s: requests.Session, headers: dict, output_tz: datetime.timezone = datetime.timezone.utc, token: str=""):
        print(f"\nListing Flight of [{reg_id}]")
        
        # Result may have multiple pages
        page = 1
        more_page = True
        ids: list[str] = []
        summaries: list[Flight_Summary] = []
        REG_URL_ADDITIONAL_TEMPLATE = '&timestamp=[TIMESTAMP]&olderThenFlightId=[HEX_ID]'
        
        while more_page:
            os.makedirs(os.path.join(RESPONSE_DIR, reg_id), exist_ok=True)
            RESPONSE1_FILE = os.path.join(RESPONSE_DIR, reg_id, f'List_{reg_id}_{page:03d}.json')
            print(f"  Getting Page {page:3d} of [{reg_id}]")
            
            # Generate URL
            reg_url = REG_URL_TEMPLATE.replace('[REG_ID]', reg_id).replace('[TOKEN]', token).replace('[PAGE]', str(page))
            # If more than one page, payload needs to include some details about last page
            if page > 1:
                time.sleep(2)
                last_id = list_dict['result']['response']['data'][-1]['identification']['id']
                # If the last flight within the page is None, it should be converted into '' 
                if not last_id:
                    last_id = ''
                timestamp = list_dict['result']['response']['data'][-1]['time']['scheduled']['departure']
                reg_url += REG_URL_ADDITIONAL_TEMPLATE.replace('[TIMESTAMP]', str(timestamp)).replace('[HEX_ID]', last_id)

            # Getting Data
            r = multiple_requests(s, reg_url, method='GET', headers=headers)
            if r.status_code!=200:
                print(f'Error code {r.status_code}')
                return []

            # Saving Data
            if save_response:
                with open(RESPONSE1_FILE, 'w', encoding='utf-8') as f:
                    f.write(r.text)

            # Processing Data
            list_dict = json.loads(r.text)

            if list_dict['result']['response']['data'] is None:
                print('  No results found')
                return ids, summaries
        
            ids += [list_dict['result']['response']['data'][i]['identification']['id'] for i in range(len(list_dict['result']['response']['data'])) if list_dict['result']['response']['data'][i]['identification']['id']]

            # Extracting summary of each flight
            for data in list_dict['result']['response']['data']:
                if data['identification']['id'] is not None:
                    flight_summary = Flight_Summary(data['identification']['id'])
                else:
                    continue
                # Callsign
                if data['identification']['number']['default']:
                    flight_summary.callsign = data['identification']['number']['default']
                else:
                    flight_summary.callsign = f"({data['identification']['callsign']})"
                # Real Departure Time
                if data['time']['real']['departure']:
                    flight_summary.timestamp = data['time']['real']['departure']
                else:
                    flight_summary.timestamp = data['time']['scheduled']['departure']
                # Origin
                if data['airport']['origin']:
                    flight_summary.origin = data['airport']['origin']['code']['iata']
                # Real Destination
                if data['airport']['real']:
                    flight_summary.real_dest = data['airport']['real']['code']['iata']
                elif data['airport']['destination']:
                    flight_summary.real_dest = data['airport']['destination']['code']['iata']
                # Append to summaries list
                summaries.append(flight_summary)

            # Prepare for next page
            more_page = list_dict['result']['response']['page']['more']
            page += 1
        
        # Save summaries to file
        if save_response:
            HEX_FILE = os.path.join(HEX_DIR, f'{reg_id}_hex.json')
            valid_old_file = False
            old_summaries: list[Flight_Summary] = []
            # Check whether old file exists
            if os.path.exists(HEX_FILE):
                valid_old_file = True
                with open(HEX_FILE, 'r', encoding='utf-8') as f:
                    try:
                        loaded_dict: dict = json.load(f)
                    except json.decoder.JSONDecodeError:
                        loaded_dict = {}
                # Our target reg_id is the only key in the loaded file
                if len(loaded_dict) == 1 and reg_id in loaded_dict.keys():
                    for raw_summary in loaded_dict[reg_id]:
                        old_summary = Flight_Summary.from_dict(raw_summary)
                        if not isinstance(old_summary, Flight_Summary):
                            valid_old_file = False
                            break
                        old_summaries.append(old_summary)
                else:
                    valid_old_file = False
                # After iterating old file, decide which to do
                if valid_old_file:
                    print('  Old file found: Appending')
                else:
                    old_summaries = []
                    print('  Old file found: Overwriting')
            # Merging with old summaries
            for old_summary in old_summaries:
                if old_summary.hex_id not in ids and type(old_summary.hex_id) is str:
                    summaries.append(old_summary)
            summaries = sorted(summaries, key=lambda x: x.hex_id, reverse=True)
            # Output final result
            with open(HEX_FILE, 'w', encoding='utf-8') as f:
                json.dump({reg_id: summaries}, f, indent=2, cls=AdvancedJSONEncoder)
        
        print(f'  {len(ids):2d} results found:')
        print(f'    {ids[0]}')
        print(f'      ....')
        print(f'    {ids[-1]}\n')
        return ids, summaries
    
    
    # List flights' hex ids from reg
    def list_flights_from_list(s: requests.Session, headers: dict, output_tz: datetime.timezone = datetime.timezone.utc, token: str = ''):
        # Getting reg list
        with open(FLEET_LIST_FILE, 'r') as f:
            reg_id_list: list[str] = [line.strip() for line in f.readlines() if not line.strip().startswith('#')]
        
        print(f'Listing Flights of {len(reg_id_list)} aircrafts, this might take a while')
        
        # Iterate across regs
        ids_dict: dict[str:list[str]] = {}
        summaries_dict: dict[str:list[Flight_Summary]] = {}
        for reg_id in reg_id_list:
            # Get flight from a reg
            ids, summaries = list_flights(reg_id, s, headers, output_tz, token)
            ids_dict[reg_id] = ids
            summaries_dict[reg_id] = summaries
            time.sleep(1)

        return ids_dict, summaries_dict

    # Fetch data of flight hex id
    def search_flight(flight_id: str, s: requests.Session, headers: dict, output_tz: datetime.timezone = datetime.timezone.utc, clear_cookie: bool = False, save_hex2date: bool = True):
        print(f"\nSearching Flight: {flight_id}")

        # Generate URL
        timestamp_str = str(int((datetime.datetime.now()).timestamp()))
        flight_url = FLIGHT_URL_TEMPLATE.replace('[FLIGHT_ID]', flight_id).replace('[TIMESTAMP]', timestamp_str)
        print("  "+flight_url)

        # Getting Data
        if clear_cookie:
            s.cookies.clear()
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

        # Filename will depend on flight status
        if full_dict['result']['response']['data']['flight']['status']['generic']['status']['text'] in ['landed', 'diverted']:
            print(f"  {reg}, {full_dict['result']['response']['data']['flight']['status']['generic']['status']['text']}")
            if save_response:
                os.makedirs(os.path.join(WORKING_DIR, 'Responses', reg), exist_ok=True)
                RESPONSE2_FILE = os.path.join(WORKING_DIR, 'Responses', reg, f'{eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")}_{flight_id}.json')
                with open(RESPONSE2_FILE, 'w', encoding='utf-8') as f:
                    f.write(r.text)
        else:
            # For tracks that have status not in ['landed', 'diverted']
            print(f"  {reg}, {full_dict['result']['response']['data']['flight']['status']['generic']['status']['text']}")
            if save_response:
                os.makedirs(os.path.join(RESPONSE_ERROR_DIR, reg), exist_ok=True)
                RESPONSE2_FILE = os.path.join(RESPONSE_ERROR_DIR, reg, f'{eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")}_{flight_id}.json')
                with open(RESPONSE2_FILE, 'w', encoding='utf-8') as f:
                    f.write(r.text)
            else:
                print("    json will not be saved")
        
        # TODO, Saving to hex-to-date database
        if save_hex2date:
            for trkpt_dict in full_dict['result']['response']['data']['flight']['track']:
                trkptTime = datetime.datetime.fromtimestamp(trkpt_dict['timestamp'], tz=datetime.timezone.utc)
                print(trkptTime.isoformat())
                break

        return full_dict['result']['response']['data']['flight']

    # Save fetched data to kml
    def outputKML(flight_dict: dict, specific_path, output_tz: datetime.timezone = datetime.timezone.utc, timezone_mode = 2):
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
        if timezone_mode == TIMEZONE_UTC:
            time_str = eventTime.isoformat(timespec="minutes").replace("+00:00", "Z").replace(":","")
        elif timezone_mode == TIMEZONE_CUSTOM:
            time_str = eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")
        elif timezone_mode == TIMEZONE_AUTO:
            try:
                output_tzinfo = datetime.timezone(datetime.timedelta(seconds=flight_dict['airport']['destination']['timezone']['offset']))
                time_str = eventTime.astimezone(tz=output_tzinfo).isoformat(timespec="minutes").replace(":","")
            except TypeError:
                time_str = eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")
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
        if specific_path:
            kml_file_list.append(os.path.join(specific_path, kml_filename))
        for kml_file in kml_file_list:
            with open(kml_file, 'w', encoding='utf-8') as f:
                trk_name_str = 'Flight'
                if OUT_FLT_NUM:
                    trk_name_str += f' {flt_num}'
                trk_name_str += f' of {reg} at {eventTime.strftime("%Y-%m-%dZ")}'
                f.write(KML_TEMPLATE.replace('[COORDS]', coords_str).replace('[TRK_NAME]', trk_name_str).replace('[TRK_DSCRP]', f'{trk_name_str}, {flight_id}@FR24'))

    # Save fetched data to gpx
    def outputGPX(flight_dict: dict, specific_path, output_tz: datetime.timezone = datetime.timezone.utc, timezone_mode = 2):
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
        if timezone_mode == TIMEZONE_UTC:
            time_str = eventTime.isoformat(timespec="minutes").replace("+00:00", "Z").replace(":","")
        elif timezone_mode == TIMEZONE_CUSTOM:
            time_str = eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")
        elif timezone_mode == TIMEZONE_AUTO:
            try:
                output_tzinfo = datetime.timezone(datetime.timedelta(seconds=flight_dict['airport']['destination']['timezone']['offset']))
                time_str = eventTime.astimezone(tz=output_tzinfo).isoformat(timespec="minutes").replace(":","")
            except TypeError:
                time_str = eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")

        # Handle output filename
        gpx_filename = time_str
        if OUT_FLT_NUM:
            gpx_filename += f'_{flt_num}'
        gpx_filename += f'_{reg}_{flight_id}.gpx'

        os.makedirs(os.path.join(WORKING_DIR, 'GPXs', reg), exist_ok=True)
        # Default gpx output
        gpx_file_list = [os.path.join(WORKING_DIR, 'GPXs', reg, gpx_filename)]
        if specific_path:
            gpx_file_list.append(os.path.join(specific_path, gpx_filename))
        for gpx_file in gpx_file_list:
            with open(gpx_file, 'w', encoding='utf-8') as f:
                trk_name_str = 'Flight'
                if OUT_FLT_NUM:
                    trk_name_str += f' {flt_num}'
                trk_name_str += f' of {reg} at {eventTime.strftime("%Y-%m-%dZ")}'
                f.write(GPX_TEMPLATE.replace('[COORDS]', coords_str).replace('[TIME]', eventTime.astimezone(tz=output_tz).isoformat(timespec="minutes").replace(":","")).replace('[TRK_NAME]', trk_name_str))

    #-----------------------------
    # Argument parser
    #-----------------------------
    parser = argparse.ArgumentParser(prog='A FR24 track downloader', description=HELP_TEXT, epilog='... and that is how you easily create your track collection.\nFor more question, check out the gitHub page!',formatter_class=argparse.RawTextHelpFormatter)
    
    # Runmodes
    parser_rm_group = parser.add_mutually_exclusive_group(required=True)
    parser_rm_group.add_argument('-r0', action='store', metavar='REG', type=str
                                 , help='\nlist flights by registration "REG", but not fetching data')
    parser_rm_group.add_argument('-r1', action='store', metavar='REG', type=str
                                 , help='\nfetch all flights by registration "REG"')
    parser_rm_group.add_argument('-r2', action='store', metavar='HEX_ID', type=str
                                 , help='\nfetch flight of FR24 HEX_ID')
    parser_rm_group.add_argument('-r3', action='store', metavar='HEX_ID1', nargs='*', type=str
                                 , help='\nfetch flights of FR24 HEX_IDs')
    parser_rm_group.add_argument('-r4', action='store', metavar='HEX_ID', nargs=2, type=str
                                 , help='\nwalkthough all flights between two FR24 HEX_IDs')
    parser_rm_group.add_argument('-r5', action='store_true'
                                 , help='\nlist flights in "fleet_list.txt", but not fetching data\n\n')

    # Optional Variables
    parser.add_argument('-tzm', '--timezone-mode', action='store', dest='timezone_mode', type=int, default=2, choices=range(3)
                        , help= textwrap.dedent('''\
                        Output modes of time in output filename
                        0, UTC   : 2023-09-08T1230Z
                        1, CUSTOM: 2023-09-08T2030+0800 (specified in "-tzo" option)
                        2, AUTO  : 2023-09-08T2030+0800 (use FR24 Destination's timezone, default)
    '''))
    parser.add_argument('-tzo', '--timezone-offset', action='store', metavar='H', dest='timezone_offset', default=0, type=float
                        , help='desired timezone offset in hour, if "-tzm" option is 1')
    
    parser.add_argument('-ck', '--cookie', action='store_true', dest='use_cookie'
                        , help='Use cookie in "cookie.txt"')
    parser.add_argument('-nr', '--no-response', action='store_false', dest='save_response'
                        , help="don't save response file fetched from server")
    parser.add_argument('-ng', '--no-gpx', action='store_false', dest='output_gpx'
                        , help="don't save as gpx file after fetched from server")
    parser.add_argument('-nk', '--no-kml', action='store_false', dest='output_kml'
                        , help="don't save as kml file after fetched from server")
    parser.add_argument('-nh', '--no-hex2date', action='store_false', dest='save_hex2date'
                        , help="don't save relationship between fr24 hex_id & flight date")
    parser.add_argument('-c', '--copy', action='store', dest='specific_path', metavar='PATH'
                        , help="also save another GPX/KML copy to specified folder")
    
    #-----------------------------
    # Parse argument
    #-----------------------------
    # To verify a hex id is valid
    def is_valid_hex(input_str: str, digit: int=8):
        if len(input_str) <= digit:
            try:
                int(input_str, 16)
                return True
            except ValueError:
                pass
        print(f'error: invalid FR24 HEX_ID: [{input_str}]')
        return False
    
    # Some old constants
    LIST_FLIGHT_BY_REG = 0
    SEARCH_FLIGHT_BY_REG = 1
    SEARCH_FLIGHT_BY_FLIGHT_ID = 2
    SEARCH_FLIGHT_BY_FLIGHT_IDS = 3
    RUN_FOR_A_RANGE = 4
    LIST_FLIGHT_BY_REG_LIST = 5
    
    TIMEZONE_UTC = 0
    TIMEZONE_CUSTOM = 1
    TIMEZONE_AUTO = 2
    
    arg_dict = vars(parser.parse_args())

    timezone_mode = arg_dict['timezone_mode']
    timezone_offset = arg_dict['timezone_offset']
    output_tz = datetime.timezone(datetime.timedelta(hours=timezone_offset))
    
    save_response = arg_dict['save_response']
    output_gpx = arg_dict['output_gpx']
    output_kml = arg_dict['output_kml']
    save_hex2date = arg_dict['save_hex2date']
    
    specific_path = arg_dict['specific_path']
    if specific_path:
        COPY_TO_SPECIFIC_PATH = True

    # session object
    token = ''
    s = requests.Session()
    with open(HEADERS_FILE, 'r', encoding='utf-8') as f1:
        headers = json.load(f1)
    if arg_dict['use_cookie']:
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            cookie_text = ''.join(f.readlines())
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token = ''.join(f.readlines())
        headers['Cookie'] = cookie_text
    
    # Different logic based on run modes
    if arg_dict['r0']:
        run_mode = LIST_FLIGHT_BY_REG
        reg_id = arg_dict['r0']
        ids, summaries = list_flights(reg_id=reg_id, s=s, headers=headers, output_tz=output_tz, token=token)
        ids = []
    elif arg_dict['r1']:
        run_mode = SEARCH_FLIGHT_BY_REG
        reg_id = arg_dict['r1']
        ids, summaries = list_flights(reg_id=reg_id, s=s, headers=headers, output_tz=output_tz)
    elif arg_dict['r2'] or arg_dict['r3']:
        run_mode = SEARCH_FLIGHT_BY_FLIGHT_IDS
        ids = []
        if arg_dict['r2']:
            arg_dict['r3'] = [arg_dict['r2']]
        for id in arg_dict['r3']:
            if(is_valid_hex(id)):
                flight_id = id
                ids.append(id)
    elif arg_dict['r4']:
        run_mode = RUN_FOR_A_RANGE
        ids = []
        start_hex = arg_dict['r4'][0]
        end_hex = arg_dict['r4'][1]
        if is_valid_hex(start_hex) and is_valid_hex(end_hex):
            start_num = int(start_hex, 16)
            end_num = int(end_hex, 16)
            ids = ['{:08x}'.format(i).upper() for i in range(start_num, end_num)]
            print(f"Tranversing all {len(ids)} entries")
        else:
            print(f'error: please check enclosing HEX_IDs')
    if arg_dict['r5']:
        run_mode = LIST_FLIGHT_BY_REG_LIST
        reg_id = arg_dict['r5']
        ids_dict, summaries_dict = list_flights_from_list(s=s, headers=headers, output_tz=output_tz, token=token)
        ids = []

    #-----------------------------
    # Constants
    #-----------------------------
    ENABLE_SLEEP = True
    SLEEP_EVERY_N_SEARCH = 100
    EVERY_SLEEP_DURATION = 5

    #-----------------------------
    # Addtional directories
    #-----------------------------
    os.makedirs(RESPONSE_DIR, exist_ok=True)

    if COPY_TO_SPECIFIC_PATH:
        print(f'Also copying to "{specific_path}"')
        SPECIFIC_GPX_PATH = os.path.join(specific_path, 'GPXs')
        SPECIFIC_KML_PATH = os.path.join(specific_path, 'KMLs')
        os.makedirs(SPECIFIC_GPX_PATH, exist_ok=True)
        os.makedirs(SPECIFIC_KML_PATH, exist_ok=True)
    else:
        SPECIFIC_GPX_PATH = None
        SPECIFIC_KML_PATH = None

    if run_mode in [SEARCH_FLIGHT_BY_REG, SEARCH_FLIGHT_BY_FLIGHT_ID, SEARCH_FLIGHT_BY_FLIGHT_IDS, RUN_FOR_A_RANGE]:
        search_cycle = 0
        for flight_id in ids:
            if ENABLE_SLEEP:
                if search_cycle >= SLEEP_EVERY_N_SEARCH:
                    time.sleep(EVERY_SLEEP_DURATION)
                    search_cycle = 0
                search_cycle += 1
            try:
                flight_dict = search_flight(flight_id=flight_id, s=s, headers=headers, output_tz=output_tz, save_hex2date=save_hex2date)
            except KeyError as e:
                print('    '+str(e))
                continue
            except TypeError as e:
                print('    '+str(e))
                continue
            except IndexError as e:
                print('    '+str(e))
                continue
            except AttributeError as e:
                for i in range(10):
                    try:
                        time.sleep(EVERY_SLEEP_DURATION*(i+1))
                        print('    AttributeError, retry shortly')
                        flight_dict = search_flight(flight_id=flight_id, s=s, headers=headers, output_tz=output_tz, clear_cookie=True, save_hex2date=save_hex2date)
                        break
                    except AttributeError as e:
                        if i > 8:
                            print('Too many AttributeError, exiting...')
                            exit()
                        else:
                            continue
            if output_kml:
                outputKML(flight_dict, specific_path=SPECIFIC_KML_PATH, timezone_mode=timezone_mode)
            if output_gpx:
                outputGPX(flight_dict, specific_path=SPECIFIC_GPX_PATH, timezone_mode=timezone_mode)
    
    exit()
