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
    const toPlot = document.getElementById("toggleGraph").checked ? metaLabel["EUI"] : metaLabel["consumption"];
    console.log( metaLabel["EUI"])
    const dataToPlot = browserData.filteredSummary || [];

    let x = [];
    let y = [];
    let customdata = [];
    let bmg = [];
    let bmt = [];

    const showBenchmarks = (toPlot === metaLabel["EUI"]);

    for (let building of dataToPlot) {
        const utilityData = building[activeTab];
        if (!utilityData || Object.keys(utilityData).length === 0) continue;

        // Take the first meter in this utility group
        const meterIds = Object.keys(utilityData);
        if (meterIds.length === 0) continue;

        const firstMeter = utilityData[meterIds[0]];
        const value = firstMeter[toPlot];

        if (value == null || isNaN(value)) continue;

        x.push(Math.round(parseFloat(value) * 100) / 100);
        y.push(building.meta[metaLabel["building_name"]] || "Unknown");
        customdata.push(meterIds[0]); // Meter ID string

        if (showBenchmarks) {
            bmg.push(firstMeter.benchmark?.good ?? null);
            bmt.push(firstMeter.benchmark?.typical ?? null);
        } else {
            bmg.push(null);
            bmt.push(null);
        }
    }

    return {
        x: x,
        y: y,
        customdata: customdata,
        bmg: bmg,
        bmt: bmt,
        marker: { color: [] },
        type: barType,
        orientation: 'h'
    };
}

function redrawGraph() {
    let dateDiff = new Date(document.getElementById("sb-end-date").value) - new Date(document.getElementById("sb-start-date").value);
    dateDiff = dateDiff / (24*3600*1000);
    var pData = convertMLToPlotly("bar");

    // add x-axis title
    if (document.getElementById("toggleGraph").checked) {
        pLayoutGraph["xaxis"]["title"]["text"] = capFirst(activeTab) +
            " " + uncapFirst($('label[for="toggleGraph"]')[0].lastElementChild.innerHTML) + " for " +
            //" [" + unitsEUIPlain[activeTab] + "], scaled up to annual based on " +
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
        pLayoutGraph["shapes"] = [];

        pLayoutGraph["xaxis"]["title"]["text"] = capFirst(activeTab) +
            " " + uncapFirst($('label[for="toggleGraph"]')[0].firstElementChild.innerHTML) + " for " +
            //" [" + unitsConsPlain[activeTab] + "], over " +
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
                window.location.href = "browser?ref=map&meter_id="+contextMeterClicked.slice(0, 5);
            }
        }
    });

    /* TBD context
    const meters = [];
    for (const [buildingId, buildingData] of Object.entries(browserData.hierarchy)) {
        for (const utility of utilityTypes) {
            if (buildingData[utility]) {
                meters.push(...buildingData[utility]);
            }
        }
    }

    let uri = "getcontext?meter="+meters+"&start="+getCurPageStartDate()+"&end="+getCurPageEndDate();
    fetch(uri, {method: 'GET'})
    .then(response => response.json())
    .then(data => {
        // '⚠️' data error
        // 'ℹ️' or '&#128161;' one-off/recurring
        // more: https://html-css-js.com/html/character-codes/icons/
        let annotations = [];
        for (e of data["context"]) {
            for (d in pData.customdata) {
                if (e.meter == pData.customdata[d]) {
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
    */
};

function toggleGraph() {
    redrawGraph();
};

function filterGraph() {
    const occType = metaLabel["occupancy_type"];
    const nameKey = metaLabel["building_name"];
    const areaKey = metaLabel["floor_area"];

    let filtered = Object.values(browserData.summary);

    const searchInput = document.getElementById("building-search").value.toLowerCase();
    if (searchInput.length > 0) {
        filtered = filtered.filter(b => b.meta?.[nameKey]?.toLowerCase().includes(searchInput));
    }

    if (!document.getElementById("residential").checked) {
        filtered = filtered.filter(b => !b.meta?.[occType]?.toLowerCase().includes("residential"));
    }
    if (!document.getElementById("nonres").checked) {
        filtered = filtered.filter(b => !b.meta?.[occType]?.toLowerCase().includes("non res"));
    }
    if (!document.getElementById("mixed").checked) {
        filtered = filtered.filter(b => !b.meta?.[occType]?.toLowerCase().includes("split"));
    }

    const min = parseInt(document.getElementById("fromInput1").value);
    const max = parseInt(document.getElementById("toInput1").value);
    filtered = filtered.filter(b => {
        const area = parseInt(b.meta?.[areaKey]);
        return !isNaN(area) && area >= min && area <= max;
    });

    browserData.filteredSummary = filtered;

    document.getElementById("span-total").innerHTML = filtered.length;
    redrawGraph();
}

