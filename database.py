from flask import g

import os
import pandas as pd

from constants import metadata_file, offline_data_files
import models
from models import db
import log


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