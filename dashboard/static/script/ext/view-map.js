// define globals
var mazeMarker;
var curBuilding = [];
var myMap;

// dirty workaround - empty polygon for when we delete a search entry.
var emptyPolygon = [{"type":"Feature", "geometry":{"type":"Polygon",
    "coordinates":[[[-2.784911788191609, 54.00761655528876], [-2.784911434538633, 54.007616796493075]]]}}];

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
		campuses: 341,
		center: {lng: -2.780372, lat: 54.008809},
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
	clearBuildingMarker();
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
	if (building == null) {
		return;
	}
	
	building.properties.zLevel = 0;
	myMap.highlighter.highlight(building);
	const lngLat = Mazemap.Util.getPoiLngLat(building);
	myMap.flyTo({center: lngLat, speed: 0.5});
	buildingPopup(building, e);
};

function clearBuildingMarker() {
	if(mazeMarker){
		mazeMarker.remove();
	}
	myMap.highlighter.clear();
	document.getElementById("building-popup").style.display = "none";
};

function buildingPopup(building, e) {
	for (b of masterList) {
		if (b["mazemapID"] == building.properties.id) {
			curBuilding = b;
		}
	}
	
	// list of meta data wanted
	let wanted = [
		"Building Name",
		"Planon Code",
		"Floor Size",
		"Type",
		"Year Built",
		"Campus Zone",
		"Main Meters:",
		"Electricity",
		"Gas",
		"Heat",
		"Water"
	]
	
	// print building meta data in table
	let text = "<table border='0' class='b-popup'>"
	for (w of wanted) {
		let val = curBuilding[w];
		if (val == "") {
			val = "(n/a)";
		}
		if (w == "Floor Size") {
			text += "<tr><td style='font-weight: bold;'>" + w + "</td><td>" + val + " sqm</td></tr>";
		} else if (w == "Building Name") {
			text += "<tr><th colspan='2' style='font-size: 1.2em;'>" + val + "<br><br></th></tr>";
		} else if (w == "Main Meters:") {
			text += "<tr><th colspan='2'><br>" + w + "</th></tr>";
		} else {
			text += "<tr><td style='font-weight: bold;'>" + w + "</td><td>" + val + "</td></tr>";
		}
	}
	text += "</table>"
	//text += "<br><div class='centered'><button onclick='viewEnergyData(&quot;"+curBuilding['Property.code']+"&quot;)'  class='energy_view_button'>View energy data</button></div>"
	//text += "<br><div class='centered'><button onclick='viewEnergyData()' class='energy_view_button'>View energy data</button></div>"
	text += "<br><div class='centered'><button onclick='viewEnergyData()' class='button-type'>View energy data</button></div>"
	document.getElementById("building-popup").innerHTML = text;
	document.getElementById("building-popup").style.top = e.point['y'];
	document.getElementById("building-popup").style.left = e.point['x'];
	document.getElementById("building-popup").style.display = "inline";
	// store so we can re-access in case we want the detailed view
	curBuilding = curBuilding;
};

function highlightBuildingsList() {
    let mazeIDs = masterList.map(b => parseInt(b["mazemapID"]));
	let selectedBuildings = [];
	for (b of allBuildings) {
		if (mazeIDs.includes(b.properties.id)) {
			selectedBuildings.push(b);
		}
	}
	myMap.getSource("custom-polygon-layer").setData({type: "FeatureCollection", features: selectedBuildings});
};

function viewEnergyData() {
    document.getElementById("building-popup").style.display = "none";
	clearBuildingMarker();
    viewBuilding(curBuilding);
};
