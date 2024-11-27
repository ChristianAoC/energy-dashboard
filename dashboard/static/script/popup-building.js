var pConfigPopup = {
    displayModeBar: false
};

var pLayoutPopup = {
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

function viewBuilding(buildingID) {
    var curBuilding = [];
	for (b of masterList) {
		if (b[varNameMLBuildingID] == buildingID) {
			curBuilding = b;
		}
	}

    commentParent = "building-data";

	document.getElementById("building-data").style.display = "inline";
	document.getElementById("b-meta-header").innerHTML = curBuilding[varNameMLBuildingName];
	document.getElementById("b-meta1span").innerHTML = curBuilding[varNameMLUsage];

	// populate the select option
	var hasOption=false;
	
	var html = ""
	for (x of ["electricity", "gas", "water", "heat"]) {
	    if (curBuilding[x]["sensor_uuid"].length > 0) {
            for (y in curBuilding[x]["sensor_uuid"]) {
        		html += '<div class="b-inputs"><input class="b-input-radio" type="radio" id="' + x + y + '" name="sensor" value="' + curBuilding[x]["sensor_uuid"][y];
                if (hasOption){ html += '"/>' }
                else {
                    html += '" checked />'
                    hasOption = true
                }
                let intCnt = parseInt(y) + 1;
                html += '<label for="' + x + y + '">' + capFirst(x) + ' ' + intCnt + '</label></div>'
            }
	    }
	}
	document.getElementById('b-sensor-select').innerHTML = html;

	var type = document.querySelector('input[name="sensor"]:checked').id;
    type = type.substring(0, type.length - 1);
    // meta header - do this after and pick first sensor that is available for data
    if ((curBuilding[varNameMLFloorSize] != 0) && (curBuilding[varNameMLFloorSize] != null)) {
		document.getElementById("b-meta2span").innerHTML = curBuilding[varNameMLFloorSize] + " m&sup2;";
		document.getElementById("b-meta3span").innerHTML = curBuilding[type]["eui_annual"]+" "+curBuilding[type]["unit"] + "/m&sup2;";
		document.getElementById("b-meta4span").innerHTML = curBuilding[type]["usage"]+" "+curBuilding[type]["unit"];
	} else {
		document.getElementById("b-meta2span").innerHTML = "(unknown)";
		document.getElementById("b-meta3span").innerHTML = "(unknown)";
		document.getElementById("b-meta4span").innerHTML = "(unknown)";
	}

	redrawPlot();
};

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape' && document.getElementById("building-data").style.display == "inline") {
		closeBuildingDataView()
	}
});

function closeBuildingDataView() {
	if ((document.getElementById("building-data").style) &&
		(document.getElementById("building-data").style.display) &&
		(document.getElementById("building-data").style.display == "inline")) {
			document.getElementById("building-data").style.display = "none";
            commentParent = document.querySelector('input[name=select-view]:checked').value;
            leaveCommentMode();
	}
};

// re-purpose this later to write a monthly agg script
function createAggregate(tsd, each) {
	let name = Object.keys(tsd)[0];
	let tsdT = [];
	let i = 0;
	let sum = 0;
	do {
		sum += tsd[name][i].value;
		if ((i+1) % (each) == 0) {
			tsdT.push({"time": tsd[name][i].time, "value": sum});
			sum = 0;
		}
		i++;
	} while (i < tsd[name].length);
	return {[name]: tsdT};
};

function downloadSensorData(){
	var sensor = document.querySelector('input[name="sensor"]:checked').value;
	var startDate = document.getElementById('b-start-date').value;
	var endDate = document.getElementById('b-end-date').value;
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
	var sensor = document.querySelector('input[name="sensor"]:checked').value;
	var type = document.querySelector('input[name="sensor"]:checked').id;
    type = type.substring(0, type.length - 1);
	var agg = document.querySelector('input[name="agg"]:checked').value;
    var startDate = document.getElementById('b-start-date').value;
	var endDate = document.getElementById('b-end-date').value;
    let dateDiff = new Date(endDate) - new Date(startDate);
    dateDiff = dateDiff / (24*3600*1000);

    var uri="api/meter_obs?uuid=" + sensor +
	    "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
	    "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
        "&aggregate=" + agg + "H";

    document.getElementById('b-plot').innerHTML = "<img src='gfx/loading.gif' alt='Loading...' />";
	document.getElementById('b-plot-header').innerHTML = 'Consumption for sensor "'+sensor+'" (measuring: '+type+') over ' + dateDiff + " days";
	
	callApiJSON( uri ).then((data) => {
		if (data == null) {
			document.getElementById('b-plot').innerHTML = "<br><br>Could not connect to API.";
			return;
		}
		document.getElementById('b-plot').innerHTML = "";
        let resArr = convertTSDToPlotlyPopup(data[sensor].obs, "bar");
        let pData = resArr[0];
        let totalSum = resArr[1];
        document.getElementById("b-meta3span").innerHTML = calcIntensity(totalSum, dateDiff, "", sensor.slice(0, 5)) + " " + data[sensor].unit + "/m&sup2;";
        document.getElementById("b-meta4span").innerHTML = totalSum + " " + data[sensor].unit;
        pLayoutPopup["yaxis"]["title"]["text"] = capFirst(type) + " [" + data[sensor].unit + "]";
        Plotly.newPlot("b-plot", [pData], pLayoutPopup, pConfigPopup);
	});
};
