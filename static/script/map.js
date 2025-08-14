// define globals
let myMap;
let clickedOn = "";
let contextMarkers = [];

function initMap() {
    myMap = new Mazemap.Map({
        container: 'view-map',
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

        filterMap();
    });
}

$(document).ready( async function () {
    try {
        const [hierarchyData, mazemapPolygons, getcontext] = await Promise.all([
            getData({ hierarchy: {} }).then(res => res.hierarchy),
            fetch(apiEndpoints.mazemap_polygons).then(res => res.json()),
            fetch(apiEndpoints.getcontext).then(res => {
                if (!res.ok) return [];
                return res.json();
            })
        ]);

        browserData.hierarchy = hierarchyData;
        browserData.filteredHierarchy = Object.values(hierarchyData);
        browserData.mazemapPolygons = mazemapPolygons;
        browserData.context = getcontext;

        if (browserData.hierarchy) {
            initMap();
            getMapSliderRanges();
        }
    } catch (err) {
        console.error("Failed to load data", err);
    }

    // some css stuff as the map needs a bit special treatment
    let navHeight = document.getElementById("nav-top-bar").offsetHeight;
    let sideW = document.getElementById("sidebar").offsetWidth;
    document.getElementById("view-map").style.marginTop = navHeight + "px";
    document.getElementById("view-map").style.height = "calc(100% - " + navHeight + "px)";
    document.getElementById("view-map").style.marginLeft = sideW + "px";
    document.getElementById("view-map").style.width = "calc(100% - " + sideW + "px)";
    let h2 = parseInt(document.getElementById("nav-top-bar").offsetHeight) + 24;
    document.getElementById("sidebar").style.height = "calc(100vh - " + h2 + "px)";                    

    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "view-map";

    document.getElementById("building-search").addEventListener("input", filterMap);
    document.getElementById("residential").addEventListener("click", filterMap);
    document.getElementById("nonres").addEventListener("click", filterMap);
    document.getElementById("mixed").addEventListener("click", filterMap);
    document.getElementById("fromSlider1").addEventListener("input", filterMap);
    document.getElementById("toSlider1").addEventListener("input", filterMap);
    document.getElementById("unmute").addEventListener("change", filterMap);
});

function updateMutedCount() {
    if (!browserData.context) return;
    const userEmail = getCookie("Email");
    const mutedMeterIds = new Set(
    browserData.context
        .filter(ctx => ctx.context_type === "Global-mute" || (ctx.context_type === "User-mute" && ctx.author === userEmail))
        .map(ctx => ctx.target_id)
    );

    const mutedCount = mutedMeterIds.size;

    // Update the muted meters count display
    const spanMutedCount = document.getElementById("span-mutedCount");
    if (spanMutedCount) {
        spanMutedCount.textContent = mutedCount;
    }

    // Show or hide the checkbox container based on mutedCount
    const mutedDiv = document.getElementById("muted-div");
    if (mutedDiv) {
        mutedDiv.style.display = mutedCount > 0 ? "block" : "none";
    }
}

function clearContextMarkers() {
    for (let m of contextMarkers) {
        m.remove();
    }
    contextMarkers = [];
}

function displayContextMarkers() {
    clearContextMarkers();

    for (let e of browserData.context) {
        if (e.target_type === "meter") {
            for (let [buildingCode, buildingObj] of Object.entries(browserData.hierarchy)) {
                for (let t of utilityTypes) {
                    const meterList = buildingObj[t] || [];
                    if (meterList.includes(e.target_id)) {
                        const mazeMapId = buildingObj.meta[metaLabel["mazemap_label"]]?.[0]; // get first MazeMap ID
                        if (mazeMapId) {
                            const matchedBuilding = browserData.mazemapPolygons.find(f => f.properties.id === mazeMapId);
                            if (matchedBuilding) {
                                placeContextMarker(matchedBuilding, e);
                            }
                        }
                    }
                }
            }
        }

        if (e.target_type === "building") {
            const buildingObj = browserData.hierarchy[e.target_id];
            if (buildingObj) {
                const mazeMapId = buildingObj.meta[metaLabel["mazemap_label"]]?.[0];
                if (mazeMapId) {
                    const matchedBuilding = browserData.mazemapPolygons.find(f => f.properties.id === mazeMapId);
                    if (matchedBuilding) {
                        placeContextMarker(matchedBuilding, e);
                    }
                }
            }
        }
    }
}

