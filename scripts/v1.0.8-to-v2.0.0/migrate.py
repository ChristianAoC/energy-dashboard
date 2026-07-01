# For those who are reviewing this script as advised, I have tried to write it as linearly as possible.
#
# Feel free to email me using the address listed in the README if you want to discuss the script. Alternatively, you can
# open an issue or discussion post on GitHub.
#
# - Luke Needle (v2.0.0 release coordinator)

import getpass
import json
import os
import requests
import secrets
import sqlite3 # NOTE: using sqlite directly to decrease the number of dependencies needed to migrate
import shutil

###########################################################
###                      Variables                      ###
###########################################################

SCRIPT_FOLDER = "scripts/v1.0.8-to-v2.0.0"
LOG_FILE = os.path.join(SCRIPT_FOLDER, "log.json")
SCRIPT_FILE = os.path.join(SCRIPT_FOLDER, "migrate.py")

MIGRATOR_DOMAIN = "migrator"
MIGRATOR_ACCOUNT = f"v2.0.0@{MIGRATOR_DOMAIN}"

METADATA_FILE = os.path.join("data", "input", "SingleSourceOfTruth.xlsx")
ORIGINAL_DB = os.path.join("data", "data.sqlite")
ORIGINAL_DOTENV = ".env"

TEMP_FOLDER = os.path.join(SCRIPT_FOLDER, "temp")
ADDRESS_CACHE_FILE = os.path.join(TEMP_FOLDER, "dashboard-address.txt")
NON_ENV_SETTINGS_FILE = os.path.join(TEMP_FOLDER, "non-env-settings.json")
TEMP_ENV_FILE = os.path.join(TEMP_FOLDER, ".env")
ENV_BAK_FILE = f"{ORIGINAL_DOTENV}.v2-migration.bak"
COOKIE_JAR_FILE = os.path.join(TEMP_FOLDER, "cookie-jar.json")
SMTP_STATE_FILE = os.path.join(TEMP_FOLDER, "smtp-enabled.txt")

log_steps = {
    "settings": False,
    "create-migrator": False,
    "non-env-settings": False,
    "users": False,
    "metadata": False,
    "context": False,
    "cleanup": False
}
EXPECTED_KEYS = log_steps.keys()

# key is old {category}.{key}
OLD_TO_NEW_SETTINGS_MAP = {
    "users.DEFAULT_USER_LEVEL": "default_user_level",
    "users.USER_LEVEL_VIEW_DASHBOARD": "user_level_view_dashboard",
    "users.USER_LEVEL_VIEW_HEALTHCHECK": "user_level_view_healthcheck",
    "users.USER_LEVEL_VIEW_COMMENTS": "user_level_view_comments",
    "users.USER_LEVEL_SUBMIT_COMMENTS": "user_level_submit_comments",
    "users.USER_LEVEL_EDIT_COMMENTS": "user_level_edit_comments",
    "users.USER_LEVEL_ADMIN": "user_level_admin",
    "users.REQUIRED_EMAIL_DOMAINS": "required_email_domains",
    "users.DEMO_EMAIL_DOMAINS": "demo_email_domains",
    "mazemap.MAZEMAP_CAMPUS_ID": "mazemap_campus_id",
    "mazemap.MAZEMAP_LNG": "mazemap_lng",
    "mazemap.MAZEMAP_LAT": "mazemap_lat",
    "smtp.SMTP_ENABLED": "smtp_enabled",
    "smtp.SMTP_ADDRESS": "smtp_address",
    "smtp.SMTP_PASSWORD": "smtp_password",
    "smtp.SMTP_SERVER": "smtp_server",
    "smtp.SMTP_PORT": "smtp_port",
    "site.SITE_NAME": "site_name",
    "site.default_start_page": "default_start_page",
    "site.default_daterange_benchmark": "default_daterange_benchmark",
    "site.default_daterange_browser": "default_daterange_browser",
    "site.default_daterange_health-check": "default_daterange_health-check",
    "site.capavis_url": "capavis_url",
    "site.clustering_url": "clustering_url",
    "influx.InfluxURL": "influx_url",
    "influx.InfluxPort": "influx_port",
    "influx.InfluxUser": "influx_user",
    "influx.InfluxPass": "influx_pass",
    "influx.InfluxTable": "influx_table",
    "influx.data_interval": "influx_data_interval",
    "data.offline_mode": "offline_mode",
    "data.hc_update_time": "hc_update_time",
    "data.cache_time_health_score": "cache_time_health_score",
    "data.cache_time_summary": "cache_time_summary",
    "metadata.offline_data_start_time": "offline_data_start_time",
    "metadata.offline_data_end_time": "offline_data_end_time",
    "metadata.offline_data_interval": "offline_data_interval",
    "metadata.meter_sheet.meter_sheet": "metadata.meter_sheet",
    "metadata.meter_sheet.meter_id": "metadata.meter_sheet.meter_id",
    "metadata.meter_sheet.raw_uuid": "metadata.meter_sheet.raw_uuid",
    "metadata.meter_sheet.description": "metadata.meter_sheet.description",
    "metadata.meter_sheet.building_level_meter": "metadata.meter_sheet.building_level_meter",
    "metadata.meter_sheet.meter_type": "metadata.meter_sheet.meter_type",
    "metadata.meter_sheet.reading_type": "metadata.meter_sheet.reading_type",
    "metadata.meter_sheet.units": "metadata.meter_sheet.units",
    "metadata.meter_sheet.resolution": "metadata.meter_sheet.resolution",
    "metadata.meter_sheet.unit_conversion_factor": "metadata.meter_sheet.unit_conversion_factor",
    "metadata.meter_sheet.tenant": "metadata.meter_sheet.tenant",
    "metadata.meter_sheet.meter_building": "metadata.meter_sheet.meter_building",
    "metadata.building_sheet.building_sheet": "metadata.building_sheet",
    "metadata.building_sheet.building_code": "metadata.building_sheet.building_code",
    "metadata.building_sheet.building_name": "metadata.building_sheet.building_name",
    "metadata.building_sheet.floor_area": "metadata.building_sheet.floor_area",
    "metadata.building_sheet.year_built": "metadata.building_sheet.year_built",
    "metadata.building_sheet.usage": "metadata.building_sheet.usage",
    "metadata.building_sheet.maze_map_label": "metadata.building_sheet.maze_map_label",
    "logging.log_level": "log_level",
    "server.BACKGROUND_TASK_TIMING": "background_task_timing",
    "server.meter_batch_size": "meter_batch_size",
    "server.session_timeout": "session_timeout",
    "server.login_code_timeout": "login_code_timeout",
    "server.log_info_expiry": "log_info_expiry",
    "server.log_warning_expiry": "log_warning_expiry",
    "server.log_error_expiry": "log_error_expiry",
    "server.log_critical_expiry": "log_critical_expiry"
}

