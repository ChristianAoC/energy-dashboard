import datetime

from flask import Blueprint, jsonify, make_response, request, Response, json
import datetime as dt
import pandas as pd
from influxdb import InfluxDBClient
from dotenv import load_dotenv
import os
import time
import threading
import csv
import math

api_bp = Blueprint('api_bp', __name__, static_url_path='')

load_dotenv()

val = os.getenv("OFFLINE_MODE", "True")
offlineMode = val.strip().lower() in ("1", "true", "yes", "on")

val = os.getenv("ANON_MODE", "True")
anonMode = val.strip().lower() in ("1", "true", "yes", "on")

InfluxURL = os.getenv("INFLUX_URL")
InfluxPort = os.getenv("INFLUX_PORT")
InfluxUser = os.getenv("INFLUX_USER")
InfluxPass = os.getenv("INFLUX_PASS")

if InfluxURL == None or InfluxPort == None or InfluxUser == None or InfluxPass == None:
    offlineMode = True

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

hc_update_time = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", "9"))

meters_file = os.path.join(DATA_DIR, "internal_meta", 'meters_all.json')
buildings_file = os.path.join(DATA_DIR, "internal_meta", 'UniHierarchy.json')
buildings_usage_file = os.path.join(DATA_DIR, "internal_meta", 'UniHierarchyWithUsage.json')

if not os.path.isfile(meters_file) or not os.path.isfile(buildings_file):
    offlineMode = True

hc_latest_file = os.path.join(DATA_DIR, "health_check", 'hc_latest.json')
hc_meta_file = os.path.join(DATA_DIR, "health_check", 'hc_meta.json')

meter_health_score_files = os.path.join(DATA_DIR, "meter_health_score")
meter_snapshots_files = os.path.join(DATA_DIR, "meter_snapshots")
meter_health_score_anon_files = os.path.join(DATA_DIR, "anon_meter_health_score")
meter_health_score_offline_files = os.path.join(DATA_DIR, "offline_meter_health_score")
meter_snapshots_anon_files = os.path.join(DATA_DIR, "anon_meter_snapshots")
meter_snapshots_offline_files = os.path.join(DATA_DIR, "offline_meter_snapshots")

meters_anon_file = os.path.join(DATA_DIR, "meta_anon", 'anon_meters.json')
buildings_anon_file = os.path.join(DATA_DIR, "meta_anon", 'anon_buildings.json')
usage_anon_file = os.path.join(DATA_DIR, "meta_anon", 'anon_usage.json')

## #################################################################
## constants - should not be changed later in code
def METERS():
    if anonMode == True:
        return json.load(open(meters_anon_file))
    return json.load(open(meters_file))

def BUILDINGS():
    if anonMode == True:
        return json.load(open(buildings_anon_file))
    return json.load(open(buildings_file))

# offline file needed so the UI doesn't wait for the API call to compute sample usage
def BUILDINGSWITHUSAGE():
    if anonMode == True:
        return json.load(open(usage_anon_file))
    return json.load(open(buildings_usage_file))

## #################################################################
## helper functions

