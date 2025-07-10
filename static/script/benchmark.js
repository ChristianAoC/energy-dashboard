// this is for the small sidebar tabs, used a lot so store as var
var activeTab = "electricity";

var pConfigGraph = { displayModeBar: true, responsive: true };
var pLayoutGraph = {
    autosize: 'true',
    height: 600,
    margin:{
        t: 50
        },
    xaxis: {
        title: {},
            automargin: true
        },
    yaxis: {
        showticklabels: true,
        automargin: true,
        type: 'category',
        categoryorder: 'total ascending'
        }
    };

function convertMLToPlotly(barType) {
    let toPlot = document.getElementById("toggleGraph").checked ? "eui_annual" : "usage";
	let x = [];
	let y = [];
    let customdata = [];
    let bmg = [];
    let bmt = [];
	let i = 0;
    if (narrowML.length > 0) {
        do {
            if(narrowML[i][activeTab][toPlot] != null) {
                x.push(Math.round(parseFloat(narrowML[i][activeTab][toPlot])));
                y.push(narrowML[i][varNameMLBuildingName]);
                customdata.push(narrowML[i][activeTab]["sensor_uuid"].join(';'));
                bmg.push(narrowML[i][activeTab]["bm_good"]);
                bmt.push(narrowML[i][activeTab]["bm_typical"]);
            }
            i++;
        } while (i < narrowML.length);
    }

	return {
		'x': x,
		'y': y,
        'customdata': customdata,
        'bmg': bmg,
        'bmt': bmt,
        'marker': { "color": []},
		'type': barType,
        'orientation': 'h'
	};
};

function redrawGraph() {
    let dateDiff = new Date(document.getElementById("sb-end-date").value) - new Date(document.getElementById("sb-start-date").value);
    dateDiff = dateDiff / (24*3600*1000);
    var pData = convertMLToPlotly("bar");

    // add x-axis title
    if (document.getElementById("toggleGraph").checked) {
        pLayoutGraph["xaxis"]["title"]["text"] = capFirst(activeTab) +
            " " + uncapFirst($('label[for="toggleGraph"]')[0].lastElementChild.innerHTML) +
            " [" + unitsEUIPlain[activeTab] + "], scaled up to annual based on " +
            dateDiff + " days (starting " +
            document.getElementById("sb-start-date").value + ")";

        // add benchmarkt stuff
        var benchmarkLines = [];
        for (i=0; i<pData.x.length; i++) {
            if (pData["bmt"][i] == null) continue;
            // typical
            benchmarkLines.push(
                {
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: pData["bmt"][i],
                    y0: i-0.4,
                    x1: pData["bmt"][i],
                    y1: i+0.4,
                    line: {
                        color:'black',
                        height: 2
                    }                    
                }
            )
            // good
            benchmarkLines.push(
                {
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: pData["bmg"][i],
                    y0: i-0.4,
                    x1: pData["bmg"][i],
                    y1: i+0.4,
                    line: {
                        color:'blue',
                        height: 2
                    }                    
                }
            )
            // set bar color
            if (pData["x"][i] > pData["bmt"][i]) pData.marker.color[i] = "red";
            else if (pData["x"][i] > pData["bmg"][i]) pData.marker.color[i] = "orange";
            else pData.marker.color[i] = "green";
        }

        pLayoutGraph["shapes"] = benchmarkLines;
    } else {
        pLayoutGraph["xaxis"]["title"]["text"] = capFirst(activeTab) +
            " " + uncapFirst($('label[for="toggleGraph"]')[0].firstElementChild.innerHTML) +
            " [" + unitsConsPlain[activeTab] + "], over " +
            dateDiff + " days (starting " +
            document.getElementById("sb-start-date").value + ")";
    }

    pLayoutGraph["height"] = (pData['y'].length + 2) * 18 + 100;
    Plotly.newPlot("comparison-plot", [pData], pLayoutGraph, pConfigGraph);
    document.getElementById("span-type").innerHTML = activeTab;
    document.getElementById("span-typeCount").innerHTML = pData['x'].length;
    
    document.getElementById("comparison-plot").on('plotly_click', function(data){
        if (data.points[0].customdata != null && data.points[0].customdata != "") {
            contextMeterClicked = data.points[0].customdata.split(";")[0];
            if (!commentMode) {
                //viewEnergyData(contextMeterClicked.slice(0, 5));
                window.location.href = "browser.html?ref=map&meter_id="+contextMeterClicked.slice(0, 5);
            }
        }
    });

    let sensors = "";
    for (s of narrowML) {
        sensors += s[activeTab]["sensor_uuid"].join(";")+";";
    }
    let uri = "getcontext?sensor="+sensors+"&start="+getCurPageStartDate()+"&end="+getCurPageEndDate();
    fetch(uri, {method: 'GET'})
    .then(response => response.json())
    .then(data => {
        // '⚠️' data error
        // 'ℹ️' or '&#128161;' one-off/recurring
        // more: https://html-css-js.com/html/character-codes/icons/
        let annotations = [];
        for (e of data["context"]) {
            for (d in pData.customdata) {
                if (e.sensor == pData.customdata[d]) {
                    annotations.push({
                        x: pData.x[d],
                        y: pData.y[d],
                        showarrow: false,
                        text: '&#128161;',
                        hovertext:
                            "<b>Context:</b><br>" +
                            e.comment + ",<br><br>" +
                            "  Start: " + (e.startfuzzy ? "ca. " : "") + e.start + "<br>" +
                            "  End: " + (e.endfuzzy ? "ca. " : "") + e.end + "<br>" +
                            "    (Added by: " + e.author + ")"
                    })
                }
            }
        }
        Plotly.relayout("comparison-plot", { annotations });
    })
};