function placeContextMarker(building, contextEntry) {
    const lngLat = Mazemap.Util.getPoiLngLat(building);
    
    const el = document.createElement('div');
    el.className = 'context-marker';
    el.innerHTML = "&#128161;";
    el.style.fontSize = "20px";
    el.style.cursor = "pointer";

    const start = contextEntry.start_timestamp == null ? "No start date": contextEntry.start_timestamp;
    const end = contextEntry.end_timestamp == null ? "No end date": contextEntry.end_timestamp;
    const hoverText = "<b>Context:</b><br>" +
        contextEntry.context_type + (contextEntry.comment ? ": " + contextEntry.comment : "") + "<br><br>" +
        "Start: " + start + "<br>" +
        "End: " + end + "<br>" +
        "(Added by: " + contextEntry.author + ")";

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

	let shouldHandleBldClick = buildingLabel || (myMap.getZoom() < 17 && buildingFeature);
	if (!shouldHandleBldClick) return;

	let buildingId = buildingLabel ? buildingLabel.properties.id : buildingFeature.properties.id;

	// Lookup building directly from polygon list
	const building = browserData.mazemapPolygons.find(b => b.properties.id == buildingId);
	if (!building) return;

	// Optional: commentMode logic (skip or update later if meter_uuid not available)
	if (commentMode) {
        for (const b of Object.values(browserData.filteredHierarchy)) {
            const labels = b.meta?.[metaLabel["mazemap_label"]];
            const labelArray = Array.isArray(labels) ? labels : [labels];
            if (labelArray.includes(buildingId)) {
                clickedOn = b;
                return;
            }
        }
	}

	building.properties.zLevel = 0;

	clearBuildingMarker();
	myMap.highlighter.highlight(building);
	const lngLat = Mazemap.Util.getPoiLngLat(building);
	myMap.flyTo({ center: lngLat, speed: 0.5 });

	buildingPopup(building, e);
}

function clearBuildingMarker() {
    clickedOn = "";
	myMap.highlighter.clear();
	document.getElementById("building-popup").style.display = "none";
};

function buildingPopup(building, e) {
	// Get matching hierarchy entry by mazemap_label
	let curBuilding = null;
	const buildingId = building.properties.id;

	for (const b of Object.values(browserData.filteredHierarchy)) {
		const labels = b.meta?.[metaLabel["mazemap_label"]];
		const labelArray = Array.isArray(labels) ? labels : [labels];
		if (labelArray.includes(buildingId)) {
			curBuilding = b;
			break;
		}
	}
	if (!curBuilding) return;

	let text = "<table border='0' class='b-popup'>";
	text += `<tr><th colspan='2' style='font-size: 1.2em;'>${curBuilding.meta[metaLabel["building_name"]]}<br><br></th></tr>`;
	text += `<tr><td style='font-weight: bold;'>Building Code</td><td>${curBuilding.meta[metaLabel["building_id"]]}</td></tr>`;
	text += `<tr><td style='font-weight: bold;'>Floor Area</td><td>${curBuilding.meta[metaLabel["floor_area"]]} m&sup2;</td></tr>`;
	text += `<tr><td style='font-weight: bold;'>Res/Non-res</td><td>${curBuilding.meta[metaLabel["occupancy_type"]]}</td></tr>`;
	text += `<tr><td style='font-weight: bold;'>Year Built</td><td>${curBuilding.meta[metaLabel["year_built"]]}</td></tr>`;

	text += `<tr><th colspan='2'><br>Meters available:</th></tr>`;

	for (const t of utilityTypes) {
		const meters = curBuilding[t];
		if (meters && meters.length > 0) {
			text += `<tr><td style='font-weight: bold;'>${capFirst(t)}</td><td>${meters.length} meters</td></tr>`;
		} else {
            text += `<tr><td style='font-weight: bold;'>${capFirst(t)}</td><td>N/A</td></tr>`;
        }
	}

	text += "</table>";
	text += `<br><div class='centered'><button onclick='viewEnergyData("${curBuilding.meta[metaLabel["building_id"]]}")' class='button-generic'>View energy data</button></div>`;

	const popupEl = document.getElementById("building-popup");
	popupEl.innerHTML = text;
    // figure out a better way, too often too low - seems good now?
	//popupEl.style.top = e.point.y + "px";
	popupEl.style.left = e.point.x + "px";
	popupEl.style.display = "inline";
}

window.addEventListener('keydown', function (event) {
	if (event.key === 'Escape' && document.getElementById("building-popup").style.display == "inline") {
		clearBuildingMarker();
	}
});

