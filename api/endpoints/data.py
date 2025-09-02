from flask import Blueprint, current_app, jsonify, make_response, request, Response, g

import datetime as dt
from functools import wraps
import json
import os
import threading
import time

import api.cache as cache
from api.data_handling import query_time_series, get_health, generate_summary, generate_health_score
from api.helpers import calculate_time_args, data_cleaner
from api.users import get_user_level, is_admin
from constants import *
from database import db, initial_database_population
import log
import models


data_api_bp = Blueprint('data_api_bp', __name__, static_url_path='')

# decorator to limit certain pages to a specific user level
def required_user_level(level_config_key):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            # Bypass authentication for internal calls
            if (request.remote_addr in ['127.0.0.1', '::1']
                and request.headers.get("Authorization") == current_app.config["internal_api_key"]):
                print("Bypassed user level authorization for internal call")
                log.write(msg="Bypassed user level authorization for internal call", level=log.info)
                return function(*args, **kwargs)
            
            try:
                level = g.settings[level_config_key]
                
                # Skip validating if required level is 0 (allow unauthenticated users)
                if level != 0:
                    cookies = request.cookies
                    email = cookies.get("Email", None)
                    sessionID = cookies.get("SessionID", None)
                    
                    if get_user_level(email, sessionID) < level:
                        return make_response("Access Denied", 401)
            except Exception as e:
                print("No or wrong cookie")
                log.write(msg="No or wrong cookie", extra_info=str(e), level=log.warning)
                return make_response("Access Denied", 401)

            return function(*args, **kwargs)
        return wrapper
    return decorator


###########################################################
###                      Endpoints                      ###
###########################################################

## simple health check the server is running
## Parameters:
## Return:
## current time
##
## Example:
## http://127.0.0.1:5000/api/
@data_api_bp.route('/')
@data_api_bp.route('')
def health():
    return make_response(jsonify( dt.datetime.now(dt.timezone.utc) ), 200)

## Helper function needed for accessing raw list of all meters in other blueprint
@data_api_bp.route('/meters/')
@data_api_bp.route('/meters')
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def meters():
    statement = db.select(models.Meter)
    if not is_admin():
        statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
    data = [x.to_dict() for x in db.session.execute(statement).scalars().all()]
    
    # Filter out SEED_UUID and invoiced
    try:
        keys = request.args["columns"]
        if keys is None:
            raise Exception
        keys = keys.split(";")
    except:
        keys = ["meter_id", "description", "main", "utility_type", "reading_type", "units", "resolution",
                "scaling_factor", "building_id", "building_name"]
    
    out = data_cleaner(data, keys)
    
    return make_response(jsonify(out), 200)

## Health check cache meta
@data_api_bp.route('/hc-meta/')
@data_api_bp.route('/hc-meta')
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def hc_meta():
    hc_meta = db.session.execute(
        db.select(models.CacheMeta)
        .where(models.CacheMeta.meta_type == "health_check")
    ).scalar_one_or_none()
    if hc_meta is None:
        return make_response(jsonify({}), 404)

    return make_response(jsonify(hc_meta.to_dict()), 200)

## Create usage summary of meters
##
## Only returns meters that are attached to a building.
## Only includes buildings with a valid floor area at least one meter.
##
## Parameters:
## from_time - options initial date YYYY-mm-dd format (summary of usage from 00:00 of this date) - default 30 days before to_time
## to_time - options final observation time in YYYY-mm-dd format (summary of usage upto 23:59 of this date) - default current date
##
## Returns:
## json object:
## {
##     "building_code": {
##         "meta": {
##             Building metadata
##         },
##         "electricity": {
##             "meter_id": {
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
##             "meter_id": {
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
##             "meter_id": {
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
##             "meter_id": {
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
@data_api_bp.route('/summary/')
@data_api_bp.route('/summary')
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def summary():
    to_time = request.args.get("to_time")
    from_time = request.args.get("from_time")
    offline_mode = g.settings["offline_mode"]
    from_time, to_time, days = calculate_time_args(from_time, to_time, g.settings["default_daterange_benchmark"], offline_mode)

    cache_meta = db.session.execute(
        db.select(models.CacheMeta)
        .where(models.CacheMeta.meta_type == "usage_summary")
    ).scalar_one_or_none()
    
    valid_cache = False
    if (cache_meta is not None
        and cache_meta.to_time == to_time.timestamp()
        and cache_meta.from_time == from_time.timestamp()
        and cache_meta.offline == g.settings["offline_mode"]):
        valid_cache = True
    
    data = {}
    if valid_cache:
        for x in db.session.execute(db.select(models.UtilityData)).scalars().all():
            data[x.building.id] = x.to_dict()
    else:
        cache_result = True
        if g.settings["offline_mode"]:
            latest_data_date = dt.datetime.strptime(g.settings["offline_data_end_time"], "%Y-%m-%dT%H:%M:%S%z")
        else:
            latest_data_date = dt.datetime.now(dt.timezone.utc)
        latest_data_date = latest_data_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if to_time < latest_data_date:
            cache_result = False
        
        if days != 365:
            cache_result = False
        
        data = generate_summary(from_time, to_time, days, cache_result)
    return make_response(jsonify(data), 200)