# Key is the setting's key
# For settings that can't be mapped to a .env entry, value is None
SETTINGS_TO_ENV_MAP = {
    "default_user_level": "DEFAULT_USER_LEVEL",
    "user_level_view_dashboard": "USER_LEVEL_VIEW_DASHBOARD",
    "user_level_view_healthcheck": "USER_LEVEL_VIEW_HEALTHCHECK",
    "user_level_view_comments": "USER_LEVEL_VIEW_COMMENTS",
    "user_level_submit_comments": "USER_LEVEL_SUBMIT_COMMENTS",
    "user_level_edit_comments": "USER_LEVEL_EDIT_COMMENTS",
    "user_level_admin": "USER_LEVEL_ADMIN",
    "required_email_domains": "REQUIRED_EMAIL_DOMAINS",
    "demo_email_domains": "DEMO_EMAIL_DOMAINS",
    "mazemap_campus_id": "MAZEMAP_CAMPUS_ID",
    "mazemap_lng": "MAZEMAP_LNG",
    "mazemap_lat": "MAZEMAP_LAT",
    "smtp_enabled": "SMTP_ENABLED",
    "smtp_address": "SMTP_ADDRESS",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_server": "SMTP_SERVER",
    "smtp_port": "SMTP_PORT",
    "site_name": "SITE_NAME",
    "default_start_page": None,
    "default_daterange_benchmark": None,
    "default_daterange_browser": None,
    "default_daterange_health-check": None,
    "capavis_url": None,
    "clustering_url": None,
    "influx_url": "INFLUX_URL",
    "influx_port": "INFLUX_PORT",
    "influx_user": "INFLUX_USER",
    "influx_pass": "INFLUX_PASS",
    "influx_table": "INFLUX_TABLE",
    "influx_data_interval": "INFLUX_DATA_INTERVAL",
    "offline_mode": "OFFLINE_MODE",
    "hc_update_time": "HEALTH_CHECK_UPDATE_TIME",
    "cache_time_health_score": "HEALTH_SCORE_CACHE_TIME",
    "cache_time_summary": "SUMMARY_CACHE_TIME",
    "offline_data_start_time": None,
    "offline_data_end_time": None,
    "offline_data_interval": None,
    "metadata.meter_sheet": None,
    "metadata.meter_sheet.meter_id": None,
    "metadata.meter_sheet.raw_uuid": None,
    "metadata.meter_sheet.description": None,
    "metadata.meter_sheet.building_level_meter": None,
    "metadata.meter_sheet.meter_type": None,
    "metadata.meter_sheet.reading_type": None,
    "metadata.meter_sheet.units": None,
    "metadata.meter_sheet.resolution": None,
    "metadata.meter_sheet.unit_conversion_factor": None,
    "metadata.meter_sheet.tenant": None,
    "metadata.meter_sheet.meter_building": None,
    "metadata.building_sheet": None,
    "metadata.building_sheet.building_code": None,
    "metadata.building_sheet.building_name": None,
    "metadata.building_sheet.floor_area": None,
    "metadata.building_sheet.year_built": None,
    "metadata.building_sheet.usage": None,
    "metadata.building_sheet.maze_map_label": None,
    "log_level": "LOG_LEVEL",
    "background_task_timing": "BACKGROUND_TASK_TIMING",
    "meter_batch_size": "METER_BATCH_SIZE",
    "session_timeout": None,
    "login_code_timeout": None,
    "log_info_expiry": None,
    "log_warning_expiry": None,
    "log_error_expiry": None,
    "log_critical_expiry": None
}

