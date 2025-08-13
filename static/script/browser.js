let pConfigPopup = {
    displayModeBar: false
};

let pLayoutPopup = {
    barmode: 'group',
    margin:{
        t: 50
        },
    xaxis: {
        title: {
            text: 'Time'
            }
        },
    yaxis: {
        title: {
            text: 'unit [tbd]'
            }
        }
};

function convertTSDToPlotlyPopup(tsd, type) {
	let x = [];
	let y = [];
	let i = 0;
    let totalSum = 0;
    if (tsd != null && tsd.length > 0) {
        do {
            x.push(tsd[i].time);
            y.push(tsd[i].value);
            totalSum += tsd[i].value;
            i++;
        } while (i < tsd.length);
    }

	return [{
		'x': x,
		'y': y,
		'type': type
	}, totalSum];
};

function downloadMeterData(){
    const meter = document.getElementById("select-meter").value;
    const startDate = document.getElementById("sb-start-date").value;
    const endDate = document.getElementById("sb-end-date").value;

    // build query params cleanly
    const params = new URLSearchParams({
        id: meter,
        from_time: startDate,
        to_time:   endDate,
        to_rate: 'false',
        format: 'csv'
    });

    const uri = `${apiEndpoints.obs}?${params.toString()}`;

    // create an invisible link to trigger download
    const element = document.createElement('a');
    element.href = uri;
    element.download = meter; // filename to suggest
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
};

async function redrawPlot() {
	let selMeter = document.getElementById("select-meter").value;
	if (selMeter == "") {
		return;
	}

	let type = document.getElementById("select-utility").value;

	let toRate = document.getElementById("cumultorate").checked;
	let agg = document.querySelector("input[name='agg']:checked").value;
    let startDate = document.getElementById("sb-start-date").value;
	let endDate = document.getElementById("sb-end-date").value;

	document.getElementById('b-plot').innerHTML = `<div class="centered"><img src='${appConfig.loadingGifUrl}' alt='Loading...' /><div>`;

	let params = {
        id: selMeter,
        from_time: startDate,
        to_time:   endDate,
        to_rate: toRate
    };
    if (agg && agg !== "None" && agg != 0) {
        params.aggregate = `${agg}h`;
    }

    try {
        const { obs } = await getData({ obs: params }, true); 

        if (!obs) {
            document.getElementById('b-plot').innerHTML = "<br><br>Could not connect to API.";
            return;
        }

		document.getElementById('b-plot').innerHTML = "";
        let resArr = convertTSDToPlotlyPopup(obs[selMeter].obs, "bar");
        let pData = resArr[0];
        pLayoutPopup["yaxis"]["title"]["text"] = capFirst(type) + " [" + obs[selMeter].unit + "]";
        Plotly.newPlot("b-plot", [pData], pLayoutPopup, pConfigPopup);

    } catch (err) {
        console.error("Failed to load meter data", err);
        document.getElementById('b-plot').innerHTML = "<br><br>Error retrieving data.";
    }	
};

function selectPopulator(selectID, selectArray) {
	const selectElement = document.getElementById(selectID);
	selectElement.innerHTML = "<option value=''>--Select--</option>";

	for (let i = 0; i < selectArray.length; i++) {
		const opt = selectArray[i];

		// Skip meta if in type selection
		if (selectID === "select-utility" && opt === "meta") continue;

		const el = document.createElement("option");
		el.value = opt;

		if (selectID === "select-building") {
			const bName = browserData.hierarchy[opt]?.["meta"][metaLabel["building_name"]] || "(Unknown name)";
			el.textContent = `${bName} (${opt})`;
		} else if (selectID === "select-meter") {
			const meterMeta = browserData.meters.find(m => m[metaLabel["meter_id"]] === opt);
			const mName = meterMeta?.[metaLabel["description"]] || "(Unnamed meter)";
			el.textContent = `${mName} (${opt})`;
		} else if (selectID === "select-utility") {
			el.textContent = capFirst(opt);
		} else {
			el.textContent = opt;
		}

		selectElement.appendChild(el);
	}
}

// called when a building is selected - only needs updating type fields
function buildingSelected() {
	let selBuilding = document.getElementById("select-building").value;
	let selectType = document.getElementById("select-utility");
	selectType.innerHTML = "<option value=''>--Select--</option>";
	let selectMeter = document.getElementById("select-meter");
	selectMeter.innerHTML = "<option value=''>--Select--</option>";

	if (selBuilding !== "") {
		selectPopulator("select-utility", Object.keys(browserData.hierarchy[selBuilding]));
	}
};

// called when a type is selected - only needs populating meters
function typeSelected() {
	let selType = document.getElementById("select-utility").value;
	let selMeter = document.getElementById("select-meter");
	selMeter.innerHTML = "<option value=''>--Select--</option>";
	if (selType != "") {
		selectPopulator("select-meter", browserData.hierarchy[document.getElementById("select-building").value][selType]);
	}
};

