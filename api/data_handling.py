from flask import g, current_app
from sqlalchemy import not_

import datetime as dt
from influxdb import InfluxDBClient
import json
import math
import os
import pandas as pd
import threading
import time

from api.helpers import calculate_time_args, data_cleaner, clean_file_name, has_g_support
import api.settings as settings
from api.users import is_admin
from constants import *
from database import db
import log
import models


## Minimal/efficient call - get time series as Pandas
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
def query_influx(m: models.Meter, from_time, to_time, offline_mode) -> pd.DataFrame:
    if offline_mode:
        try:
            with open(os.path.join(offline_data_files, f"{m.id}.csv"), "r") as f:
                obs = pd.read_csv(f)
            obs['time'] = pd.to_datetime(obs['time'], format="%Y-%m-%d %H:%M:%S%z", utc=True)
            obs.drop(obs[obs.time < from_time.astimezone(dt.timezone.utc)].index, inplace=True)
            obs.drop(obs[obs.time > to_time.astimezone(dt.timezone.utc)].index, inplace=True)
            obs['time'] = obs['time'].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            return obs
        except:
            return pd.DataFrame()

    if m.SEED_uuid is None:
        return pd.DataFrame()

    if has_g_support():
        InfluxURL = g.settings["InfluxURL"]
        InfluxPort = g.settings["InfluxPort"]
        InfluxUser = g.settings["InfluxUser"]
        InfluxPass = g.settings["InfluxPass"]
        InfluxTable = g.settings["InfluxTable"]
    else:
        InfluxURL = settings.get("InfluxURL")
        InfluxPort = settings.get("InfluxPort")
        InfluxUser = settings.get("InfluxUser")
        InfluxPass = settings.get("InfluxPass")
        InfluxTable = settings.get("InfluxTable")
    
    if InfluxURL is None or InfluxPort is None or InfluxUser is None or InfluxPass is None or InfluxTable is None:
        log.write(msg="Tried to talk to Influx with no credentials",
                  extra_info="To use online mode the Influx credentials need to be filled in",
                  level=log.error)
        return pd.DataFrame()
    
    # format query
    qry = f'SELECT * as value FROM "{InfluxTable}"."autogen"."' + m.SEED_uuid + \
        '" WHERE time >= \'' + from_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\'' + \
        ' AND time <= \'' + to_time.strftime("%Y-%m-%dT%H:%M:%SZ") + '\''
    
    # create client for influx
    client = InfluxDBClient(host = InfluxURL,
                            port = InfluxPort,
                            username = InfluxUser,
                            password = InfluxPass)
    result = client.query(qry)

    return pd.DataFrame(result.get_points())

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
        "id": m.id,
        "label": m.description,
        "obs": [],
        "unit": m.units
    }

    if has_g_support():
        offline_mode = g.settings["offline_mode"]
    else:
        offline_mode = current_app.config["offline_mode"]
    
    df = query_influx(m, from_time, to_time, offline_mode)
    if df.empty:
        return out

    # standardise the value based on resolution and format time
    if m.resolution is not None:
        kappa = m.scaling_factor / m.resolution
        rho = m.resolution
    else:
        kappa = 1.0
        rho = 1.0
    
    df['value'] = round(rho * round(df['value'] * kappa), 10)
    try:
        df['time'] = pd.to_datetime(df['time'], format = '%Y-%m-%dT%H:%M:%S%z', utc=True)
    except:
        return out

    ## uncumulate if required
    if to_rate and (m.reading_type == "cumulative"):
        obs = df.to_dict('records')
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
        df = pd.DataFrame(obs)
    
    ## aggregate and scale
    if agg != "raw":
        df.set_index('time', inplace=True)
        df = df.resample(agg, origin='end').mean() ## windows go backwards
        df.reset_index(inplace=True)
    
    df['time'] = df['time'].dt.strftime('%Y-%m-%dT%H:%M:%S%z') ## check keeps utc?
    out["obs"] = json.loads(df.to_json(orient='records')) #This is ugly but seems to avoid return NaN rather than null - originally used pd.DataFrame.to_dict(df,orient="records")
    return out

