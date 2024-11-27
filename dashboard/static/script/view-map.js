// define globals
var myMap;
var clickedOn = "";

$(document).ready( function () {
    if (testGraphMode) {
        return;
    }

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
    });
});

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
    if (commentParent == "view-map") {
        document.getElementById("building-popup").style.display = "none";
        clearBuildingMarker();
    }
    viewBuilding(buildingID);
};