function renderContext() {
    const startDate = document.getElementById("sb-start-date").value;
    const endDate = document.getElementById("sb-end-date").value;
    const selMeter = document.getElementById("select-meter").value;
    const contextDiv = document.getElementById("b-context");
    contextDiv.innerHTML = ""; // clear existing content

    if (!selMeter || !browserData.context || browserData.context == [] || browserData.context == "Context file missing") {
        return;
    }

    const filtered = browserData.context.filter(c => {
        if (c.meter !== selMeter) return false;

        const withinStart = c.startnone || c.start <= endDate;
        const withinEnd = c.endnone || c.end >= startDate;
        return withinStart || withinEnd;
    });

    if (!filtered) return;
    
    contextDiv.classList.toggle("hidden");

    for (const c of filtered) {
        const author = c.author.split('@')[0];
        const dateInfo = [
            c.startnone ? "" : `start: ${c.start}`,
            c.endnone ? "" : `end: ${c.end}`
        ].filter(Boolean).join(", ");

        const line = `<div><strong style="font-size: 1.1em">Comments:</strong><br><b>${author}</b>: ${c.comment}${dateInfo ? " <small>(for " + dateInfo + ")</small>" : ""}</div>`;
        contextDiv.insertAdjacentHTML("beforeend", line);
    }
}

// when a new building is selected - update cumultorate and redraw
function meterSelected() {
    const selMeter = document.getElementById("select-meter").value;
    const cumulCheckbox = document.getElementById("cumultorate");
    const rateWarning = document.getElementById("alreadyrate");
    const metaDiv = document.getElementById("b-meta-info");
    const plotHeader = document.getElementById("b-plot-header");

    if (selMeter !== "") {
        const selected = browserData.meters.find(m => m[metaLabel["meter_id"]] === selMeter);
        const buildingId = selected?.[metaLabel["building_id"]];
        const utilityType = selected?.[metaLabel["utility_type"]];

        const buildingMeta = browserData.hierarchy?.[buildingId]?.meta || {};

        // Set plot header: Meter name (ID)
        const meterName = selected?.[metaLabel["description"]] || "(Unnamed meter)";
        plotHeader.textContent = `${meterName} (${selected?.[metaLabel["meter_id"]]})`;

        // Reading type logic
        const readingType = selected[metaLabel["reading_type"]]?.toLowerCase();
        if (readingType === "cumulative") {
            cumulCheckbox.disabled = false;
            rateWarning.hidden = true;
        } else {
            cumulCheckbox.disabled = true;
            rateWarning.hidden = false;
        }

        // Format meta info
        const buildingName = buildingMeta?.[metaLabel["building_name"]] || "(Unknown building)";
        const occupancy = buildingMeta?.[metaLabel["occupancy_type"]] || "n/a";
        const yearBuilt = buildingMeta?.[metaLabel["year_built"]] || "n/a";
        const floorArea = buildingMeta?.[metaLabel["floor_area"]] || "n/a";

        const resolution = selected?.[metaLabel["resolution"]] || "n/a";
        const units = selected?.[metaLabel["units"]] || "n/a";
        const isMain = selected?.[metaLabel["is_main_meter"]] ? "Main meter" : "Submeter";

        // Inject meta info
        metaDiv.innerHTML = `
            <strong>Meter type:</strong> ${isMain} | 
            <strong>Resolution:</strong> ${resolution} | 
            <strong>Units:</strong> ${units}<br>
            <strong>Building:</strong> ${buildingName} (${buildingId}) |
            <strong>Occupancy:</strong> ${occupancy} | 
            <strong>Year built:</strong> ${yearBuilt} | 
            <strong>Floor area:</strong> ${floorArea} m²
        `;
    } else {
        plotHeader.textContent = "(No meter selected)";
        metaDiv.innerHTML = "";
        rateWarning.hidden = true;
        cumulCheckbox.disabled = true;
    }

    renderContext();

    redrawPlot();
}

function updateUrlFromSelections() {
    const building = document.getElementById("select-building").value;
    const utilityType = document.getElementById("select-utility").value;
    const meter = document.getElementById("select-meter").value;

    // build query params
    const params = new URLSearchParams(window.location.search);

    if (building) {
        params.set("building", building);
    } else {
        params.delete("building");
    }

    if (utilityType) {
        params.set("utility_type", utilityType); // optional, you can include type if useful
    } else {
        params.delete("utility_type");
    }

    if (meter) {
        params.set("meter_id", meter);
    } else {
        params.delete("meter_id");
    }

    // update without reloading
    const newUrl = window.location.pathname + "?" + params.toString();
    window.history.replaceState({}, "", newUrl);
};

