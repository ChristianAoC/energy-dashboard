// define globals
let myMap;
let clickedOn = "";
let contextMarkers = [];
getCommonData().then((common) => {
    window.devices = common.devices;
    window.masterlist = common.masterlist;
});

$(document).ready( function () {
    let navHeight = document.getElementById("nav-top-bar").offsetHeight;
    let sideW = document.getElementById("map-sidebar").offsetWidth;
    document.getElementById("view-map").style.marginTop = navHeight + "px";
    document.getElementById("view-map").style.height = "calc(100% - " + navHeight + "px)";
    document.getElementById("view-map").style.marginLeft = sideW + "px";
    document.getElementById("view-map").style.width = "calc(100% - " + sideW + "px)";
    let h2 = parseInt(document.getElementById("nav-top-bar").offsetHeight) + 24;
    document.getElementById("map-sidebar").style.height = "calc(100vh - " + h2 + "px)";                    

    myMap = new Mazemap.Map({
        container: 'view-map',
        //campuses: 341,
        campuses: mazemapCampusID,
        center: {lng: mazemapLng, lat: mazemapLat},
        zoom: 15.1,
        zLevel: 1,
        scrollZoom: true,
        doubleClickZoom: false,
        touchZoomRotate: false
    });

    myMap.on('load', function(){
        // Initialize a Highlighter for POIs
        // Storing the object on the map just makes it easy to access for other things
        
        myMap.highlighter = new Mazemap.Highlighter( myMap, {
            showOutline: true,
            showFill: true,
            outlineColor: Mazemap.Util.Colors.MazeColors.MazeBlue,
            fillColor: Mazemap.Util.Colors.MazeColors.MazeBlue
        } );
        
        myMap.addLayer({
            id: 'custom-polygon-layer',
            type: "fill",
            source: {
                type: 'geojson',
                data: null,
            },
            paint: {
                "fill-color": "blue",
                "fill-opacity": 0.1,
                "fill-outline-color": "red" // TBD check if we can change opacity
            }
        });
                
        myMap.on('click', onMapClick);
        // Add zoom and rotation controls to the map.
        myMap.addControl(new Mazemap.mapboxgl.NavigationControl());
        
        highlightBuildingsList();

        let sensors = "";
        for (let b of masterList) {
            for (let t of ["electricity", "gas", "heat", "water"]) {
                if (b[t] && b[t]["sensor_uuid"] && b[t]["sensor_uuid"].length > 0) {
                    sensors += b[t]["sensor_uuid"].join(";") + ";";
                }
            }
        }

        let uri = "getcontext?sensor=" + sensors +
                "&start=" + getCurPageStartDate() +
                "&end=" + getCurPageEndDate();

        fetch(uri, { method: 'GET' })
            .then(response => response.json())
            .then(data => {
                displayContextMarkers(data["context"]);
            });
    });
});

function clearContextMarkers() {
    for (let m of contextMarkers) {
        m.remove();
    }
    contextMarkers = [];
}

function displayContextMarkers(contextData) {
    clearContextMarkers();

    for (let e of contextData) {
        for (let b of masterList) {
            for (let t of ["electricity", "gas", "heat", "water"]) {
                if (b[t] && b[t]["sensor_uuid"].includes(e.sensor)) {
                    // Found the building this sensor is in
                    const matchedBuilding = allBuildings.find(f => f.properties.id == b[varNameMLMazeMapID]);
                    if (matchedBuilding) {
                        const lngLat = Mazemap.Util.getPoiLngLat(matchedBuilding);
                        
                        const el = document.createElement('div');
                        el.className = 'context-marker';
                        el.innerHTML = "&#128161;";
                        el.style.fontSize = "20px";
                        el.style.cursor = "pointer";

                        const hoverText = "<b>Context:</b><br>" +
                            e.comment + ",<br><br>" +
                            "  Start: " + (e.startfuzzy ? "ca. " : "") + e.start + "<br>" +
                            "  End: " + (e.endfuzzy ? "ca. " : "") + e.end + "<br>" +
                            "    (Added by: " + e.author + ")";

                        const popup = new Mazemap.mapboxgl.Popup({
                            closeButton: true,
                            closeOnClick: true
                        }).setHTML(hoverText);

                        const marker = new Mazemap.mapboxgl.Marker(el)
                            .setLngLat(lngLat)
                            .addTo(myMap);

                        el.addEventListener('mouseenter', () => {
                            popup.setLngLat(lngLat).addTo(myMap);
                        });

                        el.addEventListener('mouseleave', () => {
                            popup.remove();
                        });
                        
                        contextMarkers.push(marker);
                    }
                }
            }
        }
    }
}

