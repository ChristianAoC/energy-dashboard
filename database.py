from flask import g
from flask_sqlalchemy import SQLAlchemy

import copy
from dotenv import load_dotenv
import os
import pandas as pd
import json
import sys

from constants import metadata_file, offline_data_files, offline_meta_file

db = SQLAlchemy()

def init(app) -> bool:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'data.sqlite')}"
    db.init_app(app)

    with app.app_context():
        db.create_all()

        try:
            if not initialise_settings_table(True):
                try:
                    import log
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
                import log
                log.write(msg="Failed to initialise settings table", extra_info=str(e), level=log.critical)
            except:
                pass
            return False
    return True

def generate_offline_meta(write_to_db: bool = True) -> bool|dict:
    import models
    import settings
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
        
        temp_interval = df['time'].diff().dropna().min().total_seconds()/60 # type: ignore
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
    
    if not write_to_db:
        return out
    
    for key in out.keys():
        setting = db.session.execute(
            db.select(models.Settings)
            .where(models.Settings.key == key)
            .where(models.Settings.category == "metadata")
        ).scalar_one_or_none()
        if setting is None:
            return False
        
        setting_type = "str" if key != "interval" else "int"
        
        try:
            settings.update_record(setting, out[key], setting_type, "metadata") # type: ignore
        except:
            return False
    
    return True

def load_settings_from_env(from_env: bool = True) -> dict:
    from settings import default_settings
    result = copy.deepcopy(default_settings)
    
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
        
        result["data"]["offline_mode"] = offline_mode
        result["influx"]["InfluxURL"] = influx_url
        result["influx"]["InfluxPort"] = influx_port
        result["influx"]["InfluxUser"] = influx_user
        result["influx"]["InfluxPass"] = influx_pass
        result["influx"]["InfluxTable"] = influx_table
        result["influx"]["data_interval"] = int(os.getenv("data_interval", default_settings["influx"]["data_interval"]))
        
        result["data"]["hc_update_time"] = int(os.getenv("HEALTH_CHECK_UPDATE_TIME",
                                                 default_settings["data"]["hc_update_time"]))
        result["data"]["cache_time_health_score"] = int(os.getenv("HEALTH_SCORE_CACHE_TIME",
                                                          default_settings["data"]["cache_time_health_score"]))
        result["data"]["cache_time_summary"] = int(os.getenv("SUMMARY_CACHE_TIME",
                                                     default_settings["data"]["cache_time_summary"]))
        
        result["logging"]["log_level"] = os.getenv("LOG_LEVEL", default_settings["logging"]["log_level"])
        
        result["SITE_NAME"] = os.getenv("SITE_NAME", default_settings["site"]["SITE_NAME"])
        
        result["mazemap"]["MAZEMAP_CAMPUS_ID"] = int(os.getenv("MAZEMAP_CAMPUS_ID",
                                                    default_settings["mazemap"]["MAZEMAP_CAMPUS_ID"]))
        result["mazemap"]["MAZEMAP_LNG"] = os.getenv("MAZEMAP_LNG", default_settings["mazemap"]["MAZEMAP_LNG"])
        result["mazemap"]["MAZEMAP_LAT"] = os.getenv("MAZEMAP_LAT", default_settings["mazemap"]["MAZEMAP_LAT"])
        
        smtp_address = os.getenv("SMTP_ADDRESS")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        
        val = os.getenv("SMTP_ENABLED", "False")
        smtp_enabled = val.strip().lower() in ("1", "true", "yes", "on")
        
        if smtp_address is None or smtp_password is None or smtp_server is None or smtp_port is None:
            smtp_enabled = False
        result["smtp"]["SMTP_ENABLED"] = smtp_enabled
        result["smtp"]["SMTP_ADDRESS"] = smtp_address
        result["smtp"]["SMTP_PASSWORD"] = smtp_password
        result["smtp"]["SMTP_SERVER"] = smtp_server
        result["smtp"]["SMTP_PORT"] = smtp_port
        
        result["users"]["REQUIRED_EMAIL_DOMAINS"] = os.getenv("REQUIRED_EMAIL_DOMAINS", "")
        result["users"]["DEMO_EMAIL_DOMAINS"] = os.getenv("DEMO_EMAIL_DOMAINS", "")
        
        result["users"]["DEFAULT_USER_LEVEL"] = int(os.getenv("DEFAULT_USER_LEVEL",
                                                     default_settings["users"]["DEFAULT_USER_LEVEL"]))
        result["users"]["USER_LEVEL_VIEW_DASHBOARD"] = int(os.getenv("USER_LEVEL_VIEW_DASHBOARD",
                                                            default_settings["users"]["USER_LEVEL_VIEW_DASHBOARD"]))
        result["users"]["USER_LEVEL_VIEW_HEALTHCHECK"] = int(os.getenv("USER_LEVEL_VIEW_HEALTHCHECK",
                                                              default_settings["users"]["USER_LEVEL_VIEW_HEALTHCHECK"]))
        result["users"]["USER_LEVEL_VIEW_COMMENTS"] = int(os.getenv("USER_LEVEL_VIEW_COMMENTS",
                                                           default_settings["users"]["USER_LEVEL_VIEW_COMMENTS"]))
        result["users"]["USER_LEVEL_SUBMIT_COMMENTS"] = int(os.getenv("USER_LEVEL_SUBMIT_COMMENTS",
                                                             default_settings["users"]["USER_LEVEL_SUBMIT_COMMENTS"]))
        result["users"]["USER_LEVEL_EDIT_COMMENTS"] = int(os.getenv("USER_LEVEL_EDIT_COMMENTS",
                                                           default_settings["users"]["USER_LEVEL_EDIT_COMMENTS"]))
        result["users"]["USER_LEVEL_ADMIN"] = int(os.getenv("USER_LEVEL_ADMIN", default_settings["users"]["USER_LEVEL_ADMIN"]))
        
        val = generate_offline_meta(write_to_db=False)
        
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
        
        result["metadata"]["offline_data_start_time"] = start_time
        result["metadata"]["offline_data_end_time"] = end_time
        result["metadata"]["offline_data_interval"] = interval
        
        result["server"]["BACKGROUND_TASK_TIMING"] = os.getenv("BACKGROUND_TASK_TIMING",
                                                     default_settings["server"]["BACKGROUND_TASK_TIMING"])
        result["server"]["meter_batch_size"] = os.getenv("meter_batch_size", default_settings["server"]["meter_batch_size"])
    return result

