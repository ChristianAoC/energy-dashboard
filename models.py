from database import db
from sqlalchemy import CheckConstraint
from api.helpers import data_cleaner


class Meter(db.Model):
    # ID is the meter_clean_id from the input data
    id = db.Column(db.String(30), primary_key=True)

    # Allowed to be null for offline data
    SEED_uuid = db.Column(db.String(36), unique=True)

    # Is name a required field? (not included in offline data)
    # Not unique as found some meter names in our dataset are duplicated
    name = db.Column(db.String(75), nullable=False)

    main = db.Column(db.Boolean, nullable=False, default=False)
    utility_type = db.Column(db.String(11),
                             CheckConstraint("utility_type IN ('gas', 'electricity', 'heat', 'water', 'weather')"),
                             nullable=False)
    reading_type = db.Column(db.String(10), CheckConstraint("reading_type IN ('cumulative', 'rate')"), nullable=False)
    units = db.Column(db.String(5), nullable=False)

    # Some of the resolutions in the dataset are null (and existing code handles these cases)
    resolution = db.Column(db.Float)

    scaling_factor = db.Column(db.Float, nullable=False, default=1)
    invoiced = db.Column(db.Boolean, nullable=False, default=False)
    building_id = db.Column(db.String, db.ForeignKey("building.id"), nullable=False)
    
    hc_record = db.relationship("HealthCheck", uselist=False, back_populates='meter')

    def __init__(self, meter_id_clean: str, raw_uuid: str, meter_name: str, building_level_meter: bool,
                 utility_type: str, reading_type: str, units: str, resolution: float, unit_conversion_factor: float,
                 tenant: bool, building: str):
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
        self.building_id = building

    def to_dict(self) -> dict:
        return {
            'meter_id': self.id,
            'SEED_uuid': self.SEED_uuid,
            'meter_name': self.name,
            'main': self.main,
            'utility_type': self.utility_type,
            'reading_type': self.reading_type,
            'units': self.units,
            'resolution': self.resolution,
            'scaling_factor': self.scaling_factor,
            'invoiced': self.invoiced,
            'building_id': self.building_id
        }
    
    def __repr__(self) -> str:
        return f"<Meter {self.id}>"

allowed_occupancy_types = ['sport', 'lecture theatre', 'library', 'catering', 'administration', 'academic bio', 'academic arts', 'academic physics', 'academic engineering', 'academic other', 'Residential', 'Non Res', 'Split Use']
occupancy_type_check_constraint = "occupancy_type IN ('" + "', '".join(allowed_occupancy_types) + "')"
class Building(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(75), nullable=False, unique=True)

    # Allowing null for now as some buildings don't have floor areas
    floor_area = db.Column(db.Integer)

    # Not a required field
    year_built = db.Column(db.Integer)
    
    occupancy_type = db.Column(db.String(11), CheckConstraint(occupancy_type_check_constraint), nullable=False)
    maze_map_label = db.Column(db.JSON)
    
    ud_record = db.relationship("UtilityData", uselist=False, back_populates='building')

    def __init__(self, building_code: str, building_name: str, floor_area: int, year_built: int, occupancy_type: str, maze_map_label: list):
        self.id = building_code
        self.name = building_name
        self.floor_area = floor_area
        self.year_built = year_built

        if occupancy_type == "Unknown" or occupancy_type is None or occupancy_type not in allowed_occupancy_types:
            occupancy_type = "academic other"
        self.occupancy_type = occupancy_type
        
        self.maze_map_label = maze_map_label

    def to_dict(self) -> dict:
        return {
            "building_id": self.id,
            "building_name": self.name,
            "floor_area": self.floor_area,
            "year_built": self.year_built,
            "occupancy_type": self.occupancy_type,
            "maze_map_label": self.maze_map_label
        }
    
    def __repr__(self) -> str:
        return f"<Building {self.id}>"

