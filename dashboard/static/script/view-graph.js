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
            //console.log(pData['y']+" "+pData['x']+" "+pData['bmt'])
            //console.log(pData['y'][i]+" "+pData['x'][i]+" "+pData['bmt'][i])
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
                viewEnergyData(contextMeterClicked.slice(0, 5));
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

$(document).ready( function () {

    redrawGraph();
});