## Minimal/efficient call - get time series as Pandas
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
def query_pandas(m, from_time, to_time):

    if m["raw_uuid"] is None: ## can't get data
        return pd.DataFrame()

    ## format query
    qry = 'SELECT * as value FROM "SEED"."autogen"."' + m["raw_uuid"] + \
        '" WHERE time >= \'' + from_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\'' + \
        ' AND time < \'' + to_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\''

    ## create client for influx
    client = InfluxDBClient(host = InfluxURL,
                            port = InfluxPort,
                            username = InfluxUser,
                            password = InfluxPass)

    return pd.DataFrame(client.query(qry).get_points())

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
        #"label": m["serving"], #use serving revised because this is way too lengthy
        "label": m["serving_revised"],
        "obs": [],
        "unit": m["units_after_conversion"]
    }

    obs = []

    if not offlineMode and not anonMode:
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
        try:
            if anonMode:
                f = open('api/data/anon/'+m["meter_id_clean"]+'.json',)
                obs = json.load(f)
                f.close()
            if offlineMode:
                f = open('api/data/offline/'+m["meter_id_clean"]+'.json',)
                obs = json.load(f)
                f.close()

            newobs = []
            for o in obs:
                if dt.datetime.strptime(o["time"], "%Y-%m-%dT%H:%M:%S+0000").astimezone(dt.timezone.utc) >= from_time.astimezone(dt.timezone.utc) and dt.datetime.strptime(o["time"], "%Y-%m-%dT%H:%M:%S+0000").astimezone(dt.timezone.utc) <= to_time.astimezone(dt.timezone.utc):
                    o["time"] = o["time"][:-5] + 'Z'
                    newobs.append(o)

            obs = newobs
        except:
            return out

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

    ## convert uuid to string for query
    ##ustr = ",".join(['"SEED"."autogen"."'+x+'"' for x in uuid])
    if m["raw_uuid"] is None:
        return None

    # if offline, last obs is simply last line of file
    if anonMode == True:
        try:
            f = open('api/data/sample/'+m["meter_id_clean"]+'.json',)
        except:
            return make_response("Anon mode and can't open/find a file for this UUID", 500)
        obs = json.load(f)
        f.close()
        if len(obs) > 0:
            return obs[-1]["time"]

    if offlineMode == True:
        try:
            f = open('api/data/offline/'+m["meter_id_clean"]+'.json',)
        except:
            return make_response("Offline mode and can't open/find a file for this UUID", 500)
        obs = json.load(f)
        f.close()
        if len(obs) > 0:
            return obs[-1]["time"]

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