class HealthCheck(db.Model):
    meter_id = db.Column(db.String, db.ForeignKey("meter.id"), primary_key=True)

    # All of the following columns can be null
    count = db.Column(db.Integer)
    count_perc = db.Column(db.String(6))
    count_score = db.Column(db.Integer)
    zeroes = db.Column(db.Integer)
    zeroes_perc = db.Column(db.String(6))
    zeroes_score = db.Column(db.Integer)
    diff_neg = db.Column(db.Integer)
    diff_neg_perc = db.Column(db.String(6))
    diff_pos = db.Column(db.Integer)
    diff_pos_perc = db.Column(db.String(6))
    diff_pos_score = db.Column(db.Integer)
    diff_zero = db.Column(db.Integer)
    diff_zero_perc = db.Column(db.String(6))
    class_check = db.Column(db.String(20))
    functional_matrix = db.Column(db.Integer)
    mean = db.Column(db.Integer)
    median = db.Column(db.Integer)
    mode = db.Column(db.Integer)
    std = db.Column(db.Integer)
    min_value = db.Column(db.Integer)
    max_value = db.Column(db.Integer)
    outliers = db.Column(db.Integer)
    score = db.Column(db.Integer)
    outliers_perc = db.Column(db.String(6))
    outliers_ignz = db.Column(db.Integer)
    outliers_ignz_perc = db.Column(db.Integer)

    meter = db.relationship(Meter, back_populates="hc_record")

    def __init__(self, meter_id: str, hc_data: dict = {}):
        self.meter_id = meter_id
        self.count = hc_data.get("HC_count", None)
        self.count_score = hc_data.get("HC_count_score", None)
        self.zeroes = hc_data.get("HC_zeroes", None)
        self.zeroes_perc = hc_data.get("HC_zeroes_perc", None)
        self.zeroes_score = hc_data.get("HC_zeroes_score", None)
        self.diff_neg = hc_data.get("HC_diff_neg", None)
        self.diff_neg_perc  = hc_data.get("HC_diff_neg_perc", None)
        self.diff_pos = hc_data.get("HC_diff_pos", None)
        self.diff_pos_perc  = hc_data.get("HC_diff_pos_perc", None)
        self.diff_pos_score = hc_data.get("HC_diff_pos_score", None)
        self.diff_zero = hc_data.get("HC_diff_zero", None)
        self.diff_zero_perc = hc_data.get("HC_diff_zero_perc", None)
        self.class_check = hc_data.get("HC_class_check", None)
        self.functional_matrix = hc_data.get("HC_functional_matrix", None)
        self.mean = hc_data.get("HC_mean", None)
        self.median = hc_data.get("HC_median", None)
        self.mode = hc_data.get("HC_mode", None)
        self.std = hc_data.get("HC_std", None)
        self.min_value = hc_data.get("HC_min_value", None)
        self.max_value = hc_data.get("HC_max_value", None)
        self.outliers = hc_data.get("HC_outliers", None)
        self.score = hc_data.get("HC_score", None)
        self.outliers_ignz = hc_data.get("HC_outliers_ignz", None)
        self.outliers_ignz_perc = hc_data.get("HC_outliers_ignz_perc", None)

    def update(self, hc_data: dict):
        self.count = hc_data.get("count")
        self.count_score = hc_data.get("count_score")
        self.zeroes = hc_data.get("zeroes")
        self.zeroes_perc = hc_data.get("zeroes_perc")
        self.zeroes_score = hc_data.get("zeroes_score")
        self.diff_neg = hc_data.get("diff_neg")
        self.diff_neg_perc = hc_data.get("diff_neg_perc")
        self.diff_pos = hc_data.get("diff_pos")
        self.diff_pos_perc = hc_data.get("diff_pos_perc")
        self.diff_pos_score = hc_data.get("diff_pos_score")
        self.diff_zero = hc_data.get("diff_zero")
        self.diff_zero_perc = hc_data.get("diff_zero_perc")
        self.class_check = hc_data.get("class_check")
        self.functional_matrix = hc_data.get("functional_matrix")
        self.mean = hc_data.get("mean")
        self.median = hc_data.get("median")
        self.mode = hc_data.get("mode")
        self.std = hc_data.get("std")
        self.min_value = hc_data.get("min_value")
        self.max_value = hc_data.get("max_value")
        self.outliers = hc_data.get("outliers")
        self.score = hc_data.get("score")
        self.outliers_ignz = hc_data.get("outliers_ignz")
        self.outliers_ignz_perc = hc_data.get("outliers_ignz_per")

    def to_dict(self) -> dict:
        # Filter out SEED_UUID and invoiced
        keys = ["meter_id", "meter_name", "main", "utility_type", "reading_type", "units", "resolution", "scaling_factor", "building_id"]
        meter_dict: dict = data_cleaner(self.meter.to_dict(), keys) # type: ignore
        
        return {
            **meter_dict,
            "HC_count": self.count,
            "HC_count_score": self.count_score,
            "HC_zeroes": self.zeroes,
            "HC_zeroes_perc": self.zeroes_perc,
            "HC_zeroes_score": self.zeroes_score,
            "HC_diff_neg": self.diff_neg,
            "HC_diff_neg_perc": self.diff_neg_perc,
            "HC_diff_pos": self.diff_pos,
            "HC_diff_pos_perc": self.diff_pos_perc,
            "HC_diff_pos_score": self.diff_pos_score,
            "HC_diff_zero": self.diff_zero,
            "HC_diff_zero_perc": self.diff_zero_perc,
            "HC_class": meter_dict.get("reading_type", None),
            "HC_class_check": self.class_check,
            "HC_functional_matrix": self.functional_matrix,
            "HC_mean": self.mean,
            "HC_median": self.median,
            "HC_mode": self.mode,
            "HC_std": self.std,
            "HC_min_value": self.min_value,
            "HC_max_value": self.max_value,
            "HC_outliers": self.outliers,
            "HC_score": self.score,
            "HC_outliers_ignz": self.outliers_ignz,
            "HC_outliers_ignz_perc": self.outliers_ignz_perc
        }
    
    def __repr__(self) -> str:
        return f"<HealthCheck {self.meter_id}>"

