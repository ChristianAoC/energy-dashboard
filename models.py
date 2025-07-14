from database import db
from sqlalchemy import CheckConstraint


class Meter(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    SEED_uuid = db.Column(db.String(36), unique=True) # Allowed to be null for offline data

    # Is name a required field? (not included in offline data)
    # Not unique as found some meter names in our dataset are duplicated
    name = db.Column(db.String(75), nullable=False)

    main = db.Column(db.Boolean, nullable=False, default=False)
    utility_type = db.Column(db.String(11), CheckConstraint("utility_type IN ('gas', 'electricity', 'heat', 'water', 'weather')"), nullable=False)
    reading_type = db.Column(db.String(10), CheckConstraint("reading_type IN ('cumulative', 'rate')"), nullable=False)
    units = db.Column(db.String(5), nullable=False)
    resolution = db.Column(db.Float) # Some of the resolutions in the dataset are null (and existing code handles these cases)
    scaling_factor = db.Column(db.Float, nullable=False, default=1)
    invoiced = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, meter_id_clean: str, raw_uuid: str, meter_name: str, building_level_meter: bool, utility_type: str, reading_type: str, units: str, resolution: float, unit_conversion_factor: float, tenant: bool):
        self.id = meter_id_clean
        self.SEED_uuid = raw_uuid
        self.name = meter_name
        self.main = building_level_meter
        self.utility_type = utility_type.lower()

        reading_type = reading_type.lower()
        # Existing code assumes rate meter if not explicitly set to "cumulative"
        if reading_type != "cumulative":
            reading_type = "rate"

        self.reading_type = reading_type
        self.units = units
        self.resolution = resolution
        self.scaling_factor = unit_conversion_factor
        self.invoiced = tenant


occupancy_type_check_constraint = "occupancy_type IN ('sport', 'lecture theatre', 'library', 'catering', 'administration', 'academic bio', 'academic arts', 'academic physics', 'academic engineering', 'academic other', 'Residential', 'Non Res', 'Split Use')"

class Building(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(75), nullable=False, unique=True)
    floor_area = db.Column(db.Integer) # Allowing null for now as some buildings don't have floor areas
    year_built = db.Column(db.Integer) # Not a required
    occupancy_type = db.Column(db.String(11), CheckConstraint(occupancy_type_check_constraint), nullable=False)

    def __init__(self, building_code: str, building_name: str, floor_area: int, year_built: int, occupancy_type: str):
        self.id = building_code
        self.name = building_name
        self.floor_area = floor_area
        self.year_built = year_built
        if occupancy_type == "Unknown":
            occupancy_type = "academic other"
        self.occupancy_type = occupancy_type

class BuildingMeterRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_id = db.Column(db.String, db.ForeignKey("building.id"), nullable=False)
    meter_id = db.Column(db.String, db.ForeignKey("meter.id"), nullable=False)

    def __init__(self, building_id: str, meter_id: str):
        self.building_id = building_id
        self.meter_id = meter_id
