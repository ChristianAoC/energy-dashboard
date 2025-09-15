import os


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