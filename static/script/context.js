function showContextEdit(id) {
    var data;
    for (c of browserData.context) {
        if (c.id == id) {
            data = c;
        }
    }
    
    document.getElementById("context-container").classList.remove("hidden");

    populateDD();
    document.getElementById("contextDD").value = data["meter"];
    document.getElementById("con-start-date").value = data["start"];
    document.getElementById("con-end-date").value = data["end"];

    if (document.querySelector('input[name="context-type"][value="'+data["type"]+'"]') != null) {
        document.querySelector('input[name="context-type"][value="'+data["type"]+'"]').checked = true;
        document.getElementById("context-other-text").value = "";
        document.getElementById("context-other-text").disabled = true;
    } else {
        document.querySelector('input[name="context-type"][value="Other"]').checked = true;
        document.getElementById("context-other-text").value = data["type"];
        document.getElementById("context-other-text").disabled = false;
    }

    document.getElementById("context-comment").value = data["comment"];
    document.getElementById("context-button").setAttribute("context-id", data["id"]);
};

function deleteContext(id) {
    // TODO-CONTEXTSQL change this once context gets moved to SQL
    fetch(BASE_PATH + "/deletecontext?contextID="+id, {method: 'POST'})
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
            {data: "start", title: "Start",
                render: function (data, type, row) {
                    if (row["startnone"] == true) {
                        return "None";
                    } else {
                        return row["start"];
                    }
                }
            },
            {data: "end", title: "End",
                render: function (data, type, row) {
                    if (row["endnone"] == true) {
                        return "None";
                    } else {
                        return row["end"];
                    }
                }
            },
            {data: "type", title: "Type of Context"},
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