function randomMeter(buildingFilter = null) {
    if (!Array.isArray(browserData.meters) || browserData.meters.length === 0) {
        console.warn('No meters loaded yet');
        return;
    }

    let meterIds = getMeterListFromHierarchy(browserData.hierarchy, buildingFilter);

    if (meterIds.length === 0) {
        console.warn(`No meters found for building ${buildingFilter}`);
        return;
    }

    // Pick random meter
    const randomMeterID = meterIds[Math.floor(Math.random() * meterIds.length)];
    const randomMeter = browserData.meters.find(meter => meter[metaLabel["meter_id"]] === randomMeterID);

    if (!randomMeter) {
        console.warn(`Random meter ID ${randomMeterID} not found in browserData.meters`);
        return;
    }

    const buildingId = randomMeter[metaLabel["building_id"]];
    const utilityType = randomMeter[metaLabel["utility_type"]];
    const meterId = randomMeter[metaLabel["meter_id"]];

    // Update dropdowns
    document.getElementById("select-building").value = buildingId;
    buildingSelected();

    setTimeout(() => {
        document.getElementById("select-utility").value = utilityType;
        typeSelected();

        setTimeout(() => {
            document.getElementById("select-meter").value = meterId;
            meterSelected();
        }, 0);
    }, 0);

    // Update URL
    const url = new URL(window.location);
    url.searchParams.set('building', buildingId);
    url.searchParams.set('utility_type', utilityType);
    url.searchParams.set('meter_id', meterId);
    window.history.replaceState({}, '', url.toString());
}

function dateChange() {
    redrawPlot();
}

$(document).ready(async function () {
    try {
        const { hierarchy, meters, getcontext } = await getData({
            hierarchy: {},
            meters: {},
            getcontext: {}
        });

        browserData.hierarchy = hierarchy;
        browserData.meters = meters;
        if (getcontext) {
            browserData.context = getcontext;
        } else {
            browserData.context = [];
        }

        if (browserData.hierarchy) {
            const buildingEntries = Object.entries(browserData.hierarchy);

            // sort by building_name in meta
            buildingEntries.sort((a, b) => {
                const nameA = a[1].meta?.[metaLabel["building_name"]] || "";
                const nameB = b[1].meta?.[metaLabel["building_name"]] || "";
                return nameA.localeCompare(nameB);
            });

            // extract sorted building IDs
            const sortedBuildingIds = buildingEntries.map(entry => entry[0]);

            selectPopulator("select-building", sortedBuildingIds);

            const params = new URLSearchParams(window.location.search);
            let buildingFromUrl = params.get("building");
            let typeFromUrl     = params.get("utility_type");
            let meterFromUrl    = params.get("meter_id");
            let randomRequest   = params.get("ref") === "map" || params.get("ref") === "benchmark";

            // Derive missing building/type from meter_id if needed
            if (meterFromUrl && (!buildingFromUrl || !typeFromUrl)) {
                for (let i = 0; i < browserData.meters.length; i++) {
                    if (browserData.meters[i][metaLabel["meter_id"]] === meterFromUrl) {
                        buildingFromUrl = browserData.meters[i][metaLabel["building_id"]];
                        typeFromUrl     = browserData.meters[i][metaLabel["utility_type"]].toLowerCase();
                        break;
                    }
                }
            }

            // Auto-load behaviour
            if (randomRequest && buildingFromUrl) {
                // Pick random meter from a specific building
                randomMeter(buildingFromUrl);
            } else if (!buildingFromUrl && !meterFromUrl) {
                // No params at all — just pick anything
                randomMeter();
            }

            // STEP 1: set building and populate types
            if (buildingFromUrl) {
                document.getElementById("select-building").value = buildingFromUrl;
            }
            buildingSelected();

            // defer STEP 2 until type options are ready
            setTimeout(() => {
                if (typeFromUrl) {
                    document.getElementById("select-utility").value = typeFromUrl;
                    typeSelected();
                }

                // defer STEP 3 until meter options are ready
                setTimeout(() => {
                    const meterSelect = document.getElementById("select-meter");

                    if (meterFromUrl) {
                        // if meter_id passed, select that
                        meterSelect.value = meterFromUrl;
                    } else if (meterSelect.options.length > 1) {
                        // no meter_id? select first available after placeholder
                        meterSelect.selectedIndex = 1;
                    }

                    meterSelected();
                }, 0);
            }, 0);
		}

    } catch (err) {
        console.error("Failed to load data", err);
    }
	
	commentParent = "view-browser";
	document.getElementById("comment-bubble").classList.remove("hidden");

    document.getElementById("cumultorate").addEventListener("click", redrawPlot);
    document.getElementsByName("agg").forEach( function(radio) {
        radio.addEventListener('click', redrawPlot);
    });

    document.getElementById("select-building").addEventListener("change", () => {
        buildingSelected();
        updateUrlFromSelections();
    });

    document.getElementById("select-utility").addEventListener("change", () => {
        typeSelected();
        updateUrlFromSelections();
    });

    document.getElementById("select-meter").addEventListener("change", () => {
        meterSelected();
        updateUrlFromSelections();
    });

    document.getElementById("download-button").addEventListener("click", downloadMeterData);
});