function toggleGraph() {
    redrawGraph();
};

function filterMasterListGraph() {
    masterList = originalMasterList;
	
	// check search input
    const searchInput = document.getElementById("building-search").value.toLowerCase();
    masterList = masterList.filter(b => b[varNameMLBuildingName].toLowerCase().includes(searchInput));

	// check for type (res/non-res/split use)
    if (!(document.getElementById("residential").checked)) {
        masterList = masterList.filter(b => b[varNameMLUsage] != "Residential");
    }
    if (!(document.getElementById("nonres").checked)) {
        masterList = masterList.filter(b => b[varNameMLUsage] != "Non-residential");
    }
    if (!(document.getElementById("mixed").checked)) {
        masterList = masterList.filter(b => b[varNameMLUsage] != "Split Use");
    }

    // slider range check
    let min = parseInt(document.getElementById("fromInput1").value);
    let max = parseInt(document.getElementById("toInput1").value);
    masterList = masterList.filter(b => (min <= parseInt(b[varNameMLFloorSize]) && max >= parseInt(b[varNameMLFloorSize])));
        
    // other sliders: for now, only do this into a "narrowML"
    let minEUI = parseInt(document.getElementById("fromInput2").value);
    let maxEUI = parseInt(document.getElementById("toInput2").value);
    narrowML = masterList.filter(b => (minEUI <= parseInt(b[activeTab]["eui_annual"]) && maxEUI >= parseInt(b[activeTab]["eui_annual"])));
    let minCons = parseInt(document.getElementById("fromInput3").value);
    let maxCons = parseInt(document.getElementById("toInput3").value);
    narrowML = narrowML.filter(b => (minCons <= parseInt(b[activeTab]["usage"]) && maxCons >= parseInt(b[activeTab]["usage"])));

    document.getElementById("span-total").innerHTML = masterList.length;

    redrawGraph();
};

function consumerClick(source) {
    let allTabs = document.getElementsByClassName("tab");
    if (source.classList.contains("active")) {
        return;
    }
    for (e of allTabs) {
        if (e.id == source.id) {
            e.classList.add("active");
        } else {
            e.classList.remove("active");
        }
    }
    document.getElementById("span-intensity").innerHTML = "[" + unitsEUI[source.id] + "]";
    document.getElementById("span-consumption").innerHTML = "[" + unitsCons[source.id] + "]";
    updateRange(source.id);
    activeTab = source.id;
    filterMasterListGraph();
    getSliderRanges();
    redrawGraph();
};

