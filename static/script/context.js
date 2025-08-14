
function showContextEdit(id) {
    var data;
    for (c of browserData.context) {
        if (c.id == id) {
            data = c;
        }
    }
    
    document.getElementById("context-container").classList.remove("hidden");

    fetchMeterListIntoDD()
        .then(populateDD)
        .then(() => {
            if (data["target_type"] == "meter") {
                document.getElementById("context-building").checked = false;
                document.getElementById("contextDD").value = data["target_id"];
            } else {
                document.getElementById("context-building").checked = true;
                for (e of browserData.meters) {
                    if (e.building_id == data["target_id"]) {
                        document.getElementById("contextDD").value = e.meter_id;
                        break;
                    }
                }
            }
        })
    
    if (data["start_timestamp"]) {
        document.getElementById("con-start-date").disabled = false;
        document.getElementById("none-from").checked = false;
        document.getElementById("con-start-date").value = data["start_timestamp"];
    } else {
        document.getElementById("con-start-date").disabled = true;
        document.getElementById("none-from").checked = true;
    }
    if (data["end_timestamp"]) {
        document.getElementById("con-end-date").disabled = false;
        document.getElementById("none-to").checked = false;
        document.getElementById("con-end-date").value = data["end_timestamp"];
    } else {
        document.getElementById("con-end-date").disabled = true;
        document.getElementById("none-to").checked = true;
    }

    if (document.querySelector('input[name="context-type"][value="'+data["context_type"]+'"]') != null) {
        document.querySelector('input[name="context-type"][value="'+data["context_type"]+'"]').checked = true;
        document.getElementById("context-other-text").value = "";
        document.getElementById("context-other-text").disabled = true;
    } else {
        document.querySelector('input[name="context-type"][value="Other"]').checked = true;
        document.getElementById("context-other-text").value = data["context_type"];
        document.getElementById("context-other-text").disabled = false;
    }

    document.getElementById("context-comment").value = data["comment"];
    document.getElementById("context-button").setAttribute("context-id", data["id"]);
};

function deleteContext(id) {
    fetch(BASE_PATH + "/api/context/delete?contextID="+id, {method: 'POST'})
    .then(response => response.text())
    .then(data => {
        // does't really return anything
        location.reload();
    });
};

function initContextTable(userEmail, userLevel) {
    // remove all "deleted" context elements, can add some checkbox for that later
    var contextFiltered = [];
    for (i in browserData.context) {
        if (browserData.context[i]["deleted"] == "1") {
            continue
        } else {
            contextFiltered.push(browserData.context[i]);
        }
    }

    let contextTable = $('#contextTable').DataTable({
		"data": contextFiltered,
		"pageLength": 25,
        columns: [
            {data: "id", visible: false},
            {data: "author", title: "Author"},
            {data: "target_type", title: "Scope"},
            {data: "target_id", title: "Meter or Building ID"},
            {data: "start_timestamp", title: "Start"},
            {data: "end_timestamp", title: "End"},
            {data: "context_type", title: "Type of Context"},
            {data: "comment", title: "Comment"},
            {data: "id", title: "",
                render: function (data, type, row) {
                    if (userLevel >= 4 || row.author === userEmail) {
                        return "<button type='button' onclick='showContextEdit("+data+")'>Edit</button> "+
                            "<button type='button' onclick='if(confirm(\"Are you sure you want to delete this context element?\")) deleteContext("+data+");'>Delete</button>";
                    }
                    return "";
                }
            }
        ]
	});
}

$(document).ready(async function () {
    try {
        const { getcontext } = await getData({
            getcontext: {}
        });

        browserData.context = getcontext;

        const userEmail = getCookie("Email");
        const sessionID = getCookie("SessionID");
        const userLevelData = await getData({
            userLevel: {
                email: userEmail,
                SessionID: sessionID
            }
        });
        const userLevel = parseInt(userLevelData.userLevel);

        if (browserData.context) {
            initContextTable(userEmail, userLevel);
        }
    } catch (err) {
        console.error("Failed to load data", err);
    }

    document.getElementById("context-header").firstElementChild.innerHTML = "Edit Context Information";
    document.getElementById("context-button").innerHTML = "Save Context";
    document.getElementById("context-button").setAttribute("action", "edit");
});
