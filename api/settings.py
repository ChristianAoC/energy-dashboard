from flask import request, g, current_app

from database import db
import log
import models


default_settings = {
    # User levels
    "DEFAULT_USER_LEVEL": 3,
    "USER_LEVEL_VIEW_DASHBOARD": 1,
    "USER_LEVEL_VIEW_HEALTHCHECK": 1,
    "USER_LEVEL_VIEW_COMMENTS": 1,
    "USER_LEVEL_SUBMIT_COMMENTS": 3,
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
    # Data settings
    "offline_mode": True,
    "hc_update_time": 9,
    "cache_time_health_score": 365,
    "cache_time_summary": 30,
    "BACKGROUND_TASK_TIMING": "02:00",
    "meter_sheet": "Energie points",
    "building_sheet": "Buildings",
    # "log_level": log.warning
    "log_level": log.info
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
            raise TypeError

        if obj.key == "offline_mode":
            current_app.config["offline_mode"]
        
        obj.value = value
        obj.category = category
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get(key: str):
    existing_setting = db.session.execute(
        db.Select(models.Settings)
        .where(models.Settings.key == key)
    ).scalar_one_or_none()
    if existing_setting is None:
        value = default_settings.get(key)
        if value is None:
            log.write(msg="Error retrieving setting", extra_info=f"Key {key}", level=log.error)
            return None
    else:
        value = existing_setting.value
    return value