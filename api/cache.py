import datetime as dt
import json
import os
import threading
import time

from constants import *
from database import db
import models
from api.data_handling import process_meter_health, query_time_series
from api.helpers import calculate_time_args, is_admin, clean_file_name


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

    if offlineMode:
        with open(offline_meta_file, "r") as f:
            anon_data_meta = json.load(f)
        data_start_time = dt.datetime.strptime(anon_data_meta['start_time'], "%Y-%m-%dT%H:%M:%S%z")
        data_end_time = dt.datetime.strptime(anon_data_meta['end_time'], "%Y-%m-%dT%H:%M:%S%z")
    else:
        data_start_time = None
        data_end_time = dt.datetime.now(dt.timezone.utc)

    # Don't need to filter id by not null as id is primary key and therefore not null
    # We aren't filtering out tenanted meters here so that the cache contains all meters
    meters = db.session.execute(db.select(models.Meter)).scalars().all()

    n = 35 # Process 35 meters at a time (35 was a random number I chose)
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

def get_health(args, returning=False, app_context=None):
    # Because this function can be run in a separate thread, we need to
    if app_context is not None:
        app_context.push()

    try:
        meter_ids = args["id"] # this is url decoded
        meter_ids = meter_ids.split(";")
    except:
        statement = db.select(models.Meter.id)
        if not is_admin():
            statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
        
        meter_ids = [x.id for x in db.session.execute(statement)]

    to_time = args.get("to_time")
    from_time = args.get("from_time")
    try:
        date_range = int(args["date_range"]) # this is url decoded
    except:
        date_range = 30
    from_time, to_time, _ = calculate_time_args(from_time, to_time, date_range)

    # TODO: Should this be implemented or removed?
    try:
        fmt = args["format"] # this is url decoded
    except:
        fmt = "json"

    ## load and trim meters
    statement = db.select(models.Meter).where(models.Meter.id.in_(meter_ids)) # type: ignore
    if not is_admin():
        statement = statement.where(models.Meter.invoiced.is_(False)) # type: ignore
    
    meters = db.session.execute(statement).scalars().all()

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
    if set(args).isdisjoint({"date_range", "from_time", "to_time", "id"}):
        try:
            for meter in out:
                update_health_check(meter)

            try:
                hc_meta = {
                    "to_time": to_time.timestamp(),
                    "from_time": from_time.timestamp(),
                    "timestamp": dt.datetime.now(dt.timezone.utc).timestamp(),
                    "processing_time": proc_time
                }

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
        except Exception as e:
            print("Error trying to save current health check in cache")
            print(e)

        print("Completed HC update")
    
    if returning:
        exclude_tenants = not is_admin()
        if not exclude_tenants:
            return out
        
        cleaned_out = []
        for meter_data in out:
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