## time series of data for a given meter
##
## Parameters:
## id - meter id
## to_time - final observation time, defaults to current time
## from_time - first observation time, defaults to 30 days ago
## format - use csv if required otherwise returns json
## aggregate - aggregate as used by pandas e.g. 168H, 7D etc.
## Note that 168H and 7D are the same but only the formers works in pandas 2.0.3
## to_rate - should cumulative values be converted to rate
##
## Return:
## json format time series data
## Example:
## http://127.0.0.1:5000/api/meter-obs?id=AP001_L01_M2
## http://127.0.0.1:5000/api/meter-obs?id=AP001_L01_M2;AP080_L01_M5
## http://127.0.0.1:5000/api/meter-obs?id=WTHR_0
@data_api_bp.route('/meter-obs/')
@data_api_bp.route('/meter-obs')
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def meter_obs():
    try:
        meter_ids = request.args["id"] # this is url decoded
        meter_ids = meter_ids.split(";")
    except:
        return make_response("Bad meter id supplied", 500)

    to_time = request.args.get("to_time")
    from_time = request.args.get("from_time")
    from_time, to_time, _ = calculate_time_args(from_time, to_time, g.settings["default_daterange_browser"], offline_mode=g.settings["offline_mode"])

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

    statement = db.select(models.Meter).where(models.Meter.id.in_(meter_ids)) # type: ignore
    if not is_admin():
        statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
    
    meters = db.session.execute(statement).scalars().all()

    out = dict.fromkeys(meter_ids)

    for m in meters:
        out[m.id] = query_time_series(m, from_time, to_time, agg=agg, to_rate=to_rate)

    if fmt == "csv":
        try:
            csv = 'series,unit,time,value\n'
            ## repackage data as csv and return
            for k in out.keys():
                for obs in out[k]["obs"]:
                    csv += out[k]["id"] + ',' + out[k]["unit"] + "," + obs["time"] + ',' + str(obs["value"]) + '\n'

            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=export.csv"})
        except:
            return make_response("Unable to make csv file",500)

    else:
        return make_response(jsonify(out), 200)

