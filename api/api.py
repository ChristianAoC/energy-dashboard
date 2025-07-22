from flask import Blueprint, jsonify, make_response, request, Response, json, current_app
from sqlalchemy import not_

import datetime as dt
import pandas as pd
from influxdb import InfluxDBClient
from dotenv import load_dotenv
import os
import time
import threading
import math
from functools import wraps
import sys

from database import db
import models
import dashboard.user as user


api_bp = Blueprint('api_bp', __name__, static_url_path='')

load_dotenv()

val = os.getenv("OFFLINE_MODE", "True")
offlineMode = val.strip().lower() in ("1", "true", "yes", "on")

# val = os.getenv("ANON_MODE", "True")
# anonMode = val.strip().lower() in ("1", "true", "yes", "on")

InfluxURL = os.getenv("INFLUX_URL")
InfluxPort = os.getenv("INFLUX_PORT")
InfluxUser = os.getenv("INFLUX_USER")
InfluxPass = os.getenv("INFLUX_PASS")

if InfluxURL is None or InfluxPort is None or InfluxUser is None or InfluxPass is None:
    offlineMode = True

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

hc_update_time = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", "9"))

meters_file = os.path.join(DATA_DIR, "input", 'meters_all.json')
buildings_file = os.path.join(DATA_DIR, "input", 'UniHierarchy.json')
buildings_usage_file = os.path.join(DATA_DIR, "input", 'UniHierarchyWithUsage.json')

if not offlineMode:
    meter_health_score_files = os.path.join(DATA_DIR, "cache", "meter_health_score")
    meter_snapshots_files = os.path.join(DATA_DIR, "cache", "meter_snapshots")
else:
    meter_health_score_files = os.path.join(DATA_DIR, "cache", "offline_meter_health_score")
    meter_snapshots_files = os.path.join(DATA_DIR, "cache", "offline_meter_snapshots")
if not os.path.exists(meter_health_score_files):
    os.mkdir(meter_health_score_files)
if not os.path.exists(meter_snapshots_files):
    os.mkdir(meter_snapshots_files)

cache_generation_lock = threading.Lock()
cache_time_health_score = int(os.getenv("HEALTH_SCORE_CACHE_TIME", "365"))
cache_time_summary = int(os.getenv("SUMMARY_CACHE_TIME", "30"))

benchmark_data_file = os.path.join(DATA_DIR, "benchmarks.json")

offline_meta_file = os.path.join(DATA_DIR, "meta", "offline_data.json")
offline_data_files = os.path.join(DATA_DIR, "offline")

meters_anon_file = os.path.join(DATA_DIR, "input", 'anon_meters.json')
buildings_anon_file = os.path.join(DATA_DIR, "input", 'anon_buildings.json')
usage_anon_file = os.path.join(DATA_DIR, "input", 'anon_usage.json')

if offlineMode and not os.path.exists(os.path.join(DATA_DIR, "offline")):
    print("\n" + "="*20)
    print("\tERROR: You are runnning in offline mode without any offline data!")
    print("\tPlease place your data in ./data/offline/")
    print("\n" + "="*20)
    sys.exit(1)

## #################################################################
## constants - should not be changed later in code
def METERS():
    if offlineMode:
        return json.load(open(meters_anon_file))
    return json.load(open(meters_file))

def BUILDINGS():
    if offlineMode:
        return json.load(open(buildings_anon_file))
    return json.load(open(buildings_file))

# offline file needed so the UI doesn't wait for the API call to compute sample usage
def BUILDINGSWITHUSAGE():
    if offlineMode:
        return json.load(open(usage_anon_file))
    return json.load(open(buildings_usage_file))

## #################################################################
## helper functions

## Minimal/efficient call - get time series as Pandas
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
def query_pandas(m: models.Meter, from_time, to_time):

    if m.SEED_uuid is None: ## can't get data
        return pd.DataFrame()

    ## format query
    qry = 'SELECT * as value FROM "SEED"."autogen"."' + m.SEED_uuid + \
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
def query_time_series(m: models.Meter, from_time, to_time, agg="raw", to_rate=False):
    # set some constants
    max_time_interval = dt.timedelta(days=3650)

    # convert to UTC for influx
    from_time = from_time.astimezone(dt.timezone.utc)
    to_time = to_time.astimezone(dt.timezone.utc)

    # check time limits
    if to_time - from_time > max_time_interval:
        from_time = to_time - max_time_interval

    # set the basic output
    out = {
        "uuid": m.id,
        "label": m.name,
        "obs": [],
        "unit": m.units
    }

    obs = []

    if not offlineMode:
        if m.SEED_uuid is None: # can't get data
            return out

        # format query
        qry = 'SELECT * as value FROM "SEED"."autogen"."' + m.SEED_uuid + \
            '" WHERE time >= \'' + from_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\'' + \
            ' AND time <= \'' + to_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\''

        # create client for influx
        client = InfluxDBClient(host = InfluxURL,
                                port = InfluxPort,
                                username = InfluxUser,
                                password = InfluxPass)

        result = client.query(qry)

        # get as list of dictionaries
        obs = list(result.get_points())

    else:
        try:
            with open(os.path.join(offline_data_files, f"{m.id}.json"), "r") as f:
                obs = json.load(f)

            obs = pd.DataFrame.from_dict(obs)
            obs['time'] = pd.to_datetime(obs['time'], format="%Y-%m-%dT%H:%M:%S%z", utc=True)
            obs.drop(obs[obs.time < from_time.astimezone(dt.timezone.utc)].index, inplace=True)
            obs.drop(obs[obs.time > to_time.astimezone(dt.timezone.utc)].index, inplace=True)
            obs['time'] = obs['time'].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            obs = obs.to_dict('records')
        except:
            return out

    if len(obs)==0:
        return out

    # standardise the value based on resolution and format time
    if m.resolution is not None:
        kappa = m.scaling_factor / m.resolution
        rho = m.resolution
    else:
        kappa = 1.0
        rho = 1.0

    for o in obs:
        o['value'] = round( rho * round(o["value"] * kappa) ,10 )
        if o['time'][:-1] == "Z":
            o['time'] = o['time'][:-1] + '+0000'

    ## uncumulate if required
    if to_rate and (m.reading_type == "cumulative"):
        xcur = obs[-1]["value"]
        for ii in reversed(range(len(obs)-1)):
            if obs[ii]["value"]==0:
                obs[ii]["value"] = None

            if obs[ii]["value"] is None:
                obs[ii+1]["value"] = None ## rate on next step not valid
                continue

            if xcur is None:
                xcur = obs[ii]["value"]

            if obs[ii]["value"] > xcur:
                ## can't be valid
                obs[ii]["value"] = None
            else:
                xcur = obs[ii]["value"]

            if obs[ii+1]["value"] is None or obs[ii]["value"] is None:
                obs[ii+1]["value"] = None
            else:
                obs[ii+1]["value"] -= obs[ii]["value"] ## change to rate

        obs[0]["value"] = None

    ## aggregate and scale
    if agg != "raw":
        df = pd.DataFrame.from_dict(obs)
        df['time'] = pd.to_datetime(df['time'],format = '%Y-%m-%dT%H:%M:%S%z', utc=True)
        df.set_index('time', inplace=True)
        df = df.resample(agg, origin='end').mean() ## windows go backwards

        df.reset_index(inplace=True)
        df['time'] = df['time'].dt.strftime('%Y-%m-%dT%H:%M:%S%z') ## check keeps utc?

        obs = json.loads(df.to_json(orient='records')) #This is ugly but seems to avoid return NaN rather than null - originally used pd.DataFrame.to_dict(df,orient="records")

    out["obs"] = obs
    return out

