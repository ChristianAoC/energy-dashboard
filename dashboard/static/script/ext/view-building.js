const apiUrl="https://scc-net0i.lancs.ac.uk/api2"

function unitOf(type) {
    if (type == "Electricity") { return "kWh"; }
    else { return "dm³"; }
}

function unitOfEUI(type) {
    if (type == "Electricity") { return "Wh/sqm"; }
    else if (type == "Heat") { return "dm³/sqm"; }
    else { return "cm³/sqm"; }
}

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape') {
		closeBuildingDataView()
	}
})

function closeBuildingDataView() {
	if ((document.getElementById("building-data").style) &&
		(document.getElementById("building-data").style.display) &&
		(document.getElementById("building-data").style.display == "inline")) {
			document.getElementById("building-data").style.display = "none";
	}
}

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
}

function convertTSDToPlotly(tsd, type, name) {
	let x = [];
	let y = [];
	let i = 0;
	do {
		x.push(tsd[i].time);
		y.push(tsd[i].value);
		i++;
	} while (i < tsd.length);

	return {
		'x': x,
		'y': y,
		'name': name,
		'type': type
	};
}

function viewBuilding(curBuilding) {
	document.getElementById("building-data").style.display = "inline";
	document.getElementById("b-meta-header").innerHTML = curBuilding["Building Name"];
	document.getElementById("b-meta1span").innerHTML = curBuilding["Type"];

	// populate the select option
	var hasOption=false;
	
	var html = ""
	for (var x of ["Electricity", "Gas", "Water", "Heat"]) {
	    if (curBuilding[x]) {
		html += '<div class="b-inputs"><input type="radio" id="' + x +'" name="meter" value="' + curBuilding[x];
		if(hasOption){ html += '"/>' }
		else{
		    html += '" checked />'
		    hasOption = true
		}
		html += '<label for="' + x + '">' + x + '</label></div>'
	    }
	}
	document.getElementById('b-meter-select').innerHTML = html;

	var type = document.querySelector('input[name="meter"]:checked').id;
    // meta header - do this after and pick first meter that is available for data
    if ((curBuilding["Floor Size"] != 0) && (curBuilding["Floor Size"] != null)) {
		document.getElementById("b-meta2span").innerHTML = curBuilding["Floor Size"];
		document.getElementById("b-meta3span").innerHTML = Math.round(curBuilding[type+" EUI"])+" "+unitOfEUI(type);
		document.getElementById("b-meta4span").innerHTML = Math.round(curBuilding[type+" Usage"])+" "+unitOf(type);
	} else {
		document.getElementById("b-meta2span").innerHTML = "(unknown)";
		document.getElementById("b-meta3span").innerHTML = "(unknown)";
		document.getElementById("b-meta4span").innerHTML = "(unknown)";
	}

	redrawPlot();
}

function redrawPlot() {
	var meter = document.querySelector('input[name="meter"]:checked').value;
	var type = document.querySelector('input[name="meter"]:checked').id;
	var agg = document.querySelector('input[name="agg"]:checked').value;
    var startDate = document.getElementById('b-start-date').value;
	var endDate = document.getElementById('b-end-date').value;

    var uri=apiUrl + "/series_obs?sid=" + meter +
	    "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
	    "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
        "&aggregate=" + agg + "H";

    document.getElementById('b-plot').innerHTML = "<img src='static/gfx/loading.gif' alt='Loading...' />";
	document.getElementById('b-plot-header').innerHTML = 'Consumption for meter "'+meter+'" (measuring: '+type+')';
	var unit = "";
	if (type == "Electricity") {
		unit = "Electricity [kWh]";
	} else if (type == "Gas") {
		unit = "Gas [m³]";
	} else if (type == "Heat") {
		unit = "Heat [MWh]";
	} else if (type == "Water") {
		unit = "Water [m³]"; // &sup3; doesn't work?
	}
	
	callApiJSON( uri ).then((data) => {
		tsd = data[meter];
		pData = convertTSDToPlotly(tsd, "bar", name);
        console.log(pData);
		
		var pConfig = { displayModeBar: false };
		var pLayout = { barmode: 'group',
						xaxis: {
							title: {
								text: 'Time'
								}
							},
						yaxis: {
							title: {
								text: unit
								}
							}
						};
		
		document.getElementById('b-plot').innerHTML = "";
		Plotly.newPlot("b-plot", [pData], pLayout, pConfig);
	});
}

function downloadMeterData(){
	var meter = document.querySelector('input[name="meter"]:checked').value;
	var startDate = document.getElementById('b-start-date').value;
	var endDate = document.getElementById('b-end-date').value;
	var uri=apiUrl + "/meter?uid=" + encodeURIComponent(meter)+
		"&start=" + encodeURIComponent(startDate) +
		"&end=" + encodeURIComponent(endDate) +
		"&format=csv"

	//creating an invisible element
	var element = document.createElement('a');
	element.setAttribute('href', 
				 uri);
	element.setAttribute('download', encodeURIComponent(meter));

	// Above code is equivalent to
	// <a href="path of file" download="file name">

	document.body.appendChild(element);

	//onClick property
	element.click();

	document.body.removeChild(element);
}