class CacheMeta(db.Model):
    meta_type = db.Column(db.String, primary_key=True)
    # Could these be DateTime objects?
    to_time = db.Column(db.Float, nullable=False)
    from_time = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)
    processing_time = db.Column(db.Float, nullable=False)

    def __init__(self, meta_type: str, new_meta: dict):
        if meta_type not in ["health_check", "usage_summary"]:
            raise ValueError("Invalid meta type")

        self.meta_type = meta_type
        self.update(new_meta)

    def update(self, new_meta: dict):
        self.to_time = new_meta["to_time"]
        self.from_time = new_meta["from_time"]
        self.timestamp = new_meta["timestamp"]
        self.processing_time = new_meta["processing_time"]

    def to_dict(self) -> dict:
        return {
            "to_time": self.to_time,
            "from_time": self.from_time,
            "timestamp": self.timestamp,
            "processing_time": self.processing_time
        }

    def __repr__(self) -> str:
        return f"<CacheMeta {self.meta_type}>"

class UtilityData(db.Model):
    building_id = db.Column(db.String, db.ForeignKey("building.id"), primary_key=True)
    
    # Each utility json should look like this
    # {
    #     "meter_id": {
    #         "EUI": EUI,
    #         "consumption": consumption,
    #         "benchmark": {
    #             "good": good_benchmark,
    #             "typical": typical_benchmark
    #         }
    #     },
    #     ...
    # }
    electricity = db.Column(db.JSON)
    gas = db.Column(db.JSON)
    heat = db.Column(db.JSON)
    water = db.Column(db.JSON)
    
    building = db.relationship(Building, back_populates="ud_record")

    def __init__(self, building_id: str, electricity: dict, gas: dict, heat: dict, water: dict):
        self.building_id = building_id
        self.update(electricity, gas, heat, water)
    
    def _check_dict(self, dictionary: dict, require_benchmark=True) -> bool:
        if len(dictionary) == 0:
            return True # Allow empty data
        
        for meter in dictionary.values():
            if bool(meter.keys() - {"EUI", "consumption", "benchmark"}):
                return False

            if require_benchmark:
                if bool(meter["benchmark"].keys() - {"good", "typical"}):
                    return False
        
        return True
    
    def update(self, electricity: dict, gas: dict, heat: dict, water: dict):
        if not self._check_dict(electricity):
            raise ValueError("Invalid electricity data")
        if not self._check_dict(gas):
            raise ValueError("Invalid gas data")
        if not self._check_dict(heat):
            raise ValueError("Invalid heat data")
        if not self._check_dict(water, False):
            raise ValueError("Invalid water data")
        
        self.electricity = electricity
        self.gas = gas
        self.heat = heat
        self.water = water

    def to_dict(self) -> dict:
        # Filter out building id as the data is indexed with it
        keys = ["building_name", "floor_area", "year_built", "occupancy_type", "maze_map_label"]
        building_dict: dict = data_cleaner(self.building.to_dict(), keys) # type: ignore
        
        return {
            "meta": building_dict,
            "electricity": self.electricity,
            "gas": self.gas,
            "heat": self.heat,
            "water": self.water
        }
    
    def __repr__(self) -> str:
        return f"<UtilityData {self.building_id}>"