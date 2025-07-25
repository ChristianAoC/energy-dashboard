const browserData = {};

let metaLabel = {
    "meter_id": "id",
    "building_id": "building_id",
    "utility_type": "utility_type",
    "description_short": "serving_revised",
    "description_long": "serving",
    "reading_type": "reading_type",
    "tenant": "tenant",
    "invoiced": "invoiced", // probably remove and only add/keep tenant
    "location": "meter_location",
    "main_meter": "main",
    "resolution": "resolution",
    "units": "units",
    "scaling_factor": "scaling_factor", // do we need this? should only be needed in API?

    "maze_map_label": "maze_map_label",
    "floor_area": "floor_area",
    "occupancy_type": "occupancy_type",
    "year_built": "year_built"
}

/*
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

var originalMasterList = [];
var narrowML = [];
if (typeof masterList !== 'undefined') {
    originalMasterList = masterList;
    narrowML = masterList;
}
*/

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

// A map of data keys to base endpoints
const apiEndpoints = {
    // Provides a list of meters for each health_score per building
    // params: to_time, from_time
    healthScore: '/api/health_score',

    // Simple static list of buildings as JSON hierarchy (formerly "masterlist" without usage)
    // no params
    hierarchy: '/api/meter_hierarchy',

    // Summary of usage as pet buildings and their main meters (formerly "masterlist" with usage)
    // params: to_time, from_time
    summary: '/api/summary',

    // Health check - detailed stats analysis for each meter (or one if ID given)
    // params: id, to_time, from_time, date_range
    meterHealth: '/api/meter_health',

    // Health check meta info
    // no params
    hcMeta: '/api/hc_meta',

    // Return time series data for given meter/time
    // params: id, to_time, from_time, format, aggregate, to_rate
    obs: '/api/meter_obs',

    // List of all meters (formerly "devices", endpoint to be renamed to /meters)
    // params: planon, uuid, lastobs
    meters: '/api/devices'
};

/**
 * Build a URL with query parameters from a base endpoint.
 * @param {string} baseUrl 
 * @param {Object} params (optional) key/value pairs
 */
function buildUrl(baseUrl, params = {}) {
    const url = new URL(baseUrl, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
    });
    return url.toString();
}

/**
 * Fetch multiple data keys, each optionally with params.
 * 
 * @param {Object} requests - e.g.
 *   {
 *     devices: true,
 *     masterlist: { from_time: '2024-01-01', to_time: '2024-01-31' },
 *     benchmarks: { category: 'A' }
 *   }
 */
async function getData(requests = {}, forceReload = false) {
    try {
        const keys = Object.keys(requests);
        const promises = keys.map(key => {
            const baseUrl = apiEndpoints[key];
            if (!baseUrl) throw new Error(`Unknown data key: ${key}`);

            const params = requests[key] === true ? {} : requests[key];
            let url = buildUrl(baseUrl, params);

            // optional cache-busting
            if (forceReload) {
                const sep = url.includes('?') ? '&' : '?';
                url += `${sep}_=${Date.now()}`;
            }

            return callApiJSON(url, false);
        });

        const results = await Promise.all(promises);

        // Build response object
        return keys.reduce((acc, key, idx) => {
            acc[key] = results[idx];
            return acc;
        }, {});
    } catch (err) {
        console.error('Error in getData', err);
        return {};
    }
};
