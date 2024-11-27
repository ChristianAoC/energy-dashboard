// get all sizes, usages, and EUI (below) to populate sliders once site is loaded
var sizes = masterList.map(x => parseInt(x["Floor Size"]));
var elecUse, gasUse, heatUse, waterUse;
var elecEUI, gasEUI, heatEUI, waterEUI;
var originalMasterList;
var tmpMaster;
var narrowML;
var activeTab = "Electricity";

function usageNumbers() {
    elecUse = masterList.map(x => Math.round(parseFloat(x["Electricity Usage"])));
    gasUse = masterList.map(x => Math.round(parseFloat(x["Gas Usage"])*1000)); // dm3
    heatUse = masterList.map(x => Math.round(parseFloat(x["Heat Usage"]))); // m3
    waterUse = masterList.map(x => Math.round(parseFloat(x["Water Usage"])*1000)); // dm3
}

/*
// this is to add EUI to the masterlist - should be moved to API once Paul is back.
var gasEUI = gasUse.map((x, i) => Math.round((x/sizes[i])*1000)); // cm3/sqm
var elecEUI = elecUse.map((x, i) => Math.round((x/sizes[i])*1000));
var heatEUI = heatUse.map((x, i) => Math.round((x/sizes[i])*1000)); // m3/sqm
var waterEUI = waterUse.map((x, i) => Math.round((x/sizes[i])*1000)); // cm3/sqm

masterList.forEach( (x, i) => {
    x["Electricity EUI"] = elecEUI[i];
    x["Gas EUI"] = gasEUI[i];
    x["Heat EUI"] = heatEUI[i];
    x["Water EUI"] = waterEUI[i];
})
console.log(masterList);
*/

// update EUIs - run as function because we need to re-run this once we update usage
function updateEUIs() {
    elecUse = elecUse.filter(x => !Number.isNaN(x));
    elecEUI = masterList.map(x => Math.round(parseFloat(x["Electricity EUI"]))).filter(x => !Number.isNaN(x));
    gasUse = gasUse.filter(x => !Number.isNaN(x));
    gasEUI = masterList.map(x => Math.round(parseFloat(x["Gas EUI"]))).filter(x => !Number.isNaN(x));
    heatUse = heatUse.filter(x => !Number.isNaN(x));
    heatEUI = masterList.map(x => Math.round(parseFloat(x["Heat EUI"]))).filter(x => !Number.isNaN(x));
    waterUse = waterUse.filter(x => !Number.isNaN(x));
    waterEUI = masterList.map(x => Math.round(parseFloat(x["Water EUI"]))).filter(x => !Number.isNaN(x));
};

function roundUsage() {
    // format electricity usage as it has lots of unnecessary decimals in places
    for (d of masterList) {
        if (d["Electricity Usage"] != null) {
            d["Electricity Usage"] = d["Electricity Usage"].toFixed(2);
        }
        if (d["Gas Usage"] != null) {
            d["Gas Usage"] = d["Gas Usage"].toFixed(2);
        }
        if (d["Heat Usage"] != null) {
            d["Heat Usage"] = d["Heat Usage"].toFixed(2);
        }
        if (d["Water Usage"] != null) {
            d["Water Usage"] = d["Water Usage"].toFixed(2);
        }
    };
};

function filterEmpty() {
    // filter master list of buildings before doing anything
    tmpMaster = [];
    for (let i = 0; i<masterList.length; i++) {
        let e = masterList[i];
        // only keep buildings that have at least one main meter
        if (e["Electricity"]+e["Gas"]+e["Heat"]+e["Water"] != "") {
            tmpMaster.push(e);
        }
    };
};

/*
var origMeters = {
    "Electricity": masterList.map(b => b["Electricity"]).filter(b => b != "").join(';'),
    "Gas": masterList.map(b => b["Gas"]).filter(b => b != "").join(';'),
    "Heat": masterList.map(b => b["Heat"]).filter(b => b != "").join(';'),
    "Water": masterList.map(b => b["Water"]).filter(b => b != "").join(';')
}
*/

