//var devices;
var deviceTable;

$(document).ready( function () {
    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "deviceTable";
    //devices = devicesOffline;
    deviceTable = $('#deviceTable').DataTable({
        data: devices,
		"pageLength": 25,
        "columns": [
			{"data": varNameDevSensorID, "title": "Sensor ID"},
			{"data": null,
                render: function (data, type, row) {
                    if (typeof row[varNameDevLastObs] != "string") {
                        return "None";
                    } else {
                        return row[varNameDevLastObs].replace("T", " ").slice(0, -8);
                    }
                },
                "title": "Last data point"},

			{"data": "perc", "defaultContent": "", "title": "Percentage pings"},

			{"data": varNameDevMeasuringShort, "title": "Building"},
            {"data": varNameDevBuilding, "title": "Building Code"},
			{"data": varNameDevMeasuringLong, "title": "Measuring What?"},
			{"data": varNameDevSensorLocation, "title": "Sensor Location"},
			{"data": varNameDevSensorType, "title": "Sensor Type"},
			{"data": varNameDevClass, "title": "Rate/Cum."},
			{"data": varNameDevResolution, "title": "Resolution"},
			{"data": varNameDevUnits, "title": "Measured Units"},

            {"data": varNameDevMeterLevel, "title": "Meter Level"},
            {"data": varNameDevBuildingLevelMeter, "title": "Building Level Meter?"},

            {"data": varNameDevInvoiced, "title": "Invoiced?"},
            {"data": varNameDevTenant, "title": "Tenant?"},
			{"data": varNameDevTenantName, "title": "Tenant Name"},
        ],
        createdRow: function (row, data, dataIndex) {
            $(row).attr("data-sensor", data[varNameDevSensorID]);
        }
    });

    let colHeaders = deviceTable.columns().header().toArray();
    for (c in colHeaders) {
        let elem = "<button class='toggle-vis' data-column='" + c + "'>";
        elem += colHeaders[c].innerText + "</button> ";
        document.getElementById("dt-cols-toggles").innerHTML += elem;
    }

    document.querySelectorAll('button.toggle-vis').forEach((el) => {
        el.addEventListener('click', function (e) {
            e.preventDefault();
    
            let columnIdx = e.target.getAttribute('data-column');
            let column = deviceTable.column(columnIdx);
            column.visible(!column.visible());

            let urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('hidden')) {
                if (urlParams.get('hidden') == columnIdx) {
                    window.history.pushState({},"", "devices.html");
                } else {
                    hiddenCols = ";" + urlParams.get('hidden') + ";";
                    if (hiddenCols.includes(";"+columnIdx+";")) {
                        hiddenCols = hiddenCols.replace(";"+columnIdx+";", ";");
                    } else {
                        hiddenCols += columnIdx;
                    }
                    hiddenCols = hiddenCols.replace(";;", ";");
                    window.history.pushState({},"", "devices.html?hidden="+hiddenCols);
                }
            } else {
                window.history.pushState({},"", "devices.html?hidden="+columnIdx);
            }
        });
    });

    let urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('hidden')) {
        let hiddenCols = urlParams.get('hidden').split(";");
        for (h of hiddenCols) {
            deviceTable.column(h).visible(false);
        };
    };

    deviceTable.on('click', 'tbody tr', function() {
        if (commentMode) return;
        viewDevice(deviceTable.row(this).data()[varNameDevSensorID]);
    });

    // for now disabled this entire thing because API endpoint took > 2 mins
    /*
    fetch("/apimeter?lastobs=true").then((response) => {
        if (response.ok) {
            return response.json()
        } else {
            data = devicesOffline;
            return data;
        }
    })
    .then(data => {
        devices = data;
        // instead of the above, only put lastobs in the array and then clear
        // but first/alternatively figure out why this call takes so long!
        //deviceTable.clear();
        deviceTable.rows.add(data).draw();
    })
    */

    fetch("api/meter_ping?summary=perc").then(res => {
        if (res.ok) return res.json();
    }).then(data => {
        if (data == null) return;
        for (d of devices) {
            d["perc"] = "0 %";
            if (d[varNameDevSensorID] in data) {
                if (data[d[varNameDevSensorID]] != null) {
                    d["perc"] = data[d[varNameDevSensorID]] + " %";
                }
            }
        }
        deviceTable.clear();
        deviceTable.rows.add(devices).draw();
    });

});
