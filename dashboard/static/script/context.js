function showContextEdit(id) {
    var data;
    for (c of context) {
        if (c.id == id) {
            data = c;
        }
    }
    
    document.getElementById("context-container").classList.remove("hidden");

    populateDD();
    document.getElementById("contextDD").value = data["sensor"];
    document.getElementById("con-start-date").value = data["start"];
    document.getElementById("con-end-date").value = data["end"];
    document.getElementById("fuzzy-from").checked = data["startfuzzy"];
    document.getElementById("fuzzy-to").checked = data["endfuzzy"];

    if (document.querySelector('input[name="context-type"][value="'+data["type"]+'"]') != null) {
        document.querySelector('input[name="context-type"][value="'+data["type"]+'"]').checked = true;
        document.getElementById("context-other-text").value = "";
        document.getElementById("context-other-text").disabled = true;
    } else {
        document.querySelector('input[name="context-type"][value="Other"]').checked = true;
        document.getElementById("context-other-text").value = data["type"];
        document.getElementById("context-other-text").disabled = false;
    }

    if (data["type"] == "Recurring") {
        document.getElementById("recurring-number").value = data["recurring-number"];
        document.querySelector('input[name="context-recurring"][value="'+data["recurring-time"]+'"]').checked = true;
    }

    document.getElementById("recurring-number").disabled = !$('#context-type-recurring').is(':checked');
    setRadioButtons("context-recurring", !$('#context-type-recurring').is(':checked'));

    document.getElementById("context-comment").value = data["comment"];
    document.getElementById("context-button").setAttribute("context-id", data["id"]);
};

function deleteContext(id) {
    fetch("deletecontext?contextID="+id, {method: 'POST'})
    .then(response => response.text())
    .then(data => {
        // does't really return anything
        location.reload();
    });
};

$(document).ready( function () {
    if (context == "Context file missing") {
        return;
    }

    // remove all "deleted" context elements, can add some checkbox for that later
    var contextFiltered = [];
    for (i in context) {
        if (context[i]["deleted"] == "1") {
            continue
        } else {
            contextFiltered.push(context[i]);
        }
    }

    var contextTable = $('#contextTable').DataTable({
		"data": contextFiltered,
		"pageLength": 25,
        columns: [
            {data: "id", visible: false},
            {data: "author", title: "Author"},
            {data: "sensor", title: "Sensor"},
            {data: "start", title: "Start",
                render: function (data, type, row) {
                    if (row["startnone"] == true) {
                        return "None";
                    } else {
                       return row["startfuzzy"] == false ? data : "Ca. "+data;
                    }
                }
            },
            //{data: "startfuzzy", title: "Exact Start", render: function (data) { return data == true ? "No" : "Yes"; }},
            {data: "end", title: "End",
                render: function (data, type, row) {
                    if (row["endnone"] == true) {
                        return "None";
                    } else {
                        return row["endfuzzy"] == false ? data : "Ca. "+data;
                    }
                }
            },
            //{data: "endfuzzy", title: "Exact End", render: function (data) { return data == true ? "No" : "Yes"; }},
            {data: "type", title: "Type of Context",
                render: function (data, type, row) {
                    return data == "Recurring" ? "Recurring every "+row["recurring-number"]+" "+row["recurring-time"] : data;
                }                
            },
            {data: "comment", title: "Comment"},
            {data: "id", title: "",
                render: function (data) {
                    return "<button type='button' onclick='showContextEdit("+data+")'>Edit</button> "+
                        "<button type='button' onclick='if(confirm(\"Are you sure you want to delete this context element?\")) deleteContext("+data+");'>Delete</button>";
                }                
            }
        ]
	});

    document.getElementById("context-header").firstElementChild.innerHTML = "Edit Context Information";
    document.getElementById("context-button").innerHTML = "Save Context";
    document.getElementById("context-button").setAttribute("action", "edit");
});