## Create health check of meters (requested by IES)
##
## Parameters:
## id - meter id or missing for all gauges
## to_time - final observation time, defaults to current time
## from_time - first observation time, defaults to 30 days ago
## date_range - how far back we want to check in days (ignored if from_time is given)
##
## Return:
## json format time series data
##
## Return Headers:
## X-Cache-State: either 'stale' or 'fresh'
##
## Example:
## http://127.0.0.1:5000/api/meter-health?id=AP001_L01_M2&date_range=30
@data_api_bp.route('/meter-health/')
@data_api_bp.route('/meter-health')
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def meter_health():
    # The frontend should read the headers sent with this response and send another request later to retrieve the latest version if 'X-Cache-State'=stale
    # TODO: maybe add a header telling the frontend how long to wait (could guesstimate this from number of meters)
    #       Alternativly, the frontend could just set timeouts with increasing intervals until it received a fresh cache
    
    # load existing cache
    statement = db.select(models.HealthCheck)
    if not is_admin():
        statement = (statement.where(models.HealthCheck.meter_id == models.Meter.id)
                     .where(models.Meter.invoiced.is_(False))) # type: ignore
    hc_cache = [x.to_dict() for x in db.session.execute(statement).scalars().all()]
    
    # If database hasn't been initialised properly then the frontend enters a loop of retries because a 500 is returned
    # if there isn't any cache available to serve.
    if len(db.session.execute(db.select(models.Meter)).scalars().all()) == 0:
        response = make_response(jsonify([]), 200)
        response.headers['X-Cache-State'] = "fresh"
        return response

    # TODO: What does the last statement do?
    if len(request.args) == 0 or g.settings["offline_mode"] or list(request.args.keys()) == ["hidden"]:
        if hc_cache:
            try:
                if g.settings["offline_mode"]:
                    latest_data_date = dt.datetime.strptime(g.settings["offline_data_end_time"],
                                                            "%Y-%m-%dT%H:%M:%S%z").timestamp()
                else:
                    latest_data_date = dt.datetime.now(dt.timezone.utc).timestamp()

                meta = db.session.execute(
                    db.select(models.CacheMeta)
                    .where(models.CacheMeta.meta_type == "health_check")
                ).scalar_one_or_none()
                if meta is None:
                    raise Exception
                
                if not g.settings["offline_mode"]:
                    cache_age = latest_data_date - meta.to_time
                    if cache_age < 3600 * g.settings["hc_update_time"] and meta.offline == g.settings["offline_mode"]:
                        response = make_response(jsonify(hc_cache), 200)
                        response.headers['X-Cache-State'] = "fresh"
                        return response
                elif meta.offline == g.settings["offline_mode"]:
                        response = make_response(jsonify(hc_cache), 200)
                        response.headers['X-Cache-State'] = "fresh"
                        return response
            except:
                updateOngoing = False
                for th in threading.enumerate():
                    if th.name == "updateMainHC":
                        updateOngoing = True
                        break
                if not updateOngoing:
                    print("Error reading cache metadata, skipping HC cache")
                    log.write(msg="Error reading cache metadata, skipping HC cache", level=log.warning)

        # TODO: Implement a lock here instead of this
        updateOngoing = False
        for th in threading.enumerate():
            if th.name == "updateMainHC":
                updateOngoing = True
                break
        
        if not updateOngoing:
            thread = threading.Thread(target=get_health, args=(request.args, current_app._get_current_object(), False),
                                      name="updateMainHC", daemon=True)
            thread.start()

        if hc_cache:
            response = make_response(jsonify(hc_cache), 200)
            response.headers['X-Cache-State'] = "stale"
            return response

        response = make_response(jsonify([]), 500)
        response.headers['X-Cache-State'] = "stale"
        return response
    else:
        health_check_data = get_health(request.args, current_app._get_current_object(), True)
        response = make_response(jsonify(health_check_data), 200)
        response.headers['X-Cache-State'] = "fresh"
        return response

## Return meter hierarchy
##
## Only returns meters that are attached to a building and only includes buildings with meters
##
## Return:
## json object:
## {
##     "building_code": {
##         "meta": {
##             Building metadata
##         },
##         "electricity": [
##             "meter_id",
##             ...
##         ],
##         "gas": [
##             "meter_id",
##             ...
##         ],
##         "heat": [
##             "meter_id",
##             ...
##         ],
##         "water": [
##             "meter_id",
##             ...
##         ]
##     },
##     ...
## }
@data_api_bp.route('/meter-hierarchy/')
@data_api_bp.route('/meter-hierarchy')
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def meter_hierarchy():
    buildings = db.session.execute(db.select(models.Building)).scalars().all()

    data = {}
    for b in buildings:
        building_response = {}
        
        statement = db.select(models.Meter).where(models.Meter.building_id == b.id).where(models.Meter.main)
        if not is_admin():
            statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
        
        meters = db.session.execute(statement).scalars().all()
        
        if len(meters) == 0:
            continue
        
        for m in meters:
            meter_type = m.utility_type
            if meter_type not in ['gas', 'electricity', 'heat', 'water']:
                continue

            # Create utility entries on occurrence so that the response is smaller
            if meter_type not in building_response:
                building_response[meter_type] = []

            building_response[meter_type].append(m.id)
        
        building_response["meta"] = b.to_dict()
        data[b.id] = building_response

    return make_response(jsonify(data), 200)

