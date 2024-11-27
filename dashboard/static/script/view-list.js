$(document).ready( function () {
    addMasterListBenchmarks();
    var buildingsTable = $('#buildingsTable').DataTable({
		"data": masterList,
		"pageLength": 10,
		"columns": [
			{"data": varNameMLBuildingName, "title": "Building Name"},
			{"data": varNameMLBuildingID, "title": "Building ID"},
			{"data": varNameMLFloorSize, "title": "Floor Size [m&sup2;]"},
			{"data": varNameMLUsage, "title": "Type"},
			{"data": varNameMLYearBuilt, "title": "Year Built"},
			// {"data": 'Campus Zone', "title": "Campus Zone"}, // PAUL: Lost this in new summary?

			{"data": 'electricity.sensor_uuid[, ]', "title": "Electricity Sensor(s)"},
			{"data": null,
                render: function (data, type, row) {
                    if (row.electricity.usage == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.electricity.usage + " " + row.electricity.unit;
                        } else {
                            return row.electricity.usage;
                        }
                    }
                },
                "title": "Electricity Usage"
            },
            {"data": null,
                render: function (data, type, row) {
                    if (row.electricity.eui_annual == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.electricity.eui_annual + " " + row.electricity.unit+"/m2";
                        } else {
                            return row.electricity.eui_annual;
                        }
                    }
                },
                "title": "Electricity Intensity"
            },
            {"data": null,
                render: function (data, type, row) {
                    if (row.electricity.bm_good == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.electricity.bm_good + " " + row.electricity.unit+"/m2";
                        } else {
                            return row.electricity.bm_good;
                        }
                    }
                },
                "title": "Electricity Benchmark \"Good\""
            },
            {"data": null,
                render: function (data, type, row) {
                    if (row.electricity.bm_typical == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.electricity.bm_typical + " " + row.electricity.unit+"/m2";
                        } else {
                            return row.electricity.bm_typical;
                        }
                    }
                },
                "title": "Electricity Benchmark \"Typical\""
            },
            {"data": 'gas.sensor_uuid[, ]', "title": "Gas Sensor"},
			{"data": null,
                render: function (data, type, row) {
                    if (row.gas.usage == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.gas.usage + " " + row.gas.unit;
                        } else {
                            return row.gas.usage;
                        }
                    }
                },
                "title": "Gas Usage"},
			{"data": 'heat.sensor_uuid[, ]', "title": "Heat Sensor"},
			{"data": null,
                render: function (data, type, row) {
                    if (row.heat.usage == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.heat.usage + " " + row.heat.unit;
                        } else {
                            return row.heat.usage;
                        }
                    }
                },
                "title": "Heat Usage"
            },
			{"data": 'water.sensor_uuid[, ]', "title": "Water Sensor"},
			{"data": null,
                render: function (data, type, row) {
                    if (row.water.usage == null) {
                        return null;
                    } else {
                        if (type === "display") {
                            return row.water.usage + " " + row.water.unit;
                        } else {
                            return row.water.usage;
                        }
                    }
                },
                "title": "Water Usage"
            }
		],
        createdRow: function (row, data, dataIndex) {
            for (t of ["water", "heat", "gas", "electricity"]) {
                if (data[t]["sensor_uuid"].length > 0) {
                    $(row).attr("data-sensor", data[t]["sensor_uuid"][0]);
                }
            }
        }
	});

    let colHeaders = buildingsTable.columns().header().toArray();
    for (c in colHeaders) {
        let elem = "<button class='toggle-vis' data-column='" + c + "'>";
        elem += colHeaders[c].innerText + "</button> ";
        document.getElementById("dt-cols-toggles").innerHTML += elem;
    }

    document.querySelectorAll('button.toggle-vis').forEach((el) => {
        el.addEventListener('click', function (e) {
            e.preventDefault();
    
            let columnIdx = e.target.getAttribute('data-column');
            let column = buildingsTable.column(columnIdx);
            column.visible(!column.visible());

            let urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('hidden')) {
                if (urlParams.get('hidden') == columnIdx) {
                    window.history.pushState({},"", "start.html");
                } else {
                    hiddenCols = ";" + urlParams.get('hidden') + ";";
                    if (hiddenCols.includes(";"+columnIdx+";")) {
                        hiddenCols = hiddenCols.replace(";"+columnIdx+";", ";");
                    } else {
                        hiddenCols += columnIdx;
                    }
                    hiddenCols = hiddenCols.replace(";;", ";");
                    window.history.pushState({},"", "start.html?hidden="+hiddenCols);
                }
            } else {
                window.history.pushState({},"", "start.html?hidden="+columnIdx);
            }
        });
    });

    let urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('hidden')) {
        let hiddenCols = urlParams.get('hidden').split(";");
        for (h of hiddenCols) {
            buildingsTable.column(h).visible(false);
        };
    };

	buildingsTable.on('click', 'tbody tr', function() {
        if (commentMode) return;
        for (b of masterList) {
            if (b[varNameMLBuildingID] == buildingsTable.row(this).data()[varNameMLBuildingID]) {
                viewBuilding(b[varNameMLBuildingID]);
            }
        }
	})
});
