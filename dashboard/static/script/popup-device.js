var pConfigDevicePopup = {
    displayModeBar: false
};

var pLayoutDevicePopup = {
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

function convertTSDToPlotlyDevicePopup(tsd, type) {
	let x = [];
	let y = [];
	let i = 0;
    if (tsd != null && tsd.length > 0) {
        do {
            x.push(tsd[i].time);
            y.push(tsd[i].value);
            i++;
        } while (i < tsd.length);
    }

	return {
		'x': x,
		'y': y,
		'type': type
	};
};

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape' && document.getElementById("device-data").style.display == "inline") {
		closeDeviceDataView();
	}
});

function closeDeviceDataView() {
	if ((document.getElementById("device-data").style) &&
		(document.getElementById("device-data").style.display) &&
		(document.getElementById("device-data").style.display == "inline")) {
			document.getElementById("device-data").style.display = "none";
            commentParent = "deviceTable";
            leaveCommentMode();
	}
};

function downloadSensorDeviceData(){
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

function viewDevice(sensorID) {
    commentParent = "device-data";

	document.getElementById("device-data").style.display = "inline";
	document.getElementById("b-plot-header").innerHTML = sensorID;
	document.getElementById("b-meta-header").innerHTML = sensorID;

    document.getElementById("b-button").setAttribute('data-sensor', sensorID);
	redrawDevicePlot();
};

function redrawDevicePlot() {
    var sensor = document.getElementById('b-button').dataset.sensor;
	var rateCum = document.querySelector('input[name="class"]:checked').value;
    var startDate = document.getElementById('b-start-date').value;
	var endDate = document.getElementById('b-end-date').value;

    var uri="api/meter_obs?uuid=" + sensor +
	    "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
	    "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z";
        if (rateCum == "cum") {
            uri += "&to_rate=false";
        }
        //        uri += "&aggregate=" + agg + "H";

    let thisDev;
    for (d of devices) {
        if (d[varNameDevSensorID] == sensor) {
            thisDev = d;
        }
    }

    document.getElementById('b-plot').innerHTML = "<img src='gfx/loading.gif' alt='Loading...' />";
    document.getElementById("b-plot-header").innerHTML = "Sensor " +
    thisDev[varNameDevSensorID] + " (" +
    thisDev[varNameDevMeasuringShort] + ")";
    document.getElementById("b-meta-header").innerHTML = "Measuring " +
    thisDev[varNameDevMeasuringShort] + " (" +
    thisDev[varNameDevSensorType] + "), as " +
    thisDev[varNameDevClass] + " in " +
    thisDev[varNameDevUnits];
	
	callApiJSON( uri ).then((data) => {
		document.getElementById('b-plot').innerHTML = "";
        let pData = convertTSDToPlotlyDevicePopup(data[sensor].obs, "scatter");
        pLayoutDevicePopup["yaxis"]["title"]["text"] = thisDev[varNameDevSensorType] + " [" + thisDev[varNameDevUnits] + "]";
        Plotly.newPlot("b-plot", [pData], pLayoutDevicePopup, pConfigDevicePopup);
	});
};
