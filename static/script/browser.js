let hierarchy = "";

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
                window.location.href = "map.html";
			} else if (ref == "view-graph") {
                window.location.href = "benchmark.html";
			}
		}
	}
});

function downloadSensorData(){
	var sensor = document.querySelector('input[name="sensor"]:checked').value;
	var startDate = document.getElementById("sb-start-date").value;
	var endDate = document.getElementById("sb-end-date").value;
    var uri="api/meter_obs?uuid=" + sensor +
	    "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
	    "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
        "&to_rate=false" +
		"&format=csv"

	//creating an invisible element
	var element = document.createElement('a');
	element.setAttribute('href', uri);
	element.setAttribute('download', encodeURIComponent(sensor));

	// Above code is equivalent to
	// <a href="path of file" download="file name">

	document.body.appendChild(element);

	//onClick property
	element.click();

	document.body.removeChild(element);
};

function redrawPlot() {
	let selMeter = document.getElementById("select-meter").value;
	if (selMeter == "") {
		return;
	}

	let type = document.getElementById("select-type").value;

	let toRate = document.getElementById("cumultorate").checked;
	let agg = document.querySelector("input[name='agg']:checked").value;
    let startDate = document.getElementById("sb-start-date").value;
	let endDate = document.getElementById("sb-end-date").value;

    let uri="api/meter_obs?uuid=" + selMeter +
	    "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
	    "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
		"&to_rate=" + toRate;
	if (agg != "None") uri += "&aggregate=" + agg + "H";

	document.getElementById('b-plot').innerHTML = `<img src='${appConfig.loadingGifUrl}' alt='Loading...' />`;
	document.getElementById('b-plot-header').innerHTML = selMeter;
	
	callApiJSON( uri ).then((data) => {
		if (data == null) {
			document.getElementById('b-plot').innerHTML = "<br><br>Could not connect to API.";
			return;
		}
		document.getElementById('b-plot').innerHTML = "";
        let resArr = convertTSDToPlotlyPopup(data[selMeter].obs, "bar");
        let pData = resArr[0];
        pLayoutPopup["yaxis"]["title"]["text"] = capFirst(type) + " [" + data[selMeter].unit + "]";
        Plotly.newPlot("b-plot", [pData], pLayoutPopup, pConfigPopup);
	});
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
		selectPopulator("select-type", Object.keys(hierarchy[selBuilding]));
	}
};

// called when a type is selected - only needs populating meters
function typeSelected() {
	let selType = document.getElementById("select-type").value;
	let selMeter = document.getElementById("select-meter");
	selMeter.innerHTML = "<option value=''>--Select--</option>";
	if (selType != "") {
		selectPopulator("select-meter", hierarchy[document.getElementById("select-building").value][selType]);
	}
};

// when a new building is selected - update cumultorate and redraw
function meterSelected() {
	selMeter = document.getElementById("select-meter").value;

	if (selMeter != "") {
		for( let i = 0; i < devices.length; i++ ) {
			if (devices[i]["meter_id_clean"] == selMeter) {
				if (devices[i]["class"] == "Cumulative") {
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
	commentParent = "device-data";
	document.getElementById("comment-bubble").classList.remove("hidden");

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    document.getElementById('sb-start-date').value = sideBarStartDate;
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    document.getElementById('sb-end-date').value = sideBarEndDate;

    hierarchy = await callApiJSON('/api/meter_hierarchy');
    if (hierarchy) {
        selectPopulator("select-building", Object.keys(hierarchy));
    } else {
        console.error("Failed to load hierarchy data");
    }

	// TODO implement a cumultorate filter
    document.getElementById("cumultorate").addEventListener("click", redrawPlot);

	document.getElementById("select-building").addEventListener("change", buildingSelected);
    document.getElementById("select-type").addEventListener("change", typeSelected);
    document.getElementById("select-meter").addEventListener("change", meterSelected);

    document.getElementById("download-button").addEventListener("click", downloadSensorData);

	let params = new URLSearchParams(document.location.search);
	if (params.get("building")) {
		document.getElementById("select-building").value = params.get("building");
	}
	buildingSelected();

	if (params.get("meter_id")) {
		for( let i = 0; i < devices.length; i++ ) {
			if (devices[i]["meter_id_clean"] == params.get("meter_id")) {
				document.getElementById("select-building").value = devices[i]["building"];
				buildingSelected();
				document.getElementById("select-type").value = devices[i]["meter_type"].toLowerCase();
				typeSelected();
			}
		};
		document.getElementById("select-meter").value = params.get("meter_id");
	}
	meterSelected();
});