function updateData() {
    document.getElementById("loading-text").classList.remove("hidden");
    document.getElementById("sb-start-date").disabled = true;
    document.getElementById("sb-end-date").disabled = true;
    var startDate = document.getElementById('sb-start-date').value;
	var endDate = document.getElementById('sb-end-date').value;
    
    var uri=apiUrl + "/series_obs?sid=" + origMeters +
        "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
        "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
        "&aggregate=50000H"; // this is to make it a single value, ~4y, until Paul updated the summary endpoint

    callApiJSON( uri ).then((data) => {
        for (d in data) {
            var idx = -2;
            var type = "";
            for (t of ["Electricity", "Gas", "Heat", "Water"]) {
                var tmp = originalMasterList.findIndex(x => x[t] === d);
                if (tmp >= 0) {
                    idx = tmp;
                    type = t;
                    break;
                }
            }
            if (idx < 0) {
                //console.log(d+" meter not found in original list - this is weird");
                continue;
            }
            if (typeof data[d] === undefined || data[d] == null) {
                //console.log(d+" API returned an empty element of sorts");
            } else {
                if (data[d].length < 1) {
                    //console.log(d+" no data");
                    originalMasterList[idx][type+" Usage"] = null;
                } else {
                    originalMasterList[idx][type+" Usage"] = data[d][0]["value"];
                }
            }
        }

        roundUsage()
        updateEUIs();
        masterList = originalMasterList;
        document.getElementById("loading-text").classList.add("hidden");
        document.getElementById("sb-start-date").disabled = false;
        document.getElementById("sb-end-date").disabled = false;
        });

    // this is actually super slow and doesn't really work because of the async call.
    /*
    for (type of ["Electricity", "Gas", "Heat", "Water"]) {
        var uri=apiUrl + "/series_obs?sid=" + origMeters[type] +
            "&from_time=" + encodeURIComponent(startDate) + "T00:00:00Z" +
            "&to_time=" + encodeURIComponent(endDate) + "T23:59:59Z" +
            "&aggregate=50000H"; // this is to make it a single value, ~4y, until Paul updated the summary endpoint
    
        callApiJSON( uri ).then((data) => {
            console.log(type);
            for (d in data) {
                console.log(d);
                var idx = originalMasterList.findIndex(x => x[type] === d);
                console.log(idx);
                if (typeof data[d] === undefined) {
                    console.log(d+" meter not found");
                } else {
                    if (typeof data[d][0] === "undefined") {
                        console.log(d+" no data");
                        originalMasterList[idx][type+" Usage"] = null;
                    } else {
                        originalMasterList[idx][type+" Usage"] = data[d][0]["value"];
                    }
                }
            }
        });

        updateEUIs();
    }*/
};

// TODO fix this into a proper call?
/*
async function callApiJSON(uri) {
    const response = await fetch(encodeURI(uri))
        .then(response => response.text())
        .then(text => {
        try {
            var json = JSON.parse(text);
            return json; // doesn't return because inside a .then.then MEH
        } catch(err) {
            console.log("API error: "+err);
            console.log("  on URI: "+uri);
            console.log("  response was: "+text);
            console.log("  probably faulty meter is:");
            console.log("    "+new URL(uri).searchParams.get("sid"));
        }
    })
};
*/

// function to call api for json
// TODO: need to add error catching
async function callApiJSON(uri) {
	const response = await fetch(encodeURI(uri));
	return response.json();
}

// this doesn't return anything but checks which meters are returning bogus
async function callApiJSONTester(uri) {
    const response = await fetch(encodeURI(uri))
        .then(response => response.text())
        .then(text => {
        try {
            var json = JSON.parse(text);
            console.log(json);
        } catch(err) {
            console.log("API error: "+err);
            console.log("  on URI: "+uri);
            console.log("  response was: "+text);
            console.log("  probably faulty meter is:");
            console.log("    "+new URL(uri).searchParams.get("sid"));
        }
    })
};

function filterMasterList() {
    masterList = originalMasterList;
	
	// check search input
	const searchInput = document.getElementById("building-search").value.toLowerCase();
    masterList = masterList.filter(b => b["Building Name"].toLowerCase().includes(searchInput));

	// check for type (res/non-res/split use)
	if (!(document.getElementById("residential").classList.contains("pressed"))) {
        masterList = masterList.filter(b => b["Type"] != "Residential");
	}
	if (!(document.getElementById("nonres").classList.contains("pressed"))) {
        masterList = masterList.filter(b => b["Type"] != "Non-residential");
	}
	if (!(document.getElementById("mixed").classList.contains("pressed"))) {
        masterList = masterList.filter(b => b["Type"] != "Split Use");
	}

    // slider range check
	let min = parseInt(document.getElementById("fromInput1").value);
	let max = parseInt(document.getElementById("toInput1").value);
    masterList = masterList.filter(b => (min <= parseInt(b["Floor Size"]) && max >= parseInt(b["Floor Size"])));
    
    // other sliders: for now, only do this into a "narrowML"
	let minEUI = parseInt(document.getElementById("fromInput2").value);
	let maxEUI = parseInt(document.getElementById("toInput2").value);
    narrowML = masterList.filter(b => (minEUI <= parseInt(b[activeTab+" EUI"]) && maxEUI >= parseInt(b[activeTab+" EUI"])));
	let minCons = parseInt(document.getElementById("fromInput3").value);
	let maxCons = parseInt(document.getElementById("toInput3").value);
    narrowML = narrowML.filter(b => (minCons <= parseInt(b[activeTab+" Usage"]) && maxCons >= parseInt(b[activeTab+" Usage"])));

    document.getElementById("span-total").innerHTML = masterList.length;

    if (document.querySelector('input[name=select-view]:checked').value == "view-map") {
        highlightBuildingsList();
    } else if (document.querySelector('input[name=select-view]:checked').value == "view-list") {
        $('#buildingsTable').DataTable().clear().rows.add(masterList).draw();
    } else if (document.querySelector('input[name=select-view]:checked').value == "view-graph") {
        if (!isLoading) {
            //Plotly.redraw('comparison-plot');
            redrawGraph();
        }
    }
};