function updateRange(type) {
    if (type == "Electricity") {
        setRanges(2, Math.min(...elecEUI), Math.max(...elecEUI));
        setRanges(3, Math.min(...elecUse), Math.max(...elecUse));
    } else if (type == "Gas") {
        setRanges(2, Math.min(...gasEUI), Math.max(...gasEUI));
        setRanges(3, Math.min(...gasUse), Math.max(...gasUse));
    } else if (type == "Heat") {
        setRanges(2, Math.min(...heatEUI), Math.max(...heatEUI));
        setRanges(3, Math.min(...heatUse), Math.max(...heatUse));
    } else if (type == "Water") {
        setRanges(2, Math.min(...waterEUI), Math.max(...waterEUI));
        setRanges(3, Math.min(...waterUse), Math.max(...waterUse));
    }
};

function getSliderRanges() {
    sizes = masterList.map(x => parseInt(x[varNameMLFloorSize]));
    setRanges(1, Math.min(...sizes), Math.max(...sizes));

    elecUse = masterList.map(x => Math.round(parseFloat(x["electricity"]["usage"]))).filter(x => x); // kWh
    gasUse = masterList.map(x => Math.round(parseFloat(x["gas"]["usage"]))).filter(x => x); // m3
    heatUse = masterList.map(x => Math.round(parseFloat(x["heat"]["usage"]))).filter(x => x); // m3
    waterUse = masterList.map(x => Math.round(parseFloat(x["water"]["usage"]))).filter(x => x); // m3

    elecEUI = masterList.map(x => parseFloat(x["electricity"]["eui_annual"])).filter(x => x);
    gasEUI = masterList.map(x => parseFloat(x["gas"]["eui_annual"])).filter(x => x);
    heatEUI = masterList.map(x => parseFloat(x["heat"]["eui_annual"])).filter(x => x);
    waterEUI = masterList.map(x => parseFloat(x["water"]["eui_annual"])).filter(x => x);

    setRanges(2, Math.min(...elecEUI), Math.max(...elecEUI));
    setRanges(3, Math.min(...elecUse), Math.max(...elecUse));
};


function getNewSummary() {
    return "to be implemented once API is done";
    document.getElementById("loading-text").classList.remove("hidden");
    document.getElementById("sb-start-date").disabled = true;
    document.getElementById("sb-end-date").disabled = true;
    var startDate = document.getElementById("sb-start-date").value;
	var endDate = document.getElementById("sb-end-date").value;

    // changed to get this from our own endpoint to enable caching - UPDATE: disabled for now
    // var uri="getdata/summary?" +
	var uri="api/summary?" +
        "from_time=" + encodeURIComponent(startDate) +
	    "&to_time=" + encodeURIComponent(endDate);

    callApiJSON( uri ).then((data) => {
        masterList = data;
        originalMasterList = masterList;
        getSliderRanges();
        document.getElementById("loading-text").classList.add("hidden");
        document.getElementById("sb-start-date").disabled = false;
        document.getElementById("sb-end-date").disabled = false;
    });
};

$(document).ready( function () {
    commentParent = "view-graph";

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    document.getElementById('sb-start-date').value = sideBarStartDate;
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    document.getElementById('sb-end-date').value = sideBarEndDate;

    document.getElementById("comment-bubble").classList.remove("hidden");
    document.getElementById("span-total").innerHTML = masterList.length;

    document.getElementById("building-search").addEventListener("input", filterMasterListGraph);
    document.getElementById("residential").addEventListener("click", filterMasterListGraph);
    document.getElementById("nonres").addEventListener("click", filterMasterListGraph);
    document.getElementById("mixed").addEventListener("click", filterMasterListGraph);
    document.getElementById("fromSlider1").addEventListener("input", filterMasterListGraph);
    document.getElementById("toSlider1").addEventListener("input", filterMasterListGraph);
    document.getElementById("fromSlider2").addEventListener("input", filterMasterListGraph);
    document.getElementById("toSlider2").addEventListener("input", filterMasterListGraph);
    document.getElementById("fromSlider3").addEventListener("input", filterMasterListGraph);
    document.getElementById("toSlider3").addEventListener("input", filterMasterListGraph);

    redrawGraph();
    getSliderRanges();
});
