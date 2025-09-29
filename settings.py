from flask import request, g, current_app, has_app_context
from sqlalchemy import not_

import copy
import datetime as dt
import pandas as pd

from constants import metadata_file
from database import db, process_building_row, process_meter_row, create_building_record, create_meter_record, delete_building_record, delete_meter_record
import log
import models


default_settings = {
    "users": {
        "DEFAULT_USER_LEVEL": 1,
        "USER_LEVEL_VIEW_DASHBOARD": 0,
        "USER_LEVEL_VIEW_HEALTHCHECK": 1,
        "USER_LEVEL_VIEW_COMMENTS": 1,
        "USER_LEVEL_SUBMIT_COMMENTS": 1,
        "USER_LEVEL_EDIT_COMMENTS": 4,
        "USER_LEVEL_ADMIN": 5,
        "REQUIRED_EMAIL_DOMAINS": None,
        "DEMO_EMAIL_DOMAINS": None
    },
    "mazemap": {
        "MAZEMAP_CAMPUS_ID": 341,
        "MAZEMAP_LNG": "-2.780372",
        "MAZEMAP_LAT": "54.008809"
    },
    "smtp": {
        "SMTP_ENABLED": False,
        "SMTP_ADDRESS": None,
        "SMTP_PASSWORD": None,
        "SMTP_SERVER": None,
        "SMTP_PORT": None
    },
    "site": {
        "SITE_NAME": "Energy Dashboard",
        "default_start_page": "browser",
        "default_daterange_benchmark": 365,
        "default_daterange_browser": 30,
        "default_daterange_health-check": 30,
        "capavis_url": "",
        "clustering_url": ""
    },
    "influx": {
        "data_interval": 10,
        "InfluxURL": None,
        "InfluxPort": None,
        "InfluxUser": None,
        "InfluxPass": None,
        "InfluxTable": None
    },
    # Data settings
    "data": {
        "offline_mode": True,
        "hc_update_time": 20,
        "cache_time_health_score": 365,
        "cache_time_summary": 30
    },
    "metadata": {
        "offline_data_start_time": None,
        "offline_data_end_time": None,
        "offline_data_interval": None,
        "meter_sheet": {
            "meter_sheet": "Energie points",
            "meter_id": "meter_id_clean2",
            "raw_uuid": "SEED_uuid",
            "description": "description",
            "building_level_meter": "Building Level Meter",
            "meter_type": "Meter Type",
            "reading_type": "class",
            "units": "units_after_conversion",
            "resolution": "Resolution",
            "unit_conversion_factor": "unit_conversion_factor",
            "tenant": "tenant",
            "meter_building": "Building code"
        },
        "building_sheet": {
            "building_sheet": "Buildings",
            "building_code": "Property code",
            "building_name": "Building Name",
            "floor_area": "floor_area",
            "year_built": "Year",
            "usage": "Function",
            "maze_map_label": "mazemap_ids"
        }
    },
    "logging": {
        "log_level": log.warning
    },
    "server": {
        "BACKGROUND_TASK_TIMING": "02:00",
        "meter_batch_size": 16,
        "session_timeout": 365,
        "login_code_timeout": 60,
        "log_info_expiry": 7,
        "log_warning_expiry": 14,
        "log_error_expiry": 30,
        "log_critical_expiry": 180
    }
}

def process_categories(settings: dict, key: str, category: str, value = None, write: bool = False):
    parts = category.split('.')
    
    temp = settings
    for part in parts[:-1]:
        temp = temp.setdefault(part, {})
    
    if write:
        temp[parts[-1]][key] = value
    else:
        return temp[parts[-1]][key]