usageNumbers();
updateEUIs();
roundUsage();
filterEmpty();
// TODO manually stripped:
// MC045-L01/M9R45099 (elec)
// MC042-L01/M10R20 (heat)
// MC210-L02/M9R2048 (water)
// get list of all meters so we can do update ML any time
var origMeters = masterList.map(b => b["Electricity"]).filter(b => b != "").join(';');
origMeters += ";"+masterList.map(b => b["Gas"]).filter(b => b != "").join(';');
origMeters += ";"+masterList.map(b => b["Heat"]).filter(b => b != "").join(';');
origMeters += ";"+masterList.map(b => b["Water"]).filter(b => b != "").join(';');

masterList = tmpMaster;
// since we use masterList to store the currently selected buildings, keep the orig
originalMasterList = masterList;
narrowML = masterList;

$(document).ready( function () {
    document.getElementById("span-total").innerHTML = masterList.length;

    let allButtons = document.querySelectorAll(".button-type");
    allButtons.forEach(checkSetting);
    
    setRanges(1, Math.min(...sizes), Math.max(...sizes));
    // TODO check which one is actually active on load/session
    setRanges(2, Math.min(...elecEUI), Math.max(...elecEUI));
    setRanges(3, Math.min(...elecUse), Math.max(...elecUse));
    
    // from https://codepen.io/Kelderic/pen/Qjagjz
    // TODO check why this is called twice
    document.getElementById('viewToggle').addEventListener('click', function(event){
        viewToggled(this, event);
    });

    // TODO uncomment while working on the graph view. fix that map looks shit then though...
    //document.getElementById("view-graph-select").click();
});

function viewToggled(elem, event) {
    if (event.target.tagName.toLowerCase() == 'input') {
            
        let input = event.target;
        let slider = elem.querySelector('div');
        let inputs = elem.querySelectorAll('input');
        
        slider.style.transform = `translateX(${input.dataset.location})`;
        inputs.forEach(function(inp){
            if ( inp == input ) {
                document.getElementById(inp.value).hidden = false;
                inp.parentElement.classList.add('selected');
                if (inp.value == "view-map") {
                    let h2 = parseInt(document.getElementById("nav-top-bar").offsetHeight) + 24;
                    document.getElementById("map-sidebar").style.height = "calc(100vh - " + h2 + "px)";
                    highlightBuildingsList();
                }
            } else {
                document.getElementById(inp.value).hidden = true;
                inp.parentElement.classList.remove('selected');
            }
        });
        
        filterMasterList();
    }
};

function setRanges(num, min, max) {
    document.getElementById("fromInput"+num).min = min;
    document.getElementById("toInput"+num).min = min;
    document.getElementById("fromSlider"+num).min = min;
    document.getElementById("toSlider"+num).min = min;
    document.getElementById("fromInput"+num).value = min;
    document.getElementById("fromSlider"+num).value = min;

    document.getElementById("fromInput"+num).max = max;
    document.getElementById("toInput"+num).max = max;
    document.getElementById("fromSlider"+num).max = max;
    document.getElementById("toSlider"+num).max = max;
    document.getElementById("toInput"+num).value = max;
    document.getElementById("toSlider"+num).value = max;
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
    if (source.id == "Electricity") {
        document.getElementById("span-intensity").innerHTML = "[Wh/sqm]";
        document.getElementById("span-consumption").innerHTML = "[kWh]";
    } else if (source.id == "Gas") {
        document.getElementById("span-intensity").innerHTML = "[dm³/sqm]";
        document.getElementById("span-consumption").innerHTML = "[cm³]";
    } else if (source.id == "Heat") {
        document.getElementById("span-intensity").innerHTML = "[dm³/sqm]";
        document.getElementById("span-consumption").innerHTML = "[dm³]";
    } else if (source.id == "Water") {
        document.getElementById("span-intensity").innerHTML = "[dm³/sqm]";
        document.getElementById("span-consumption").innerHTML = "[cm³]";
    }
    updateRange(source.id);
    activeTab = source.id;
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

function sliderChange() {
	filterMasterList();
};

function buttonChange() {
	filterMasterList();
};

function searchChange() {
	filterMasterList();
};

function dateChange() {
    updateData();
}

function toggleButton(ele) {
  ele.classList.toggle("pressed");
  if (ele.classList.contains("pressed")) {
	  localStorage.setItem(ele.id, true);
  } else {
	  localStorage.setItem(ele.id, false);
  }
  buttonChange();
};

function checkSetting(btn) {
	if ((localStorage.getItem(btn.id) != null) && (localStorage.getItem(btn.id) == "true")) {
		btn.classList.add("pressed");
	} else {
		btn.classList.remove("pressed");
	}
};
