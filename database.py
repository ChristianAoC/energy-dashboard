from flask import g
from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv
import os
import pandas as pd
import sys

from constants import metadata_file

db = SQLAlchemy(engine_options={
    "pool_size": 20,
    "max_overflow": 20
})

def init(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'data.sqlite')}"
    db.init_app(app)

    with app.app_context():
        db.create_all()

        try:
            initialise_settings_table(True)
        except:
            print("\n" + "="*20)
            print("\tERROR: Failed to initialise settings table!")
            print("\tThis could be because:")
            print("="*20 + "\n")
            sys.exit(1)

def load_settings_from_env(from_env: bool = True) -> dict:
    from api.settings import default_settings
    result = {**default_settings}
    
    if from_env:
        load_dotenv()
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
        result["offline_mode"] = offlineMode
        result["InfluxURL"] = InfluxURL
        result["InfluxPort"] = InfluxPort
        result["InfluxUser"] = InfluxUser
        result["InfluxPass"] = InfluxPass
        
        result["hc_update_time"] = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", default_settings["hc_update_time"]))
        result["cache_time_health_score"] = int(os.getenv("HEALTH_SCORE_CACHE_TIME",
                                                          default_settings["cache_time_health_score"]))
        result["cache_time_summary"] = int(os.getenv("SUMMARY_CACHE_TIME", default_settings["cache_time_summary"]))
        
        result["log_level"] = os.getenv("LOG_LEVEL", default_settings["log_level"])
        
        result["SITE_NAME"] = os.getenv("SITE_NAME", default_settings["SITE_NAME"])
        
        result["MAZEMAP_CAMPUS_ID"] = int(os.getenv("MAZEMAP_CAMPUS_ID", default_settings["MAZEMAP_CAMPUS_ID"]))
        result["MAZEMAP_LNG"] = os.getenv("MAZEMAP_LNG", default_settings["MAZEMAP_LNG"])
        result["MAZEMAP_LAT"] = os.getenv("MAZEMAP_LAT", default_settings["MAZEMAP_LAT"])
        
        SMTP_ADDRESS = os.getenv("SMTP_ADDRESS")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = os.getenv("SMTP_PORT")
        
        val = os.getenv("SMTP_ENABLED", "False")
        SMTP_ENABLED = val.strip().lower() in ("1", "true", "yes", "on")
        
        if SMTP_ADDRESS is None or SMTP_PASSWORD is None or SMTP_SERVER is None or SMTP_PORT is None:
            SMTP_ADDRESS = None
            SMTP_PASSWORD = None
            SMTP_SERVER = None
            SMTP_PORT = None
            SMTP_ENABLED = False
        result["SMTP_ENABLED"] = SMTP_ENABLED
        result["SMTP_ADDRESS"] = SMTP_ADDRESS
        result["SMTP_PASSWORD"] = SMTP_PASSWORD
        result["SMTP_SERVER"] = SMTP_SERVER
        result["SMTP_PORT"] = SMTP_PORT
        
        result["REQUIRED_EMAIL_DOMAINS"] = os.getenv("REQUIRED_EMAIL_DOMAINS", "")
        result["DEMO_EMAIL_DOMAINS"] = os.getenv("DEMO_EMAIL_DOMAINS", "")
        
        result["DEFAULT_USER_LEVEL"] = int(os.getenv("DEFAULT_USER_LEVEL", default_settings["DEFAULT_USER_LEVEL"]))
        result["USER_LEVEL_VIEW_DASHBOARD"] = int(os.getenv("USER_LEVEL_VIEW_DASHBOARD",
                                                            default_settings["USER_LEVEL_VIEW_DASHBOARD"]))
        result["USER_LEVEL_VIEW_HEALTHCHECK"] = int(os.getenv("USER_LEVEL_VIEW_HEALTHCHECK",
                                                              default_settings["USER_LEVEL_VIEW_HEALTHCHECK"]))
        result["USER_LEVEL_VIEW_COMMENTS"] = int(os.getenv("USER_LEVEL_VIEW_COMMENTS",
                                                           default_settings["USER_LEVEL_VIEW_COMMENTS"]))
        result["USER_LEVEL_SUBMIT_COMMENTS"] = int(os.getenv("USER_LEVEL_SUBMIT_COMMENTS",
                                                             default_settings["USER_LEVEL_SUBMIT_COMMENTS"]))
        result["USER_LEVEL_EDIT_COMMENTS"] = int(os.getenv("USER_LEVEL_EDIT_COMMENTS",
                                                           default_settings["USER_LEVEL_EDIT_COMMENTS"]))
        result["USER_LEVEL_ADMIN"] = int(os.getenv("USER_LEVEL_ADMIN", default_settings["USER_LEVEL_ADMIN"]))
        
        result["BACKGROUND_TASK_TIMING"] = os.getenv("BACKGROUND_TASK_TIMING",
                                                     default_settings["BACKGROUND_TASK_TIMING"])
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
            value=temp_default_settings["DEFAULT_USER_LEVEL"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_DASHBOARD",
            value=temp_default_settings["USER_LEVEL_VIEW_DASHBOARD"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_HEALTHCHECK",
            value=temp_default_settings["USER_LEVEL_VIEW_HEALTHCHECK"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_VIEW_COMMENTS",
            value=temp_default_settings["USER_LEVEL_VIEW_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_SUBMIT_COMMENTS",
            value=temp_default_settings["USER_LEVEL_SUBMIT_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_EDIT_COMMENTS",
            value=temp_default_settings["USER_LEVEL_EDIT_COMMENTS"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="USER_LEVEL_ADMIN",
            value=temp_default_settings["USER_LEVEL_ADMIN"],
            category="users",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="REQUIRED_EMAIL_DOMAINS",
            value=temp_default_settings["REQUIRED_EMAIL_DOMAINS"],
            category="users",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="DEMO_EMAIL_DOMAINS",
            value=temp_default_settings["DEMO_EMAIL_DOMAINS"],
            category="users",
            setting_type="str"
        ))
        
        # Mazemap info
        settings.append(models.Settings(
            key="MAZEMAP_CAMPUS_ID",
            value=temp_default_settings["MAZEMAP_CAMPUS_ID"],
            category="mazemap",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="MAZEMAP_LNG",
            value=temp_default_settings["MAZEMAP_LNG"],
            category="mazemap",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="MAZEMAP_LAT",
            value=temp_default_settings["MAZEMAP_LAT"],
            category="mazemap",
            setting_type="str"
        ))

        # SMTP
        settings.append(models.Settings(
            key="SMTP_ENABLED",
            value=temp_default_settings["SMTP_ENABLED"],
            category="smtp",
            setting_type="bool"
        ))
        settings.append(models.Settings(
            key="SMTP_ADDRESS",
            value=temp_default_settings["SMTP_ADDRESS"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_PASSWORD",
            value=temp_default_settings["SMTP_PASSWORD"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_SERVER",
            value=temp_default_settings["SMTP_SERVER"],
            category="smtp",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="SMTP_PORT",
            value=temp_default_settings["SMTP_PORT"],
            category="smtp",
            setting_type="str"
        ))
        
        # Site info
        settings.append(models.Settings(
            key="SITE_NAME",
            value=temp_default_settings["SITE_NAME"],
            category="site",
            setting_type="str"
        ))
        
        # Data
        settings.append(models.Settings(
            key="offline_mode",
            value=temp_default_settings["offline_mode"],
            category="data",
            setting_type="bool"
        ))
        settings.append(models.Settings(
            key="hc_update_time",
            value=temp_default_settings["hc_update_time"],
            category="data",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="cache_time_health_score",
            value=temp_default_settings["cache_time_health_score"],
            category="data",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="cache_time_summary",
            value=temp_default_settings["cache_time_summary"],
            category="data",
            setting_type="int"
        ))
        settings.append(models.Settings(
            key="BACKGROUND_TASK_TIMING",
            value=temp_default_settings["BACKGROUND_TASK_TIMING"],
            category="data",
            setting_type="str"
        ))
        
        # Metadata
        settings.append(models.Settings(
            key="meter_sheet",
            value=temp_default_settings["meter_sheet"],
            category="metadata",
            setting_type="str"
        ))
        settings.append(models.Settings(
            key="building_sheet",
            value=temp_default_settings["building_sheet"],
            category="metadata",
            setting_type="str"
        ))
        
        # Logging
        settings.append(models.Settings(
            key="log_level",
            value=temp_default_settings["log_level"],
            category="logging",
            setting_type="str"
        ))
        
        db.session.add_all(settings)
        
        db.session.commit()
        return True
    except Exception as e:
        log.write(msg="Error initialising settings table", extra_info=str(e), level=log.critical)
        db.session.rollback()
        raise Exception("Error initialising settings table")

def initial_database_population() -> bool:
    # Import here to stop circular import issue
    import models
    import log
    
    if len(db.session.execute(db.select(models.Meter)).scalars().all()) > 0:
        return False
    
    if len(db.session.execute(db.select(models.Building)).scalars().all()) > 0:
        return False
    
    buildings = pd.read_excel(metadata_file, sheet_name=g.settings["building_sheet"])
    building_mappings = {
        "building_code": "Property code",
        "building_name": "Building Name",
        "floor_area": "floor_area",
        "year_built": "Year",
        "usage": "Function",
        "maze_map_label": "mazemap_ids"
    }
    for _, row in buildings.iterrows():
        try:
            meter_id_clean = row[building_mappings["building_code"]]
            if pd.isna(meter_id_clean) or meter_id_clean is None:
                continue
            
            floor_area_raw = row[building_mappings["floor_area"]]
            floor_area = None
            if not pd.isna(floor_area_raw) and floor_area_raw is not None:
                floor_area = int(floor_area_raw)
            
            year_built_raw = row[building_mappings["year_built"]]
            year_built = None
            if not pd.isna(year_built_raw) and year_built_raw is not None:
                year_built = int(year_built_raw)
            
            usage_raw = row[building_mappings["usage"]]
            if pd.isna(meter_id_clean) or meter_id_clean is None:
                continue
            usage = str(usage_raw).strip()
            
            maze_map_label_raw = row[building_mappings["maze_map_label"]]
            maze_map_label = []
            if not pd.isna(maze_map_label_raw) and maze_map_label_raw is not None:
                values = str(maze_map_label_raw).split(';')
                for v in values:
                    try:
                        maze_map_label.append(int(v))
                    except ValueError:
                        continue
            
            new_building = models.Building(
                meter_id_clean.strip(),
                row[building_mappings["building_name"]].strip(),
                floor_area,
                year_built,
                usage,
                maze_map_label
            )
            db.session.add(new_building)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            log.write(msg="Error loading building from metadata file", extra_info=str(e), level=log.warning)
            continue
    
    meters = pd.read_excel(metadata_file, sheet_name=g.settings["meter_sheet"])
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
    for _, row in meters.iterrows():
        try:
            # We don't currently handle Oil meters
            if row[meter_mappings["meter_type"]] in ["Oil", "Spare"]:
                continue
            
            meter_id_clean_raw = row[meter_mappings["meter_id_clean"]]
            if pd.isna(meter_id_clean_raw) or meter_id_clean_raw is None:
                continue
            meter_id_clean = str(meter_id_clean_raw).strip()
            
            raw_uuid_raw = row[meter_mappings["raw_uuid"]]
            raw_uuid = None
            if not pd.isna(raw_uuid_raw) and raw_uuid_raw is not None:
                raw_uuid = str(raw_uuid_raw).strip()
            
            building_level_meter_raw = row[meter_mappings["building_level_meter"]]
            building_level_meter = False
            if not pd.isna(building_level_meter_raw) and building_level_meter_raw is not None:
                if str(building_level_meter_raw).strip().lower() in ["yes", "1", "y", "true"]:
                    building_level_meter = True
            
            tenant_raw = row[meter_mappings["tenant"]]
            tenant = False
            if not pd.isna(tenant_raw) and tenant_raw is not None:
                if str(tenant_raw).strip().lower() in ["yes", "1", "y", "true"]:
                    tenant = True
            
            reading_type_raw = row[meter_mappings["reading_type"]]
            if pd.isna(reading_type_raw) or reading_type_raw is None:
                continue
            reading_type = str(reading_type_raw).strip().lower()
            if reading_type not in ["cumulative", "rate"]:
                continue
            
            resolution_raw = row[meter_mappings["resolution"]]
            if pd.isna(resolution_raw) or resolution_raw is None:
                continue
            resolution = float(resolution_raw)
            
            unit_conversion_factor_raw = row[meter_mappings["unit_conversion_factor"]]
            if pd.isna(unit_conversion_factor_raw) or unit_conversion_factor_raw is None:
                continue
            unit_conversion_factor = float(unit_conversion_factor_raw)

            new_meter = models.Meter(
                meter_id_clean,
                raw_uuid,
                row[meter_mappings["description"]].strip(),
                building_level_meter,
                row[meter_mappings["meter_type"]].strip(),
                reading_type,
                row[meter_mappings["units_after_conversion"]].strip(),
                resolution,
                unit_conversion_factor,
                tenant,
                row[meter_mappings["building"]]
            )
            db.session.add(new_meter)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            log.write(msg="Error loading meter from metadata file", extra_info=str(e), level=log.warning)
            continue
    return True