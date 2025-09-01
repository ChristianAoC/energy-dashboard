from flask import request, g, current_app, has_app_context
from sqlalchemy import not_

import pandas as pd

from constants import metadata_file
from database import db, process_building_row, process_meter_row, create_building_record, create_meter_record, delete_building_record, delete_meter_record
import log
import models


default_settings = {
    # User levels
    "DEFAULT_USER_LEVEL": 1,
    "USER_LEVEL_VIEW_DASHBOARD": 0,
    "USER_LEVEL_VIEW_HEALTHCHECK": 1,
    "USER_LEVEL_VIEW_COMMENTS": 1,
    "USER_LEVEL_SUBMIT_COMMENTS": 1,
    "USER_LEVEL_EDIT_COMMENTS": 4,
    "USER_LEVEL_ADMIN": 5,
    # Mazemap info
    "MAZEMAP_CAMPUS_ID": 341,
    "MAZEMAP_LNG": "-2.780372",
    "MAZEMAP_LAT": "54.008809",
    # SMTP settings
    "SMTP_ENABLED": False,
    # Site info
    "SITE_NAME": "Energy Dashboard",
    "default_start_page": "browser",
    "default_daterange_benchmark": 365,
    "default_daterange_browser": 30,
    "default_daterange_health-check": 30,
    "capavis_url": "",
    "clustering_url": "",
    # Influx settings
    "data_interval": 60,
    # Data settings
    "offline_mode": True,
    "hc_update_time": 20,
    "cache_time_health_score": 365,
    "cache_time_summary": 30,
    "BACKGROUND_TASK_TIMING": "02:00",
    # Metadata settings
    "meter_sheet": "Energie points",
    "building_sheet": "Buildings",
    "data_start_time": None,
    "data_end_time": None,
    "data_interval": None,
    # Logging settings
    "log_level": log.warning
}

def load_settings():
    # I had an idea to implement a "lazy loading" system here but for now there isn't enough settings to require it.
    # May be worth looking into if the DB gets locked up
    
    # NOTE: When accessing g settings you should use `g.settings[key]` to raise an Exception (unless you can handle it locally)
    if request.path.startswith('/static'):
        return
    
    if 'settings' not in g:
        g.settings = {
            **default_settings,
            **{setting.key: setting.value for setting in db.session.execute(db.select(models.Settings)).scalars().all()}
        }

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
        
        obj.value = value
        obj.category = category
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get(key: str):
    try:
        statement = db.Select(models.Settings).where(models.Settings.key == key)
        if has_app_context():
            existing_setting = db.session.execute(statement).scalar_one_or_none()
        else:
            from app import app
            with app.app_context():
                existing_setting = db.session.execute(statement).scalar_one_or_none()
    except:
        existing_setting = None
    
    if existing_setting is None:
        value = default_settings.get(key)
        if value is None:
            log.write(msg="Error retrieving setting", extra_info=f"Key {key}", level=log.error)
            return None
    else:
        value = existing_setting.value
    return value

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
            buildings = pd.read_excel(metadata_file, sheet_name=g.settings["building_sheet"])
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
                last_seen_id = data["building_id"]
                
                with db.session.no_autoflush:
                    existing_building = db.session.execute(
                        db.select(models.Building)
                        .where(models.Building.id == data["building_id"])
                    ).scalar_one_or_none()
                    if existing_building is None:
                        create_building_record(data)
                    else:
                        log.write(msg=f"Modifying building record: {data['building_id']}", level=log.info, commit=False)
                        existing_building.update(data) # type: ignore
                
                seen_building_ids.append(data["building_id"])
            del buildings
            
            with db.session.no_autoflush:
                missing_buildings = db.session.execute(
                    db.select(models.Building)
                    .where(not_(models.Building.id.in_(seen_building_ids))) # type: ignore
                ).scalars().all()
                for building in missing_buildings:
                    delete_building_record(building)

            meters = pd.read_excel(metadata_file, sheet_name=g.settings["meter_sheet"])
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
                    # We don't currently handle Oil meters
                    if data["utility_type"] in ["Oil", "Spare"]:
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
                
                with db.session.no_autoflush:
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
            
            with db.session.no_autoflush:
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