## Retrieve data from influx and process it for meter health
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
## xcount - number of readings meters should have read
def process_meter_health(m: dict, from_time: datetime.datetime, to_time: datetime.datetime, xcount: int):
    # time series for this meter
    m_obs = query_pandas(m, from_time, to_time)
    # m_obs = query_time_series(m, from_time, to_time)["obs"]

    # count values. if no values, stop
    m["HC_count"] = len(m_obs)
    if m["HC_count"] == 0:
        m["HC_count_perc"] = "0%"
        m["HC_score"] = 0
        return

    m["HC_count_perc"] = round(100 * m["HC_count"] / xcount, 2)
    if m["HC_count_perc"] > 100:
        m["HC_count_perc"] = 100
    m["HC_count_score"] = math.floor(m["HC_count_perc"] / 20)
    m["HC_count_perc"] = str(m["HC_count_perc"]) + "%"

    # count zeroes
    m["HC_zeroes"] = int(m_obs["value"][m_obs["value"] == 0].count())
    m["HC_zeroes_perc"] = round(100 * m["HC_zeroes"] / xcount, 2)
    if m["HC_zeroes_perc"] > 100:
        m["HC_zeroes_perc"] = 100
    m["HC_zeroes_score"] = math.floor((100 - m["HC_zeroes_perc"]) / 20)
    m["HC_zeroes_perc"] = str(m["HC_zeroes_perc"]) + "%"

    # create diff (increase for each value) to prep for cumulative check
    m_obs["diffs"] = m_obs["value"].diff()
    diffcount = m_obs["diffs"].count().sum()
    if diffcount == 0:
        return

    # count positive, negative, and no increase
    m["HC_diff_neg"] = int(m_obs.diffs[m_obs.diffs < 0].count())
    m["HC_diff_neg_perc"] = round(100 * m["HC_diff_neg"] / diffcount, 2)
    if m["HC_diff_neg_perc"] > 100:
        m["HC_diff_neg_perc"] = 100

    m["HC_diff_pos"] = int(m_obs.diffs[m_obs.diffs > 0].count())
    m["HC_diff_pos_perc"] = round(100 * m["HC_diff_pos"] / diffcount, 2)
    if m["HC_diff_pos_perc"] > 100:
        m["HC_diff_pos_perc"] = 100
    m["HC_diff_pos_score"] = math.floor(m["HC_diff_pos_perc"] / 20)

    m["HC_diff_zero"] = int(m_obs.diffs[m_obs.diffs == 0].count())
    m["HC_diff_zero_perc"] = round(100 * m["HC_diff_zero"] / diffcount, 2)
    if m["HC_diff_zero_perc"] > 100:
        m["HC_diff_zero_perc"] = 100

    # assume that cumulative meters have > 80% of values increase and vice versa
    m["HC_class"] = m["class"]
    if m["HC_diff_zero_perc"] > 80:
        m["HC_class_check"] = "Too many zero diffs to check"

    if m["class"] == "Cumulative":
        if m["HC_diff_pos_perc"] < 80 and m["HC_diff_neg_perc"] > 20:
            m["HC_class_check"] = "Check (seems rate)"
            m["HC_class"] = "Rate"
        else:
            m["HC_class_check"] = "Okay (cumulative)"
    else:
        if m["HC_diff_pos_perc"] > 80:
            m["HC_class_check"] = "Check (seems cumulative)"
            m["HC_class"] = "Cumulative"
        else:
            m["HC_class_check"] = "Okay (rate)"

    m["HC_diff_neg_perc"] = str(m["HC_diff_neg_perc"]) + "%"
    m["HC_diff_pos_perc"] = str(m["HC_diff_pos_perc"]) + "%"
    m["HC_diff_zero_perc"] = str(m["HC_diff_zero_perc"]) + "%"

    m["HC_functional_matrix"] = m["HC_count_score"] * m["HC_zeroes_score"]

    # if cumulative (or assumed cumul) run statistics on that data, otherwise on raw
    if m["HC_class"] == "Cumulative":
        m["HC_mean"] = int(m_obs["diffs"].mean())
        m["HC_median"] = int(m_obs["diffs"].median())
        m["HC_mode"] = int(m_obs["diffs"].mode()[0])
        m["HC_std"] = int(m_obs["diffs"].std())
        m["HC_min"] = int(m_obs["diffs"].min())
        m["HC_max"] = int(m_obs["diffs"].max())
        m["HC_outliers"] = int(m_obs.diffs[m_obs.diffs > m["HC_mean"] * 5].count())
        m_obs["HC_ignz"] = m_obs[m_obs["diffs"] != 0]["diffs"]
        m["HC_cumulative_matrix"] = m["HC_diff_pos_score"] * m["HC_functional_matrix"]
        m["HC_score"] = math.floor(m["HC_cumulative_matrix"] / 25)

    else:
        m["HC_mean"] = int(m_obs["value"].mean())
        m["HC_median"] = int(m_obs["value"].median())
        m["HC_mode"] = int(m_obs["value"].mode()[0])
        m["HC_std"] = int(m_obs["value"].std())
        m["HC_min"] = int(m_obs["value"].min())
        m["HC_max"] = int(m_obs["value"].max())
        m["HC_outliers"] = int(m_obs["value"][m_obs["value"] > m["HC_mean"] * 5].count())
        m_obs["HC_ignz"] = m_obs[m_obs["value"] != 0]["value"]
        m["HC_score"] = math.floor(m["HC_functional_matrix"] / 5)

    m["HC_outliers_perc"] = round(100 * m["HC_outliers"] / xcount, 2)
    if m["HC_outliers_perc"] > 100:
        m["HC_outliers_perc"] = 100
    m["HC_outliers_perc"] = str(m["HC_outliers_perc"]) + "%"

    ignz_count = m_obs["HC_ignz"].count().sum()
    m["HC_outliers_ignz"] = int(m_obs.HC_ignz[m_obs.HC_ignz > m_obs["HC_ignz"].mean() * 5].count())
    if ignz_count == 0:
        return
    m["HC_outliers_ignz_perc"] = round(100 * m["HC_outliers_ignz"] / ignz_count, 2)
    if m["HC_outliers_ignz_perc"] > 100:
        m["HC_outliers_ignz_perc"] = 100
    m["HC_outliers_ignz_perc"] = str(m["HC_outliers_ignz_perc"]) + "%"

