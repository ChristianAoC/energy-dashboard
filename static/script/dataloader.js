const browserData = {};
const utilityTypes = ["gas", "electricity", "heat", "water"];
const utilityUnits = {"gas": "m³", "electricity": "kWh", "heat": "MWh", "water": "m³"};

let metaLabel = {

    // metadata from meters list
    "meter_id": "meter_id",
    "building_id": "building_id", // also used in hierarchy/building list
    "utility_type": "utility_type",
    "description": "meter_name", // replace with long description? our own?
    "reading_type": "reading_type",
    //"tenant": "tenant", currently NYI
    "invoiced": "invoiced", // use this or tenant to filter?
    //"location": "meter_location", currently NYI
    "main_meter": "main",
    "resolution": "resolution",
    "units": "units",
    "scaling_factor": "scaling_factor", // do we need this? should only be needed in API?

    // metadata from buildings list/hierarchy
    "maze_map_label": "maze_map_label",
    "floor_area": "floor_area",
    "building_name": "building_name",
    "occupancy_type": "occupancy_type",
    "year_built": "year_built",

    // metadata in summary
    "EUI": "EUI",
    "consumption": "consumption",

    // health check specific labels
    "HC_class": "HC_class",
    "HC_class_check": "HC_class_check",
    "HC_count": "HC_count",
    "HC_count_score": "HC_count_score",
    "HC_diff_neg": "HC_diff_neg",
    "HC_diff_neg_perc": "HC_diff_neg_perc",
    "HC_diff_pos": "HC_diff_pos",
    "HC_diff_pos_perc": "HC_diff_pos_perc",
    "HC_diff_pos_score": "HC_diff_pos_score",
    "HC_diff_zero": "HC_diff_zero",
    "HC_diff_zero_perc": "HC_diff_zero_perc",
    "HC_functional_matrix": "HC_functional_matrix",
    "HC_max_value": "HC_max_value",
    "HC_mean": "HC_mean",
    "HC_median": "HC_median",
    "HC_min_value": "HC_min_value",
    "HC_mode": "HC_mode",
    "HC_outliers": "HC_outliers",
    "HC_outliers_ignz": "HC_outliers_ignz",
    "HC_outliers_ignz_perc": "HC_outliers_ignz_perc",
    "HC_score": "HC_score",
    "HC_std": "HC_std",
    "HC_zeroes": "HC_zeroes",
    "HC_zeroes_perc": "HC_zeroes_perc",
    "HC_zeroes_score": "HC_zeroes_score"
}

// A map of data keys to base endpoints
const apiEndpoints = {
    // List of all meters (formerly "devices")
    // no params
    meters: '/api/meters',

    // Simple static list of buildings as JSON hierarchy (formerly "masterlist" without usage)
    // no params
    hierarchy: '/api/meter_hierarchy',
    
    // Summary of usage as pet buildings and their main meters (formerly "masterlist" with usage)
    // params: to_time, from_time
    summary: '/api/summary',

    // Mazemap polygons
    // noaparms
    mazemap_polygons: '/api/mazemap_polygons',

    // Provides a list of meters for each health_score per building
    // params: to_time, from_time
    healthScore: '/api/health_score',

    // Health check - detailed stats analysis for each meter (or one if ID given)
    // params: id, to_time, from_time, date_range
    meterHealth: '/api/meter_health',

    // Health check meta info
    // no params
    hcMeta: '/api/hc_meta',

    // Returns first and last date for offline data and interval
    // no params
    offlineMeta: '/api/offline_meta',
    
    // Return time series data for given meter/time
    // params: id, to_time, from_time, format, aggregate, to_rate
    obs: '/api/meter_obs',

    // Gets all context entries
    // noparams
    getcontext: '/getcontext',

    // get user level
    // params: email, SessionID
    userLevel: '/get_user_level'
};

// need this frequently, strangely JS has no native function for this
function capFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
};

function uncapFirst(str) {
    return str.charAt(0).toLowerCase() + str.slice(1);
};

// sometimes i need only the raw list of meters from hierarchy
function getMeterListFromHierarchy(hierarchy, buildingFilter = null) {
    const meterIds = [];
    for (const buildingId in hierarchy) {
        // If filtering by building, skip others
        if (buildingFilter && buildingId !== buildingFilter) continue;

        const building = hierarchy[buildingId];
        for (const utilType of Object.keys(building)) {
            if (utilType === 'meta') continue;
            let meters = building[utilType];
            meters.forEach(meterId => meterIds.push(meterId));
        }
    }
    return meterIds;
}

// sometimes i need only the raw list of meters from summary
function getMeterListFromSummary(summary, buildingFilter = null) {
    let meters = [];
    for (const buildingKey in summary) {
        const building = summary[buildingKey];

        utilityTypes.forEach(utility => {
            const ms = building[utility];
            if (ms) {
                for (const meterName in ms) {
                    meters.push([meterName, buildingKey]);
                }
            }
        });
    }
    return meters;
}

// function to call api for json.
async function callApiJSON(uri) {
   try {
        // this was double encoding... removed this (turned @ into %2540)
        //let url = encodeURI(uri);
        let url = uri;
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