def load_settings():
    # I had an idea to implement a "lazy loading" system here but for now there isn't enough settings to require it.
    # May be worth looking into if the DB gets locked up frequently
    
    # NOTE: When accessing g settings you should use `g.settings[category][key]` to raise an Exception
    #       (unless you can handle it locally)
    if request.path.startswith('/static'):
        return
    
    if 'settings' not in g:
        g.settings = copy.deepcopy(default_settings)
        
        for setting in db.session.execute(db.select(models.Settings)).scalars().all():
            process_categories(settings=g.settings,
                               key=setting.key,
                               category=setting.category,
                               value=setting.value,
                               write=True)

def create_record(key: str, value, setting_type: str, category: str|None = None):
    try:
        new_record = models.Settings(
            key=key,
            value=value,
            category=category,
            setting_type=setting_type
        )
        db.session.add(new_record)
        db.session.commit()
    except:
        db.session.rollback()
        raise ValueError

def update_record(obj: models.Settings, value, setting_type: str, category: str|None = None):
    try:
        if obj.setting_type != setting_type:
            raise TypeError(f"Type {setting_type} doesn't match the existing type of {obj.setting_type}")

        if obj.key == "offline_mode" and obj.value != value:
            current_app.config["offline_mode"] = value
            invalidate_hc_cache()
            invalidate_summary_cache()
        
        if obj.key == "USER_LEVEL_ADMIN" and value > obj.value:
            elevate_existing_admins(value)
        
        obj.value = value
        obj.category = category
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get(key: str, category: str):
    existing_setting = None
    try:
        existing_setting = db.session.execute(
            db.Select(models.Settings)
            .where(models.Settings.key == key)
            .where(models.Settings.category == category)
        ).scalar_one_or_none()
    except:
        existing_setting = None
    
    if existing_setting is None:
        value = process_categories(default_settings, key, category)
        if value is None:
            log.write(msg="Error retrieving setting", extra_info=f"{category}.{key}", level=log.error)
            raise Exception(f"Unable to retrieve settings with key {key}")
    else:
        value = existing_setting.value
    return value

def elevate_existing_admins(new_level: int):
    if new_level <= g.settings["users"]["USER_LEVEL_ADMIN"]:
        raise ValueError("New level for admins is lower than the current level")
    existing_admins = db.session.execute(
        db.select(models.User)
        .where(models.User.level == g.settings["users"]["USER_LEVEL_ADMIN"])
    ).scalars().all()
    
    for admin in existing_admins:
        admin.level = new_level

def invalidate_summary_cache(commit: bool = True, just_meta: bool = False):
    # This function invalidates *all* summary caches, usually because benchmark data has been updated
    db.session.execute(db.delete(models.CacheMeta).where(models.CacheMeta.meta_type == "usage_summary"))
    if not just_meta:
        db.session.execute(db.delete(models.UtilityData))
    if commit:
        db.session.commit()

def invalidate_hc_cache(commit: bool = True, just_meta: bool = False):
    # This function invalidates *all* health check caches, usually because benchmark data has been updated
    db.session.execute(db.delete(models.CacheMeta).where(models.CacheMeta.meta_type == "health_check"))
    if not just_meta:
        db.session.execute(db.delete(models.HealthCheck))
    if commit:
        db.session.commit()

