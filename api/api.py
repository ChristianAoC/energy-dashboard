# Original code by Paul Smith
# Adapted and expanded by Christian Remy

from flask import Blueprint, jsonify, make_response, request, Response, json
import datetime as dt
import pandas as pd
from influxdb import InfluxDBClient
from dotenv import load_dotenv
import os

api_bp = Blueprint('api_bp', __name__, static_url_path='')

load_dotenv()
InfluxURL = os.getenv("INFLUX_URL")
InfluxPort = os.getenv("INFLUX_PORT")
InfluxUser = os.getenv("INFLUX_USER")
InfluxPass = os.getenv("INFLUX_PASS")

offlineMode = False
if InfluxURL == None or InfluxPort == None or InfluxUser == None or InfluxPass == None:
    offlineMode = True

meters_file = "./api/data/internal/UniMeters.json"
meters_weather_file = "./api/data/internal/weather_meters.json"
buildings_file = "./api/data/internal/UniHierarchy.json"
buildings_usage_file = "./api/data/internal/UniHierarchyWithUsage.json"

if not os.path.isfile(meters_file) or not os.path.isfile(buildings_file):
    offlineMode = True

meters_offline = "./api/data/meters.json"
buildings_offline = "./api/data/buildings.json"
usage_offline = "./api/data/usage.json"

## #################################################################
## constants - should not be changed later in code
def METERS():
    if not offlineMode and os.path.isfile(meters_weather_file):
        meters = json.load(open(meters_file)) + json.load(open(meters_weather_file))
    if not offlineMode:
        meters = json.load(open(meters_file))
    else:
        meters = json.load(open(meters_offline))
    meters = [m for m in meters if m["meter_id_clean"] is not None]
    return meters

def BUILDINGS():
    if offlineMode:
        return json.load(open(buildings_offline))
    return json.load(open(buildings_file))

# offline file needed so the UI doesn't wait for the API call to compute sample usage
def BUILDINGSWITHUSAGE():
    if offlineMode:
        return json.load(open(usage_offline))
    return json.load(open(buildings_usage_file))

## #################################################################
## helper functions

# TODO ONLY FOR TESTING
offlineMode = True

## Get Data from influx
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
## agg - aggregation as accepted by pandas time aggregation - raw leave data alone (str)
## to_rate - logical, should data be "un-cumulated"
def query_time_series(m, from_time, to_time, agg="raw", to_rate=False):
    ## set come constants
    max_time_interval = dt.timedelta(days=3650)
    
    ## convert to UTC for influx
    from_time = from_time.astimezone(dt.timezone.utc)
    to_time = to_time.astimezone(dt.timezone.utc)
        
    ## check time limits
    if to_time - from_time > max_time_interval:
        from_time = to_time - max_time_interval

    ## set the basic output
    out = {
        "uuid": m["meter_id_clean"],
        #"label": m["serving"], #user serving revised because this is way too lengthy
        "label": m["serving_revised"],
        "obs": [],
        "unit": m["units_after_conversion"]
    }

    obs = []

    if not offlineMode:
        if m["raw_uuid"] is None: ## can't get data
            return out

        ## format query
        qry = 'SELECT * as value FROM "SEED"."autogen"."' + m["raw_uuid"] + \
            '" WHERE time >= \'' + from_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\'' + \
            ' AND time <= \'' + to_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\''

        ## create client for influx
        client = InfluxDBClient(host = InfluxURL,
                                port = InfluxPort,
                                username = InfluxUser,
                                password = InfluxPass)
        
        result = client.query(qry)

        ## get as list of dictionaries
        obs = list(result.get_points())

    else:
        f = open('api/data/sample/'+m["meter_id_clean"]+'.json',)
        obs = json.load(f)
        f.close()

        newobs = []
        for o in obs:
            if dt.datetime.strptime(o["time"], "%Y-%m-%dT%H:%M:%S+0000").astimezone(dt.timezone.utc) >= from_time.astimezone(dt.timezone.utc) and dt.datetime.strptime(o["time"], "%Y-%m-%dT%H:%M:%S+0000").astimezone(dt.timezone.utc) <= to_time.astimezone(dt.timezone.utc):
                o["time"] = o["time"][:-5] + 'Z'
                newobs.append(o)

        obs = newobs

    if len(obs)==0:
        return out
    
    ## standarise the value based on resolution and format time
    if m["resolution"] is not None:
        kappa = m["unit_conversion_factor"] / m["resolution"]
        rho = m["resolution"]
    else:
        kappa = 1.0
        rho = 1.0
        
    for o in obs:
        o['value'] = round( rho * round(o["value"] * kappa) ,10 )
        o['time'] = o['time'][:-1] + '+0000'
            
    ## uncumulate if required
    if to_rate and (m["class"] == "Cumulative"):
        xcur = obs[-1]["value"]
        for ii in reversed(range(len(obs)-1)):
            if obs[ii]["value"]==0:
                obs[ii]["value"] = None
                
            if obs[ii]["value"] == None:
                obs[ii+1]["value"] = None ## rate on next step not valid
                continue
            
            if xcur==None:
                xcur = obs[ii]["value"]
                
            if obs[ii]["value"] > xcur:
                ## can't be valid
                obs[ii]["value"] = None
            else:
                xcur = obs[ii]["value"]
                
            if obs[ii+1]["value"]==None or obs[ii]["value"]==None:
                obs[ii+1]["value"] = None
            else:
                obs[ii+1]["value"] -= obs[ii]["value"] ## change to rate

        obs[0]["value"] = None

    ## aggregate and scale
    if agg != "raw":
        df = pd.DataFrame.from_dict(obs)
        df['time'] = pd.to_datetime(df['time'],format = '%Y-%m-%dT%H:%M:%S%z', utc=True)
        df.set_index('time', inplace=True)
        df = df.resample(agg, origin='end').sum() ## windows go backwards

        df.reset_index(inplace=True)
        df['time'] = df['time'].dt.strftime('%Y-%m-%dT%H:%M:%S%z') ## check keeps utc?
        
        obs = json.loads(df.to_json(orient='records')) #This is ugly buut seems to avoid return NaN rather then null - originaly used pd.DataFrame.to_dict(df,orient="records")

    out["obs"] = obs
    
    return out

