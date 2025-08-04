from dotenv import load_dotenv
import os
import sys


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

meters_file = os.path.join(DATA_DIR, "input", 'meters_all.json')
buildings_file = os.path.join(DATA_DIR, "input", 'UniHierarchy.json')
buildings_usage_file = os.path.join(DATA_DIR, "input", 'UniHierarchyWithUsage.json')

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

meters_anon_file = os.path.join(DATA_DIR, "input", 'anon_meters.json')
buildings_anon_file = os.path.join(DATA_DIR, "input", 'anon_buildings.json')
usage_anon_file = os.path.join(DATA_DIR, "input", 'anon_usage.json')

mazemap_polygons_file = os.path.join(DATA_DIR, "mazemap_polygons.json")

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
    cannot_initialise = True

if offlineMode and not os.path.exists(offline_meta_file):
    print("\n" + "="*20)
    print("\tERROR: You are runnning in offline mode with offline data but no offline metadata!")
    print("\tPlease place your metadata in ./data/meta/offline_data.json")
    print("="*20 + "\n")
    cannot_initialise = True

if not os.path.exists(benchmark_data_file):
    print("\n" + "="*20)
    print("\tERROR: You have removed the included benchmark data!")
    print("\tPlease place the benchmark data in ./data/meta/offline_data.json")
    print("="*20 + "\n")
    cannot_initialise = True

if not os.path.exists(mazemap_polygons_file):
    print("\n" + "="*20)
    print("\tERROR: You don't have any mazemap polygons defined!")
    print("\tPlease place the data in ./data/mazemap_polygons.json")
    print("="*20 + "\n")
    cannot_initialise = True

# Show all error messages before exiting
if cannot_initialise:
    sys.exit(1)

del cannot_initialise