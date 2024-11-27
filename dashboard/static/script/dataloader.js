/*
if (typeof summaryCache !== 'undefined' && summaryCache.length > 50) {
    masterList = summaryCache;
}
*/

// variable names in API/JSON/CSV responses and files
var varNameDevSensorID = "meter_id_clean";
var varNameDevLastObs = "last_obs_time";
var varNameDevSensorType = "meter_type"; // gas heat water elec
var varNameDevSensorLocation = "meter_location"; // TODO not in anon
var varNameDevMeasuringLong = "serving"; // TODO not in anon (too long)
var varNameDevMeasuringShort = "serving_revised";
var varNameDevClass = "class"; // cumulative or rate
var varNameDevResolution = "resolution";
//var varNameDevUnits = "measured_units"; // this is converted in the API acc. to Paul, see below
var varNameDevUnits = "units_after_conversion";
var varNameDevTenantName = "tenant_name"; // TODO not in anon

  // those are new, should we add them to table?
var varNameDevInvoiced = "to_be_invoiced"; // TODO not in anon
var varNameDevMeterLevel = "meter_level";
//var varNameDevConfigCheckedDate = "config_checked_date";
var varNameDevBuildingLevelMeter = "building_level_meter";
var varNameDevBuilding = "building";
//var varNameDevAdjustmentFactor = "adjustment_factor";
var varNameDevParent = "parent"; // TODO not in anon
var varNameDevParentTwo = "parent2"; // TODO not in anon
var varNameDevRedundant = "redundant"; // TODO not in anon
var varNameDevTenant = "tenant"; // TODO not in anon
var varNameDevTenantID = "tenant_unit_id"; // TODO not in anon
var varNameDevUnitConversionFactor = "unit_conversion_factor";
//var varNameDevUnitsAfterConversion = "unit_after_conversion"; // Paul said this is actually the returned unit

// masterList variables
var varNameMLBuildingName = "building_name";
var varNameMLBuildingGroupName = "building_group_name"; // TODO not in anon
var varNameMLBuildingID = "building_code";
var varNameMLBuildingGroup = "building_group"; // TODO not in anon
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

// units for buildings/tabs overview since they're the same across all meters can't get from individual ML arrays
// needs plain units as alternative because Plotly can't parse HTML symbols in legend
var unitsCons = {
    "electricity" : "kWh",
    "gas" : "m&sup3;",
    "heat" : "MWh",
    "water" : "m&sup3;"
};
var unitsConsPlain = {
    "electricity" : "kWh",
    "gas" : "m3",
    "heat" : "MWh",
    "water" : "m3"
};
var unitsEUI = {
    "electricity" : "kWh/m&sup2;",
    "gas" : "m&sup3;/m&sup2;",
    "heat" : "MWh/m&sup2;",
    "water" : "m&sup3;/m&sup2;"
};
var unitsEUIPlain = {
    "electricity" : "kWh/m2",
    "gas" : "m3/m2",
    "heat" : "MWh/m2",
    "water" : "m3/m2"
};

function calcIntensity(cons, days, sqm, buildingID) {
    if (sqm == "") {
        for (m of masterList) {
            if (m[varNameMLBuildingID] == buildingID) {
                sqm = parseInt(m[varNameMLFloorSize]);
            }
        }
    }

    if (sqm == "" && buildingID == "") {
        return false;
    }

    let factor = 365/days;
    return Math.round( ( cons * factor ) / sqm );
}

var sizes;
var elecUse, gasUse, heatUse, waterUse;
var elecEUI, gasEUI, heatEUI, waterEUI;

function getSliderRanges() {
    sizes = masterList.map(x => parseInt(x[varNameMLFloorSize]));

    elecUse = masterList.map(x => Math.round(parseFloat(x["electricity"]["usage"]))).filter(x => x); // kWh
    gasUse = masterList.map(x => Math.round(parseFloat(x["gas"]["usage"]))).filter(x => x); // m3
    heatUse = masterList.map(x => Math.round(parseFloat(x["heat"]["usage"]))).filter(x => x); // m3
    waterUse = masterList.map(x => Math.round(parseFloat(x["water"]["usage"]))).filter(x => x); // m3

    elecEUI = masterList.map(x => parseFloat(x["electricity"]["eui_annual"])).filter(x => x);
    gasEUI = masterList.map(x => parseFloat(x["gas"]["eui_annual"])).filter(x => x);
    heatEUI = masterList.map(x => parseFloat(x["heat"]["eui_annual"])).filter(x => x);
    waterEUI = masterList.map(x => parseFloat(x["water"]["eui_annual"])).filter(x => x);

    setRanges(1, Math.min(...sizes), Math.max(...sizes));
    // TO-DO check which one is actually active on load/session
    setRanges(2, Math.min(...elecEUI), Math.max(...elecEUI));
    setRanges(3, Math.min(...elecUse), Math.max(...elecUse));
};

// need this frequently, strangely JS has no native function for this
function capFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
};

function uncapFirst(str) {
    return str.charAt(0).toLowerCase() + str.slice(1);
};

// function to call api for json. "forceReload=true" ignores cache
async function callApiJSON(uri, forceReload=false) {
    if (!forceReload)
    try {
        const response = await fetch(encodeURI(uri));
        if (response.ok) {
            try {
                const json = response.json();
                return json;
            } catch {
                console.error('Could not convert response to proper JSON');
            }
        } else {
            console.error('Promise resolved but HTTP status failed');
        }
    } catch {
    console.error('Promise rejected');
    }
};

function addMasterListBenchmarks() {
    var benchmarksCibse = benchmarksCibseFile;
    for (m of masterList) {
        if (!["Residential", "Split Use", "Non Res"].includes(m["usage"])) { continue; }
        m["electricity"]["bm_good"] = benchmarksCibse[m["usage"]]["electricity"]["good"];
        m["electricity"]["bm_typical"] = benchmarksCibse[m["usage"]]["electricity"]["typical"];
        m["gas"]["bm_good"] = benchmarksCibse[m["usage"]]["fossil"]["good"];
        m["gas"]["bm_typical"] = benchmarksCibse[m["usage"]]["fossil"]["typical"];
        m["heat"]["bm_good"] = benchmarksCibse[m["usage"]]["fossil"]["good"];
        m["heat"]["bm_typical"] = benchmarksCibse[m["usage"]]["fossil"]["typical"];
    }
};