## Get time of last observation
## m - meter
## to_time - time to get data to (datetime)
## from_time - time to get data from (datetime)
def query_last_obs_time(m, to_time, from_time):

    # if offline, last obs is simply last line of file
    if offlineMode:
        try:
            f = open('api/data/sample/'+m["meter_id_clean"]+'.json',)
        except:
            return make_response("Offline mode and can't open/find a file for this UUID", 500)
        obs = json.load(f)
        f.close()
        if len(obs) > 0:
            return obs[-1]["time"]

    ## convert uuid to string for query
    ##ustr = ",".join(['"SEED"."autogen"."'+x+'"' for x in uuid])
    if m["raw_uuid"] is None:
        return None
    
    ustr = '"SEED"."autogen"."' + m["raw_uuid"] + '"'
    ## convert to_time to correct time zone
    to_time = to_time.astimezone(dt.timezone.utc)
    from_time = from_time.astimezone(dt.timezone.utc)

    ## form query
    qry = 'SELECT LAST(value) FROM ' + ustr + ' WHERE time <= \'' + to_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\'' + \
        ' AND time >= \'' + from_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\''
    
    ## create client for influx
    client = InfluxDBClient(host = InfluxURL,
                            port = InfluxPort,
                            username = InfluxUser,
                            password = InfluxPass)
    
    result = client.query(qry)
    out = list(result.get_points())
    if len(out)>0:
        out = out[0]['time']
        out = out[:-1] + '+0000'
    else:
        out = None
    
    return out
    ## handle result
    # out = dict.fromkeys(uuid)    
    # for u in uuid:
    #     out[u] = list(result.get_points(measurement=u))

    # return out


## #############################################################################################

## simple health check the server is running
## Parameters:
## Return:
## current time
@api_bp.route('/', methods=["GET"])
def health():
    return make_response(jsonify( dt.datetime.now(dt.timezone.utc) ), 200)

## Return the building -> meter hierarchy that is statically cached
##
## Parameters: None
##
## Return:
## json containing the structure
##
## Example:
## http://127.0.0.1:5000/hierarchy
@api_bp.route('/hierarchy')
def hierarchy():
    return make_response(jsonify( BUILDINGS() ), 200)

