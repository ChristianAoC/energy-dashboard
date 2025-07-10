/*
if (typeof summaryCache !== 'undefined' && summaryCache.length > 50) {
    masterList = summaryCache;
}
*/

// variable names in API/JSON/CSV responses and files
var varNameDevSensorID = "meter_id_clean";
var varNameDevLastObs = "last_obs_time";
var varNameDevSensorType = "meter_type"; // gas heat water elec
var varNameDevSensorLocation = "meter_location"; // not in anon
var varNameDevMeasuringLong = "serving"; // not in anon (too long)
var varNameDevMeasuringShort = "serving_revised";
var varNameDevClass = "class"; // cumulative or rate
var varNameDevResolution = "resolution";
//var varNameDevUnits = "measured_units"; // this is converted in the API acc. to Paul, see below
var varNameDevUnits = "units_after_conversion";
var varNameDevTenantName = "tenant_name"; // not in anon

  // those are new, should we add them to table?
var varNameDevInvoiced = "to_be_invoiced"; // not in anon
var varNameDevMeterLevel = "meter_level";
//var varNameDevConfigCheckedDate = "config_checked_date";
var varNameDevBuildingLevelMeter = "building_level_meter";
var varNameDevBuilding = "building";
//var varNameDevAdjustmentFactor = "adjustment_factor";
var varNameDevParent = "parent"; // not in anon
var varNameDevParentTwo = "parent2"; // not in anon
var varNameDevRedundant = "redundant"; // not in anon
var varNameDevTenant = "tenant"; // not in anon
var varNameDevTenantID = "tenant_unit_id"; // not in anon
var varNameDevUnitConversionFactor = "unit_conversion_factor";
//var varNameDevUnitsAfterConversion = "unit_after_conversion"; // Paul said this is actually the returned unit

// masterList variables
var varNameMLBuildingName = "building_name";
var varNameMLBuildingGroupName = "building_group_name"; // not in anon
var varNameMLBuildingID = "building_code";
var varNameMLBuildingGroup = "building_group"; // not in anon
var varNameMLMazeMapID = "maze_map_label";
var varNameMLFloorSize = "floor_area";
var varNameMLUsage = "usage"; // (this is residential/non-res etc)
var varNameMLYearBuilt = "year_built";

var originalMasterList = [];
var narrowML = [];
if (typeof masterList !== 'undefined') {
    originalMasterList = masterList;
    narrowML = masterList;
}

// need this frequently, strangely JS has no native function for this
function capFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
};

function uncapFirst(str) {
    return str.charAt(0).toLowerCase() + str.slice(1);
};

// function to call api for json.
async function callApiJSON(uri) {
   try {
        let url = encodeURI(uri);
        const response = await fetch(url, { /* headers */});

        if (!response.ok) {
            console.error(`HTTP error ${response.status} for ${url}`);
            return null;
        }

        const json = await response.json();
        return json;
    } catch (err) {
        console.error('Failed fetching ${uri}:', err);
        return null;
    }
};

// data loader to call required JSON objects for a given page
async function getCommonData() {
    try {
        const [
            // TODO add here later: scoreSummary and usage
            devices,
            masterlist,
            summary
        ] = await Promise.all([
            callApiJSON('/api/devices'),
            callApiJSON('/api/usageoffline'),
            callApiJSON('/api/summary')
        ]);

        return {
            devices,
            masterlist,
            summary
        };
    } catch (err) {
        console.error("Error loading common data", err);
        return {};
    }
}