## Get time of last observation
## m - meter
## to_time - time to get data to (datetime)
## from_time - time to get data from (datetime)
def query_last_obs_time(m: models.Meter, to_time, from_time):

    ## convert uuid to string for query
    ##ustr = ",".join(['"SEED"."autogen"."'+x+'"' for x in uuid])
    if m.id is None:
        return None

    # if offline, last obs is simply last line of file
    if offlineMode:
        try:
            with open(f"data/offline/{m.id}.json", "r") as f:
                obs = json.load(f)
        except:
            return make_response("Offline mode and can't open/find a file for this UUID", 500)
        
        if len(obs) > 0:
            return obs[-1]["time"]

    ustr = '"SEED"."autogen"."' + m.SEED_uuid + '"'
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
    if len(out) > 0:
        out = out[0]['time']
        out = out[:-1] + '+0000'
    else:
        out = None

    return out

## Retrieve data from influx and process it for meter health
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
def process_meter_health(m: models.Meter, from_time: dt.datetime, to_time: dt.datetime, all_outputs: list = []) -> dict|None:
    if offlineMode:
        try:
            with open(offline_meta_file, "r") as f:
                anon_data_meta = json.load(f)
            interval = anon_data_meta.get("interval", 60) * 60
        except:
            interval = 3600

        # Offline data is recorded at 1 hour intervals
        xcount = int((to_time - from_time).total_seconds()//interval) - 1
    else:
        # Live data is recorded at 10 minute intervals
        xcount = int((to_time - from_time).total_seconds()//600) - 1

    # Bring SQL update output back in line with the original output (instead of just returning calculated values)
    out = m.to_dict()

    # time series for this meter
    if not offlineMode:
        m_obs = query_pandas(m, from_time, to_time)
    else:
        try:
            with open(f"data/offline/{m.id}.json", "r") as f:
                obs = json.load(f)

            m_obs = pd.DataFrame.from_dict(obs)
            m_obs['time'] = pd.to_datetime(m_obs['time'], format="%Y-%m-%dT%H:%M:%S%z", utc=True)
            m_obs.drop(m_obs[m_obs.time < from_time.astimezone(dt.timezone.utc)].index, inplace=True)
            m_obs.drop(m_obs[m_obs.time > to_time.astimezone(dt.timezone.utc)].index, inplace=True)
        except FileNotFoundError as e:
            print(f"Offline data: {e.filename} does not exist")
            return None
        except:
            out["HC_count"] = 0
            out["HC_count_perc"] = "0%"
            out["HC_score"] = 0

            # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
            all_outputs.append(out)
            return out

    # count values. if no values, stop
    out["HC_count"] = len(m_obs)
    if out["HC_count"] == 0:
        out["HC_count_perc"] = "0%"
        out["HC_score"] = 0

        # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
        all_outputs.append(out)
        return out

    out["HC_count_perc"] = round(100 * out["HC_count"] / xcount, 2)
    if out["HC_count_perc"] > 100:
        out["HC_count_perc"] = 100
    out["HC_count_score"] = math.floor(out["HC_count_perc"] / 20)
    out["HC_count_perc"] = str(out["HC_count_perc"]) + "%"

    # count zeroes
    out["HC_zeroes"] = int(m_obs["value"][m_obs["value"] == 0].count())
    out["HC_zeroes_perc"] = round(100 * out["HC_zeroes"] / xcount, 2)
    if out["HC_zeroes_perc"] > 100:
        out["HC_zeroes_perc"] = 100
    out["HC_zeroes_score"] = math.floor((100 - out["HC_zeroes_perc"]) / 20)
    out["HC_zeroes_perc"] = str(out["HC_zeroes_perc"]) + "%"

    # create diff (increase for each value) to prep for cumulative check
    m_obs["diffs"] = m_obs["value"].diff()
    diffcount = m_obs["diffs"].count().sum()
    if diffcount == 0:
        # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
        all_outputs.append(out)
        return out

    # count positive, negative, and no increase
    out["HC_diff_neg"] = int(m_obs.diffs[m_obs.diffs < 0].count())
    out["HC_diff_neg_perc"] = round(100 * out["HC_diff_neg"] / diffcount, 2)
    if out["HC_diff_neg_perc"] > 100:
        out["HC_diff_neg_perc"] = 100

    out["HC_diff_pos"] = int(m_obs.diffs[m_obs.diffs > 0].count())
    out["HC_diff_pos_perc"] = round(100 * out["HC_diff_pos"] / diffcount, 2)
    if out["HC_diff_pos_perc"] > 100:
        out["HC_diff_pos_perc"] = 100
    out["HC_diff_pos_score"] = math.floor(out["HC_diff_pos_perc"] / 20)

    out["HC_diff_zero"] = int(m_obs.diffs[m_obs.diffs == 0].count())
    out["HC_diff_zero_perc"] = round(100 * out["HC_diff_zero"] / diffcount, 2)
    if out["HC_diff_zero_perc"] > 100:
        out["HC_diff_zero_perc"] = 100

    # assume that cumulative meters have > 80% of values increase and vice versa
    out["HC_class"] = m.reading_type
    if out["HC_diff_zero_perc"] > 80:
        out["HC_class_check"] = "Too many zero diffs to check"

    if m.reading_type == "Cumulative":
        if out["HC_diff_pos_perc"] < 80 and out["HC_diff_neg_perc"] > 20:
            out["HC_class_check"] = "Check (seems rate)"
            out["HC_class"] = "Rate"
        else:
            out["HC_class_check"] = "Okay (cumulative)"
    else:
        if out["HC_diff_pos_perc"] > 80:
            out["HC_class_check"] = "Check (seems cumulative)"
            out["HC_class"] = "Cumulative"
        else:
            out["HC_class_check"] = "Okay (rate)"

    out["HC_diff_neg_perc"] = str(out["HC_diff_neg_perc"]) + "%"
    out["HC_diff_pos_perc"] = str(out["HC_diff_pos_perc"]) + "%"
    out["HC_diff_zero_perc"] = str(out["HC_diff_zero_perc"]) + "%"

    out["HC_functional_matrix"] = out["HC_count_score"] * out["HC_zeroes_score"]

    # if cumulative (or assumed cumul) run statistics on that data, otherwise on raw
    if out["HC_class"] == "Cumulative":
        out["HC_mean"] = int(m_obs["diffs"].mean())
        out["HC_median"] = int(m_obs["diffs"].median())
        out["HC_mode"] = int(m_obs["diffs"].mode()[0])
        out["HC_std"] = int(m_obs["diffs"].std())
        out["HC_min"] = int(m_obs["diffs"].min())
        out["HC_max"] = int(m_obs["diffs"].max())
        out["HC_outliers"] = int(m_obs.diffs[m_obs.diffs > out["HC_mean"] * 5].count())
        m_obs["HC_ignz"] = m_obs[m_obs["diffs"] != 0]["diffs"]
        out["HC_cumulative_matrix"] = out["HC_diff_pos_score"] * out["HC_functional_matrix"]
        out["HC_score"] = math.floor(out["HC_cumulative_matrix"] / 25)

    else:
        out["HC_mean"] = int(m_obs["value"].mean())
        out["HC_median"] = int(m_obs["value"].median())
        out["HC_mode"] = int(m_obs["value"].mode()[0])
        out["HC_std"] = int(m_obs["value"].std())
        out["HC_min"] = int(m_obs["value"].min())
        out["HC_max"] = int(m_obs["value"].max())
        out["HC_outliers"] = int(m_obs["value"][m_obs["value"] > out["HC_mean"] * 5].count())
        m_obs["HC_ignz"] = m_obs[m_obs["value"] != 0]["value"]
        out["HC_score"] = math.floor(out["HC_functional_matrix"] / 5)

    out["HC_outliers_perc"] = round(100 * out["HC_outliers"] / xcount, 2)
    if out["HC_outliers_perc"] > 100:
        out["HC_outliers_perc"] = 100
    out["HC_outliers_perc"] = str(out["HC_outliers_perc"]) + "%"

    ignz_count = m_obs["HC_ignz"].count().sum()
    out["HC_outliers_ignz"] = int(m_obs.HC_ignz[m_obs.HC_ignz > m_obs["HC_ignz"].mean() * 5].count())
    if ignz_count == 0:
        # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
        all_outputs.append(out)
        return out
    out["HC_outliers_ignz_perc"] = round(100 * out["HC_outliers_ignz"] / ignz_count, 2)
    if out["HC_outliers_ignz_perc"] > 100:
        out["HC_outliers_ignz_perc"] = 100
    out["HC_outliers_ignz_perc"] = str(out["HC_outliers_ignz_perc"]) + "%"

    all_outputs.append(out)
    return out

## Creates a list with the information required to fill in the missing cache entries for the given cache data
## It also strips out any expired cache data
## days - The number of days to store data in the cache
## existing_cache - The existing cache dictionary to be updated - Defaults to an empty dictionary
## data_start_time - The earliest date in the cache (If None, assume that all data that we want to access is available)
## data_end_time - The latest date that there is data for (Current time if online)
def cache_items(days: int, existing_cache: dict, data_start_time: dt.datetime, data_end_time: dt.datetime) -> list[tuple[dt.date, dt.datetime, dt.datetime]]:
    todo = []

    if data_start_time is not None:
        days = min((data_end_time.date() - data_start_time.date()).days, days)

    start_date = data_end_time.date() - dt.timedelta(days=days)

    # We don't cache today's data as it will never be complete
    for offset in range(days):
        date = (start_date + dt.timedelta(days=offset))
        if date.isoformat() in existing_cache:
            continue
        date_range_start = dt.datetime(date.year, date.month, date.day)
        date_range_end = date_range_start + dt.timedelta(hours=23, minutes=59, seconds=59)
        todo.append((date, date_range_start, date_range_end))

    if existing_cache == {}:
        return todo

    # Need to remove expired cache items
    for cache_item in existing_cache.copy().keys():
        if dt.date.fromisoformat(cache_item) < start_date:
            existing_cache.pop(cache_item)

    return todo

## Returns whether the given cache is valid. It is a stripped down version of cache_items to run faster.
## days - The number of days to store data in the cache
## cache_file - The cache file to be updated
## data_start_time - The earliest date in the cache (If None, assume that all data that we want to access is available)
## data_end_time - The latest date that there is data for (Current time if online)
def cache_validity_checker(days: int, cache_file: str, data_start_time: dt.datetime|None, data_end_time: dt.datetime) -> bool:
    if not os.path.exists(cache_file):
        return False

    try:
        existing_cache = json.load(open(cache_file, "r"))
    except:
        return False

    if existing_cache == {}:
        return False

    if data_start_time is not None:
        days = min((data_end_time.date() - data_start_time.date()).days, days)

    start_date = data_end_time.date() - dt.timedelta(days=days)

    for offset in range(days):
        date = (start_date + dt.timedelta(days=offset))
        if date.isoformat() not in existing_cache:
            return False

    # Need to remove expired cache items
    for cache_item in existing_cache:
        if dt.date.fromisoformat(cache_item) < start_date:
            return False

    return True

## Cleans the provided file name by replacing / with _
## file_name - The file name to be cleaned
def clean_file_name(file_name: str):
    file_name = file_name.replace("/", "_")
    file_name = file_name.replace("\\", "_")
    file_name = file_name.replace(" ", "_")
    file_name = file_name.replace("?", "_")
    file_name = file_name.replace(",", "_")
    return file_name

## Generate the cache for the provided meter
## m - the meter to generate cache for
## data_start_time - The earliest date in the cache (If None, assume that all data that we want to access is available)
## data_end_time - The latest date that there is data for (Current time if online)
def generate_meter_cache(m: models.Meter, data_start_time: dt.datetime, data_end_time: dt.datetime) -> None:
    print(f"Started: {m.id}")
    try:
        file_name = clean_file_name(f"{m.id}.json")

        meter_health_score_file = os.path.join(meter_health_score_files, file_name)
        meter_health_scores = {}
        if os.path.exists(meter_health_score_file):
            try:
                meter_health_scores = json.load(open(meter_health_score_file, "r"))
            except:
                meter_health_scores = {}

        for cache_item in cache_items(cache_time_health_score, meter_health_scores, data_start_time, data_end_time):
            score = process_meter_health(m, cache_item[1], cache_item[2])
            if score is None:
                # Something happended to the offline data since running cache_validity_checker, quit thread
                print(f"Ended: {m.id} - An Error occured accessing the offline data for this meter")
                return
            meter_health_scores.update({cache_item[0].isoformat(): score['HC_score']})

        with open(meter_health_score_file, "w") as f:
            json.dump(meter_health_scores, f)

        # Meter Snapshot Cache
        meter_snapshots_file = os.path.join(meter_snapshots_files, file_name)
        meter_snapshots = {}
        if os.path.exists(meter_snapshots_file):
            try:
                meter_snapshots = json.load(open(meter_snapshots_file, "r"))
            except:
                meter_snapshots = {}

        for cache_item in cache_items(cache_time_summary, meter_snapshots, data_start_time, data_end_time):
            meter_obs = query_time_series(m, cache_item[1], cache_item[2], "24h")['obs']

            cache_value = meter_obs[0]['value'] if len(meter_obs) > 0 else None

            meter_snapshots.update({cache_item[0].isoformat(): cache_value})

        with open(meter_snapshots_file, "w") as f:
            json.dump(meter_snapshots, f)
    except Exception as e:
        print(f"An error occurred generating cache for meter {m.id}")
        raise e
    print(f"Ended: {m.id}")

## Generates the cache data for meter health scores and meter snapshots
## return_if_generating - Whether to return or wait for current generation to complete - defaults to True
##
## The generation of each meter's cache is handed of to a separate thread, this dramatically speeds up cache generation
## **IF** the majority of the cache is expired/missing, or if this is the first time generating the cache.
## If the cache has just been updated, and we haven't gone past midnight UTC, then this will likely be slower than doing
## everything in the request's thread.
def generate_meter_data_cache(return_if_generating=True) -> None:
    skip_cache_generation = False
    if cache_generation_lock.locked():
        # Cache is in the process of (re)generating, therefore wait for it to be done and then use existing cache
        skip_cache_generation = True
        if return_if_generating:
            return

    cache_generation_lock.acquire()

    if skip_cache_generation:
        cache_generation_lock.release()
        return

    if offlineMode:
        with open(offline_meta_file, "r") as f:
            anon_data_meta = json.load(f)
        data_start_time = dt.datetime.strptime(anon_data_meta['start_time'], "%Y-%m-%dT%H:%M:%S%z")
        data_end_time = dt.datetime.strptime(anon_data_meta['end_time'], "%Y-%m-%dT%H:%M:%S%z")
    else:
        data_start_time = None
        data_end_time = dt.datetime.now(dt.timezone.utc)

    # Don't need to filter id by not null as id is primary key and therefore not null
    meters = db.session.execute(db.select(models.Meter)).scalars().all()

    n = 20 # Process 35 meters at a time (35 was a random number I chose)
    meter_chunks = [meters[i:i + n] for i in range(0, len(meters), n)]

    seen_meters = []

    for meter_chunk in meter_chunks:
        threads = []
        for m in meter_chunk:
            clean_meter_name = clean_file_name(m.id)
            thread_name = f"Mtr_Cache_Gen_{clean_meter_name}"
            file_name = f"{clean_meter_name}.json"

            if offlineMode and not os.path.exists(os.path.join(DATA_DIR, "offline", file_name)):
                continue

            meter_health_score_file = os.path.join(meter_health_score_files, file_name)
            meter_snapshots_file = os.path.join(meter_snapshots_files, file_name)

            seen_meters.append(file_name)

            if (cache_validity_checker(cache_time_health_score, meter_health_score_file, data_start_time, data_end_time) and
                    cache_validity_checker(cache_time_summary, meter_snapshots_file, data_start_time, data_end_time)):
                print(f"Skipping: {m.id}")
                continue

            threads.append(threading.Thread(target=generate_meter_cache, args=(m, data_start_time, data_end_time), name=thread_name, daemon=True))
            threads[-1].start()

        # Wait for all threads in chunk to complete
        for t in threads:
            t.join()

    # Clean up non-existent meters
    existing_cache_files = os.listdir(meter_health_score_files)
    for existing_cache_file in existing_cache_files:
        if existing_cache_file[-5:] != ".json":
            continue
        if existing_cache_file not in seen_meters:
            os.remove(os.path.join(meter_health_score_files, existing_cache_file))

    cache_generation_lock.release()
    return


## #############################################################################################
# decorator to limit certain pages to a specific user level
def required_user_level(level_config_key):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            cookies = request.cookies
            try:
                level = int(current_app.config[level_config_key])
                if int(user.get_user_level(cookies["Email"], cookies["SessionID"])) < level:
                    return make_response("Access Denied", 401)
            except:
                print("No or wrong cookie")
                return make_response("Access Denied", 401)

            print("Authorised!")
            return function(*args, **kwargs)
        return wrapper
    return decorator

@api_bp.route('/regeneratecache', methods=["GET"])
@required_user_level("USER_LEVEL_ADMIN")
def regenerate_cache():
    print("Start!")
    start_time = time.time()
    generate_meter_data_cache()
    end_time = time.time()
    print("Done!")
    total_time = end_time - start_time
    print(f"Took {total_time} seconds")
    return make_response(str(total_time), 200)

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

## Helper function needed for accessing raw list of all meters in other blueprint
@api_bp.route('/devices')
def devices():
    data = [x.to_dict() for x in db.session.execute(db.select(models.Meter)).scalars().all()]
    return make_response(jsonify(data), 200)

## Helper function needed for accessing quick usage list so UI doesn't delay too much
@api_bp.route('/usageoffline')
def usageoffline():
    data = [x.to_dict() for x in db.session.execute(db.select(models.UtilityData)).scalars().all()]
    return make_response(jsonify(data), 200)

## Return the latest health check table so we're not waiting for ages
@api_bp.route('/hc_latest')
def hc_latest():
    hc_cache = [x.to_dict() for x in db.session.execute(db.select(models.HealthCheck)).scalars().all()]
    return make_response(jsonify(hc_cache), 200)

## Health check cache meta
@api_bp.route('/hc_meta')
def hc_meta():
    hc_meta = db.session.execute(db.select(models.HealthCheckMeta)).scalar_one_or_none()
    if hc_meta is None:
        return make_response(jsonify({}), 500)

    return make_response(jsonify(hc_meta.to_dict()), 200)

## Create usage summary of meters
##
## Only returns meters that are attached to a building.
## Only includes buildings with a valid floor area at least one meter.
##
## Parameters:
## from_time - options initial date YYYY-mm-dd format (summary of usage from 00:00 of this date) - default 7 days before to_time
## to_time - options final observation time in YYYY-mm-dd format (summary of usage upto 23:59 of this date) - default current date
##
## Return:
## json object:
## {
##     "building_code": {
##         "electricity": {
##             "meter_id_clean": {
##                 "EUI": EUI,
##                 "consumption": consumption,
##                 "benchmark": {
##                     "good": good_benchmark,
##                     "typical": typical_benchmark
##                 }
##             },
##             ...
##         },
##         "gas": {
##             "meter_id_clean": {
##                 "EUI": EUI,
##                 "consumption": consumption,
##                 "benchmark": {
##                     "good": good_benchmark,
##                     "typical": typical_benchmark
##                 }
##             },
##             ...
##         },
##         "heat": {
##             "meter_id_clean": {
##                 "EUI": EUI,
##                 "consumption": consumption,
##                 "benchmark": {
##                     "good": good_benchmark,
##                     "typical": typical_benchmark
##                 }
##             },
##             ...
##         },
##         "water": {
##             "meter_id_clean": {
##                 "EUI": EUI,
##                 "consumption": consumption,
##                 "benchmark": {
##                     "good": good_benchmark,
##                     "typical": typical_benchmark
##                 }
##             },
##             ...
##         }
##     },
##     ...
## }
##
## Example:
## http://127.0.0.1:5000/api/summary
@api_bp.route('/summary')
def summary():
    if not offlineMode:
        to_time = request.args.get("to_time")
        if to_time is not None:
            to_time = dt.datetime.combine(dt.datetime.strptime(to_time, "%Y-%m-%d"), dt.datetime.max.time())
        else:
            to_time = dt.datetime.combine(dt.date.today(), dt.datetime.max.time())

        from_time = request.args.get("from_time")
        if from_time is not None:
            from_time = dt.datetime.combine(dt.datetime.strptime(from_time,"%Y-%m-%d"), dt.datetime.min.time())
        else:
            from_time = to_time - dt.timedelta(days=7, seconds=1)
    else:
        with open(offline_meta_file, "r") as f:
            anon_data_meta = json.load(f)

        to_time = dt.datetime.strptime(anon_data_meta['end_time'], "%Y-%m-%dT%H:%M:%S%z")
        from_time = dt.datetime.strptime(anon_data_meta['start_time'], "%Y-%m-%dT%H:%M:%S%z")

        if (from_time - to_time) > dt.timedelta(days=7, seconds=1):
            from_time = to_time - dt.timedelta(days=7, seconds=1)

    buildings = db.session.execute(
        db.select(models.Building)
        .join(models.Meter)
        .where(not_(models.Meter.building_id.is_(None))) # type: ignore
        .where(not_(models.Building.floor_area.is_(None))) # type: ignore
    ).scalars().all()

    units = {'gas': "m3", 'electricity': "kWh", 'heat': "MWh", 'water': "m3"}

    with open(benchmark_data_file, "r") as f:
        benchmark_data = json.load(f)

    data = {}
    for b in buildings:
        building_response = {}

        meters = db.session.execute(
            db.select(models.Meter)
            .where(models.Meter.building_id == b.id)
            .where(models.Meter.main)
        ).scalars().all()

        for m in meters:
            meter_type = m.utility_type

            if meter_type not in units.keys():
                continue

            x = query_time_series(m, from_time, to_time, agg='876000h', to_rate=True)

            # No data available
            if len(x['obs']) == 0:
                continue

            usage = x['obs'][0]['value']

            if usage is None:
                usage = 0

            # handle unit changes
            if x['unit'] != units[meter_type]:
                if meter_type == "heat" and x['unit'] == "kWh":
                    usage *= 1e-3  # to MWh
                elif meter_type == "heat" and x['unit'] == "kW":
                    # presume 10 minute data, round to nearest kWh
                    usage = round(usage * 1e-3 * (1.0 / 6.0), 3)
                else:
                    continue

            # process EUI
            eui = float(f"{(usage / b.floor_area):.2g}")

            # Create utility entries on occurrence so that the response is smaller
            if meter_type not in building_response:
                building_response[meter_type] = {}

            benchmark = None
            if meter_type in ["gas", "heat"]:
                benchmark = benchmark_data[b.occupancy_type]["fossil"]
            elif meter_type == "electricity":
                benchmark = benchmark_data[b.occupancy_type]["electricity"]

            building_response[meter_type][m.id] = {
                "EUI": eui,
                "consumption": usage,
                "benchmark": benchmark
            }

        data[b.id] = building_response
    return make_response(jsonify(data), 200)

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

    statement = db.select(models.Meter)
    if planon is not None:
        statement = statement.where(models.Meter.building_id.in_(planon)) # type: ignore
    elif uuid is not None:
        statement = statement.where(models.Meter.id.in_(uuid)) # type: ignore
    
    meters = [meter.to_dict() for meter in db.session.execute(statement).scalars().all()]

    to_time = dt.datetime.now(dt.timezone.utc)
    from_time = to_time - dt.timedelta(days=1)

    if lastobs == "true":
        for m in meters:
            m["last_obs_time"] = query_last_obs_time(m, to_time, from_time)

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
        if agg == "0H" or agg == "0h":
            agg = "raw"
    except:
        agg = "raw"

    try:
        to_rate = request.args["to_rate"].lower() in ['true', '1', 't', 'y'] # this is url decoded
    except:
        to_rate = True

    meters = db.session.execute(
        db.select(models.Meter)
        .where(models.Meter.id.in_(uuids)) # type: ignore
    ).scalars().all()

    out = dict.fromkeys(uuids)

    for m in meters:
        out[m.id] = query_time_series(m, from_time, to_time, agg=agg, to_rate=to_rate)

    if fmt == "csv":
        try:
            csv = 'series,unit,time,value\n'
            ## repackage data as csv and return
            for k in out.keys():
                for obs in out[k]["obs"]:
                    csv += out[k]["uuid"] + ',' + out[k]["unit"] + "," + obs["time"] + ',' + str(obs["value"]) + '\n'

            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=mydata.csv"})
        except:
            return make_response("Unable to make csv file",500)

    else:
        return make_response(jsonify(out), 200)

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

    meters = db.session.execute(
            db.select(models.Meter)
            .where(models.Meter.id.in_(uuids)) # type: ignore
        ).scalars().all()

    out = dict.fromkeys(uuids)

    for m in meters:
        out[m.id] = query_last_obs_time(m, to_time, from_time)

    return make_response(jsonify(out), 200)

def get_health(args, returning=False, app=None):
    # Because this function can be run in a separate thread, we need to
    if app is not None:
        app.app_context().push()

    try:
        uuids = args["uuid"] # this is url decoded
        uuids = uuids.split(";")
    except:
        uuids = [x.id for x in db.session.execute(db.select(models.Meter.id))]

    try:
        to_time = args["to_time"] # this is url decoded
        to_time = dt.datetime.strptime(to_time,"%Y-%m-%d")
    except:
        if offlineMode:
            with open(offline_meta_file, "r") as f:
                to_time = dt.datetime.strptime(json.load(f)['end_time'], "%Y-%m-%dT%H:%M:%S%z")
        else:
            to_time = dt.datetime.now(dt.timezone.utc)

    try:
        date_range = int(args["date_range"]) # this is url decoded
    except:
        date_range = 30

    try:
        from_time = args["from_time"] # this is url decoded
        from_time = dt.datetime.strptime(from_time,"%Y-%m-%d")
    except:
        if offlineMode:
            with open(offline_meta_file, "r") as f:
                from_time = dt.datetime.strptime(json.load(f)['start_time'], "%Y-%m-%dT%H:%M:%S%z")
            date_range = min((to_time - from_time).days, date_range)
            from_time = to_time - dt.timedelta(days=date_range)
        else:
            from_time = to_time - dt.timedelta(days=date_range)

    # TODO: Should this be implemented or removed?
    try:
        fmt = args["format"] # this is url decoded
    except:
        fmt = "json"

    ## load and trim meters
    meters = db.session.execute(db.select(models.Meter).where(
            models.Meter.id.in_(uuids), # type: ignore
            models.Meter.id is not None
        )
    ).scalars().all()

    start_time = time.time()

    threads = []
    out = []
    for m in meters:
        print(m.id)
        threads.append(threading.Thread(target=process_meter_health, args=(m, from_time, to_time, out), name=f"HC_{m.id}", daemon=True))
        threads[-1].start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    proc_time = (time.time() - start_time)
    # print("--- Health check took %s seconds ---" % proc_time)

    # save cache, but only if it's a "default" query
    if set(args).isdisjoint({"date_range", "from_time", "to_time", "uuid"}):
        try:
            for meter in out:
                update_health_check(meter)

            try:
                hc_meta = {
                    "meter_count": len(out),
                    "to_time": to_time.timestamp(),
                    "from_time": from_time.timestamp(),
                    "date_range": date_range,
                    "timestamp": dt.datetime.now(dt.timezone.utc).timestamp(),
                    "processing_time": proc_time
                }

                existing_hc_meta = db.session.execute(db.select(models.HealthCheckMeta)).scalar_one_or_none()
                if existing_hc_meta is None:
                    new_hc_meta = models.HealthCheckMeta(hc_meta)
                    db.session.add(new_hc_meta)
                else:
                    existing_hc_meta.update(hc_meta)
                db.session.commit()
            except Exception as e:
                print("Error trying to save metadata for latest HC cache")
                print(e)
        except Exception as e:
            print("Error trying to save current health check in cache")
            print(e)

    print("Completed HC update")
    
    if returning:
        return out

def update_health_check(values: dict):
    existing_hc = db.session.execute(db.select(models.HealthCheck).where(models.HealthCheck.meter_id == values["id"])).scalar_one_or_none()
    if existing_hc is None:
        new_hc = models.HealthCheck(meter_id=values["id"], hc_data=values)
        db.session.add(new_hc)
    else:
        existing_hc.update(values)
    db.session.commit()

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
# TODO: does this need a route?
@api_bp.route('/meter_health_internal')
def meter_health_internal(args):
    # if "default" call, check if there's a cache
    hc_cache = hc_latest().json

    # What does the 2nd statement do?
    if len(args) == 0 or list(args.keys()) == ["hidden"]:
        if hc_cache and len(hc_cache) > 2:
            try:
                if offlineMode:
                    with open(offline_meta_file, "r") as f:
                        latest_data_date = dt.datetime.strptime(json.load(f)['end_time'], "%Y-%m-%dT%H:%M:%S%z").timestamp()
                else:
                    latest_data_date = dt.datetime.now(dt.timezone.utc).timestamp()
                
                no_meters = len(db.session.execute(db.select(models.Meter)).all())
                
                meta = db.session.execute(db.select(models.HealthCheckMeta)).scalar_one_or_none()
                if meta is None:
                    raise Exception
                
                cache_age = latest_data_date - meta.to_time
                if cache_age < 3600 * hc_update_time and meta.date_range == 30 and no_meters > 1000:
                    return hc_cache
            except:
                print("Error reading meta file, skipping cache")

        # Implement a lock here instead of this
        updateOngoing = False
        for th in threading.enumerate():
            if th.name == "updateMainHC":
                updateOngoing = True
        if not updateOngoing:
            thread = threading.Thread(target=get_health, args=(args, False, current_app._get_current_object()), name="updateMainHC", daemon=True)
            thread.start()

        # TODO: let front end know that we are serving stale cache so that it knows to send another request later
        # Could be done with a custom header (eg: X-Cache-State: stale and X-Cache-State: fresh) and maybe a header telling the frontend how long to wait (could guesstimate this from number of meters)
        if hc_cache and len(hc_cache) > 2:
            return hc_cache
        else:
            return []
    else:
        return get_health(args, True)

## Return meter hierarchy
##
## Only returns meters that are attached to a building and only includes buildings with meters
##
## Return:
## json object:
## {
##     "building_code": {
##         "electricity": [
##             "meter_id_clean",
##             ...
##         ],
##         "gas": [
##             "meter_id_clean",
##             ...
##         ],
##         "heat": [
##             "meter_id_clean",
##             ...
##         ],
##         "water": [
##             "meter_id_clean",
##             ...
##         ]
##     },
##     ...
## }
@api_bp.route('/meter_hierarchy')
def hierarchy():
    buildings = db.session.execute(
        db.select(models.Building)
        .join(models.Meter)
        .where(not_(models.Meter.building_id.is_(None)) # type: ignore
    )).scalars().all()

    data = {}
    for b in buildings:
        building_response = {}
        
        meters = db.session.execute(
            db.select(models.Meter)
            .where(models.Meter.building_id == b.id)
            .where(models.Meter.main)
        ).scalars().all()
        
        for m in meters:
            meter_type = m.utility_type
            if meter_type not in ['gas', 'electricity', 'heat', 'water']:
                continue

            # Create utility entries on occurrence so that the response is smaller
            if meter_type not in building_response:
                building_response[meter_type] = []

            building_response[meter_type].append(m.id)

        data[b.id] = building_response

    return make_response(jsonify(data), 200)

## Parameters:
## to_time - options final observation time in YYYY-MM-DD format (meter health up to 23:59 of this date) - default current date
## from_time - options initial date YYYY-MM-DD format (meter health from 00:00 of this date) - default 7 days before to_time
##
## [
##     {
##         building_id:[
##             0: [meter_clean_id],
##             1: [meter_clean_id],
##             2: [meter_clean_id],
##             3: [meter_clean_id],
##             4: [meter_clean_id],
##             5: [meter_clean_id]
##         ],
##         ...
##     }
## ]
##
## Example:
## http://127.0.0.1:5000/api/health_score
@api_bp.route('/health_score')
def health_score():
    if not offlineMode:
        to_time = request.args.get("to_time")
        if to_time is not None:
            to_time = dt.datetime.combine(dt.datetime.strptime(to_time, "%Y-%m-%d"), dt.datetime.max.time())
        else:
            to_time = dt.datetime.combine(dt.date.today(), dt.datetime.max.time())

        from_time = request.args.get("from_time")
        if from_time is not None:
            from_time = dt.datetime.combine(dt.datetime.strptime(from_time,"%Y-%m-%d"), dt.datetime.min.time())
        else:
            from_time = to_time - dt.timedelta(days=7, seconds=1)
    else:
        with open(offline_meta_file, "r") as f:
            anon_data_meta = json.load(f)

        to_time = dt.datetime.strptime(anon_data_meta['end_time'], "%Y-%m-%dT%H:%M:%S%z")
        from_time = dt.datetime.strptime(anon_data_meta['start_time'], "%Y-%m-%dT%H:%M:%S%z")

        if (from_time - to_time) > dt.timedelta(days=7, seconds=1):
            from_time = to_time - dt.timedelta(days=7, seconds=1)

    days = (to_time.date() - from_time.date()).days

    buildings = db.session.execute(
        db.select(models.Building)
        .join(models.Meter)
        .where(not_(models.Meter.building_id.is_(None))) # type: ignore
    ).scalars().all()

    data = {}
    for b in buildings:
        building_response = {
            0: [],
            1: [],
            2: [],
            3: [],
            4: [],
            5: []
        }
        
        meters = db.session.execute(
            db.select(models.Meter)
            .where(models.Meter.building_id == b.id)
            .where(models.Meter.main)
        ).scalars().all()

        for m in meters:
            clean_meter_name = clean_file_name(m.id)
            meter_health_score_file = os.path.join(meter_health_score_files, f"{clean_meter_name}.json")

            if not os.path.exists(meter_health_score_file):
                continue

            with open(meter_health_score_file, "r") as f:
                meter_health_scores = json.load(f)

            health_scores = []

            for offset in range(days):
                date_entry = (from_time + dt.timedelta(days=offset)).isoformat().split("T")[0]
                if date_entry not in meter_health_scores:
                    continue
                health_scores.append(meter_health_scores[date_entry])

            total_score = 0
            for score in health_scores:
                total_score += score

            average_score = total_score//len(health_scores)

            if average_score > 5:
                average_score = 5
            elif average_score < 0:
                average_score = 0

            building_response[average_score].append(clean_meter_name)

        data[b.id] = building_response
    return make_response(jsonify(data), 200)

@api_bp.route('/populate_database')
def populate_database():
    for building in BUILDINGS():
        new_building = models.Building(
            building["building_code"],
            building["building_name"],
            building["floor_area"],
            building["year_built"],
            building["usage"],
            building["maze_map_label"]
        )

        db.session.add(new_building)
        db.session.commit()

    for meter in METERS():
        try:
            # Some entries in meters_all.json are broken - skip them
            if "Column10" in meter.keys():
                continue

            # We don't currently handle Oil meters
            if meter["meter_type"] == "Oil":
                continue

            new_meter = models.Meter(
                meter["meter_id_clean"],
                meter.get("raw_uuid", None), # If offline then there won't be a raw_uuid value - this should be handled elsewhere
                meter["serving_revised"], # Switched to serving_revised from meter_location
                meter["building_level_meter"],
                meter["meter_type"],
                meter["class"],
                meter["units_after_conversion"],
                meter["resolution"],
                meter["unit_conversion_factor"],
                meter.get("tenant", False), # Offline data doesn't specify tenant as those meters have been removed
                meter.get("building", None) # Allow unassigned meters
            )

            db.session.add(new_meter)
            db.session.commit()
        except Exception as e:
            print(e)
            print(meter)
    
    if os.path.exists(buildings_usage_file):
        for building in BUILDINGSWITHUSAGE():
            try:
                new_building_usage = models.UtilityData(
                    building["building_code"],
                    electricity={
                        "eui": building["electricity"]["eui"],
                        "eui_annual": building["electricity"]["eui_annual"],
                        "meter_ids": building["electricity"]["sensor_uuid"],
                        "usage": building["electricity"]["usage"]
                    },
                    gas={
                        "eui": building["gas"]["eui"],
                        "eui_annual": building["gas"]["eui_annual"],
                        "meter_ids": building["gas"]["sensor_uuid"],
                        "usage": building["gas"]["usage"]
                    },
                    heat={
                        "eui": building["heat"]["eui"],
                        "eui_annual": building["heat"]["eui_annual"],
                        "meter_ids": building["heat"]["sensor_uuid"],
                        "usage": building["heat"]["usage"]
                    },
                    water={
                        "eui": building["water"]["eui"],
                        "eui_annual": building["water"]["eui_annual"],
                        "meter_ids": building["water"]["sensor_uuid"],
                        "usage": building["water"]["usage"]
                    }
                )
                
                db.session.add(new_building_usage)
                db.session.commit()
            except Exception as e:
                print(e)
                print(building)

    return make_response("OK", 200)
