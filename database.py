from flask_sqlalchemy import SQLAlchemy

import os
import json

from constants import meters_file, buildings_file

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
    
    buildings = json.load(open(buildings_file))
    for building in buildings:
        new_building = models.Building(
            building["building_code"],
            building["building_name"],
            building["floor_area"],
            building["year_built"],
            building["usage"],
            building["maze_map_label"]
        )

        db.session.add(new_building)
        db.session.commit()

    meters = json.load(open(meters_file))
    for meter in meters:
        try:
            # Some entries in meters_all.json are broken - skip them
            if "Column10" in meter.keys():
                continue

            # We don't currently handle Oil meters
            if meter["meter_type"] == "Oil":
                continue

            new_meter = models.Meter(
                meter["meter_id_clean"],
                meter.get("raw_uuid", None), # If offline then there won't be a raw_uuid value - this should be handled elsewhere
                meter["serving_revised"], # Switched to serving_revised from meter_location
                meter["building_level_meter"],
                meter["meter_type"],
                meter["class"],
                meter["units_after_conversion"],
                meter["resolution"],
                meter["unit_conversion_factor"],
                meter.get("tenant", False), # Offline data doesn't specify tenant as those meters have been removed
                meter.get("building", None) # Allow unassigned meters
            )

            db.session.add(new_meter)
            db.session.commit()
        except Exception as e:
            print(e)
            print(meter)
    return True