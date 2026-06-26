print("Running init")
import copy
from dotenv import load_dotenv
from flask import Flask
import json
import os
import socket
import time

from constants import offline_meta_file
import database
import log
import models
import settings


def load_settings_from_env(from_env: bool = True) -> dict[str,str|bool|None|int|float]:
    result = copy.deepcopy(settings.default_settings)
    
    if from_env:
        load_dotenv()
        val = os.getenv("OFFLINE_MODE", "True")
        offline_mode = val.strip().lower() in ("1", "true", "yes", "on")

        influx_url = os.getenv("INFLUX_URL")
        influx_port = os.getenv("INFLUX_PORT")
        influx_user = os.getenv("INFLUX_USER")
        influx_pass = os.getenv("INFLUX_PASS")
        influx_table = os.getenv("INFLUX_TABLE")

        if influx_url is None or influx_port is None or influx_user is None or influx_pass is None or influx_table is None:
            offline_mode = True
        
        result["offline_mode"] = offline_mode
        result["influx_url"] = influx_url
        result["influx_port"] = influx_port
        result["influx_user"] = influx_user
        result["influx_pass"] = influx_pass
        result["influx_table"] = influx_table
        result["influx_data_interval"] = int(os.getenv("INFLUX_DATA_INTERVAL", settings.default_settings["influx_data_interval"]))
        
        result["hc_update_time"] = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", settings.default_settings["hc_update_time"]))
        result["cache_time_health_score"] = int(os.getenv("HEALTH_SCORE_CACHE_TIME",
                                                          settings.default_settings["cache_time_health_score"]))
        result["cache_time_summary"] = int(os.getenv("SUMMARY_CACHE_TIME", settings.default_settings["cache_time_summary"]))
        
        result["log_level"] = os.getenv("LOG_LEVEL", settings.default_settings["log_level"])
        
        result["site_name"] = os.getenv("SITE_NAME", settings.default_settings["site_name"])
        
        result["mazemap_campus_id"] = int(os.getenv("MAZEMAP_CAMPUS_ID", settings.default_settings["mazemap_campus_id"]))
        result["mazemap_lng"] = os.getenv("MAZEMAP_LNG", settings.default_settings["mazemap_lng"])
        result["mazemap_lat"] = os.getenv("MAZEMAP_LAT", settings.default_settings["mazemap_lat"])
        
        smtp_address = os.getenv("SMTP_ADDRESS")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        
        val = os.getenv("SMTP_ENABLED", "False")
        smtp_enabled = val.strip().lower() in ("1", "true", "yes", "on")
        
        if smtp_address is None or smtp_password is None or smtp_server is None or smtp_port is None:
            smtp_enabled = False
        result["smtp_enabled"] = smtp_enabled
        result["smtp_address"] = smtp_address
        result["smtp_password"] = smtp_password
        result["smtp_server"] = smtp_server
        result["smtp_port"] = smtp_port
        
        result["required_email_domains"] = os.getenv("REQUIRED_EMAIL_DOMAINS", "")
        result["demo_email_domains"] = os.getenv("DEMO_EMAIL_DOMAINS", "")
        
        result["default_user_level"] = int(os.getenv("DEFAULT_USER_LEVEL",
                                                     settings.default_settings["default_user_level"]))
        result["user_level_view_dashboard"] = int(os.getenv("USER_LEVEL_VIEW_DASHBOARD",
                                                            settings.default_settings["user_level_view_dashboard"]))
        result["user_level_view_healthcheck"] = int(os.getenv("USER_LEVEL_VIEW_HEALTHCHECK",
                                                              settings.default_settings["user_level_view_healthcheck"]))
        result["user_level_view_comments"] = int(os.getenv("USER_LEVEL_VIEW_COMMENTS",
                                                           settings.default_settings["user_level_view_comments"]))
        result["user_level_submit_comments"] = int(os.getenv("USER_LEVEL_SUBMIT_COMMENTS",
                                                             settings.default_settings["user_level_submit_comments"]))
        result["user_level_edit_comments"] = int(os.getenv("USER_LEVEL_EDIT_COMMENTS",
                                                           settings.default_settings["user_level_edit_comments"]))
        result["user_level_admin"] = int(os.getenv("USER_LEVEL_ADMIN", settings.default_settings["user_level_admin"]))
        
        val = database.generate_offline_meta(write_to_db=False)
        
        start_time = None
        end_time = None
        interval = None
        if type(val) is dict:
            start_time = val["start_time"]
            end_time = val["end_time"]
            interval = val["interval"]
        elif type(val) is bool and offline_mode:
            try:
                with open(offline_meta_file, "r") as f:
                    anon_data_meta = json.load(f)
                start_time = anon_data_meta["start_time"]
                end_time = anon_data_meta["end_time"]
                interval = anon_data_meta["interval"]
            except:
                raise ValueError("Can't generate required file: offline metadata")
        
        result["offline_data_start_time"] = start_time
        result["offline_data_end_time"] = end_time
        result["offline_data_interval"] = interval
        
        result["background_task_timing"] = os.getenv("BACKGROUND_TASK_TIMING",
                                                     settings.default_settings["background_task_timing"])
        result["meter_batch_size"] = os.getenv("METER_BATCH_SIZE", settings.default_settings["meter_batch_size"])
    return result