###########################################################
###                  Helper Functions                   ###
###########################################################

def complete_section(log_steps: dict, key: str) -> None:
    global LOG_FILE
    
    log_steps[key] = True
    
    with open(LOG_FILE, "w") as f:
        json.dump(log_steps, f)

def skip_section(log_steps: dict, key: str) -> None:
    # Skipping is only for when a section is a dependency
    # E.g: non-env-settings is marked as completed instead of skipped if there are no 
    global LOG_FILE
    
    log_steps[key] = None
    
    with open(LOG_FILE, "w") as f:
        json.dump(log_steps, f)

def check_server_up(server_address: str) -> bool:
    try:
        return requests.get(f"{server_address}/api").status_code == 200
    except:
        return False

def parse_json(var: str, expected_type: str) -> None|str|int|float|bool:
    value = json.loads("{\"value\": " + var + "}")["value"]
    actual_type = type(value).__name__
    
    if actual_type == expected_type:
        return value
    elif actual_type == "NoneType":
        return None
    
    try:
        if expected_type == "str":
            return str(value)
        elif expected_type == "int":
            return int(value)
        elif expected_type == "float":
            return float(value)
        elif expected_type == "bool":
            return value == "true"
    except:
        pass
    
    print(f"Unable to decode value: received '{var}', decoded '{value}', type '{actual_type}', expected '{expected_type}'")
    exit()

###########################################################
###                   Initialisation                    ###
###########################################################

# Make sure that the user is running the script from the correct directory
if not os.path.exists(SCRIPT_FILE):
    print("You must run this script from the project root, if you didn't clone the repo, create a folder called")
    print("`scripts` alongside your `data` folder and put this script in a folder called \'v1.0.8-to-v2.0.0\'")
    print("(the same file structure as the repo has).\n")
    print("Example folder structure:")
    print(".")
    print("|- data")
    print("|  |- data.sqlite")
    print("|- scripts")
    print("|  |- v1.0.8-to-v2.0.0")
    print("|     |- migrate.py")
    print("|- docker-compose.yml")
    exit()

if not os.path.exists(ORIGINAL_DB):
    print(f"ERROR: Cannot find original database ({ORIGINAL_DB}) - Aborting migration.")
    exit()

# Make sure that we can connect to the original database
try:
    with sqlite3.connect(ORIGINAL_DB) as conn:
        _ = conn.cursor()
except:
    print("ERROR: Cannot open a connection to the original database")

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# Recover progress from log file
if os.path.exists(LOG_FILE):
    print("=> Recovering existing migration progress. Skipping previously completed steps.")
    input("Press Enter to continue.")
    
    print() # Break up output to make it more readable
    
    # Load migration log
    try:
        with open(LOG_FILE, "r") as f:
            log_steps = json.load(f)
    except:
        print("\nAborting loading migration state: Log file couldn't be parsed to JSON")
        exit()
    
    # Check that the required keys are present
    invalid_log = False
    for setting_key in EXPECTED_KEYS:
        if setting_key not in log_steps:
            print(f"\nLog missing key '{setting_key}'")
            invalid_log = True
    if invalid_log:
        print("Aborting loading migration state: Missing keys")
        exit()
    
    # Tell the user which steps will be skipped
    print("Steps to skip:")
    
    number_skipped = 0
    for setting_key in EXPECTED_KEYS:
        if log_steps[setting_key] == True:
            print(f"- {setting_key}")
            number_skipped += 1
    
    if number_skipped == 0:
        print("== Nothing to skip ==")
    
    input("Press Enter to continue.")
else:
    with open(LOG_FILE, "w") as f:
        json.dump(log_steps, f)

print(f"""
========================================================================================================================

This script is for migrating from energy-dashboard v1.0.8 to v2.0.0, you MUST update to v1.0.8 prior to running this
script if you aren't already running it.

If you manually compile from main, and have manually migrated past 5234e1d190e2224575fbb56d2f827ddbfee49bb7 then you
*cannot* use this script. You should consult CHANGELOG.md and either manually migrate back to v1.0.8 before running this
script, or manually migrate to v2.0.0.

=> You are advised to make a backup of your data.sqlite file before attempting migration.
=> You are also advised to review this script before executing it to understand what it does. A summary is provided
   below.

This script is designed to work with an empty PostgreSQL database, if you have already partially migrated *DO NOT* use
this script. If you have started the server before running this script you need to either delete the PostgreSQL database
so that settings can be migrated, or set "settings" to `true` in {LOG_FILE}

This script:
1. Reads your app settings and creates a new .env for you to review. You can either accept it and have the script
   automatically replace it, or you can manually update your file from the suggestion provided.

2. Migrates all user accounts.
   NOTE: Internal database user IDs may change in this transition.

3. Migrates settings that aren't loaded from the .env file.

4. Re-uploads or retriggers metadata processing.
   NOTE: This may add more buildings as occupancy_type length was increased to fit all supported types.

5. Recreates context, matching up authors where possible.
   NOTE: The script tries to match old user ids with their new ones.

6. Optionally cleans up after itself

Data that cannot be migrated:
- App logs
- Current login codes
- Active user sessions
- Caches (Health check & Summary)
- Last login dates
- Login count

========================================================================================================================
""")

