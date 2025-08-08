from dotenv import load_dotenv
import json
import pandas as pd
import os
import sys

import log


def generate_offine_meta() -> bool:
    start_time = None
    end_time = None
    interval = None
    
    for file in os.listdir(offline_data_files):
        if not file.endswith(".csv"):
            continue
        
        file_path = os.path.join(offline_data_files, file)
        df = pd.read_csv(file_path)
        df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M:%S%z", utc=True)
        lower_index = df.first_valid_index()
        upper_index = df.last_valid_index()
        if lower_index is None or upper_index is None:
            return False
        
        temp_start_time = df['time'][lower_index]
        temp_end_time = df['time'][upper_index]
        
        temp_interval = df['time'].diff().dropna().min().total_seconds()/60
        if start_time is None:
            start_time = temp_start_time
        if end_time is None:
            end_time = temp_end_time
        if interval is None:
            interval = temp_interval
        
        if temp_start_time < start_time:
            start_time = temp_start_time
        if temp_end_time > end_time:
            end_time = temp_end_time
        if temp_interval != interval:
            return False

    if start_time is None or end_time is None:
        return False
    
    out = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "interval": interval
    }
    
    with open(offline_meta_file, "w") as f:
        json.dump(out, f, indent=4)
    
    return True


load_dotenv()

###########################################################
###                  Loading variables                  ###
###########################################################

val = os.getenv("OFFLINE_MODE", "True")
offlineMode = val.strip().lower() in ("1", "true", "yes", "on")

InfluxURL = os.getenv("INFLUX_URL")
InfluxPort = os.getenv("INFLUX_PORT")
InfluxUser = os.getenv("INFLUX_USER")
InfluxPass = os.getenv("INFLUX_PASS")

if InfluxURL is None or InfluxPort is None or InfluxUser is None or InfluxPass is None:
    InfluxURL = None
    InfluxPort = None
    InfluxUser = None
    InfluxPass = None
    offlineMode = True

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

hc_update_time = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", "9"))

# meters_file = os.path.join(DATA_DIR, "input", 'meters_all.json')
# buildings_file = os.path.join(DATA_DIR, "input", 'UniHierarchy.json')
metadata_file = os.path.join(DATA_DIR, "input", "SingleSourceOfTruth.xlsx")
meter_sheet = "Energie points"
building_sheet = "Buildings"

meter_health_score_files = os.path.join(DATA_DIR, "cache", "meter_health_score")
if not os.path.exists(meter_health_score_files):
    os.makedirs(meter_health_score_files)
meter_snapshots_files = os.path.join(DATA_DIR, "cache", "meter_snapshots")
if not os.path.exists(meter_snapshots_files):
    os.makedirs(meter_snapshots_files)

cache_time_health_score = int(os.getenv("HEALTH_SCORE_CACHE_TIME", "365"))
cache_time_summary = int(os.getenv("SUMMARY_CACHE_TIME", "30"))

benchmark_data_file = os.path.join(DATA_DIR, "benchmarks.json")

offline_meta_file = os.path.join(DATA_DIR, "meta", "offline_data.json")
offline_data_files = os.path.join(DATA_DIR, "offline")

mazemap_polygons_file = os.path.join(DATA_DIR, "mazemap_polygons.json")

log_level = os.getenv("LOG_LEVEL", "warning")

del val

###########################################################
###              Check required files exist             ###
###########################################################

cannot_initialise = False

if offlineMode and not os.path.exists(os.path.join(DATA_DIR, "offline")):
    print("\n" + "="*20)
    print("\tERROR: You are runnning in offline mode without any offline data!")
    print("\tPlease place your data in ./data/offline/")
    print("="*20 + "\n")
    log.write(msg="You are runnning in offline mode without any offline data",
                   extra_info="Place your data in ./data/offline/",
                   level=log.critical)
    cannot_initialise = True

if offlineMode and not os.path.exists(offline_meta_file):
    result = generate_offine_meta()
    if not result:
        print("\n" + "="*20)
        print("\tERROR: You are runnning in offline mode with no offline metadata (and it couldn't be generated)!")
        print("\tPlease place your metadata in ./data/meta/offline_data.json")
        print("="*20 + "\n")
        log.write(msg="You are runnning in offline mode with no offline metadata (and it couldn't be generated)",
                       extra_info="Place your metadata in ./data/meta/offline_data.json",
                       level=log.critical)
        cannot_initialise = True

if not os.path.exists(benchmark_data_file):
    print("\n" + "="*20)
    print("\tERROR: You have removed the included benchmark data!")
    print("\tPlease place the benchmark data in ./data/benchmarks.json")
    print("="*20 + "\n")
    log.write(msg="Can't find benchmark data",
                   extra_info="Place the benchmark data in ./data/benchmarks.json, an example is included in the repo",
                   level=log.critical)
    cannot_initialise = True

if not os.path.exists(mazemap_polygons_file):
    print("\n" + "="*20)
    print("\tERROR: You don't have any mazemap polygons defined!")
    print("\tPlease place the data in ./data/mazemap_polygons.json")
    print("="*20 + "\n")
    log.write(msg="Can't find any mazemap polygons",
                   extra_info="Place the polygon data in ./data/mazemap_polygons.json",
                   level=log.critical)
    cannot_initialise = True

# Show all error messages before exiting
if cannot_initialise:
    sys.exit(1)

del cannot_initialise