def initialise_settings_table(from_env: bool = False) -> bool:
    # Import here to stop circular import issue
    import log
    import models
    
    try:
        if len(db.session.execute(db.select(models.Settings)).scalars().all()) > 0:
            return False
        
        log.write(msg="Loading settings", level=log.info)
        
        settings = []
        
        temp_default_settings = load_settings_from_env(from_env)
        
        # Users
        settings.append(models.Settings(
            key="DEFAULT_USER_LEVEL",
            value=temp_default_settings["users"]["DEFAULT_USER_LEVEL"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_DASHBOARD",
            value=temp_default_settings["users"]["USER_LEVEL_VIEW_DASHBOARD"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_HEALTHCHECK",
            value=temp_default_settings["users"]["USER_LEVEL_VIEW_HEALTHCHECK"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_COMMENTS",
            value=temp_default_settings["users"]["USER_LEVEL_VIEW_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_SUBMIT_COMMENTS",
            value=temp_default_settings["users"]["USER_LEVEL_SUBMIT_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_EDIT_COMMENTS",
            value=temp_default_settings["users"]["USER_LEVEL_EDIT_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_ADMIN",
            value=temp_default_settings["users"]["USER_LEVEL_ADMIN"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="REQUIRED_EMAIL_DOMAINS",
            value=temp_default_settings["users"]["REQUIRED_EMAIL_DOMAINS"],
            category="users",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="DEMO_EMAIL_DOMAINS",
            value=temp_default_settings["users"]["DEMO_EMAIL_DOMAINS"],
            category="users",
            setting_type="str"
        ))
        
        # Mazemap info
        settings.append(models.Settings(
            key="MAZEMAP_CAMPUS_ID",
            value=temp_default_settings["mazemap"]["MAZEMAP_CAMPUS_ID"],
            category="mazemap",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="MAZEMAP_LNG",
            value=temp_default_settings["mazemap"]["MAZEMAP_LNG"],
            category="mazemap",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="MAZEMAP_LAT",
            value=temp_default_settings["mazemap"]["MAZEMAP_LAT"],
            category="mazemap",
            setting_type="str"
        ))

        # SMTP
        settings.append(models.Settings(
            key="SMTP_ENABLED",
            value=temp_default_settings["smtp"]["SMTP_ENABLED"],
            category="smtp",
            setting_type="bool"
        ))
        settings.append(models.Settings(
            key="SMTP_ADDRESS",
            value=temp_default_settings["smtp"]["SMTP_ADDRESS"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_PASSWORD",
            value=temp_default_settings["smtp"]["SMTP_PASSWORD"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_SERVER",
            value=temp_default_settings["smtp"]["SMTP_SERVER"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_PORT",
            value=temp_default_settings["smtp"]["SMTP_PORT"],
            category="smtp",
            setting_type="str"
        ))
        
        # Site info
        settings.append(models.Settings(
            key="SITE_NAME",
            value=temp_default_settings["site"]["SITE_NAME"],
            category="site",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="default_start_page",
            value=temp_default_settings["site"]["default_start_page"],
            category="site",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="default_daterange_benchmark",
            value=temp_default_settings["site"]["default_daterange_benchmark"],
            category="site",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="default_daterange_browser",
            value=temp_default_settings["site"]["default_daterange_browser"],
            category="site",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="default_daterange_health-check",
            value=temp_default_settings["site"]["default_daterange_health-check"],
            category="site",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="capavis_url",
            value=temp_default_settings["site"]["capavis_url"],
            category="site",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="clustering_url",
            value=temp_default_settings["site"]["clustering_url"],
            category="site",
            setting_type="str"
        ))
        
        # Influx
        settings.append(models.Settings(
            key="InfluxURL",
            value=temp_default_settings["influx"]["InfluxURL"],
            category="influx",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="InfluxPort",
            value=temp_default_settings["influx"]["InfluxPort"],
            category="influx",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="InfluxUser",
            value=temp_default_settings["influx"]["InfluxUser"],
            category="influx",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="InfluxPass",
            value=temp_default_settings["influx"]["InfluxPass"],
            category="influx",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="InfluxTable",
            value=temp_default_settings["influx"]["InfluxTable"],
            category="influx",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="data_interval",
            value=temp_default_settings["influx"]["data_interval"],
            category="influx",
            setting_type="int"
        ))
        
        # Data
        settings.append(models.Settings(
            key="offline_mode",
            value=temp_default_settings["data"]["offline_mode"],
            category="data",
            setting_type="bool"
        ))
        settings.append(models.Settings(
            key="hc_update_time",
            value=temp_default_settings["data"]["hc_update_time"],
            category="data",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="cache_time_health_score",
            value=temp_default_settings["data"]["cache_time_health_score"],
            category="data",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="cache_time_summary",
            value=temp_default_settings["data"]["cache_time_summary"],
            category="data",
            setting_type="int"
        ))
        
        # Metadata
        settings.append(models.Settings(
            key="offline_data_start_time",
            value=temp_default_settings["metadata"]["offline_data_start_time"],
            category="metadata",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="offline_data_end_time",
            value=temp_default_settings["metadata"]["offline_data_end_time"],
            category="metadata",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="offline_data_interval",
            value=temp_default_settings["metadata"]["offline_data_interval"],
            category="metadata",
            setting_type="int"
        ))

        ## Meter table
        settings.append(models.Settings(
            key="meter_sheet",
            value=temp_default_settings["metadata"]["meter_sheet"]["meter_sheet"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="meter_id",
            value=temp_default_settings["metadata"]["meter_sheet"]["meter_id"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="raw_uuid",
            value=temp_default_settings["metadata"]["meter_sheet"]["raw_uuid"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="description",
            value=temp_default_settings["metadata"]["meter_sheet"]["description"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="building_level_meter",
            value=temp_default_settings["metadata"]["meter_sheet"]["building_level_meter"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="meter_type",
            value=temp_default_settings["metadata"]["meter_sheet"]["meter_type"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="reading_type",
            value=temp_default_settings["metadata"]["meter_sheet"]["reading_type"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="units",
            value=temp_default_settings["metadata"]["meter_sheet"]["units"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="resolution",
            value=temp_default_settings["metadata"]["meter_sheet"]["resolution"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="unit_conversion_factor",
            value=temp_default_settings["metadata"]["meter_sheet"]["unit_conversion_factor"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="tenant",
            value=temp_default_settings["metadata"]["meter_sheet"]["tenant"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="meter_building",
            value=temp_default_settings["metadata"]["meter_sheet"]["meter_building"],
            category="metadata.meter_sheet",
            setting_type="str"
        ))

        ## Building table
        settings.append(models.Settings(
            key="building_sheet",
            value=temp_default_settings["metadata"]["building_sheet"]["building_sheet"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="building_code",
            value=temp_default_settings["metadata"]["building_sheet"]["building_code"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="building_name",
            value=temp_default_settings["metadata"]["building_sheet"]["building_name"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="floor_area",
            value=temp_default_settings["metadata"]["building_sheet"]["floor_area"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="year_built",
            value=temp_default_settings["metadata"]["building_sheet"]["year_built"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="usage",
            value=temp_default_settings["metadata"]["building_sheet"]["usage"],
            category="metadata.building_sheet",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="maze_map_label",
            value=temp_default_settings["metadata"]["building_sheet"]["maze_map_label"],
            category="metadata.building_sheet",
            setting_type="str"
        ))

        # Logging
        settings.append(models.Settings(
            key="log_level",
            value=temp_default_settings["logging"]["log_level"],
            category="logging",
            setting_type="str"
        ))
        
        # Server settings
        settings.append(models.Settings(
            key="BACKGROUND_TASK_TIMING",
            value=temp_default_settings["server"]["BACKGROUND_TASK_TIMING"],
            category="server",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="meter_batch_size",
            value=temp_default_settings["server"]["meter_batch_size"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="session_timeout",
            value=temp_default_settings["server"]["session_timeout"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="login_code_timeout",
            value=temp_default_settings["server"]["login_code_timeout"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="log_info_expiry",
            value=temp_default_settings["server"]["log_info_expiry"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="log_warning_expiry",
            value=temp_default_settings["server"]["log_warning_expiry"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="log_error_expiry",
            value=temp_default_settings["server"]["log_error_expiry"],
            category="server",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="log_critical_expiry",
            value=temp_default_settings["server"]["log_critical_expiry"],
            category="server",
            setting_type="int"
        ))
        
        db.session.add_all(settings)
        
        db.session.commit()
        return True
    except ValueError as e:
        db.session.rollback()
        if str(e) == "Can't generate required file: offline metadata":
            print("\n" + "="*20)
            print("\tERROR: You are running in offline mode with no offline metadata (and it couldn't be generated)!")
            print("\tPlease either place it in ./data/offline_data.json or add the data directly to the database")
            print("="*20 + "\n")
            log.write(msg="You are running in offline mode with no offline metadata (and it couldn't be generated). Please either place it in ./data/offline_data.json or add the data directly to the database.",
                        extra_info="Note: there may be other critical errors that are being masked by this one.",
                        level=log.critical)
            sys.exit(1)
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        raise e
    except Exception as e:
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        db.session.rollback()
        raise e

# ======================================================================================================================
# NOTE: None of the helper functions in this section commit to the database.
#       The commit happens at the end of initial_database_population (which is outside of the section) or
#       at the end of process_metadata_update (which is in ./api/settings.py).
#       If you use them somewhere else then you need to commit the database.

def process_building_row(row) -> dict:
    building_code_raw = row[g.settings["metadata"]["building_sheet"]["building_code"]]
    if pd.isna(building_code_raw) or building_code_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['building_sheet']['building_code']}")
    building_code = str(building_code_raw).strip()
    
    floor_area_raw = row[g.settings["metadata"]["building_sheet"]["floor_area"]]
    floor_area = None
    if not pd.isna(floor_area_raw) and floor_area_raw is not None:
        floor_area = int(floor_area_raw)
    
    year_built_raw = row[g.settings["metadata"]["building_sheet"]["year_built"]]
    year_built = None
    if not pd.isna(year_built_raw) and year_built_raw is not None:
        year_built = int(year_built_raw)
    
    usage_raw = row[g.settings["metadata"]["building_sheet"]["usage"]]
    if pd.isna(usage_raw) or usage_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['building_sheet']['usage']}")
    usage = str(usage_raw).strip()
    
    maze_map_label_raw = row[g.settings["metadata"]["building_sheet"]["maze_map_label"]]
    maze_map_label = []
    if not pd.isna(maze_map_label_raw) and maze_map_label_raw is not None:
        values = str(maze_map_label_raw).split(';')
        for v in values:
            maze_map_label.append(int(v))
    
    return {
        "building_code": building_code.strip(),
        "building_name": row[g.settings["metadata"]["building_sheet"]["building_name"]].strip(),
        "floor_area": floor_area,
        "year_built": year_built,
        "occupancy_type": usage,
        "maze_map_label": maze_map_label
    }

def process_meter_row(row) -> dict:
    meter_id_clean_raw = row[g.settings["metadata"]["meter_sheet"]["meter_id"]]
    if pd.isna(meter_id_clean_raw) or meter_id_clean_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['meter_sheet']['meter_id']}")
    meter_id_clean = str(meter_id_clean_raw).strip()
    
    raw_uuid_raw = row[g.settings["metadata"]["meter_sheet"]["raw_uuid"]]
    raw_uuid = None
    if not pd.isna(raw_uuid_raw) and raw_uuid_raw is not None:
        raw_uuid = str(raw_uuid_raw).strip()
    
    building_level_meter_raw = row[g.settings["metadata"]["meter_sheet"]["building_level_meter"]]
    building_level_meter = False
    if not pd.isna(building_level_meter_raw) and building_level_meter_raw is not None:
        if str(building_level_meter_raw).strip().lower() in ["yes", "1", "y", "true"]:
            building_level_meter = True
    
    tenant_raw = row[g.settings["metadata"]["meter_sheet"]["tenant"]]
    tenant = False
    if not pd.isna(tenant_raw) and tenant_raw is not None:
        if str(tenant_raw).strip().lower() in ["yes", "1", "y", "true"]:
            tenant = True
    
    reading_type_raw = row[g.settings["metadata"]["meter_sheet"]["reading_type"]]
    if pd.isna(reading_type_raw) or reading_type_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['meter_sheet']['reading_type']}")
    reading_type = str(reading_type_raw).strip().lower()
    if reading_type not in ["cumulative", "rate"]:
        raise ValueError(f"Invalid {g.settings['metadata']['meter_sheet']['reading_type']}, needs to be either 'cumulative' or 'rate'")
    
    resolution_raw = row[g.settings["metadata"]["meter_sheet"]["resolution"]]
    if pd.isna(resolution_raw) or resolution_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['meter_sheet']['resolution']}")
    resolution = float(resolution_raw)
    
    unit_conversion_factor_raw = row[g.settings["metadata"]["meter_sheet"]["unit_conversion_factor"]]
    if pd.isna(unit_conversion_factor_raw) or unit_conversion_factor_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata']['meter_sheet']['unit_conversion_factor']}")
    unit_conversion_factor = float(unit_conversion_factor_raw)
    
    return {
        "meter_id": meter_id_clean,
        "raw_uuid": raw_uuid,
        "description": row[g.settings["metadata"]["meter_sheet"]["description"]].strip(),
        "building_level_meter": building_level_meter,
        "utility_type": row[g.settings["metadata"]["meter_sheet"]["meter_type"]].strip(),
        "reading_type": reading_type,
        "units": row[g.settings["metadata"]["meter_sheet"]["units"]].strip(),
        "resolution": resolution,
        "unit_conversion_factor": unit_conversion_factor,
        "tenant": tenant,
        "building": row[g.settings["metadata"]["meter_sheet"]["meter_building"]]
    }

def create_building_record(building_data: dict):
    # Import here to stop circular import issue
    import models
    import log
    log.write(msg=f"Creating building record: {building_data['metadata']['building_sheet']['building_code']}", level=log.info)
    
    new_building = models.Building(
        building_data["building_code"],
        building_data["building_name"],
        building_data["floor_area"],
        building_data["year_built"],
        building_data["occupancy_type"],
        building_data["maze_map_label"]
    )
    db.session.add(new_building)

def create_meter_record(meter_data: dict):
    # Import here to stop circular import issue
    import models
    import log
    log.write(msg=f"Creating meter record: {meter_data['meter_id']}", level=log.info)
    
    new_meter = models.Meter(
        meter_data["meter_id"],
        meter_data["raw_uuid"],
        meter_data["description"],
        meter_data["building_level_meter"],
        meter_data["utility_type"],
        meter_data["reading_type"],
        meter_data["units"],
        meter_data["resolution"],
        meter_data["unit_conversion_factor"],
        meter_data["tenant"],
        meter_data["building"]
    )
    db.session.add(new_meter)

def delete_building_record(building_obj):
    # Import here to stop circular import issue
    import models
    import log
    building_id = building_obj.id
    log.write(msg=f"Deleting building record: {building_id}", level=log.info)
    
    db.session.execute(db.delete(models.UtilityData).where(models.UtilityData.building_id == building_id))
    
    meters = db.session.execute(db.select(models.Meter).where(models.Meter.building_id == building_id)).scalars().all()
    for meter in meters:
        meter.building_id = None
    
    db.session.execute(
        db.delete(models.Context)
        .where(models.Context.target_type == "building")
        .where(models.Context.target_id == building_id)
    )
    
    db.session.execute(db.delete(models.Building).where(models.Building.id == building_id))

def delete_meter_record(meter_obj):
    # Import here to stop circular import issue
    import models
    import log
    meter_id = meter_obj.id
    log.write(msg=f"Deleting meter record: {meter_id}", level=log.info)
    
    db.session.execute(db.delete(models.HealthCheck).where(models.HealthCheck.meter_id == meter_id))
    
    db.session.execute(
        db.delete(models.Context)
        .where(models.Context.target_type == "meter")
        .where(models.Context.target_id == meter_id)
    )
    
    db.session.execute(db.delete(models.Meter).where(models.Meter.id == meter_id))

# ======================================================================================================================

def initial_database_population() -> bool:
    # Import here to stop circular import issue
    import models
    import log
    
    if (len(db.session.execute(db.select(models.Meter)).scalars().all()) > 0
            or len(db.session.execute(db.select(models.Building)).scalars().all()) > 0):
        from settings import process_metadata_update
        return process_metadata_update()
    
    buildings = pd.read_excel(metadata_file, sheet_name=g.settings["metadata"]["building_sheet"])
    for _, row in buildings.iterrows():
        try:
            data = process_building_row(row)
            create_building_record(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            try:
                building_id = data["building_code"] # type: ignore
            except:
                building_id = "UNKNOWN BUILDING"
            log.write(msg="Error loading building from metadata file",
                      extra_info=f"{building_id}: {str(e)}",
                      level=log.warning)
    del buildings
    
    meters = pd.read_excel(metadata_file, sheet_name=g.settings["metadata"]["meter_sheet"]["meter_sheet"])
    for _, row in meters.iterrows():
        try:
            data = process_meter_row(row)
            
            # Filter out meters with utility types that we don't support
            if data["utility_type"] not in ["electricity", "gas", "heat", "water"]:
                continue
            
            create_meter_record(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            try:
                meter_id = data["meter_id"] # type: ignore
            except:
                meter_id = "UNKNOWN METER"
            log.write(msg="Error loading meter from metadata file",
                      extra_info=f"{meter_id}: {str(e)}",
                      level=log.warning)
    return True