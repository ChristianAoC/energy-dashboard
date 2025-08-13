var commentMode = false; // checks if the comment button was clicked and we're currently in comment mode
var commentParent = ""; // the main content div containing info that can be commented on
var contextMeterClicked = "";
var fullDD = [];

async function commentBubbleClicked() {
    if (commentMode) {
        leaveCommentMode();
    } else {
        if (commentParent != "") {
            document.getElementById(commentParent).addEventListener("click", clickCheck);
            document.getElementById(commentParent).classList.add("commenting");
        }
        document.getElementById("comment-bubble").style.background = "orange";
        document.getElementById("comment-tooltipmodeengaged").classList.remove("hidden");
        commentMode = true;
    }

    try {
        if (!browserData.meters) {
            const { meters } = await getData({ meters: {} });
            browserData.meters = meters;
        }
        fillDD(browserData.meters);
    } catch (err) {
        console.error("Failed to load data", err);
    }
};

window.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !document.getElementById("context-container").classList.contains("hidden")) {
        closeContextDialog();
    }
})

function closeContextDialog() {
    //leaveCommentMode();
    document.getElementById("context-container").classList.add("hidden");
}

// filters the DD list
function populateDD() {
    var curDD = [];

    if (commentParent == "view-benchmark" && browserData.summary) {
        let meterIDs = getMeterListFromSummary(browserData.summary);
        for (let m of fullDD) {
            if (meterIDs.some(idPair => idPair[0] === m.id)) {
                curDD.push(m);
            }
        }
    } else {
        curDD = fullDD;
    }

    var ddList = document.getElementById("contextDD");
    ddList.innerHTML = "";
    var customE = document.createElement('option');
    customE.text = "(Select a meter)"
    customE.value = "select";
    ddList.add(customE)
    for (m of curDD) {
        var option = document.createElement('option');
        option.text = m.id+" ("+m.type+", "+m.building+")";
        option.value = m.id;
        ddList.add(option);
    }
    var customE = document.createElement('option');
    customE.text = "Unknown (add details in comments)"
    customE.value = "unknown";
    ddList.add(customE);
};

function leaveCommentMode() {
    commentMode = false;
    document.getElementById("comment-bubble").style.background = "white";
    document.getElementById("comment-tooltipmodeengaged").classList.add("hidden");
    document.getElementById(commentParent).classList.remove("commenting");
    document.getElementById(commentParent).removeEventListener("click", clickCheck);
}

function updateBuildingSpan() {
    const ddElem = document.getElementById("contextDD");
    const curBuilding = document.getElementById("current-context-building");
    const clickedMeter = ddElem.value;

    if (!clickedMeter || clickedMeter === "select") {
        curBuilding.textContent = "(No building selected)";
        curBuilding.removeAttribute("data-building-id");
    } else {
        const meterObj = browserData.meters.find(m => m[metaLabel["meter_id"]] === clickedMeter);

        if (!meterObj) {
            curBuilding.textContent = "(Unknown building)";
            curBuilding.removeAttribute("data-building-id");
            return;
        }

        const buildingId = meterObj[metaLabel["building_id"]];
        
        // TODO change this to building name once backend provides it
        curBuilding.textContent = buildingId;
        
        curBuilding.setAttribute("data-building-id", buildingId);
    }
}

async function createContextDialog(clickedMeter, from, to) {
    const userEmail = getCookie("Email");
    const sessionID = getCookie("SessionID");

    const userLevelData = await getData({
        userLevel: {
            email: userEmail,
            SessionID: sessionID
        }
    });

    const userLevel = parseInt(userLevelData.userLevel);

    if (userLevel >= 4) {
        document.getElementById("mute-global-row").style.display = "block";
    }

    populateDD();
    document.getElementById("context-container").classList.remove("hidden");

    document.getElementById("context-type-comment").checked = true;
    document.getElementById("context-other-text").value = "";
    document.getElementById("context-comment").value = "";

    var ddElem = document.getElementById("contextDD");
    var curBuilding = document.getElementById("current-context-building");

    if (clickedMeter == "" || clickedMeter == null) {
        ddElem.value = "select";
        curBuilding.innerHTML = "(No building selected)";
    } else {
        ddElem.value = clickedMeter;
        updateBuildingSpan();
    }

    if (from == null) {
        document.getElementById("none-from").checked = true;
        document.getElementById("con-start-date").disabled = $('input#none-from').is(':checked');
    } else {
        document.getElementById("con-start-date").value = from;
    }

    if (to == null) {
        document.getElementById("none-to").checked = true;
        document.getElementById("con-end-date").disabled = $('input#none-to').is(':checked');
    } else {
        document.getElementById("con-end-date").value = to;
    }
};