## Helper function needed for accessing raw list of all meters in other blueprint
@api_bp.route('/devices')
def devices():
    return METERS()

## Helper function needed for accessing quick usage list so UI doesn't delay too much
@api_bp.route('/usageoffline')
def usageoffline():
    return BUILDINGSWITHUSAGE()

## Return summary of the energy usage over all buildings with main meters and mazemap ids
##
## Parameters:
## from_time - options inital date YYYY-mm-dd format (summary of usage from 00:00 of this date) - default 7 days before to_time
## to_time - options final observation time in YYYY-mm-dd format (summary of usage upto 23:59 of this date) - default current date
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/summary
@api_bp.route('/summary')
def summary():
    try:
        to_time = request.args["to_time"] # this is url decoded
        to_time = dt.datetime.combine(
            dt.datetime.strptime(to_time,"%Y-%m-%d"),
            dt.datetime.max.time())
    except:
        to_time = dt.datetime.combine(dt.date.today(), dt.datetime.max.time()) ## check

    try:
        from_time = request.args["from_time"]
        from_time = dt.datetime.combine(
            dt.datetime.strptime(from_time,"%Y-%m-%d"),
            dt.datetime.min.time()) ## check
    except:
        from_time = to_time - dt.timedelta(days=7) + dt.timedelta(seconds=1)

        
    ## trim out buildings with no mazemap id
    buildings = [x for x in BUILDINGS() if x["maze_map_label"]]

    ## trim out meters that aren't building
    for b in buildings:
        b["meters"][:] = [m for m in b["meters"] if m["building_level_meter"]]

    ## trim out buildings with no building meters        
    buildings[:] = [x for x in buildings if len(x["meters"])>0] ## remove buildings with no principle sensors

    ## process each building into correct format - slow...
    for b in buildings:

        ## process the energy usage
        for ii in ['gas','electricity','heat','water']:
            b[ii] = {'sensor_label':[],'sensor_uuid':[],'usage':None,'eui':None, 'unit': None, 'eui_annual': None}
            if ii == "gas":
                b[ii]['unit'] = "m3"
            elif ii == "electricity":
                b[ii]['unit'] = "kWh"                
            elif ii == "heat":
                b[ii]['unit'] = "MWh"
            elif ii == "water":
                b[ii]['unit'] = "m3"
                
        for s in b.pop("meters",[]):
            v = s["meter_type"].lower()

            x = query_time_series(s, from_time, to_time, agg='876000h', to_rate=True)

            b[v]['sensor_label'].append( x["label"] )
            b[v]['sensor_uuid'].append( x['uuid'] )
            
            if len(x['obs']) > 0:
                usage = x['obs'][0]['value']

                ## handle unit changes
                if v == "gas":
                    if x['unit'] != "m3":
                        print( x["meter_id_clean"] + ": " + x['unit'] + " is an unknown unit for gas" )
                elif v == "electricity":
                    if x['unit'] != "kWh":
                        print( x["meter_id_clean"] + ": " + x['unit'] + " is an unknown unit for electricity" )
                elif v == "heat":
                    if x['unit'] == "kWh":
                        usage *= 1e-3 # to MWh
                        x['unit'] = "MWh"
                    if x['unit'] == "kW":
                        usage = round(usage * 1e-3 * (1.0/6.0),3 ) ## presume 10 minute data, round to nearest kWh
                        x['unit'] = "MWh"
                    if x['unit'] != "MWh":
                        print( x["meter_id_clean"] + ": " + x['unit'] + " is an unknown unit for heat" )
                elif v == "water":
                    if x['unit'] != "m3":
                        print( s["meter_id_clean"] + ": " + x['unit'] + " is an unknown unit for water" )

                
                if b[v]['usage'] is None:    
                    b[v]['usage'] = usage
                else:
                    b[v]['usage'] += usage

        ## process EUI
        if b["floor_area"] is not None:
            for ii in ['gas','electricity','heat','water']:
                if b[ii]["usage"] is not None:
                    ## raw EUI
                    x = b[ii]["usage"] / b["floor_area"]
                    b[ii]["eui"] = float(f"{x:.2g}")
                    ## annual equivilent
                    x *= dt.timedelta(days=365) / (to_time - from_time)
                    b[ii]["eui_annual"] = float(f"{x:.2g}")
    
    return make_response(jsonify( buildings ), 200)

