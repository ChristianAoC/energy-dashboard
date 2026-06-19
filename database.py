from flask import g

import copy
from dotenv import load_dotenv
import os
import pandas as pd
import json

from constants import metadata_file, offline_data_files, offline_meta_file
import models
from models import db
import log
import settings


def init() -> bool:
    try:
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
        return False
    return True

def generate_offline_meta(write_to_db: bool = True) -> bool|dict:
    import settings
    start_time = None
    end_time = None
    interval = None
    
    if not os.path.exists(offline_data_files):
        return False
    
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
        "metadata.start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "metadata.end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "metadata.interval": interval
    }
    
    if not write_to_db:
        return out
    
    for key in out.keys():
        setting = db.session.execute(
            db.select(models.Settings)
            .where(models.Settings.key == key)
        ).scalar_one_or_none()
        if setting is None:
            return False
        
        setting_type = "str" if key != "metadata.interval" else "int"
        
        try:
            settings.update_record(setting, out[key], setting_type)
        except:
            return False
    
    return True

def load_settings_from_env(from_env: bool = True) -> dict[str,str|bool|None|int|float]:
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
        
        result["offline_mode"] = offline_mode
        result["influx_url"] = influx_url
        result["influx_port"] = influx_port
        result["influx_user"] = influx_user
        result["influx_pass"] = influx_pass
        result["influx_table"] = influx_table
        result["influx_data_interval"] = int(os.getenv("INFLUX_DATA_INTERVAL", default_settings["influx_data_interval"]))
        
        result["hc_update_time"] = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", default_settings["hc_update_time"]))
        result["cache_time_health_score"] = int(os.getenv("HEALTH_SCORE_CACHE_TIME",
                                                          default_settings["cache_time_health_score"]))
        result["cache_time_summary"] = int(os.getenv("SUMMARY_CACHE_TIME", default_settings["cache_time_summary"]))
        
        result["log_level"] = os.getenv("LOG_LEVEL", default_settings["log_level"])
        
        result["site_name"] = os.getenv("SITE_NAME", default_settings["site_name"])
        
        result["mazemap_campus_id"] = int(os.getenv("MAZEMAP_CAMPUS_ID", default_settings["mazemap_campus_id"]))
        result["mazemap_lng"] = os.getenv("MAZEMAP_LNG", default_settings["mazemap_lng"])
        result["mazemap_lat"] = os.getenv("MAZEMAP_LAT", default_settings["mazemap_lat"])
        
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
                                                     default_settings["default_user_level"]))
        result["user_level_view_dashboard"] = int(os.getenv("USER_LEVEL_VIEW_DASHBOARD",
                                                            default_settings["user_level_view_dashboard"]))
        result["user_level_view_healthcheck"] = int(os.getenv("USER_LEVEL_VIEW_HEALTHCHECK",
                                                              default_settings["user_level_view_healthcheck"]))
        result["user_level_view_comments"] = int(os.getenv("USER_LEVEL_VIEW_COMMENTS",
                                                           default_settings["user_level_view_comments"]))
        result["user_level_submit_comments"] = int(os.getenv("USER_LEVEL_SUBMIT_COMMENTS",
                                                             default_settings["user_level_submit_comments"]))
        result["user_level_edit_comments"] = int(os.getenv("USER_LEVEL_EDIT_COMMENTS",
                                                           default_settings["user_level_edit_comments"]))
        result["user_level_admin"] = int(os.getenv("USER_LEVEL_ADMIN", default_settings["user_level_admin"]))
        
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
        
        result["offline_data_start_time"] = start_time
        result["offline_data_end_time"] = end_time
        result["offline_data_interval"] = interval
        
        result["background_task_timing"] = os.getenv("BACKGROUND_TASK_TIMING",
                                                     default_settings["background_task_timing"])
        result["meter_batch_size"] = os.getenv("METER_BATCH_SIZE", default_settings["meter_batch_size"])
    return result

def initialise_settings_table(from_env: bool = False) -> bool:
    try:
        if len(db.session.execute(db.select(models.Settings)).scalars().all()) > 0:
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
        db.session.rollback()
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
        db.session.rollback()
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        raise e

# ======================================================================================================================
# NOTE: None of the helper functions in this section commit to the database.
#       The commit happens at the end of initial_database_population (which is outside of the section) or
#       at the end of process_metadata_update (which is in ./api/settings.py).
#       If you use them somewhere else then you need to commit the database.

