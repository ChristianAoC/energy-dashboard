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

building_mappings = {
    "building_code": "Property code",
    "building_name": "Building Name",
    "floor_area": "floor_area",
    "year_built": "Year",
    "usage": "Function",
    "maze_map_label": "mazemap_ids"
}
meter_mappings = {
    "meter_id_clean": "meter_id_clean2",
    "raw_uuid": "SEED_uuid",
    "description": "description",
    "building_level_meter": "Building Level Meter",
    "meter_type": "Meter Type",
    "reading_type": "class",
    "units_after_conversion": "units_after_conversion",
    "resolution": "Resolution",
    "unit_conversion_factor": "unit_conversion_factor",
    "tenant": "tenant",
    "building": "Building code"
}