input("Press Enter to continue, or press CTRL+C to cancel.")

print("\n") # Break up output

###########################################################
###                    Pre-Migration                    ###
###########################################################

# Allow the user to use the previously entered address if it exists
saved_address = None
if os.path.exists(ADDRESS_CACHE_FILE):
    with open(ADDRESS_CACHE_FILE, "r") as f:
        saved_address = f.readline().strip()
    
    if saved_address == "":
        saved_address = None

print("Please provide the address of your dashboard (e.g. https://net0i.example.com, or https://net0i.example.com:1234)")

if saved_address is not None:
    print(f"Previously entered address: {saved_address}")
    print("Press Enter to use the previous address")

server_address = input("Address: ")

if server_address == "":
    if saved_address is None:
        exit()
    else:
        server_address = saved_address

# Standardise address with no trailing / (as shown in the examples)
if server_address[-1] == "/":
    server_address = server_address[:-1]

# Save address in cache if updated
if server_address != saved_address:
    with open(ADDRESS_CACHE_FILE, "w") as f:
        f.write(server_address)

is_server_online = check_server_up(server_address)

if is_server_online and not log_steps["settings"]:
    print("The dashboard that you provided is currently online, please turn it off.")
    print("If the dashboard has already been updated then you need to clear the PostgreSQL database before continuing.")
    exit()
if not is_server_online and log_steps["settings"]:
    print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
    exit()

print() # Break up output to make it more readable

###########################################################
###               Migrating App Settings                ###
###########################################################
# NOTE: This section checks to make sure that you haven't already migrated away from categories.
#       If you have, you need to modify the settings map at the top of this file and remove this check.

