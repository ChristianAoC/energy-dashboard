from flask_sqlalchemy import SQLAlchemy

import os
import pandas as pd

from constants import metadata_file, meter_sheet, building_sheet

db = SQLAlchemy()

def init(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'data.sqlite')}"
    db.init_app(app)

    with app.app_context():
        db.create_all()

def initial_database_population() -> bool:
    # Import here to stop circular import issue
    import models
    import log
    
    if len(db.session.execute(db.select(models.Meter)).scalars().all()) > 0:
        return False
    
    if len(db.session.execute(db.select(models.Building)).scalars().all()) > 0:
        return False
    
    buildings = pd.read_excel(metadata_file, sheet_name=building_sheet)
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
    
    meters = pd.read_excel(metadata_file, sheet_name=meter_sheet)
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