// Utility function for getting the first feature matching the given layer name
function getFirstFeatureWithLayerName(features, layerNames) {
	for( let i = 0; i < features.length; i++ ){
		const id = features[i].layer.id;
		for( let n = 0; n < layerNames.length; n++ ){
			if( id === layerNames[n] ) { return features[i] }
		}
	}
	return null;
};

function onMapClick(e) {
	const features = myMap.queryRenderedFeatures(e.point);
	const buildingLabel = getFirstFeatureWithLayerName(features, ["mm-building-label"]);
	const buildingFeature = getFirstFeatureWithLayerName(features, ["mm-building-fill"]);
	// Only trigger building click if the click was on the label,
	// or on the building, and we are far enough zoomed out.
	let shouldHandleBldClick = buildingLabel || (myMap.getZoom() < 17 && buildingFeature);
	if (!shouldHandleBldClick) {
		return;
	}
	// Get building id from feature
	let buildingId = buildingLabel? buildingLabel.properties.id : buildingFeature.properties.id;
	
	let i = 0;
	let building;
	do {
		if (allBuildings[i].properties.id == buildingId) {
			building = allBuildings[i];
			i = 100000000;
		} else {
			i++;
		}
	} while (i < allBuildings.length);
	
    if (commentMode) {
        for (b of masterList) {
            if (building != null && b[varNameMLMazeMapID] == building.properties.id) {
                for (t of ["electricity", "gas", "heat", "water"]) {
                    if (b[t]["sensor_uuid"].length > 0) {
                        clickedOn = b[t]["sensor_uuid"][0];
                        return;
                    }
                }
            }
        }
    }

    if (building == null) {
		return;
	}
    building.properties.zLevel = 0;
   
	clearBuildingMarker();
	myMap.highlighter.highlight(building);
	const lngLat = Mazemap.Util.getPoiLngLat(building);
	myMap.flyTo({center: lngLat, speed: 0.5});
	buildingPopup(building, e);
};

function clearBuildingMarker() {
    clickedOn = "";
	myMap.highlighter.clear();
	document.getElementById("building-popup").style.display = "none";
};