## Retrieve data from influx and process it for meter health
## m - a meter object
## from_time - time to get data from (datetime)
## to_time - time to get data to (datetime)
def process_meter_health(m: models.Meter, from_time: dt.datetime, to_time: dt.datetime, offline_mode: bool, app_obj, all_outputs: list|None = None) -> dict|None:
    # Because this function can be run in a separate thread, we need to push app context onto the thread
    with app_obj.app_context():
        if offline_mode:
            # Offline data is recorded at intervals set in the settings (default: 60 mins)
            try:
                if has_g_support():
                    interval = g.settings["offline_data_interval"]
                else:
                    interval = settings.get("offline_data_interval")
            except:
                interval = 60
        else:
            # Live data is recorded at intervals set in the settings (default: 10 mins)
            try:
                if has_g_support():
                    interval = g.settings["data_interval"]
                else:
                    interval = settings.get("data_interval")
            except:
                interval = 10

        xcount = int((to_time - from_time).total_seconds()//(interval * 60)) - 1

        # Bring SQL update output back in line with the original output (instead of just returning calculated values)
        # Filter out SEED_UUID and invoiced
        keys = ["meter_id", "description", "main", "utility_type", "reading_type", "units", "resolution", "scaling_factor", "building_id"]
        out: dict = data_cleaner(m.to_dict(), keys) # type: ignore

        # time series for this meter
        m_obs = query_influx(m, from_time, to_time, offline_mode)

        # count values. if no values, stop
        out["HC_count"] = len(m_obs)
        if out["HC_count"] == 0:
            out["HC_count_perc"] = "0%"
            out["HC_score"] = 0

            if all_outputs is not None:
                # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
                all_outputs.append(out)
            return out
        
        m_obs['time'] = pd.to_datetime(m_obs['time'], format="%Y-%m-%dT%H:%M:%S%z", utc=True)
        
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
            if all_outputs is not None:
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
            if all_outputs is not None:
                # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
                all_outputs.append(out)
            return out
        out["HC_outliers_ignz_perc"] = round(100 * out["HC_outliers_ignz"] / ignz_count, 2)
        if out["HC_outliers_ignz_perc"] > 100:
            out["HC_outliers_ignz_perc"] = 100
        out["HC_outliers_ignz_perc"] = str(out["HC_outliers_ignz_perc"]) + "%"

        if all_outputs is not None:
            # Add current output to all_outputs dictionary incase we are threading this - is there a better way to do this?
            all_outputs.append(out)
        return out

def get_health(args, app_obj, returning=False):
    # Because this function can be run in a separate thread, we need to push app context onto the thread when ever we
    # want to use app specific functions

    try:
        meter_ids = args["id"]
        meter_ids = meter_ids.split(";")
    except:
        statement = db.select(models.Meter.id)
        if not is_admin():
            statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore

        with app_obj.app_context():
            meter_ids = [x.id for x in db.session.execute(statement)]

    if has_g_support():
        offline_mode = g.settings["offline_mode"]
    else:
        with app_obj.app_context():
            offline_mode = current_app.config["offline_mode"]

    to_time = args.get("to_time")
    from_time = args.get("from_time")
    try:
        date_range = int(args["date_range"])
    except:
        if has_g_support():
            date_range = g.settings["default_daterange_health-check"]
        else:
            date_range = settings.get("default_daterange_health-check")

    from_time, to_time, _ = calculate_time_args(from_time, to_time, date_range, offline_mode)

    # TODO: Should this be implemented or removed?
    try:
        fmt = args["format"]
    except:
        fmt = "json"

    ## load and trim meters
    statement = db.select(models.Meter).where(models.Meter.id.in_(meter_ids)) # type: ignore
    if not is_admin():
        statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore

    with app_obj.app_context():
        meters = db.session.execute(statement).scalars().all()

    start_time = time.time()

    out = []

    n = 15 # Process 15 meters at a time (15 was a random number I chose)
    meter_chunks = [meters[i:i + n] for i in range(0, len(meters), n)]
    for meter_chunk in meter_chunks:
        threads = []
        for m in meter_chunk:
            print(m.id)
            log.write(msg=f"Started health check for {m.id}", level=log.info)
            threads.append(threading.Thread(target=process_meter_health, args=(m, from_time, to_time, offline_mode, app_obj, out), name=f"HC_{m.id}", daemon=True))
            threads[-1].start()

        # Wait for all threads in chunk to complete
        for t in threads:
            t.join()

    proc_time = (time.time() - start_time)
    # print("--- Health check took %s seconds ---" % proc_time)
    log.write(msg=f"Health check took {proc_time} seconds", level=log.info)

    # save cache, but only if it's a "default" query
    if set(args).isdisjoint({"date_range", "from_time", "to_time", "id"}):
        try:
            for meter in out:
                with app_obj.app_context():
                    update_health_check(meter)

            try:
                hc_meta = {
                    "to_time": to_time.timestamp(),
                    "from_time": from_time.timestamp(),
                    "timestamp": dt.datetime.now(dt.timezone.utc).timestamp(),
                    "processing_time": proc_time,
                    "offline": offline_mode
                }

                with app_obj.app_context():
                    existing_hc_meta = db.session.execute(db.select(models.CacheMeta).where(models.CacheMeta.meta_type == "health_check")).scalar_one_or_none()
                    if existing_hc_meta is None:
                        new_hc_meta = models.CacheMeta("health_check", hc_meta)
                        db.session.add(new_hc_meta)
                    else:
                        existing_hc_meta.update(hc_meta)
                    db.session.commit()
            except Exception as e:
                print("Error trying to save metadata for latest HC cache")
                print(e)
                log.write(msg="Error trying to save metadata for latest health check cache", extra_info=str(e), level=log.warning)
        except Exception as e:
            print("Error trying to save current health check in cache")
            print(e)
            log.write(msg="Error trying to save latest health check", extra_info=str(e), level=log.warning)

        print("Completed HC update")
        log.write(msg="Completed health check update", level=log.info)

    if returning:
        exclude_tenants = not is_admin()
        if not exclude_tenants:
            return out

        cleaned_out = []
        for meter_data in out:
            with app_obj.app_context():
                meter = db.session.execute(db.select(models.Meter).where(models.Meter.id == meter_data["meter_id"])).scalar_one_or_none()
            if meter is None:
                continue

            if meter.invoiced:
                continue

            cleaned_out.append(meter_data)
        return out

def update_health_check(values: dict):
    existing_hc = db.session.execute(db.select(models.HealthCheck).where(models.HealthCheck.meter_id == values["meter_id"])).scalar_one_or_none()
    if existing_hc is None:
        new_hc = models.HealthCheck(meter_id=values["meter_id"], hc_data=values)
        db.session.add(new_hc)
    else:
        existing_hc.update(values)
    db.session.commit()

def generate_summary(from_time: dt.datetime, to_time: dt.datetime, days: int, cache_result: bool) -> dict:
    start_time = time.time()
    data = {}
    
    agg = f"{days*24*2}h"
    time_days_multiplier = 365/days
    
    buildings = db.session.execute(
        db.select(models.Building)
        .where(not_(models.Building.floor_area.is_(None))) # type: ignore
    ).scalars().all()

    units = {'gas': "m3", 'electricity': "kWh", 'heat': "MWh", 'water': "m3"}
    building_meta_keys = ["building_name", "floor_area", "year_built", "occupancy_type", "maze_map_label"]

    if not os.path.exists(benchmark_data_file):
        log.write(msg="Benchmark file is missing", level=log.error)
        raise FileNotFoundError("Benchmark file exists")
    
    with open(benchmark_data_file, "r") as f:
        benchmark_data = json.load(f)

    exclude_tenants = not is_admin()
    
    for b in buildings:
        building_response = {}

        statement = db.select(models.Meter).where(models.Meter.building_id == b.id).where(models.Meter.main)
        if exclude_tenants:
            statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
        
        meters = db.session.execute(statement).scalars().all()
        
        if len(meters) == 0:
            continue
        
        for m in meters:
            meter_type = m.utility_type

            if meter_type not in units.keys():
                continue
            
            # Calculate usage
            usage = None
            
            # This is faster than the normal calculation
            if m.reading_type == "cumulative":
                x = query_time_series(m, from_time, to_time, agg="raw", to_rate=False)
                # No data available
                if len(x['obs']) == 0:
                    continue
                
                df = pd.DataFrame.from_dict(x['obs'])
                df['time'] = pd.to_datetime(df['time'], format = '%Y-%m-%dT%H:%M:%S%z', utc=True)
                df.set_index('time', inplace=True)
                lower_index = df.first_valid_index()
                upper_index = df.last_valid_index()
                if lower_index is None or upper_index is None or lower_index == upper_index:
                    usage = None
                else:
                    lower_value = df['value'][lower_index]
                    upper_value = df['value'][upper_index]
                    
                    if lower_value > upper_value:
                        usage = None
                    else:
                        usage = upper_value - lower_value
            
            # This is the original calculation, it is slower but is more likely to get a usage value
            if m.reading_type == "rate" or usage is None:
                x = query_time_series(m, from_time, to_time, agg="raw", to_rate=True)
                # No data available
                if len(x['obs']) == 0:
                    continue
                
                df = pd.DataFrame.from_dict(x['obs'])
                df['time'] = pd.to_datetime(df['time'], format = '%Y-%m-%dT%H:%M:%S%z', utc=True)
                df.set_index('time', inplace=True)
                df = df.resample(agg, origin='end').sum()
                usage = x['obs'][0]['value']
            
            if usage is None:
                usage = 0

            # handle unit changes
            if m.units != units[meter_type]:
                if meter_type == "heat" and m.units == "kWh":
                    usage *= 1e-3  # to MWh
                elif meter_type == "heat" and m.units == "kW":
                    # presume 10 minute data, round to nearest kWh
                    usage = round(usage * 1e-3 * (1.0 / 6.0), 3)
                else:
                    continue

            # process EUI
            # eui = float(f"{(usage * time_days_multiplier/ b.floor_area):.2g}")
            eui = round(usage * time_days_multiplier/ b.floor_area)

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
        
        # Filter out building id as the data is indexed with it
        building_response["meta"] = data_cleaner(b.to_dict(), building_meta_keys)
        
        if cache_result:
            existing_summary = db.session.execute(db.select(models.UtilityData).where(models.UtilityData.building_id == b.id)).scalar_one_or_none()
            if existing_summary is None:
                new_hc = models.UtilityData(
                    building_id=b.id,
                    electricity=building_response.get("electricity", {}),
                    gas=building_response.get("gas", {}),
                    heat=building_response.get("heat", {}),
                    water=building_response.get("water", {})
                )
                db.session.add(new_hc)
            else:
                existing_summary.update(
                    electricity=building_response.get("electricity", {}),
                    gas=building_response.get("gas", {}),
                    heat=building_response.get("heat", {}),
                    water=building_response.get("water", {})
                )
            db.session.commit()
    
        data[b.id] = building_response
    
    end_time = time.time()
    
    if cache_result:
        existing_meta = db.session.execute(db.select(models.CacheMeta).where(models.CacheMeta.meta_type == "usage_summary")).scalar_one_or_none()
        
        new_meta = {
            "to_time": to_time.timestamp(),
            "from_time": from_time.timestamp(),
            "timestamp": dt.datetime.now(tz=dt.timezone.utc).timestamp(),
            "processing_time": end_time - start_time,
            "offline": g.settings["offline_mode"]
        }
        
        if existing_meta is None:
            building_usage_cache_meta = models.CacheMeta(
                "usage_summary",
                new_meta
            )
            db.session.add(building_usage_cache_meta)
        else:
            existing_meta.update(new_meta)
        db.session.commit()
    
    return data

def generate_health_score(from_time: dt.datetime, days: int) -> dict:
    data = {}
    
    buildings = db.session.execute(db.select(models.Building)).scalars().all()
    
    for b in buildings:
        building_response = {
            0: [],
            1: [],
            2: [],
            3: [],
            4: [],
            5: []
        }
        
        statement = db.select(models.Meter).where(models.Meter.building_id == b.id).where(models.Meter.main)
        if not is_admin():
            statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
        
        meters = db.session.execute(statement).scalars().all()
        
        if len(meters) == 0:
            continue

        for m in meters:
            clean_meter_name = clean_file_name(m.id)
            if g.settings["offline_mode"]:
                meter_health_score_file = os.path.join(offline_meter_health_score_files, f"{clean_meter_name}.json")
            else:
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

            if len(health_scores) != 0:
                average_score = total_score//len(health_scores)
            else:
                average_score = 0
            
            if average_score > 5:
                average_score = 5
            elif average_score < 0:
                average_score = 0

            building_response[average_score].append(clean_meter_name)

        data[b.id] = building_response
    return data