function highlightBuildingsList() {
    const selectedBuildings = [];
    const buildingLookup = new Map(browserData.mazemapPolygons.map(b => [b.properties.id, b]));

    for (const buildingData of Object.values(browserData.filteredHierarchy)) {
        const labels = buildingData.meta[metaLabel["mazemap_label"]];
        if (!labels) continue;

        const labelArray = Array.isArray(labels) ? labels : [labels];

        for (const label of labelArray) {
            const match = buildingLookup.get(label);
            if (match) {
                selectedBuildings.push(match);
            }
        }
    }

    myMap.getSource("custom-polygon-layer").setData({
        type: "FeatureCollection",
        features: selectedBuildings
    });
}

function viewEnergyData(buildingID) {
    if (commentMode) {
        return;
    }
    window.location.href = BASE_PATH + "/browser?ref=map&building="+buildingID;
};

function getMapSliderRanges() {
    const sizes = Object.values(browserData.filteredHierarchy)
        .map(b => parseInt(b.meta?.floor_area))
        .filter(n => !isNaN(n));

    if (sizes.length > 0) {
        setRanges(1, Math.min(...sizes), Math.max(...sizes));
    }
};

function filterMap() {
    // Start from full dataset
    let filtered = Object.values(browserData.hierarchy);
    const userEmail = getCookie("Email");
    let mutedCount = 0;

    // Text search
    const searchInput = document.getElementById("building-search").value.toLowerCase();
    filtered = filtered.filter(b =>
        b["meta"][metaLabel["building_name"]] &&
        b["meta"][metaLabel["building_name"]].toLowerCase().includes(searchInput)
    );

    // Occupancy type filters
    if (!document.getElementById("residential").checked) {
        filtered = filtered.filter(b => b["meta"][metaLabel["occupancy_type"]] !== "Residential");
    }
    if (!document.getElementById("nonres").checked) {
        filtered = filtered.filter(b => b["meta"][metaLabel["occupancy_type"]] !== "Non Res");
    }
    if (!document.getElementById("mixed").checked) {
        filtered = filtered.filter(b => b["meta"][metaLabel["occupancy_type"]] !== "Split Use");
    }

    // Floor area filter
    let min = parseInt(document.getElementById("fromInput1").value);
    let max = parseInt(document.getElementById("toInput1").value);
    filtered = filtered.filter(b => {
        let val = parseInt(b["meta"][metaLabel["floor_area"]]);
        return !isNaN(val) && val >= min && val <= max;
    });

    // Mute filter
    const includeMuted = document.getElementById("unmute").checked;
    if (!includeMuted && browserData.context) {
        filtered = filtered.filter(building => {
            const buildingId = building.meta[metaLabel["building_id"]];

            // Check if building is muted
            const isBuildingMuted = browserData.context.some(entry =>
                entry.target_type === "building" &&
                entry.target_id === buildingId &&
                (
                    entry.context_type === "Global-mute" ||
                    (entry.context_type === "User-mute" && entry.author === userEmail)
                )
            );

            if (isBuildingMuted) {
                mutedCount++;
                return false;
            }

            // Flatten all meter IDs from utilityTypes
            const allMeterIds = utilityTypes.flatMap(type => building[type] || []);

            const allMetersMuted = allMeterIds.length > 0 && allMeterIds.every(meterId =>
                browserData.context.some(entry =>
                    entry.target_type === "meter" &&
                    entry.target_id === meterId &&
                    (
                        entry.context_type === "Global-mute" ||
                        (entry.context_type === "User-mute" && entry.author === userEmail)
                    )
                )
            );

            if (allMetersMuted) {
                mutedCount++;
                return false;
            }

            return true;
        });
    }

    // Store result
    browserData.filteredHierarchy = filtered;

    // Update UI
    document.getElementById("span-total").innerHTML = filtered.length;

    // Show/hide muted info
    const mutedDiv = document.getElementById("muted-div");
    const mutedSpan = document.getElementById("span-mutedCount");

    if (!includeMuted) {
        if (mutedDiv) mutedDiv.style.display = mutedCount > 0 ? "block" : "none";
        if (mutedSpan) mutedSpan.textContent = mutedCount;
    } else {
        const hasMuted = browserData.context.some(entry =>
            (entry.context_type === "User-mute" && entry.author === userEmail) ||
            entry.context_type === "Global-mute"
        );
        if (mutedDiv) mutedDiv.style.display = hasMuted ? "block" : "none";
    }

    updateMutedCount();
    displayContextMarkers();
    highlightBuildingsList();
}