function buildingPopup(building, e) {
    var curBuilding = [];
	for (b of masterList) {
		if (b[varNameMLMazeMapID] == building.properties.id) {
			curBuilding = b;
		}
	}
	
	let text = "<table border='0' class='b-popup'>"
    text += "<tr><th colspan='2' style='font-size: 1.2em;'>" + curBuilding[varNameMLBuildingName] + "<br><br></th></tr>";
    text += "<tr><td style='font-weight: bold;'>Building Code</td><td>" + curBuilding[varNameMLBuildingID] + "</td></tr>";
    if (curBuilding[varNameMLBuildingGroup] != curBuilding[varNameMLBuildingID] && curBuilding[varNameMLBuildingGroup] != "") {
        text += "<tr><td style='font-weight: bold;'>Building Group</td><td>" + curBuilding[varNameMLBuildingGroupName] + "</td></tr>";
    }
    text += "<tr><td style='font-weight: bold;'>Floor Area</td><td>" + curBuilding[varNameMLFloorSize] + " m&sup2;</td></tr>";
    text += "<tr><td style='font-weight: bold;'>Res/Non-res</td><td>" + curBuilding[varNameMLUsage] + "</td></tr>";
    text += "<tr><td style='font-weight: bold;'>Year Built</td><td>" + curBuilding[varNameMLYearBuilt] + "</td></tr>";
    text += "<tr><th colspan='2'><br>Main sensors:</th></tr>";
    for (t of ["electricity", "gas", "heat", "water"]) {
        if (curBuilding[t]["sensor_uuid"] != null && curBuilding[t]["sensor_uuid"].length > 0) {
            text += "<tr><td style='font-weight: bold;'>" + capFirst(t) + "</td>";
            text += "<td>" + curBuilding[t]["sensor_uuid"].join("<br>") + "</td></tr>";
            text += "<tr><td style='font-weight: bold;'>" + capFirst(t) + " Usage</td>";
            text += "<td>" + curBuilding[t]["usage"] + " " + curBuilding[t]["unit"] + "</td></tr>";
        }
    }
	text += "</table>"
	text += "<br><div class='centered'><button onclick='viewEnergyData(\""+curBuilding[varNameMLBuildingID]+"\")' class='button-type'>View energy data</button></div>"

	document.getElementById("building-popup").innerHTML = text;
	document.getElementById("building-popup").style.top = e.point['y'];
	document.getElementById("building-popup").style.left = e.point['x'];
	document.getElementById("building-popup").style.display = "inline";
};

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape' && document.getElementById("building-popup").style.display == "inline") {
		clearBuildingMarker();
	}
});

function highlightBuildingsList() {
    let mazeIDs = masterList.map(b => parseInt(b[varNameMLMazeMapID]));
	let selectedBuildings = [];
	for (b of allBuildings) {
		if (mazeIDs.includes(b.properties.id)) {
			selectedBuildings.push(b);
		}
	}
	myMap.getSource("custom-polygon-layer").setData({type: "FeatureCollection", features: selectedBuildings});
};

function viewEnergyData(buildingID) {
    if (commentMode) {
        return;
    }
    /* not sure i still need this...
    if (commentParent == "view-map") {
        document.getElementById("building-popup").style.display = "none";
        clearBuildingMarker();
    }
    */
    //viewBuilding(buildingID);
    window.location.href = "browser.html?ref=map&building="+buildingID;
};

/* TODO - rewrite when we have new API end */
function getNewSummary() {
    return "not yet implemented";
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

function getSliderRanges() {
    sizes = masterList.map(x => parseInt(x[varNameMLFloorSize]));
    setRanges(1, Math.min(...sizes), Math.max(...sizes));
};

function filterMasterListMap() {
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

    // slider range check for floor area
	let min = parseInt(document.getElementById("fromInput1").value);
	let max = parseInt(document.getElementById("toInput1").value);
    masterList = masterList.filter(b => (min <= parseInt(b[varNameMLFloorSize]) && max >= parseInt(b[varNameMLFloorSize])));

    document.getElementById("span-total").innerHTML = masterList.length;
    highlightBuildingsList();
};

$(document).ready( function () {
    document.getElementById("span-total").innerHTML = masterList.length;

    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "view-map";

    let sideBarStartDate = new Date(new Date() - (7*24*60*60*1000));
    sideBarStartDate = sideBarStartDate.toISOString().split('T')[0];
    document.getElementById('sb-start-date').value = sideBarStartDate;
    let sideBarEndDate = new Date();
    sideBarEndDate = sideBarEndDate.toISOString().split('T')[0];
    document.getElementById('sb-end-date').value = sideBarEndDate;

    document.getElementById("building-search").addEventListener("input", filterMasterListMap);
    document.getElementById("residential").addEventListener("click", filterMasterListMap);
    document.getElementById("nonres").addEventListener("click", filterMasterListMap);
    document.getElementById("mixed").addEventListener("click", filterMasterListMap);
    document.getElementById("fromSlider1").addEventListener("input", filterMasterListMap);
    document.getElementById("toSlider1").addEventListener("input", filterMasterListMap);

    getSliderRanges();
});
