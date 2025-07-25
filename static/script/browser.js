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

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape') {
		let params = new URLSearchParams(document.location.search);
		let ref = params.get("ref");
		if (ref) {
			if (ref == "view-map") {
                window.location.href = "map";
			} else if (ref == "view-graph") {
                window.location.href = "benchmark";
			}
		}
	}
});

function downloadMeterData(){
    const meter = document.getElementById("select-meter").value;
    const startDate = document.getElementById("sb-start-date").value;
    const endDate = document.getElementById("sb-end-date").value;

    // build query params cleanly
    const params = new URLSearchParams({
        uuid: meter,
        from_time: `${startDate}T00:00:00Z`,
        to_time:   `${endDate}T23:59:59Z`,
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

	let type = document.getElementById("select-type").value;

	let toRate = document.getElementById("cumultorate").checked;
	let agg = document.querySelector("input[name='agg']:checked").value;
    let startDate = document.getElementById("sb-start-date").value;
	let endDate = document.getElementById("sb-end-date").value;

	document.getElementById('b-plot').innerHTML = `<img src='${appConfig.loadingGifUrl}' alt='Loading...' />`;
	document.getElementById('b-plot-header').innerHTML = selMeter;

	let params = {
        uuid: selMeter,
        from_time: `${startDate}T00:00:00Z`,
        to_time:   `${endDate}T23:59:59Z`,
        to_rate: toRate
    };
    if (agg && agg !== "None" && agg != 0) {
        params.aggregate = `${agg}H`;
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
	for( let i = 0; i < selectArray.length; i++ ) {
		let opt = selectArray[i];
		let el = document.createElement("option");
		if (selectID == "select-type") {
			el.textContent = capFirst(opt);
		} else {
			el.textContent = opt;
		}
		el.value = opt;
		document.getElementById(selectID).appendChild(el);
	};
};

// called when a building is selected - only needs updating type fields
function buildingSelected() {
	let selBuilding = document.getElementById("select-building").value;
	let selectType = document.getElementById("select-type");
	selectType.innerHTML = "<option value=''>--Select--</option>";
	let selectMeter = document.getElementById("select-meter");
	selectMeter.innerHTML = "<option value=''>--Select--</option>";

	if (selBuilding !== "") {
		selectPopulator("select-type", Object.keys(browserData.hierarchy[selBuilding]));
	}
};

// called when a type is selected - only needs populating meters
function typeSelected() {
	let selType = document.getElementById("select-type").value;
	let selMeter = document.getElementById("select-meter");
	selMeter.innerHTML = "<option value=''>--Select--</option>";
	if (selType != "") {
		selectPopulator("select-meter", browserData.hierarchy[document.getElementById("select-building").value][selType]);
	}
};

// when a new building is selected - update cumultorate and redraw
function meterSelected() {
	selMeter = document.getElementById("select-meter").value;

	if (selMeter != "") {
		for( let i = 0; i < browserData.meters.length; i++ ) {
			if (browserData.meters[i][metaLabel["meter_id"]] == selMeter) {
				if (browserData.meters[i][metaLabel["reading_type"]] == "Cumulative") {
					document.getElementById("cumultorate").disabled = false;
					document.getElementById("alreadyrate").hidden = true;
				} else {
					document.getElementById("cumultorate").disabled = true;
					document.getElementById("alreadyrate").hidden = false;
				}
			}
		};
	};

	redrawPlot();
};

$(document).ready(async function () {
    try {
        // fetch both hierarchy and meters at once
        const { hierarchy, meters } = await getData({
            hierarchy: {},
            meters: {}
        });

        // store them in your global browserData object
        browserData.hierarchy = hierarchy;
        browserData.meters = meters;

        if (browserData.hierarchy) {
            selectPopulator("select-building", Object.keys(browserData.hierarchy));

			// check if we pre-select building or meter from URL
			let params = new URLSearchParams(document.location.search);
			if (params.get("building")) {
				document.getElementById("select-building").value = params.get("building");
			}
			buildingSelected();

			if (params.get("meter_id")) {
				for( let i = 0; i < browserData.meters.length; i++ ) {
					if (browserData.meters[i][metaLabel["meter_id"]] == params.get("meter_id")) {
						document.getElementById("select-building").value = browserData.meters[i][metaLabel["building_id"]];
						buildingSelected();
						document.getElementById("select-type").value = browserData.meters[i][metaLabel["utility_type"]].toLowerCase();
						typeSelected();
					}
				};
				document.getElementById("select-meter").value = params.get("meter_id");
			}
			meterSelected();
		}

    } catch (err) {
        console.error("Failed to load data", err);
    }
	
	commentParent = "browser";
	document.getElementById("comment-bubble").classList.remove("hidden");

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    document.getElementById('sb-start-date').value = sideBarStartDate;
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    document.getElementById('sb-end-date').value = sideBarEndDate;

	// TODO implement a cumultorate filter
    document.getElementById("cumultorate").addEventListener("click", redrawPlot);

	document.getElementById("select-building").addEventListener("change", buildingSelected);
    document.getElementById("select-type").addEventListener("change", typeSelected);
    document.getElementById("select-meter").addEventListener("change", meterSelected);

    document.getElementById("download-button").addEventListener("click", downloadMeterData);
});