def process_metadata_update() -> bool:
    last_seen_id = "UNKNOWN BUILDING"
    with db.session.no_autoflush:
        try:
            buildings = pd.read_excel(metadata_file, sheet_name=g.settings["metadata"]["building_sheet"]["building_sheet"])
            seen_building_ids = []
            for _, row in buildings.iterrows():
                try:
                    data = process_building_row(row)
                except Exception as e:
                    log.write(msg="Error loading building from metadata file",
                            extra_info=f"{str(e)} | Last seen ID: {last_seen_id}",
                            level=log.warning,
                            commit=False)
                    continue
                last_seen_id = data["building_code"]
                
                existing_building = db.session.execute(
                    db.select(models.Building)
                    .where(models.Building.id == data["building_code"])
                ).scalar_one_or_none()
                if existing_building is None:
                    create_building_record(data)
                else:
                    log.write(msg=f"Modifying building record: {data['building_code']}", level=log.info, commit=False)
                    existing_building.update(data) # type: ignore
                
                seen_building_ids.append(data["building_code"])
            del buildings
            
            missing_buildings = db.session.execute(
                db.select(models.Building)
                .where(not_(models.Building.id.in_(seen_building_ids))) # type: ignore
            ).scalars().all()
            for building in missing_buildings:
                delete_building_record(building)

            meters = pd.read_excel(metadata_file, sheet_name=g.settings["metadata"]["meter_sheet"]["meter_sheet"])
            seen_meter_ids = []
            for _, row in meters.iterrows():
                try:
                    data = process_meter_row(row)
                except Exception as e:
                    log.write(msg="Error loading meter from metadata file",
                            extra_info=f"{str(e)} | Last seen ID: {last_seen_id}",
                            level=log.warning,
                            commit=False)
                    continue
                last_seen_id = data["meter_id"]
                
                try:
                    # Filter out meters with utility types that we don't support
                    if data["utility_type"] not in ["electricity", "gas", "heat", "water"]:
                        log.write(msg="Error loading meter from metadata file",
                                extra_info=f"Meter {data['meter_id']} is has an invalid utility type {data['utility_type']}",
                                level=log.warning,
                                commit=False)
                        continue
                except:
                    log.write(msg="Error loading meter from metadata file",
                            extra_info=f"Meter {data['meter_id']} is has an invalid utility type {data['utility_type']}",
                            level=log.warning,
                            commit=False)
                    continue
                
                existing_meter = db.session.execute(
                    db.select(models.Meter)
                    .where(models.Meter.id == data["meter_id"])
                ).scalar_one_or_none()
                if existing_meter is None:
                    create_meter_record(data)
                else:
                    log.write(msg=f"Modifying meter record: {data['meter_id']}", level=log.info, commit=False)
                    existing_meter.update(data) # type: ignore
                seen_meter_ids.append(data["meter_id"])
            del meters
            
            missing_meters = db.session.execute(
                db.select(models.Meter)
                .where(not_(models.Meter.id.in_(seen_meter_ids))) # type: ignore
            ).scalars().all()
            for meter in missing_meters:
                delete_meter_record(meter)
            
            invalidate_summary_cache(commit=False, just_meta=True)
            invalidate_hc_cache(commit=False, just_meta=True)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.write(msg="Error loading data from metadata file",
                    extra_info=f"Last seen ID: {last_seen_id} | {str(e)}",
                    level=log.error)
            return False
        return True

def clean_database_sessions():
    # Sessions are deleted after g.settings["server"]["session_timeout"] days
    
    expiry = dt.datetime.now() - dt.timedelta(days=g.settings["server"]["session_timeout"])
    
    db.session.execute(
        db.delete(models.Sessions)
        .where(models.Sessions.last_seen <= expiry)
    )
    db.session.commit()

def clean_database_login_codes():
    # Login codes are deleted after g.settings["server"]["login_code_timeout"] minutes
    
    expiry = dt.datetime.now() - dt.timedelta(minutes=g.settings["server"]["login_code_timeout"])
    
    db.session.execute(
        db.delete(models.LoginCode)
        .where(models.LoginCode.timestamp <= expiry)
    )
    db.session.commit()

def clean_database_logs():
    # Logs are deleted after:
    #  info - g.settings["server"]["log_info_expiry"] days
    #  warning - g.settings["server"]["log_warning_expiry"] days
    #  error - g.settings["server"]["log_error_expiry"] days
    #  critical - g.settings["server"]["log_critical_expiry"] days
    
    log_types = ["info", "warning", "error", "critical"]
    
    for log_type in log_types:
        expiry = dt.datetime.now() - dt.timedelta(days=g.settings["server"][f"log_{log_type}_expiry"])
        
        db.session.execute(
            db.delete(models.Log)
            .where(models.Log.level == log_type)
            .where(models.Log.timestamp <= expiry)
        )
    db.session.commit()