def initialise_settings_table(from_env: bool = False) -> bool:
    try:
        if len(models.db.session.execute(models.db.select(models.Settings)).scalars().all()) > 0:
            return False
        
        log.write(msg="Loading settings", level=log.info)

        initial_settings = load_settings_from_env(from_env)
        
        # Users
        settings.create_record(
            key="default_user_level",
            value=initial_settings["default_user_level"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_view_dashboard",
            value=initial_settings["user_level_view_dashboard"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_view_healthcheck",
            value=initial_settings["user_level_view_healthcheck"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_view_comments",
            value=initial_settings["user_level_view_comments"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_submit_comments",
            value=initial_settings["user_level_submit_comments"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_edit_comments",
            value=initial_settings["user_level_edit_comments"],
            setting_type="int"
        )
        settings.create_record(
            key="user_level_admin",
            value=initial_settings["user_level_admin"],
            setting_type="int"
        )
        settings.create_record(
            key="required_email_domains",
            value=initial_settings["required_email_domains"],
            setting_type="str"
        )
        settings.create_record(
            key="demo_email_domains",
            value=initial_settings["demo_email_domains"],
            setting_type="str"
        )
        
        # Mazemap info
        settings.create_record(
            key="mazemap_campus_id",
            value=initial_settings["mazemap_campus_id"],
            setting_type="int"
        )
        settings.create_record(
            key="mazemap_lng",
            value=initial_settings["mazemap_lng"],
            setting_type="str"
        )
        settings.create_record(
            key="mazemap_lat",
            value=initial_settings["mazemap_lat"],
            setting_type="str"
        )

        # SMTP
        settings.create_record(
            key="smtp_enabled",
            value=initial_settings["smtp_enabled"],
            setting_type="bool"
        )
        settings.create_record(
            key="smtp_address",
            value=initial_settings["smtp_address"],
            setting_type="str"
        )
        settings.create_record(
            key="smtp_password",
            value=initial_settings["smtp_password"],
            setting_type="str"
        )
        settings.create_record(
            key="smtp_server",
            value=initial_settings["smtp_server"],
            setting_type="str"
        )
        settings.create_record(
            key="smtp_port",
            value=initial_settings["smtp_port"],
            setting_type="str"
        )
        
        # Site info
        settings.create_record(
            key="site_name",
            value=initial_settings["site_name"],
            setting_type="str"
        )
        settings.create_record(
            key="default_start_page",
            value=initial_settings["default_start_page"],
            setting_type="str"
        )
        settings.create_record(
            key="default_daterange_benchmark",
            value=initial_settings["default_daterange_benchmark"],
            setting_type="int"
        )
        settings.create_record(
            key="default_daterange_browser",
            value=initial_settings["default_daterange_browser"],
            setting_type="int"
        )
        settings.create_record(
            key="default_daterange_health-check",
            value=initial_settings["default_daterange_health-check"],
            setting_type="int"
        )
        settings.create_record(
            key="capavis_url",
            value=initial_settings["capavis_url"],
            setting_type="str"
        )
        settings.create_record(
            key="clustering_url",
            value=initial_settings["clustering_url"],
            setting_type="str"
        )
        
        # Influx
        settings.create_record(
            key="influx_url",
            value=initial_settings["influx_url"],
            setting_type="str"
        )
        settings.create_record(
            key="influx_port",
            value=initial_settings["influx_port"],
            setting_type="str"
        )
        settings.create_record(
            key="influx_user",
            value=initial_settings["influx_user"],
            setting_type="str"
        )
        settings.create_record(
            key="influx_pass",
            value=initial_settings["influx_pass"],
            setting_type="str"
        )
        settings.create_record(
            key="influx_table",
            value=initial_settings["influx_table"],
            setting_type="str"
        )
        settings.create_record(
            key="influx_data_interval",
            value=initial_settings["influx_data_interval"],
            setting_type="int"
        )
        
        # Data
        settings.create_record(
            key="offline_mode",
            value=initial_settings["offline_mode"],
            setting_type="bool"
        )
        settings.create_record(
            key="hc_update_time",
            value=initial_settings["hc_update_time"],
            setting_type="int"
        )
        settings.create_record(
            key="cache_time_health_score",
            value=initial_settings["cache_time_health_score"],
            setting_type="int"
        )
        settings.create_record(
            key="cache_time_summary",
            value=initial_settings["cache_time_summary"],
            setting_type="int"
        )
        
        # Metadata
        settings.create_record(
            key="offline_data_start_time",
            value=initial_settings["offline_data_start_time"],
            setting_type="str"
        )
        settings.create_record(
            key="offline_data_end_time",
            value=initial_settings["offline_data_end_time"],
            setting_type="str"
        )
        settings.create_record(
            key="offline_data_interval",
            value=initial_settings["offline_data_interval"],
            setting_type="int"
        )

        ## Meter table
        settings.create_record(
            key="metadata.meter_sheet",
            value=initial_settings["metadata.meter_sheet"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.meter_id",
            value=initial_settings["metadata.meter_sheet.meter_id"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.raw_uuid",
            value=initial_settings["metadata.meter_sheet.raw_uuid"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.description",
            value=initial_settings["metadata.meter_sheet.description"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.building_level_meter",
            value=initial_settings["metadata.meter_sheet.building_level_meter"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.meter_type",
            value=initial_settings["metadata.meter_sheet.meter_type"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.reading_type",
            value=initial_settings["metadata.meter_sheet.reading_type"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.units",
            value=initial_settings["metadata.meter_sheet.units"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.resolution",
            value=initial_settings["metadata.meter_sheet.resolution"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.unit_conversion_factor",
            value=initial_settings["metadata.meter_sheet.unit_conversion_factor"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.tenant",
            value=initial_settings["metadata.meter_sheet.tenant"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.meter_sheet.meter_building",
            value=initial_settings["metadata.meter_sheet.meter_building"],
            setting_type="str"
        )

        ## Building table
        settings.create_record(
            key="metadata.building_sheet",
            value=initial_settings["metadata.building_sheet"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.building_code",
            value=initial_settings["metadata.building_sheet.building_code"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.building_name",
            value=initial_settings["metadata.building_sheet.building_name"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.floor_area",
            value=initial_settings["metadata.building_sheet.floor_area"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.year_built",
            value=initial_settings["metadata.building_sheet.year_built"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.usage",
            value=initial_settings["metadata.building_sheet.usage"],
            setting_type="str"
        )
        settings.create_record(
            key="metadata.building_sheet.maze_map_label",
            value=initial_settings["metadata.building_sheet.maze_map_label"],
            setting_type="str"
        )

        # Logging
        settings.create_record(
            key="log_level",
            value=initial_settings["log_level"],
            setting_type="str"
        )
        
        # Server settings
        settings.create_record(
            key="background_task_timing",
            value=initial_settings["background_task_timing"],
            setting_type="str"
        )
        settings.create_record(
            key="meter_batch_size",
            value=initial_settings["meter_batch_size"],
            setting_type="int"
        )
        settings.create_record(
            key="session_timeout",
            value=initial_settings["session_timeout"],
            setting_type="int"
        )
        settings.create_record(
            key="login_code_timeout",
            value=initial_settings["login_code_timeout"],
            setting_type="int"
        )
        settings.create_record(
            key="log_info_expiry",
            value=initial_settings["log_info_expiry"],
            setting_type="int"
        )
        settings.create_record(
            key="log_warning_expiry",
            value=initial_settings["log_warning_expiry"],
            setting_type="int"
        )
        settings.create_record(
            key="log_error_expiry",
            value=initial_settings["log_error_expiry"],
            setting_type="int"
        )
        settings.create_record(
            key="log_critical_expiry",
            value=initial_settings["log_critical_expiry"],
            setting_type="int"
        )
        return True
    except ValueError as e:
        models.db.session.rollback()
        if str(e) == "Can't generate required file: offline metadata":
            print("\n" + "="*20)
            print("\tERROR: You are running in offline mode with no offline metadata (and it couldn't be generated)!")
            print("\tPlease either place it in ./data/offline_data.json or add the data directly to the database")
            print("="*20 + "\n")
            log.write(msg="You are running in offline mode with no offline metadata (and it couldn't be generated). Please either place it in ./data/offline_data.json or add the data directly to the database.",
                        extra_info="Note: there may be other critical errors that are being masked by this one.",
                        level=log.critical)
            raise e
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        raise e
    except Exception as e:
        models.db.session.rollback()
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        raise e


app = Flask(__name__)

load_dotenv()
POSTGRES_USER = os.getenv("POSTGRES_USER", "net0i")
POSTGRES_PASS = os.getenv("POSTGRES_PASS")
POSTGRES_ADDRESS = os.getenv("POSTGRES_ADDRESS", "db")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_TABLE = os.getenv("POSTGRES_TABLE", "net0i")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_ADDRESS}:{POSTGRES_PORT}/{POSTGRES_TABLE}"

if POSTGRES_PASS is None:
    print("\n" + "="*20)
    print("\tERROR: You have not set the PostgreSQL credentials!")
    print("\tPlease set them in your .env file.")
    print("\tPostgreSQL credentials cannot be updated through the application - the values in .env are always used.")
    print("="*20 + "\n")
    exit(1)

# Test if database is accessible
database_available = False
max_database_connection_attempts = 10
for attempts in range(0, max_database_connection_attempts):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((POSTGRES_ADDRESS, POSTGRES_PORT))
        s.shutdown(socket.SHUT_RDWR)
        database_available = True
        break
    except Exception:
        if attempts < max_database_connection_attempts:
            print(f"Failed to connect to database, retrying in 1 second! ({attempts+1}/{max_database_connection_attempts})")
            time.sleep(1)

if not database_available:
    print("\n" + "="*20)
    print(f"\tFailed to connect to database after {max_database_connection_attempts} attempts, aborting startup.")
    print("\tPlease check your PostgreSQL credentials in .env, the address may not be correct")
    print("="*20 + "\n")
    exit(1)
else:
    print("Database connection successful!")

models.db.init_app(app)
try:
    with app.app_context():
        models.db.create_all()
        if not initialise_settings_table(True):
            try:
                log.write(msg="Skipped initialising settings table",
                          extra_info="Most likely already populated",
                          level=log.info)
            except:
                pass
except Exception as e:
    print("\n" + "="*20)
    print("\tERROR: Failed to initialise settings table!")
    print(f"\tThis could be because: {e}")
    print("="*20 + "\n")
    try:
        log.write(msg="Failed to initialise settings table", extra_info=str(e), level=log.critical)
    except:
        pass
    print("Exiting...")
    exit(1) # Error

print("Successfully initialised database! Restarting into app.py...")
exit(0) # Success