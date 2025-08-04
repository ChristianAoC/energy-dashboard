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
            " " + uncapFirst($('label[for="toggleGraph"]')[0].lastElementChild.innerHTML) +
            " [" + utilityUnits[activeTab] + "/m²], over " +
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
            " " + uncapFirst($('label[for="toggleGraph"]')[0].firstElementChild.innerHTML) +
            " [" + utilityUnits[activeTab] + "], over " +
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
                window.location.href = "browser?ref=benchmark&meter_id="+contextMeterClicked;
            }
        }
    });

    // Get date strings (in ISO format or compatible with your backend)
    const startDate = document.getElementById("sb-start-date").value + " 00:00";
    const endDate = document.getElementById("sb-end-date").value + " 23:59";

    // Collect all meters from the loaded summary
    let meters = getMeterListFromSummary(browserData.summary);

    const annotations = [];

    if (browserData.context) {
        const start = new Date(startDate);
        const end = new Date(endDate);

        for (const e of browserData.context) {
            if (!meters.includes(e.meter)) continue;

            // Handle optional start/end
            const ctxStart = e.startnone ? null : new Date(e.start);
            const ctxEnd = e.endnone ? null : new Date(e.end);

            // Determine if there's any overlap
            const overlaps =
                (!ctxStart || ctxStart <= end) &&
                (!ctxEnd || ctxEnd >= start);

            if (!overlaps) continue;

            for (let d in pData.customdata) {
                if (e.meter === pData.customdata[d]) {
                    let hover = "<b>Context:</b><br>" + e.comment + ",<br><br>";

                    if (!e.startnone) hover += "  Start: " + e.start + "<br>";
                    else hover += "  (no start date)<br>";
                    if (!e.endnone) hover += "  End: " + e.end + "<br>";
                    else hover += "  (no end date)<br>";

                    hover += "    (Added by: " + e.author + ")";

                    annotations.push({
                        x: pData.x[d],
                        y: pData.y[d],
                        showarrow: false,
                        text: '&#128161;',
                        hovertext: hover
                    });
                }
            }
        }
    }

    Plotly.relayout("comparison-plot", { annotations });
}

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
    document.getElementById("span-intensity").innerHTML = "[" + utilityUnits[activeTab] + "/m²]";
    document.getElementById("span-consumption").innerHTML = "[" + utilityUnits[activeTab] + "]";

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

async function getNewSummary() {
    document.getElementById("loading-text").classList.remove("hidden");
    document.getElementById("sb-start-date").disabled = true;
    document.getElementById("sb-end-date").disabled = true;

    const startDate = document.getElementById("sb-start-date").value;
    const endDate = document.getElementById("sb-end-date").value;

    try {
        const { summary, allContext } = await getData({
            summary: {
                from_time: startDate,
                to_time: endDate
            },
            allContext: {}
        });

        if (summary) {
            if (allContext) browserData.context = allContext;
            else browserData.context = [];
            browserData.summary = summary;
            browserData.filteredSummary = Object.values(summary);
            getGraphSliderRanges();
            document.getElementById("span-total").innerHTML = Object.keys(browserData.summary).length;
            redrawGraph();
        } else {
            console.warn("No summary data returned");
        }
    } catch (err) {
        console.error("Error reloading summary data", err);
    } finally {
        document.getElementById("loading-text").classList.add("hidden");
        document.getElementById("sb-start-date").disabled = false;
        document.getElementById("sb-end-date").disabled = false;
    }
}

$(document).ready(async function () {

    commentParent = "view-benchmark";

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

    getNewSummary();
});