if not log_steps["settings"]:
    print("=> Migrating Settings")
    print("This step loads your previous settings and generates a new .env file for you to use. You can optionally")
    print("skip this step and do it manually (or rely on the default values).")

    skip_settings = None
    while skip_settings is None:
        skip_settings_input = input("Would you like to skip this step? (y/N)")
        
        if skip_settings_input.lower() in ["", "n"]:
            skip_settings = False
        elif skip_settings_input.lower() == "y":
            skip_settings = True
    
    if skip_settings:
        complete_section(log_steps=log_steps, key="settings") # Not skipping as user will be doing the migration
        print(f"As you are manually skipping you must add '{MIGRATOR_DOMAIN}' to DEMO_EMAIL_DOMAINS in your .env file for this")
        print("script to work. You will also need to add your Postgres settings.")
        print("When you have finished, start the dashboard (Most likely `sudo docker compose up -d`) and once it is")
        print("online, restart this script.")
        input("Press Enter to exit.")
        exit()
    
    try:
        with sqlite3.connect(ORIGINAL_DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT category FROM settings")
    except sqlite3.OperationalError as e:
        if str(e) != "no such column: category":
            print("An error occured while trying to open the original database.")
            # Different problem
            raise e
        else:
            print("The original database's settings table doesn't seem to have a category column.")
            print("If you have checked and the category column is present then remove this check from the script.")
            input("Press Enter to exit.")
            exit()

    print("\n=> Original settings table is compatible")

    print("Please provide the credentials/settings for Postgres below (hint: press enter to use the example value if one is given):")
    postgres_address = input("POSTGRES_ADDRESS (db): ").strip()
    if postgres_address == "":
        postgres_address = "db"
    
    while True:
        postgres_port = input("POSTGRES_PORT (5432): ").strip()
        if postgres_port == "":
            postgres_port = 5432
            break
        
        try:
            postgres_port = int(postgres_port)
            if postgres_port < 1:
                print("Please provide a valid port number")
            else:
                break
        except:
            print("Please provide a valid port number")
    
    postgres_user = input("POSTGRES_USER (net0i): ").strip()
    if postgres_user == "":
        postgres_user = "net0i"
    
    while True:
        postgres_pass = getpass.getpass("POSTGRES_PASS: ", echo_char="*").strip()
        if postgres_pass.strip() == "":
            print("Please provide a password")
        else:
            break
    
    postgres_table = input("POSTGRES_TABLE (net0i): ").strip()
    if postgres_table == "":
        postgres_table = "net0i"
    
    print() # Break up output to make it more readable
    
    # Load settings from original DB
    with sqlite3.connect(ORIGINAL_DB) as conn:
        cur = conn.cursor()
        old_settings_raw = cur.execute("SELECT * FROM settings;").fetchall()
        if len(old_settings_raw) == 0:
            print("ERROR: No settings found in old DB.")
            exit()
    
    new_settings = {}
    
    for setting in old_settings_raw:
        old_key = f"{setting[1]}.{setting[0]}"
        try:
            new_key = OLD_TO_NEW_SETTINGS_MAP[old_key]
        except:
            print(f"Key '{old_key}' could not be mapped, this will be skipped.")
            continue
        
        # Parse the value from the old database with the correct type
        if setting[3] in ["str", "int", "float", "bool"]:
            typed_setting = parse_json(setting[2], setting[3])
        elif setting[3] in ["dict", "list"]:
            print(f"Key '{old_key}' has type '{setting[3]}', which has been removed, this will be skipped.")
            continue
        else:
            print(f"Key '{old_key}' has type '{setting[3]}', which can't be translated, this will be skipped.")
            continue
        
        new_settings[new_key] = {
            "value": typed_setting,
            "type": setting[3]
        }

    # Add MIGRATOR_DOMAIN domain as a demo one
    print(f"=> Adding '{MIGRATOR_DOMAIN}' domain to DEMO_EMAIL_DOMAINS")
    print("   NOTE: This is required for the remaining steps.\n")
    existing_demo_domains = new_settings.get("demo_email_domains")
    if existing_demo_domains is None or existing_demo_domains["value"] is None:
        new_demo_domains = MIGRATOR_DOMAIN
    else:
        new_demo_domains = f"{new_settings['demo_email_domains']['value']},{MIGRATOR_DOMAIN}"
    new_settings["demo_email_domains"]["value"] = new_demo_domains
    
    # Map settings to their .env equivalents
    # If a setting can't be mapped, it will be processed later. To do this, they will be saved in a temp .json file
    # The layout is:
    # {
    #     key: {
    #         "value": value,
    #         "type": type
    #     }
    # }
    settings_for_later = {}
    env_file_contents = ""
    for setting_key in new_settings.keys():
        env_key = SETTINGS_TO_ENV_MAP[setting_key]
        if env_key is None:
            settings_for_later[setting_key] = new_settings[setting_key]
            continue
        
        if new_settings[setting_key]["type"] == "str":
            env_file_contents += f"{env_key}='{new_settings[setting_key]['value']}'\n"
        else:
            env_file_contents += f"{env_key}={new_settings[setting_key]['value']}\n"
    
    if len(settings_for_later.keys()) == 0:
        print("=> No settings to migrate later, skipping 'non-env-settings' step")
        complete_section(log_steps=log_steps, key="non-env-settings") # complete instead of skip as nothing to do
    else:
        with open(NON_ENV_SETTINGS_FILE, "w") as f:
            json.dump(settings_for_later, f)
        print("=> Saved non-.env settings")
    
    # Load Flask secret from original .env file
    flask_secret = None
    with open(ORIGINAL_DOTENV, "r") as f:
        for line in f.readlines():
            if line.find("SECRET_KEY") == -1:
                continue
            flask_secret = line.strip().split("=")[1]
            break
    
    if flask_secret is None:
        print("=> Could not extract Flask secret from .env")
        print("Please enter the secret below (or choose a new one). Press Enter to generate a random 40 character secret")
        flask_secret = input("Key: ").strip()
        if flask_secret == "":
            flask_secret = secrets.token_urlsafe(40)
    
    env_file_contents += f"SECRET_KEY={flask_secret}"
    
    with open(TEMP_ENV_FILE, "w") as f:
        f.write(env_file_contents)

    complete_section(log_steps=log_steps, key="settings")

    print("=> Ready for review of .env file")
    input("When you press enter, the current .env file will be displayed")
    print("="*120)
    with open(ORIGINAL_DOTENV, "r") as f:
        print(f.read())
    print("="*120)
    
    input("When you press enter, the generated .env file will be displayed")
    print("="*120)
    print(env_file_contents)
    print("="*120)
    
    # Create a backup of the original .env file
    with open(ORIGINAL_DOTENV, "r") as f_original:
        with open(ENV_BAK_FILE, "w") as f_backup:
            f_backup.write(f_original.read())
    
    overwrite_env_file = input("Do you want this file to replace the current .env? A backup has been created. (Y/n) ")
    if overwrite_env_file.lower() in ["", "y"]:
        with open(TEMP_ENV_FILE, "r") as f_new:
            with open(ORIGINAL_DOTENV, "w") as f_original:
                f_original.write(f_new.read())
        
        print() # Break up output to make it more readable
    else:
        print(f"You will need to manually migrate your .env file, the generated one is saved in: {TEMP_ENV_FILE}")
        print("Once you do that then you can do the following steps:\n")
    
    print("You must now start the dashboard. (Most likely `sudo docker compose up -d`)")
    print("Once it is online, restart this script")
    exit()
else:
    print("=> Skipping Settings")

###########################################################
###              Creating Migrator Account              ###
###########################################################

if log_steps["create-migrator"] == False:
    print(f"=> Creating user account {MIGRATOR_ACCOUNT}")
    code_res = requests.post(f"{server_address}/api/user/login?email={MIGRATOR_ACCOUNT}")
    code = code_res.content.decode().split("code=")[1].split("\'")[0]
    activate_res = requests.get(
        f"{server_address}/api/user/verify?email={MIGRATOR_ACCOUNT}&code={code}",
        cookies=code_res.cookies,
        allow_redirects=False,
    )

    cookie_jar = activate_res.cookies

    # Save cookie jar for later
    with open(COOKIE_JAR_FILE, "w") as f:
        json.dump(requests.utils.dict_from_cookiejar(cookie_jar), f)

    level_check_res = requests.get(f"{server_address}/api/settings", cookies=cookie_jar)
    if level_check_res.status_code != 200:
        print(f"Migrator account {MIGRATOR_ACCOUNT} doesn't have a sufficient permissions. If you have already logged")
        print("in since starting the migration, that account will be an admin. Log into that account and give the")
        print("migrator account the highest level shown in the dashboard.\n")
        print("Once you do that, restart this script.")
        input("Press Enter to exit.")
        exit()

    print("=> Checking whether SMTP is enabled")
    res = requests.get(f"{server_address}/api/settings/?key=smtp_enabled", cookies=cookie_jar)
    current_smtp_state = res.content.decode().strip()

    with open(SMTP_STATE_FILE, "w") as f:
        f.write(current_smtp_state)

    if current_smtp_state == "true":
        print("=> Disabling SMTP")
        res = requests.post(
            f"{server_address}/api/settings/",
            headers={"Content-type": "application/json"},
            cookies=cookie_jar,
            json={"smtp_enabled": {"value": False, "type": "bool"}},
        )
        if res.status_code != 200:
            print("ERROR: Failed to disable SMTP")
            exit()
    else:
        print("=> SMTP already disabled, will remember this setting")

    complete_section(log_steps=log_steps, key="create-migrator")
else:
    print("=> Skipping Creating Migrator Account")

###########################################################
###             Migrating Non .env Settings             ###
###########################################################

if not log_steps["non-env-settings"]:
    if not check_server_up(server_address):
        print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
        exit()

    with open(NON_ENV_SETTINGS_FILE, "r") as f:
        non_env_settings = json.load(f)

    with open(COOKIE_JAR_FILE, "r") as f:
        cookie_jar = json.load(f)

    print("=> Setting non-.env settings")

    res = requests.post(
        f"{server_address}/api/settings/",
        headers={"Content-type": "application/json"},
        cookies=cookie_jar,
        json=non_env_settings,
    )
    if res.status_code != 200:
        print("ERROR: Failed to create non-.env settings")
        print(f"Message: {res.content.decode()}")
        print(f"Try modifying the non-.env settings file at {NON_ENV_SETTINGS_FILE}")
        exit()

    complete_section(log_steps=log_steps, key="non-env-settings")
else:
    print("=> Skipping Non .env Settings")

###########################################################
###                   Migrating Users                   ###
###########################################################

# Checking if it is False as this section can be None
if log_steps["users"] == False:
    if not check_server_up(server_address):
        print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
        exit()

    print("\nWould you like to skip User Account migration?")
    print("NOTE: This will also skip Context migration")
    skip_users = None
    while skip_users is None:
        skip_users_input = input("Would you like to skip this step? (y/N)")

        if skip_users_input.lower() in ["", "n"]:
            skip_users = False
        elif skip_users_input.lower() == "y":
            skip_users = True

    if skip_users:
        skip_section(log_steps=log_steps, key="settings")
    else:
        with open(COOKIE_JAR_FILE, "r") as f:
            cookie_jar = json.load(f)

        with sqlite3.connect(ORIGINAL_DB) as conn:
            cur = conn.cursor()
            old_users_raw = cur.execute("SELECT rowid, email, level FROM user;").fetchall()

        old_users_map = {}

        # For summary later
        emails_level_failed = []
        domains_added = []
        emails_skipped = []

        for old_user_raw in old_users_raw:
            old_users_map[old_user_raw[0]] = {
                "email": old_user_raw[1],
                "level": old_user_raw[2],
                "skipped": False
            }

        # Create user accounts
        for user_id in old_users_map.keys():
            res_add_user = requests.post(f"{server_address}/api/user/login?email={old_users_map[user_id]['email']}")
            if res_add_user.status_code == 200:
                print(f"=> Added user: {old_users_map[user_id]['email']}")
                continue

            print() # Break up output to make it more readable

            cur_user_domain = old_users_map[user_id]['email'].split("@")[1]

            print(f"=> Failed to add user '{old_users_map[user_id]['email']}'")
            print(f"Error message: {res_add_user.content.decode()}")
            print(f"You can either skip this user, or allow their domain ({cur_user_domain})")
            add_user_domain = None
            while add_user_domain is None:
                add_user_domain_input = input("Would you like to add this domain? (y/N)")

                if add_user_domain_input.lower() in ["", "n"]:
                    add_user_domain = False
                elif add_user_domain_input.lower() == "y":
                    add_user_domain = True

            if not add_user_domain:
                print(f"=> Skipped user: {old_users_map[user_id]['email']}")
                old_users_map[user_id]['skipped'] = True
                emails_skipped.append(old_users_map[user_id]['email'])
                continue

            # Get current list of domains
            res_get_domains = requests.get(f"{server_address}/api/settings/?key=required_email_domains", cookies=cookie_jar)
            current_domains = parse_json(res_get_domains.content.decode().strip(), "str")

            res_update_domains = requests.post(
                f"{server_address}/api/settings/",
                headers={"Content-type": "application/json"},
                cookies=cookie_jar,
                json={
                    "required_email_domains": {
                        "value": f"{current_domains},{cur_user_domain}",
                        "type": "str",
                    }
                },
            )
            if res_update_domains.status_code != 200:
                print("ERROR: Failed to update domain list, skipping user")
                old_users_map[user_id]['skipped'] = True
                emails_skipped.append(old_users_map[user_id]['email'])
                continue

            # Try again to create user account
            res = requests.post(f"{server_address}/api/user/login?email={old_users_map[user_id]['email']}")
            if res.status_code != 200:
                print("=> Failed to create user, skipping")
                old_users_map[user_id]['skipped'] = True
                emails_skipped.append(old_users_map[user_id]['email'])
            else:
                print(f"=> Added user: {old_users_map[user_id]['email']}")

        print("\n=> Setting user levels")

        # Set user level
        for user_id in old_users_map.keys():
            if old_users_map[user_id]['skipped']:
                continue

            res = requests.post(
                f"{server_address}/api/user/set-level",
                headers={"Content-type": "application/json"},
                cookies=cookie_jar,
                json={
                    "email": old_users_map[user_id]["email"],
                    "level": old_users_map[user_id]["level"],
                },
            )
            if res.status_code == 200:
                print(f"=> Set {old_users_map[user_id]['email']} to level {old_users_map[user_id]['level']}")
            else:
                print(f"=> Failed to set level of {old_users_map[user_id]['level']} for {old_users_map[user_id]['email']}")
                emails_level_failed.append(old_users_map[user_id]["email"])

        print("\n=> Creating map between user emails and old user IDs")

        # Display summary of users migrated
        print("User migration summary:")
        print(f"    Accounts successfully migrated: {len(old_users_map) - len(emails_skipped) - len(emails_level_failed)}")
        print(f"    Accounts with potentially incorrect level: {len(emails_level_failed)}")
        for email_level_failed in emails_level_failed:
            print(f"\t- {email_level_failed}")
        print(f"    Accounts skipped: {len(emails_skipped)}")
        for email_skipped in emails_skipped:
            print(f"\t- {email_skipped}")
        print(f"    Domains added: {len(domains_added)}")
        for domain in domains_added:
            print(f"\t- {domain}")

        complete_section(log_steps=log_steps, key="users")

        input("Press Enter to continue, or press CTRL+C to cancel.")

        print() # Break up output to make it more readable
else:
    print("=> Skipping Users")

###########################################################
###                 Migrating Metadata                  ###
###########################################################

if not log_steps["metadata"]:
    if not check_server_up(server_address):
        print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
        exit()

    with open(COOKIE_JAR_FILE, "r") as f:
        cookie_jar = json.load(f)

    print("=> Attempting to locate existing metadata file")

    # Try and use existing metadata file to save bandwidth
    if os.path.exists(METADATA_FILE):
        print("=> Existing metadata file exists, attempting to load from it")
        res = requests.get(f"{server_address}/api/populate-database", cookies=cookie_jar)
        if res.status_code != 200:
            print("=> Failed to load from existing metadata file")
            print(f"Error message: {res.content.decode().strip()}\n")
        else:
            print("=> Successfully processed existing metadata file")
            complete_section(log_steps=log_steps, key="metadata")
    else:
        print("=> Existing metadata file doesn't exist, switching to manual migration...")

    # Runs if an error occured, or if METADATA_FILE doesn't exist
    if not log_steps["metadata"]:
        print("Enter the path (relative or absolute) to the metadata file on the server. Alternatively, press Enter to")
        print("upload the file via the dashboard.")
        metadata_file_path = input("Path to metadata file: ").strip()

        if metadata_file_path != "" and os.path.exists(metadata_file_path):
            with open(metadata_file_path, "rb") as f:
                res = requests.post(
                    f"{server_address}/api/settings/upload/metadata",
                    cookies=cookie_jar,
                    files={
                        "file": (
                            os.path.basename(metadata_file_path),
                            f,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    },
                )
            if res.status_code != 200:
                print("=> Failed to load metadata file, switching to dashboard upload...")
                print(f"Error message: {res.content.decode().strip()}\n")
            else:
                print("=> Successfully processed metadata file")
                complete_section(log_steps=log_steps, key="metadata")

        # Runs if user entered "", if their location doesn't exist, or if it did exist but couldn't be processed
        if not log_steps["metadata"]:
            print("Log into the dashboard and upload your metadata file.")
            print(f"Hint: Go to {server_address}/settings and switch to the 'Upload Files' tab")
            input("Press Enter once you have uploaded it, or press CTRL+C to cancel.")

            if not os.path.exists(METADATA_FILE):
                print("ERROR: Can't find metadata file on the server.")
                print("If you believe this is a mistake and can see your meters & buildings in the dashboard, set the")
                print(f"'metadata' step to `true` in {LOG_FILE}")
                input("\nPress Enter to exit.")
                exit()

            complete_section(log_steps=log_steps, key="metadata")
else:
    print("=> Skipping Metadata")

###########################################################
###                  Migrating Context                  ###
###########################################################

# Checking if it is False as this section can be None
if log_steps["context"] == False:
    # TODO: Remove \/
    print("Context migration hasn't been implemented yet as changes are required to the context endpoints")
    print(f"To complete migration without the context step, set 'context' to `null` in {LOG_FILE} and try again.")
    exit()
    # TODO: Remove /\
    
    if log_steps["users"] is None:
        print("=> Skipping Context as User migration was skipped")
        skip_section(log_steps=log_steps, key="context")
    else:
        if not check_server_up(server_address):
            print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
            exit()
        
        with open(COOKIE_JAR_FILE, "r") as f:
            cookie_jar = json.load(f)
        
        # TODO: Get context from old DB
        with sqlite3.connect(ORIGINAL_DB) as conn:
            cur = conn.cursor()
            old_context_raw = cur.execute("SELECT author, target_type, start_timestamp, end_timestamp, context_type, comment FROM context WHERE deleted = 0;").fetchall()
            print(old_context_raw)
        
        # TODO: For each context, recreate it
        
        # TODO: Provide a summary of any that failed to the user
        
        exit() # TODO: Remove
        
        complete_section(log_steps=log_steps, key="context")
else:
    print("=> Skipping Context")

###########################################################
###                       Cleanup                       ###
###########################################################

# Checking if it is False as this section can be None
if log_steps["cleanup"] == False:
    print() # Break up output to make it more readable
    
    skip_cleanup = None
    while skip_cleanup is None:
        skip_cleanup_input = input("Would you like to skip migration clean up? (y/N)")

        if skip_cleanup_input.lower() in ["", "n"]:
            skip_cleanup = False
        elif skip_cleanup_input.lower() == "y":
            skip_cleanup = True
    
    if skip_cleanup:
        skip_section(log_steps=log_steps, key="cleanup")
    else:
        if not check_server_up(server_address):
            print("The dashboard that you provided is currently offline, please turn it on to continue migrating.")
            exit()
        
        with open(COOKIE_JAR_FILE, "r") as f:
            cookie_jar = json.load(f)

        # TODO: Revoke all sessions for demo user
        print("NOTE: The migration script currently cannot revoke existing sessions")
        
        print(f"=> Removing '{MIGRATOR_DOMAIN}' from demo_email_domains")
        
        # Get current list of demo domains
        res_get_domains = requests.get(f"{server_address}/api/settings/?key=demo_email_domains", cookies=cookie_jar)
        current_domains_raw = str(parse_json(res_get_domains.content.decode().strip(), "str"))
        
        # Skip step if there are no domains to search through
        if current_domains_raw.strip() not in ["None", ""]:
            # Remove MIGRATOR_DOMAIN from domain list
            current_demo_domains = [x.strip() for x in current_domains_raw.split(",")]
            current_demo_domains.remove(MIGRATOR_DOMAIN)
            new_demo_domains_raw = ",".join(current_demo_domains)

            res_update_domains = requests.post(
                f"{server_address}/api/settings/",
                headers={"Content-type": "application/json"},
                cookies=cookie_jar,
                json={
                    "demo_email_domains": {
                        "value": new_demo_domains_raw,
                        "type": "str"
                    }
                },
            )
            if res_update_domains.status_code != 200:
                print("ERROR: Failed to update demo domain list, please edit this manually")

        print("=> Resetting smtp_enabled setting")
        with open(SMTP_STATE_FILE, "r") as f:
            original_smtp_state = f.read().strip() == "true"
        
        res_reset_smtp = requests.post(
            f"{server_address}/api/settings/",
            headers={"Content-type": "application/json"},
            cookies=cookie_jar,
            json={
                "smtp_enabled": {
                    "value": original_smtp_state,
                    "type": "bool"
                }
            },
        )
        if res_reset_smtp.status_code != 200:
            print(f"ERROR: Failed to reset smtp_enabled to {original_smtp_state}, please edit this manually")
        
        print("=> Removing temp files")
        shutil.rmtree(TEMP_FOLDER)
        
        print(f"""
You must manually delete the user '{MIGRATOR_ACCOUNT}'. NOTE: No one can log into the account")
You should also modify your .env file to remove {MIGRATOR_DOMAIN}
""")
        input("Press Enter to continue.")
        
        complete_section(log_steps=log_steps, key="cleanup")
else:
    print("=> Skipping Cleanup")

###########################################################
###                   Post Migration                    ###
###########################################################

print(f"""
You have completed v2.0.0 migration!
Please remember to remove \'{MIGRATOR_ACCOUNT}\' from DEMO_EMAIL_DOMAINS in your .env file if you haven't already.
"The cleanup step removed it from the dashboard settings so you don't need to do that unless you skipped it.
""")