def generate_meter_data_cache():
    end_date = dt.datetime.now(dt.timezone.utc).date()

    # TODO: Thread caching as this takes a long time!

    if not anonMode and not offlineMode:

        # Health Check Score Cache
        for meter in METERS():
            # TODO: Parse existing cache to see if we need to update it
            # Should be as easy as checking if the oldest date in the cache is before end_date
            meter_health_score_file = os.path.join(meter_health_score_files, f"{meter['meter_id_clean']}.json")
            meter_health_scores = {}

            start_date = end_date - dt.timedelta(days=365)

            for offset in range((end_date - start_date).days):
                date = (start_date + dt.timedelta(days=offset))
                date_range_start = dt.datetime(date.year, date.month, date.day)
                date_range_end = date_range_start + dt.timedelta(hours=23, minutes=59, seconds=59)
                xcount = int((date_range_end - date_range_start).total_seconds() // 600) - 1

                process_meter_health(meter, date_range_start, date_range_end, xcount)
                meter_health_scores.update({date.isoformat(): meter['HC_score']})

            with open(meter_health_score_file, "w") as f:
                json.dump(meter_health_scores, f)

        # Meter Snapshot Cache
        for meter in METERS():
            # TODO: Parse existing cache to see if we need to update it
            # Should be as easy as checking if the oldest date in the cache is before end_date
            meter_snapshots_file = os.path.join(meter_snapshots_files, f"{meter['meter_id_clean']}.json")
            meter_snapshots = {}

            start_date = end_date - dt.timedelta(days=30)

            for offset in range((end_date - start_date).days):
                date = (start_date + dt.timedelta(days=offset))
                date_range_start = dt.datetime(date.year, date.month, date.day)
                date_range_end = date_range_start + dt.timedelta(hours=23, minutes=59, seconds=59)

                meter_obs = query_time_series(meter, date_range_start, date_range_end, "24h")['obs']
                if len(meter_obs) == 0:
                    # TODO: Should this set hc score to 0 if there isn't any data?
                    continue
                meter_snapshots.update({date.isoformat(): meter_obs[0]['value']})

            with open(meter_snapshots_file, "w") as f:
                json.dump(meter_snapshots, f)

    if anonMode:
        # TODO: Handle anonMode
        pass
    elif offlineMode:
        # TODO: Handle offlineMode
        pass


## #############################################################################################

## simple health check the server is running
## Parameters:
## Return:
## current time
##
## Example:
## http://127.0.0.1:5000/api/
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
## http://127.0.0.1:5000/api/hierarchy
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

## Return the latest health check table so we're not waiting for ages
@api_bp.route('/hc_latest')
def hc_latest():
    try:
        hc_cache = json.load(open(hc_latest_file))
        return hc_cache
    except:
        return []

## Health check cache meta
@api_bp.route('/hc_meta')
def hc_meta():
    try:
        hc_meta = json.load(open(hc_meta_file))
        return hc_meta
    except:
        return {}

## Return summary of the energy usage over all buildings with main meters and mazemap ids
##
## Parameters:
## from_time - options inital date YYYY-mm-dd format (summary of usage from 00:00 of this date) - default 7 days before to_time
## to_time - options final observation time in YYYY-mm-dd format (summary of usage upto 23:59 of this date) - default current date
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/api/summary
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
## http://127.0.0.1:5000/api/meter
## http://127.0.0.1:5000/api/meter?uuid=AP001_L01_M2
## http://127.0.0.1:5000/api/meter?lastobs=true
## http://127.0.0.1:5000/api/meter?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/api/meter?is_weather=true
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
## http://127.0.0.1:5000/api/meter_obs?uuid=AP001_L01_M2
## http://127.0.0.1:5000/api/meter_obs?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/api/meter_obs?uuid=WTHR_0
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
## http://127.0.0.1:5000/api/meter_ping?uuid=AP001_L01_M2
@api_bp.route('/meter_ping')
def meter_ping():

    if offlineMode == True:
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
                "Class":"Rate", "serving": None, "serving_revised": None,
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
## http://127.0.0.1:5000/api/last_meter_obs?uuid=AP001_L01_M2
## http://127.0.0.1:5000/api/last_meter_obs?uuid=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/api/last_meter_obs?uuid=WTHR_0
## http://127.0.0.1:5000/api/last_meter_obs?uuid=MC062_L01_M33_R2048&to_time=2024-01-01T00:00:00%2B0000
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

def get_health(args, returning=False):
    #if offlineMode == True:
    #    return "Offline mode, can't get meters"
        #return make_response("Offline mode, can't get meters", 500)

    meters = METERS()

    try:
        uuids = args["uuid"] # this is url decoded
        uuids = uuids.split(";")
    except:
        uuids = [x["meter_id_clean"] for x in meters]

    try:
        to_time = args["to_time"] # this is url decoded
        to_time = dt.datetime.strptime(to_time,"%Y-%m-%d")
    except:
        to_time = dt.datetime.now(dt.timezone.utc)

    try:
        date_range = int(args["date_range"]) # this is url decoded
    except:
        date_range = 30

    try:
        from_time = args["from_time"] # this is url decoded
        from_time = dt.datetime.strptime(from_time,"%Y-%m-%d")
    except:
        from_time = to_time - dt.timedelta(days=date_range)

    xcount = int((to_time - from_time).total_seconds()//600) - 1

    try:
        fmt = args["format"] # this is url decoded
    except:
        fmt = "json"

    ## load and trim meters
    if uuids is not None:
        meters[:] = [x for x in meters if x["meter_id_clean"] in uuids]

    start_time = time.time()
    mc = 0 # Not sure what this was initially for

    threads = []
    for m in meters:
        thread_name = f"HC_{m['meter_id_clean']}"
        if thread_name == "HC_":
            # If the meter doesn't have a meter_id_clean attribute, skip it
            # If we don't, it will only get skipped later in the code - may as well do it now!
            m["HC_count"] = 0
            m["HC_count_perc"] = "0%"
            m["HC_score"] = 0
            continue

        threads.append(threading.Thread(target=process_meter_health, args=(m, from_time, to_time, xcount), name=thread_name, daemon=True))
        threads[-1].start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    proc_time = (time.time() - start_time)
    print("--- Health check took %s seconds ---" % proc_time)

    # save cache, but only if it's a "default" query
    if not bool(list(set(args) & set(["date_range", "from_time", "to_time", "uuid"]))):
        try:
            with open(hc_latest_file, "w") as f:
                json.dump(meters, f)
            try:
                hc_meta = {
                    "filename": os.path.basename(hc_latest_file),
                    "meters": len(meters),
                    "to_time": to_time.timestamp(),
                    "from_time": from_time.timestamp(),
                    "date_range": date_range,
                    "timestamp": dt.datetime.now(dt.timezone.utc).timestamp(),
                    "processing_time": proc_time
                }
                with open(hc_meta_file, "w") as f:
                    json.dump(hc_meta, f)
            except:
                print("Error trying to save metadata for latest HC cache")
        except:
            print("Error trying to save current health check in cache")
    if returning:
        return meters

## Create health check of meters (requested by IES)
##
## Parameters:
## uuid - gauge id (planon style) or missing for all gauges
## to_time - final observation time, defaults to current time
## from_time - first observation time, defaults to 30 days ago
## date_range - how far back we want to check in days (ignored if from_time is given)
##
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/api/meter_health?uuid=AP001_L01_M2&date_range=7
@api_bp.route('/meter_health')
def meter_health():
    return make_response(jsonify(meter_health_internal(request.args)), 200)

# this is the same but doesn't return a response as we need the pure JSON for the template
@api_bp.route('/meter_health_internal')
def meter_health_internal(args):

    # if "default" call, check if there's a cache
    hc_cache = hc_latest()
    if len(args) == 0 or list(args.keys()) == ["hidden"]:
        if hc_cache and len(hc_cache) > 2:
            try:
                hc_meta = json.load(open(hc_meta_file))
                cache_age = dt.datetime.now(dt.timezone.utc).timestamp() - hc_meta["to_time"]
                if (cache_age < 3600 * hc_update_time and int(hc_meta["date_range"]) == 30 and int(hc_meta["meters"]) > 1000):
                    return hc_cache
            except:
                print("Error reading meta file, skipping cache")

        updateOngoing = False
        for th in threading.enumerate():
            if th.name == "updateMainHC":
                updateOngoing = True
        if not updateOngoing:
            # TODO: at the moment can't build new HC from offline (would need to be done in query_pandas)!
            thread = threading.Thread(target=get_health, args=(args,), name="updateMainHC", daemon=True)
            thread.start()
        if hc_cache and len(hc_cache) > 2:
            return hc_cache
        else:
            return []
    else:
        return get_health(args, True)