## Return the meters, optionally trimming by planon or meter_id_clean
##
## Parameters:
## planon - planon codes to filter by
## uuid - meter unique code to filter by
## lastobs - supply last obs data (slow if not limited to few meters)
##
## Return:
## json format time series data
##
## Example:
## http://127.0.0.1:5000/meter
## http://127.0.0.1:5000/meter?uuid=AP001_L01_M2
## http://127.0.0.1:5000/meter?lastobs=true
## http://127.0.0.1:5000/meter?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:500/meter?is_weather=true
@api_bp.route('/meter')
def meter():
    try:
        planon = request.args["planon"] # this is url decoded
        planon = planon.split(";")
    except:
        planon = None

    try:
        uuid = request.args["uuid"] # this is url decoded
        uuid = uuid.split(";")
    except:
        uuid = None

    try:
        lastobs = request.args["lastobs"].lower() # this is url decoded
    except:
        lastobs = None


    meters = METERS()
            
    if planon is not None:
        meters[:] = [x for x in meters if x["building"] in planon]

    if uuid is not None:
        meters[:] = [x for x in meters if x["meter_id_clean"] in uuid]

    to_time = dt.datetime.now(dt.timezone.utc)
    from_time = to_time - dt.timedelta(days=1)
    
    if lastobs == "true":
        for m in meters:
            m["last_obs_time"] = query_last_obs_time(m, to_time,from_time)

    return make_response(jsonify( meters ), 200)
        
## time series of data for a given sensor
##
## Parameters:
## uuid - meter uuid
## to_time - final observation time, defaults to current time
## from_time - first observation time, defaults to 7 days ago
## format - use csv if required otherwise returns json
## aggregate - aggregate as used by pandas e.g. 168H, 7D etc.
## Note that 168H and 7D are the same but only the formers works in pandas 2.0.3
## to_rate - should cumulative values be converted to rate
##
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/meter_obs?uuid=AP001_L01_M2
## http://127.0.0.1:5000/meter_obs?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/meter_obs?uuid=WTHR_0
@api_bp.route('/meter_obs')
def meter_obs():
    try:
        uuids = request.args["uuid"] # this is url decoded
        uuids = uuids.split(";")
    except:
        return make_response("Bad uuid supplied", 500)

    try:
        to_time = request.args["to_time"] # this is url decoded
        to_time = dt.datetime.strptime(to_time,"%Y-%m-%dT%H:%M:%S%z",)
    except:
        to_time = dt.datetime.now(dt.timezone.utc)
        
    try:
        from_time = request.args["from_time"] # this is url decoded
        from_time = dt.datetime.strptime(from_time,"%Y-%m-%dT%H:%M:%S%z")
    except:
        from_time = to_time - dt.timedelta(days=7)

    try:
        fmt = request.args["format"] # this is url decoded
    except:
        fmt = "json"
    
    try:
        agg = request.args["aggregate"] # this is url decoded
    except:
        agg = "raw"

    try:
        to_rate = request.args["to_rate"].lower() in ['true', '1', 't', 'y'] # this is url decoded
    except:
        to_rate = True 
    
    ## load and trim meters
    meters = METERS()
    meters[:] = [x for x in meters if x["meter_id_clean"] in uuids]

    out = dict.fromkeys(uuids)
    
    for m in meters:
        key = m["meter_id_clean"]
        out[key] = query_time_series(m, from_time, to_time,agg = agg, to_rate = to_rate)
                
    if(fmt=="csv"):
        try:
            csv = 'series,unit,time,value\n'
            ## repackage data as csv and return
            for k in out.keys():
                for obs in out[k]["obs"]:
                    csv += out[k]["uuid"] + ',' + out[k]["unit"] + "," + obs["time"] + ',' + str(obs["value"]) + '\n'

            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition":
                         "attachment; filename=mydata.csv"})
        except:
            return make_response("Unable to make csv file",500)
        
    else:
        return make_response(jsonify( out ), 200)


