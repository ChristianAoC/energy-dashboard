// for testing purposes: start with graph view, stop rendering map
var testGraphMode = false;

// this is for the small sidebar tabs, used a lot so store as var
var activeTab = "electricity";

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
        masterList = data;
        addMasterListBenchmarks();
        originalMasterList = masterList;
        getSliderRanges();
        document.getElementById("loading-text").classList.add("hidden");
        document.getElementById("sb-start-date").disabled = false;
        document.getElementById("sb-end-date").disabled = false;
    });
};

function filterMasterList() {
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
    highlightBuildingsList();
    redrawGraph();

    commentParent = document.querySelector('input[name=select-view]:checked').value;
};

$(document).ready( function () {
    document.getElementById("span-total").innerHTML = masterList.length;

    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "view-map";

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    //document.getElementById('sb-start-date').value = sideBarStartDate;
    // for public release instead: issue fixed date in 2023
    document.getElementById('sb-start-date').value = "2023-02-07";
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    //document.getElementById('sb-end-date').value = sideBarEndDate;
    document.getElementById('sb-end-date').value = "2023-02-13";

    let allButtons = document.querySelectorAll(".button-type");
    allButtons.forEach(checkSetting);
    
    getSliderRanges();
    
    // from https://codepen.io/Kelderic/pen/Qjagjz
    document.getElementById('viewToggle').addEventListener('click', function(event){
        viewToggled(this, event);
    });

    if (testGraphMode) {
        document.getElementById("view-graph-select").click();
    }
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
    document.getElementById("span-intensity").innerHTML = "[" + unitsEUI[source.id] + "]";
    document.getElementById("span-consumption").innerHTML = "[" + unitsCons[source.id] + "]";
    updateRange(source.id);
    activeTab = source.id;
    filterMasterList();
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
    getNewSummary();
}

function toggleButton(ele) {
    if (ele.checked == true) {
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
