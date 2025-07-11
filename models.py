from database import db
from sqlalchemy import CheckConstraint

class Meter(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    SEED_uuid = db.Column(db.String(36), unique=True) # Allowed to be null for offline data
    name = db.Column(db.String(75), nullable=False, unique=True)
    main = db.Column(db.Boolean, nullable=False, default=False)
    utility_type = db.Column(db.String(11), CheckConstraint("utility_type IN ('gas', 'electricity', 'heat', 'water')"), nullable=False)
    reading_type = db.Column(db.String(10), CheckConstraint("reading_type IN ('cumulative', 'rate')"), nullable=False)
    units = db.Column(db.String(5), nullable=False)
    resolution = db.Column(db.Float, nullable=False)
    scaling_factor = db.Column(db.Float, nullable=False, default=1)
    invoiced = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, meter_id_clean: str, raw_uuid: str, meter_name: str, building_level_meter: bool, utility_type: str, reading_type: str, units: str, resolution: float, unit_conversion_factor: float, tenant: bool):
        self.id = meter_id_clean
        self.SEED_uuid = raw_uuid
        self.name = meter_name
        self.main = building_level_meter
        self.utility_type = utility_type.lower()
        self.reading_type = reading_type.lower()
        self.units = units
        self.resolution = resolution
        self.scaling_factor = unit_conversion_factor
        self.invoiced = tenant

class Building(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(75), nullable=False, unique=True)
    floor_area = db.Column(db.Integer) # Allowing null for now as some buildings don't have floor areas
    year_built = db.Column(db.Integer) # Not a required
    occupancy_type = db.Column(db.String(11), CheckConstraint("occupancy_type IN ('Non Res', 'Residential', 'Split Use')"), nullable=False)

    def __init__(self, building_code: str, building_name: str, floor_area: int, year_built: int, occupancy_type: str):
        self.id = building_code
        self.name = building_name
        self.floor_area = floor_area
        self.year_built = year_built
        self.occupancy_type = occupancy_type

class BuildingMeterRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_id = db.Column(db.String, db.ForeignKey("building.id"), nullable=False)
    meter_id = db.Column(db.String, db.ForeignKey("meter.id"), nullable=False)

    def __init__(self, building_id: str, meter_id: str):
        self.building_id = building_id
        self.meter_id = meter_id