## Get record of pings to the meter
##
## Parameters:
## uuid - gauge id (planon style) or missing for all gauges
## to_time - final observation time, defaults to current time
## from_time - first observation time, defaults to 7 days ago
## summary - what type of summary to offer
##              - raw: raw data [default]
##              - last: time of latest sucessfull ping in windows (else null)
##              - perc: percentage of successfull pings
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/meter_ping?uuid=AP001_L01_M2
@api_bp.route('/meter_ping')
def meter_ping():
    if offlineMode:
        return make_response("Offline mode, can't ping meters", 500)
    
    meters = METERS()
    
    try:
        uuids = request.args["uuid"] # this is url decoded
        uuids = uuids.split(";")
    except:
        uuids = [x["meter_id_clean"] for x in meters]

    try:
        to_time = request.args["to_time"] # this is url decoded
        to_time = dt.datetime.strptime(to_time,"%Y-%m-%dT%H:%M:%S%z")
    except:
        to_time = dt.datetime.now(dt.timezone.utc)
        
    try:
        from_time = request.args["from_time"] # this is url decoded
        from_time = dt.datetime.strptime(from_time,"%Y-%m-%dT%H:%M:%S%z")
    except:
        from_time = to_time - dt.timedelta(days=7)

    try:
        summary = request.args["summary"] # this is url decoded
        if summary not in ["raw","perc","last"]:
            summary = "raw"
    except:
        summary = "raw"

    ## load and trim meters
    if uuids is not None:
        meters[:] = [x for x in meters if x["meter_id_clean"] in uuids]

    ## It is quicker to loop the number of logger since this is lower
    ## so make fake meters
    logger_uuids = [x["logger_uuid"] for x in meters if x["logger_uuid"]]
    logger_uuids = list(set(logger_uuids))
    def fm(x):
        return {"meter_id_clean": x, "raw_uuid":x,
                "Class":"Rate", "serving": None,
                "resolution": None,
                "units_after_conversion": None}
    
    loggers = [fm(x) for x in logger_uuids]

    ## get data for each logger
    logger_out = dict.fromkeys(logger_uuids)
    for l in loggers:
        key = l["meter_id_clean"]
        
        x = query_time_series(l, from_time, to_time)['obs']
        
        if summary == "perc":
            n = float(len(x))
            cnt = sum([i["value"] for i in x])
            x = round(100.0 * cnt / n,2) if n>0 else None
        elif summary == "last":
            x = [i["time"] for i in x if i["value"]==1] ## presumes data in time order
            x = x[-1] if x else None

        logger_out[key] = x
        
    ## copy back into meters
    out = dict.fromkeys(uuids)
    for m in meters:
        if m["logger_uuid"] in logger_uuids:
            out[ m["meter_id_clean"] ] = logger_out[ m["logger_uuid"] ]
        
    return make_response(jsonify( out ), 200)
    
## get last observation before the specified time
##
## Parameters:
## uuid - meter uuid
## to_time - final observation time, defaults to current time
##
## Return:
## json dictionary of last time or null is no observations
## Example:
## http://127.0.0.1:5000/last_meter_obs?uuid=AP001_L01_M2
## http://127.0.0.1:5000/last_meter_obs?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/last_meter_obs?uuid=WTHR_0
## http://127.0.0.1:5000/last_meter_obs?uuid=MC062_L01_M33_R2048&to_time=2024-01-01T00:00:00%2B0000
@api_bp.route('/last_meter_obs')
def last_meter_obs():
    try:
        uuids = request.args["uuid"] # this is url decoded
        uuids = uuids.split(";")
    except:
        return make_response("Bad uuid supplied", 500)

    try:
        to_time = request.args["to_time"] # this is url decoded
        to_time = dt.datetime.strptime(to_time,"%Y-%m-%dT%H:%M:%S%z",)
    except:
        to_time = dt.datetime.now(dt.timezone.utc)
        
    try:
        from_time = request.args["from_time"] # this is url decoded
        from_time = dt.datetime.strptime(from_time,"%Y-%m-%dT%H:%M:%S%z")
    except:
        from_time = to_time - dt.timedelta(days=7)

    meters = METERS()
    meters[:] = [x for x in meters if x["meter_id_clean"] in uuids]

    out = dict.fromkeys(uuids)
    
    for m in meters:
        key = m["meter_id_clean"]
        out[key] = query_last_obs_time(m, to_time, from_time)

    return make_response(jsonify( out ), 200)
