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
            building_code = row[building_mappings["building_code"]]
            if pd.isna(building_code) or building_code is None:
                continue
            
            maze_map_label_raw = row[building_mappings["maze_map_label"]]
            maze_map_label = []
            if not pd.isna(maze_map_label_raw) and maze_map_label_raw is not None:
                values = str(maze_map_label_raw).split(';')
                for v in values:
                    try:
                        num = int(v.strip())
                        maze_map_label.append(num)
                    except ValueError:
                        continue
            
            new_building = models.Building(
                building_code,
                row[building_mappings["building_name"]],
                row[building_mappings["floor_area"]],
                row[building_mappings["year_built"]],
                row[building_mappings["usage"]],
                maze_map_label
            )
            db.session.add(new_building)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            continue
    
    meters = pd.read_excel(metadata_file, sheet_name=meter_sheet)
    meter_mappings = {
        "meter_id_clean": "meter_id_clean2",
        "raw_uuid": "SEED_uuid",
        "serving_revised": "serving_revised",
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
            if row[meter_mappings["meter_type"]] == "Oil":
                continue
            
            building_level_meter_raw = row[meter_mappings["building_level_meter"]]
            building_level_meter = False
            if not pd.isna(building_level_meter_raw) and building_level_meter_raw is not None:
                if str(building_level_meter_raw).lower() in ["yes", "1", "y", "true"]:
                    building_level_meter = True
            
            reading_type_raw = row[meter_mappings["reading_type"]]
            if pd.isna(reading_type_raw) or reading_type_raw is None:
                continue
            reading_type = str(reading_type_raw).lower()
            if reading_type not in ["cumulative", "rate"]:
                continue
            
            unit_conversion_factor_raw = row[meter_mappings["unit_conversion_factor"]]
            if pd.isna(unit_conversion_factor_raw) or unit_conversion_factor_raw is None:
                continue
            unit_conversion_factor = float(unit_conversion_factor_raw)
            
            new_meter = models.Meter(
                row[meter_mappings["meter_id_clean"]],
                row[meter_mappings["raw_uuid"]],
                row[meter_mappings["serving_revised"]],
                building_level_meter,
                row[meter_mappings["meter_type"]],
                reading_type,
                row[meter_mappings["units_after_conversion"]],
                row[meter_mappings["resolution"]],
                unit_conversion_factor,
                # Offline data doesn't specify tenant as those meters have been removed
                row[meter_mappings["tenant"]] if pd.notnull(row[meter_mappings["tenant"]]) else False,
                row[meter_mappings["building"]]
            )
            db.session.add(new_meter)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            continue
    return True