function clickCheck(e) {
    if (!commentMode) { // shouldn't need this as listener is removed, but just for safety
        console.warn("Comment mode left (safety catch function)")
        return;
    }

    var clickedMeter = "";

    if (commentParent == "view-map") {
        if (clickedOn != "") {
            for (let utility of utilityTypes) {
                const meters = clickedOn[utility];
                if (Array.isArray(meters) && meters.length > 0) {
                    clickedMeter = meters[0];

                    const buildingId = clickedOn.meta[metaLabel["building_id"]];
                    const buildingName = clickedOn.meta[metaLabel["building_name"]];

                    const buildingCheckbox = document.getElementById("context-building");
                    buildingCheckbox.checked = true;

                    const curBuilding = document.getElementById("current-context-building");
                    curBuilding.textContent = buildingName; // overwritten anyways... fix below once we have that info
                    curBuilding.setAttribute("data-building-id", buildingId);

                    document.getElementById("con-start-date").disabled = true;
                    document.getElementById("con-end-date").disabled = true;

                    document.getElementById("none-from").checked = true;
                    document.getElementById("none-to").checked = true;

                    break;
                }
            }
        }

    } else if (commentParent == "view-benchmark") {
        if (contextMeterClicked != "") {
            clickedMeter = contextMeterClicked;
            contextMeterClicked = "";
        }

    } else if (commentParent == "view-browser") {
        clickedMeter = document.getElementById('select-meter').value;

    } else if (commentParent == "healthcheckTable") {
        clickedMeter = e.target.closest("tr").getAttribute("data-meter");
    }

    createContextDialog(clickedMeter, getCurPageStartDate(), getCurPageEndDate());
    leaveCommentMode();
};

function htmlEscape(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("/", "&#47;")
      .replaceAll("\\", "&#92;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
}

function saveContext() {
    if (commentParent == "healthcheckTable") {
        var table = $('#healthcheckTable').DataTable();
        var rowNode = $('#healthcheckTable tbody tr[data-meter="' + document.getElementById("contextDD").value + '"]');
        //var row = table.row(rowNode);
        var cellNode = rowNode.find('td.lastCol');
        var currentHTML = cellNode.html();
        if (currentHTML != "") {
            currentHTML += "<br>";
        }
        currentHTML += "<b>";
        currentHTML += (getCookie("Email") != "") ? getCookie("Email").split('@')[0] : "(anonymous)";
        currentHTML += "</b>: ";
        currentHTML += document.getElementById("context-comment").value;
        cellNode.html(currentHTML);
    }

    var submitType = document.querySelector('input[name="context-type"]:checked').value;
    if (submitType == "Other") {
        submitType = document.getElementById("context-other-text").value;
    }

    const selectedMeter = document.getElementById("contextDD").value;
    const applyToBuilding = document.getElementById("context-building").checked;

    // Use building ID if checkbox is ticked; else use meter ID
    let targetType, targetId;

    if (applyToBuilding) {
        targetType = "Building";
        targetId = document.getElementById("current-context-building").textContent.trim();
    } else {
        targetType = "Meter";
        targetId = selectedMeter;
    }

    let start_ts = document.getElementById("con-start-date").value;
    if (document.getElementById("none-from").checked) start_ts = null;

    let end_ts = document.getElementById("con-end-date").value;
    if (document.getElementById("none-to").checked) end_ts = null;

    const toSubmit = {
        author: getCookie("Email") || "(anonymous)",
        target_type: targetType,
        target_id: targetId,
        start: start_ts,
        end: end_ts,
        type: submitType,
        comment: htmlEscape(document.getElementById("context-comment").value)
    };

    var action = document.getElementById("context-button").getAttribute("action");
    toSubmit["id"] = document.getElementById("context-button").getAttribute("context-id");

    // this dialog is used to call either savecontext or editcontext endpoint
    fetch(BASE_PATH + "/api/context/" + action, {
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": JSON.stringify(toSubmit),
    })
    .then(res => res.text())
    .then(res => {
        // at the moment doesn't check and always returns success
        //location.reload();
        // add some feedback that context event has been added
        closeContextDialog();
    });
};

function setRadioButtons(name, state) {
    for (n of document.getElementsByName(name)) {
        n.disabled = state;
    }
};

function fillDD(data) {
    for (m of data) {
        fullDD.push({
            "id": m[metaLabel["meter_id"]],
            "type": m[metaLabel["utility_type"]],
            //"serving": m["Serving"] too long...
            "building": m[metaLabel["description"]]
        })
    }
}

$(document).ready(async function () {
    
    // to not bloat the CSS file do this
    for (e of document.querySelectorAll("div.gc-grid-element")) {
        e.style.gridArea = e.id;
    }

    document.getElementById("con-start-date").disabled = $('input#none-from').is(':checked');
    $('input#none-from').change(function(){
        document.getElementById("con-start-date").disabled = $('input#none-from').is(':checked');
    });

    document.getElementById("con-end-date").disabled = $('input#none-to').is(':checked');
    $('input#none-to').change(function(){
        document.getElementById("con-end-date").disabled = $('input#none-to').is(':checked');
    });

    document.getElementById("context-other-text").disabled = !$('#context-type-other').is(':checked');

    $('input#context-type-other').change(function(){
        document.getElementById("context-other-text").disabled = false;
    });
    $('input[type=radio]').not('#context-type-other').change(function(){
        document.getElementById("context-other-text").disabled = true;
    });

    // https://xdsoft.net/jqplugins/datetimepicker/
    jQuery('#con-start-date').datetimepicker({
        value: "2025-05-01 00:00",
        format:'Y-m-d H:i'
    });
    jQuery('#con-end-date').datetimepicker({
        value: "2025-06-10 23:50",
        format:'Y-m-d H:i'
    });

    $( function() {
        $("#context-container").draggable({
            handle: "#context-header"
        });
    });

    document.getElementById("contextDD").addEventListener("change", updateBuildingSpan);
});
