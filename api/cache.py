from flask import g, current_app

import datetime as dt
import json
import threading

from api.data_handling import process_meter_health, query_time_series
from api.helpers import clean_file_name, has_g_support
from constants import *
from database import db
import log
import models
import settings


cache_generation_lock = threading.Lock()

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

## Generate the cache for the provided meter
## m - the meter to generate cache for
## data_start_time - The earliest date in the cache (If None, assume that all data that we want to access is available)
## data_end_time - The latest date that there is data for (Current time if online)
def generate_meter_cache(m: models.Meter, data_start_time: dt.datetime, data_end_time: dt.datetime, app_obj) -> None:
    # Because this function can be run in a separate thread, we need to push app context onto the thread
    with app_obj.app_context():
        print(f"Started: {m.id}")
        log.write(msg=f"Started data cache generation for {m.id}", level=log.info)
        try:
            file_name = clean_file_name(f"{m.id}.csv")

            if has_g_support():
                offline_mode = g.settings["data"]["offline_mode"]
                cache_time_health_score = g.settings["data"]["cache_time_health_score"]
                cache_time_summary = g.settings["data"]["cache_time_summary"]
            else:
                offline_mode = current_app.config["offline_mode"]
                cache_time_health_score = int(settings.get("cache_time_health_score", "data")) # type: ignore
                cache_time_summary = int(settings.get("cache_time_summary", "data")) # type: ignore
            
            if offline_mode:
                meter_health_score_file = os.path.join(offline_meter_health_score_files, file_name)
            else:
                meter_health_score_file = os.path.join(meter_health_score_files, file_name)
            
            # Meter Health Cache
            meter_health_scores = {}
            if os.path.exists(meter_health_score_file):
                try:
                    meter_health_scores = json.load(open(meter_health_score_file, "r"))
                except:
                    meter_health_scores = {}
            
            for cache_item in cache_items(cache_time_health_score, meter_health_scores, data_start_time, data_end_time):
                score = process_meter_health(m, cache_item[1], cache_item[2], offline_mode, app_obj)
                if score is None:
                    # Something happened to the offline data since running cache_validity_checker, quit thread
                    print(f"Ended: {m.id} - An Error occurred accessing the offline data for this meter")
                    log.write(msg=f"Error accessing the offline data for {m.id}", level=log.error)
                    return
                meter_health_scores.update({cache_item[0].isoformat(): score['HC_score']})

            with open(meter_health_score_file, "w") as f:
                json.dump(meter_health_scores, f)

            # Meter Snapshot Cache
            if offline_mode:
                meter_snapshots_file = os.path.join(offline_meter_snapshots_files, file_name)
            else:
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
            log.write(msg=f"An error occurred generating cache for meter {m.id}", level=log.error)
            raise e
        print(f"Ended: {m.id}")
        log.write(msg=f"Finished data cache generation for {m.id}", level=log.info)

## Generates the cache data for meter health scores and meter snapshots
## return_if_generating - Whether to return or wait for current generation to complete - defaults to True
##
## The generation of each meter's cache is handed off to a separate thread, this dramatically speeds up cache generation
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

    if g.settings["data"]["offline_mode"]:
        data_start_time = dt.datetime.strptime(g.settings["metadata"]["offline_data_start_time"], "%Y-%m-%dT%H:%M:%S%z")
        data_end_time = dt.datetime.strptime(g.settings["metadata"]["offline_data_end_time"], "%Y-%m-%dT%H:%M:%S%z")
        current_meter_health_score_files = offline_meter_health_score_files
        current_meter_snapshots_files = offline_meter_snapshots_files
    else:
        data_start_time = None
        data_end_time = dt.datetime.now(dt.timezone.utc)
        current_meter_health_score_files = meter_health_score_files
        current_meter_snapshots_files = meter_snapshots_files

    # Don't need to filter id by not null as id is primary key and therefore not null
    # We aren't filtering out tenanted meters here so that the cache contains all meters
    meters = db.session.execute(db.select(models.Meter)).scalars().all()
    n = g.settings["server"]["meter_batch_size"]
    meter_chunks = [meters[i:i + n] for i in range(0, len(meters), n)]

    seen_meters = []

    for meter_chunk in meter_chunks:
        threads = []
        for m in meter_chunk:
            clean_meter_name = clean_file_name(m.id)
            thread_name = f"Mtr_Cache_Gen_{clean_meter_name}"
            file_name = f"{clean_meter_name}.csv"

            if g.settings["data"]["offline_mode"]:
                if not os.path.exists(os.path.join(DATA_DIR, "offline", file_name)):
                    print(f"Skipping: {m.id}")
                    continue

            meter_health_score_file = os.path.join(current_meter_health_score_files, file_name)
            meter_snapshots_file = os.path.join(current_meter_snapshots_files, file_name)

            seen_meters.append(file_name)
            
            if (cache_validity_checker(g.settings["data"]["cache_time_health_score"],
                                       meter_health_score_file,
                                       data_start_time,
                                       data_end_time)
                and cache_validity_checker(g.settings["data"]["cache_time_summary"],
                                           meter_snapshots_file,
                                           data_start_time,
                                           data_end_time)):
                print(f"Skipping: {m.id}")
                log.write(msg=f"Skipping data cache generation for {m.id}", level=log.info)
                continue

            threads.append(threading.Thread(target=generate_meter_cache, args=(m, data_start_time, data_end_time, current_app.app_context()), name=thread_name, daemon=True))
            threads[-1].start()

        # Wait for all threads in chunk to complete
        for t in threads:
            t.join()

    # Clean up non-existent meters
    existing_cache_files = os.listdir(current_meter_health_score_files)
    for existing_cache_file in existing_cache_files:
        if existing_cache_file[-4:] != ".csv":
            continue
        if existing_cache_file not in seen_meters:
            os.remove(os.path.join(current_meter_health_score_files, existing_cache_file))
    
    existing_cache_files = os.listdir(current_meter_health_score_files)
    for existing_cache_file in existing_cache_files:
        if existing_cache_file[-4:] != ".csv":
            continue
        if existing_cache_file not in seen_meters:
            os.remove(os.path.join(current_meter_health_score_files, existing_cache_file))
    
    cache_generation_lock.release()