def process_building_row(row) -> dict:
    building_code_raw = row[g.settings["metadata.building_sheet.building_code"]]
    if pd.isna(building_code_raw) or building_code_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.building_sheet.building_code']}")
    building_code = str(building_code_raw).strip()
    
    floor_area_raw = row[g.settings["metadata.building_sheet.floor_area"]]
    floor_area = None
    if not pd.isna(floor_area_raw) and floor_area_raw is not None:
        floor_area = int(floor_area_raw)
    
    year_built_raw = row[g.settings["metadata.building_sheet.year_built"]]
    year_built = None
    if not pd.isna(year_built_raw) and year_built_raw is not None:
        year_built = int(year_built_raw)
    
    usage_raw = row[g.settings["metadata.building_sheet.usage"]]
    if pd.isna(usage_raw) or usage_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.building_sheet.usage']}")
    usage = str(usage_raw).strip()
    
    maze_map_label_raw = row[g.settings["metadata.building_sheet.maze_map_label"]]
    maze_map_label = []
    if not pd.isna(maze_map_label_raw) and maze_map_label_raw is not None:
        values = str(maze_map_label_raw).split(';')
        for v in values:
            maze_map_label.append(int(v))
    
    return {
        "building_code": building_code.strip(),
        "building_name": row[g.settings["metadata.building_sheet.building_name"]].strip(),
        "floor_area": floor_area,
        "year_built": year_built,
        "occupancy_type": usage,
        "maze_map_label": maze_map_label
    }

def process_meter_row(row) -> dict:
    meter_id_clean_raw = row[g.settings["metadata.meter_sheet.meter_id"]]
    if pd.isna(meter_id_clean_raw) or meter_id_clean_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.meter_id']}")
    meter_id_clean = str(meter_id_clean_raw).strip()
    
    raw_uuid_raw = row[g.settings["metadata.meter_sheet.raw_uuid"]]
    raw_uuid = None
    if not pd.isna(raw_uuid_raw) and raw_uuid_raw is not None:
        raw_uuid = str(raw_uuid_raw).strip()
    
    building_level_meter_raw = row[g.settings["metadata.meter_sheet.building_level_meter"]]
    building_level_meter = False
    if not pd.isna(building_level_meter_raw) and building_level_meter_raw is not None:
        if str(building_level_meter_raw).strip().lower() in ["yes", "1", "y", "true"]:
            building_level_meter = True
    
    tenant_raw = row[g.settings["metadata.meter_sheet.tenant"]]
    tenant = False
    if not pd.isna(tenant_raw) and tenant_raw is not None:
        if str(tenant_raw).strip().lower() in ["yes", "1", "y", "true"]:
            tenant = True
    
    reading_type_raw = row[g.settings["metadata.meter_sheet.reading_type"]]
    if pd.isna(reading_type_raw) or reading_type_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.reading_type']}")
    reading_type = str(reading_type_raw).strip().lower()
    if reading_type not in ["cumulative", "rate"]:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.reading_type']}, needs to be either 'cumulative' or 'rate'")
    
    resolution_raw = row[g.settings["metadata.meter_sheet.resolution"]]
    if pd.isna(resolution_raw) or resolution_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.resolution']}")
    resolution = float(resolution_raw)
    
    unit_conversion_factor_raw = row[g.settings["metadata.meter_sheet.unit_conversion_factor"]]
    if pd.isna(unit_conversion_factor_raw) or unit_conversion_factor_raw is None:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.unit_conversion_factor']}")
    unit_conversion_factor = float(unit_conversion_factor_raw)
    
    units_raw = row[g.settings["metadata.meter_sheet.units"]]
    units = units_raw.strip()
    if len(units) > 5:
        raise ValueError(f"Invalid {g.settings['metadata.meter_sheet.units']}")
    
    return {
        "meter_id": meter_id_clean,
        "raw_uuid": raw_uuid,
        "description": row[g.settings["metadata.meter_sheet.description"]].strip(),
        "building_level_meter": building_level_meter,
        "utility_type": row[g.settings["metadata.meter_sheet.meter_type"]].strip().lower(),
        "reading_type": reading_type,
        "units": units,
        "resolution": resolution,
        "unit_conversion_factor": unit_conversion_factor,
        "tenant": tenant,
        "building": row[g.settings["metadata.meter_sheet.meter_building"]]
    }

def create_building_record(building_data: dict):
    log.write(msg=f"Creating building record: {building_data['building_code']}", level=log.info)
    
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
    # If records already exist then run the metadata update function that handles existing records
    if (len(db.session.execute(db.select(models.Meter)).scalars().all()) > 0
            or len(db.session.execute(db.select(models.Building)).scalars().all()) > 0):
        from settings import process_metadata_update
        return process_metadata_update()
    
    buildings = pd.read_excel(metadata_file, sheet_name=g.settings["metadata.building_sheet"])
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
    
    meters = pd.read_excel(metadata_file, sheet_name=g.settings["metadata.meter_sheet"])
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