## Parameters:
## to_time - options final observation time in YYYY-MM-DD format (meter health up to 23:59 of this date) - default current date
## from_time - options initial date YYYY-MM-DD format (meter health from 00:00 of this date) - default 30 days before to_time
##
## [
##     {
##         building_id:[
##             0: [meter_id],
##             1: [meter_id],
##             2: [meter_id],
##             3: [meter_id],
##             4: [meter_id],
##             5: [meter_id]
##         ],
##         ...
##     }
## ]
##
## Example:
## http://127.0.0.1:5000/api/health-score
@data_api_bp.route('/health-score/')
@data_api_bp.route('/health-score')
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def health_score():
    to_time = request.args.get("to_time")
    from_time = request.args.get("from_time")
    from_time, to_time, days = calculate_time_args(from_time, to_time, g.settings["default_daterange_health-check"], offline_mode=g.settings["offline_mode"])

    data = generate_health_score(from_time, days)
    
    return make_response(jsonify(data), 200)

@data_api_bp.route('/offline-meta/')
@data_api_bp.route('/offline-meta')
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def offline_meta():
    out = {
        "start_time": g.settings["offline_data_start_time"],
        "end_time": g.settings["offline_data_end_time"],
        "interval": g.settings["offline_data_end_time"]
    }
    
    return make_response(jsonify(out), 200)

@data_api_bp.route("/mazemap-polygons/")
@data_api_bp.route("/mazemap-polygons")
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def mazemap_polygons():
    if not os.path.exists(mazemap_polygons_file):
        log.write(msg="Mazemap polygons are missing", level=log.error)
        return make_response(jsonify({}), 404)
    
    with open(mazemap_polygons_file, "r") as f:
        data = json.load(f)
    return make_response(jsonify(data), 200)

@data_api_bp.route('/regenerate-cache/', methods=["GET", "POST"])
@data_api_bp.route('/regenerate-cache', methods=["GET", "POST"])
@required_user_level("USER_LEVEL_ADMIN")
def regenerate_cache():
    start_time = time.time()
    cache.generate_meter_data_cache()
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Cache regeneratation took {total_time} seconds")
    log.write(msg=f"Cache regeneratation took {total_time} seconds", level=log.info)
    return make_response(str(total_time), 200)

@data_api_bp.route('/populate-database/')
@data_api_bp.route('/populate-database')
@required_user_level("USER_LEVEL_ADMIN")
def populate_database():
    result = initial_database_population()
    if result:
        return make_response("OK", 200)
    return make_response("ERROR", 500)

## Read the server logs
##
## Parameters:
## from_time - The earliest timestamp to look for
## to_time - The latest timestamp to look for
## minimum_level - The lowest log level to look for (inclusive)
## exact_level - The exact log level to look for (overrules minimal_level)
## count - The number of logs to return
## newest_first - Whether we start with the newest log ("true"/"false") - defaults to True
##
## Returns:
## json object:
## [
##     {
##         "info": log info,  # May be "" for some logs
##         "level": log level,
##         "message": log message,
##         "timestamp": log timestamp
##     },
##     ...
## ]
##
## Example:
## http://127.0.0.1:5000/api/logs - Returns all logs
## http://127.0.0.1:5000/api/logs?from_time=1754672345&exact_level=info&count=100&newest_first=False
## http://127.0.0.1:5000/api/logs?to_time=1754672345&minimum_level=error
@data_api_bp.route('/logs/')
@data_api_bp.route('/logs')
def logs():
    try:
        from_time = dt.datetime.fromtimestamp(float(request.args["from_time"]))
    except:
        from_time = None
    
    try:
        to_time = dt.datetime.fromtimestamp(float(request.args["to_time"]))
    except:
        to_time = None
    
    try:
        minimum_level = request.args["minimum_level"].lower()
        if minimum_level not in log.index.keys():
            minimum_level = None
    except:
        minimum_level = None
    
    try:
        exact_level = request.args["exact_level"].lower()
        if exact_level not in log.index.keys():
            exact_level = None
    except:
        exact_level = None
    
    try:
        count = int(request.args["count"])
    except:
        count = None
    
    try:
        newest_first= False
        if str(request.args["newest_first"]).strip().lower() in ["yes", "1", "y", "true"]:
            newest_first = True
    except:
        newest_first = True
    
    data = log.read(from_time=from_time, to_time=to_time, minimum_level=minimum_level, exact_level=exact_level,
                    count=count, newest_first=newest_first)
    if data is None:
        return make_response(jsonify([]), 404)

    return make_response(jsonify(data), 200)