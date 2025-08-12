import json
import pandas as pd
import os


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


###########################################################
###                  Loading variables                  ###
###########################################################

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

metadata_file = os.path.join(DATA_DIR, "input", "SingleSourceOfTruth.xlsx")

meter_health_score_files = os.path.join(DATA_DIR, "cache", "meter_health_score")
if not os.path.exists(meter_health_score_files):
    os.makedirs(meter_health_score_files)
offline_meter_health_score_files = os.path.join(DATA_DIR, "cache", "offline_meter_health_score")
if not os.path.exists(offline_meter_health_score_files):
    os.makedirs(offline_meter_health_score_files)

meter_snapshots_files = os.path.join(DATA_DIR, "cache", "meter_snapshots")
if not os.path.exists(meter_snapshots_files):
    os.makedirs(meter_snapshots_files)
offline_meter_snapshots_files = os.path.join(DATA_DIR, "cache", "offline_meter_snapshots")
if not os.path.exists(offline_meter_snapshots_files):
    os.makedirs(offline_meter_snapshots_files)

benchmark_data_file = os.path.join(DATA_DIR, "benchmarks.json")

offline_meta_file = os.path.join(DATA_DIR, "offline_data.json")
offline_data_files = os.path.join(DATA_DIR, "offline")

mazemap_polygons_file = os.path.join(DATA_DIR, "mazemap_polygons.json")