function utilityClick(source) {
    if (source.classList.contains("active")) return;

    Array.from(document.getElementsByClassName("tab")).forEach(tab =>
        tab.id === source.id ? tab.classList.add("active") : tab.classList.remove("active")
    );

    activeTab = source.id.toLowerCase();

    // Update unit labels if needed
    // document.getElementById("span-intensity").innerHTML = "[" + unitsEUI[activeTab] + "]";
    // document.getElementById("span-consumption").innerHTML = "[" + unitsCons[activeTab] + "]";

    getGraphSliderRanges();
    filterGraph();
    redrawGraph();
}

function getGraphSliderRanges() {
    const summaryArray = Object.values(browserData.summary);

    // Range 1: floor area
    const floorSizes = summaryArray
        .map(x => parseInt(x.meta?.[metaLabel["floor_area"]]))
        .filter(x => !isNaN(x));
    setRanges(1, Math.min(...floorSizes), Math.max(...floorSizes));

    const currentType = activeTab;
    const euiVals = [];
    const usageVals = [];

    for (const b of summaryArray) {
        const utilData = b?.[currentType];
        for (const meterId in utilData) {
            const meter = utilData[meterId];
            if (meter?.[metaLabel["EUI"]] !== undefined) {
                const eui = parseFloat(meter[metaLabel["EUI"]]);
                if (!isNaN(eui)) euiVals.push(eui);
            }
            if (meter?.[metaLabel["consumption"]] !== undefined) {
                const use = parseFloat(meter[metaLabel["consumption"]]);
                if (!isNaN(use)) usageVals.push(Math.round(use));
            }
        }
    }

    if (euiVals.length > 0) {
        setRanges(2, Math.min(...euiVals), Math.max(...euiVals));
    }
    if (usageVals.length > 0) {
        setRanges(3, Math.min(...usageVals), Math.max(...usageVals));
    }
}

function getNewSummary() {
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
        browserData.filteredSummary = data;
        browserData.Summary = browserData.filteredSummary;
        getGraphSliderRanges();
        document.getElementById("loading-text").classList.add("hidden");
        document.getElementById("sb-start-date").disabled = false;
        document.getElementById("sb-end-date").disabled = false;
    });
};

$(document).ready(async function () {
    commentParent = "view-graph";

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    document.getElementById('sb-start-date').value = sideBarStartDate;
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    document.getElementById('sb-end-date').value = sideBarEndDate;

    document.getElementById("comment-bubble").classList.remove("hidden");

    document.getElementById("building-search").addEventListener("input", filterGraph);
    document.getElementById("residential").addEventListener("click", filterGraph);
    document.getElementById("nonres").addEventListener("click", filterGraph);
    document.getElementById("mixed").addEventListener("click", filterGraph);
    document.getElementById("fromSlider1").addEventListener("input", filterGraph);
    document.getElementById("toSlider1").addEventListener("input", filterGraph);
    document.getElementById("fromSlider2").addEventListener("input", filterGraph);
    document.getElementById("toSlider2").addEventListener("input", filterGraph);
    document.getElementById("fromSlider3").addEventListener("input", filterGraph);
    document.getElementById("toSlider3").addEventListener("input", filterGraph);

    try {
        const { summary } = await getData({
            summary: {}
        });

        browserData.summary = summary;
        browserData.filteredSummary = Object.values(browserData.summary);

        if (browserData.summary) {
            document.getElementById("span-total").innerHTML = Object.keys(browserData.summary).length;
            redrawGraph();
            getGraphSliderRanges();
        }
    } catch (err) {
        console.error("Failed to load data", err);
    }
});
