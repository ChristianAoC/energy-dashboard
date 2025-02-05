var commentMode = false; // checks if the comment button was clicked and we're currently in comment mode
var commentParent = ""; // the main content div containing info that can be commented on
var contextMeterClicked = "";
var fullDD = [];

function commentBubbleClicked() {
    console.log(new Date().toLocaleString().slice(12)+" commentParent: "+commentParent);
    console.log(new Date().toLocaleString().slice(12)+" commentMode: "+commentMode);
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

// filters the DD list based on the current view and adds it to the UI.
function populateDD() {
    var curDD = [];

    if (commentParent == "view-map" || commentParent == "view-list" || commentParent == "view-graph") {
        let sensorIDs = [];
        if (commentParent == "view-graph") {
            for (m of narrowML) {
                sensorIDs.push(...m[activeTab]["sensor_uuid"]);
            }
        } else {
            for (m of masterList) {
                for (t of ["electricity", "gas", "heat", "water"]) {
                    sensorIDs.push(...m[t]["sensor_uuid"]);
                }
            }
        }
        for (m of fullDD) {
            if (sensorIDs.includes(m.id)) {
                curDD.push(m);
            }
        }
    } else if (commentParent == "building-data") {
        for (m of fullDD) {
            if ([...document.getElementsByClassName("b-input-radio")].map(o => o.value).includes(m.id)) {
                curDD.push(m);
            }
        }
    } else if (commentParent == "device-data") {
        for (m of fullDD) {
            if (document.getElementById('b-button').dataset.sensor) {
                curDD.push(m);
            }
        }
    } else {
        curDD = fullDD;
    }

    var ddList = document.getElementById("contextDD");
    ddList.innerHTML = "";
    var customE = document.createElement('option');
    customE.text = "(Select a sensor)"
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

function clickCheck(e) {
    if (!commentMode) { // shouldn't need this as listener is removed, but just for safety
        console.log("Comment mode left (safety catch function)")
        return;
    }

    populateDD();
    leaveCommentMode();

    document.getElementById("context-container").classList.remove("hidden");

    var clickedSensor = "";
    var ddElem = document.getElementById("contextDD");

    document.getElementById("fuzzy-from").checked = false;
    document.getElementById("fuzzy-to").checked = false;
    document.getElementById("context-type-oneoff").checked = true;
    document.getElementById("context-other-text").value = "";
    document.getElementById("context-comment").value = "";
    document.getElementById("recurring-number").value = 1;
    document.getElementById("context-recurring-weeks").checked = true;

    // add sensor pre-set
    if (commentParent == "deviceTable") {
        clickedSensor = e.target.closest("tr").getAttribute("data-sensor");

    } else if (commentParent == "view-map") {
        if (clickedOn != "") {
            clickedSensor = clickedOn;
        }

    } else if (commentParent == "view-list") {
        var currentDDArray = [...document.getElementById("contextDD").options].map(o => o.value);
        if (currentDDArray.includes(e.target.innerHTML)) {
            clickedSensor = e.target.innerHTML;
        } else {
            clickedSensor = e.target.closest("tr").getAttribute("data-sensor");
        }

    } else if (commentParent == "view-graph") {
        if (contextMeterClicked != "") {
            clickedSensor = contextMeterClicked;
            contextMeterClicked = "";
        }

    } else if (commentParent == "building-data") {
        clickedSensor = document.querySelector('input[name="sensor"]:checked').value;

    } else if (commentParent == "device-data") {
        clickedSensor = document.getElementById('b-button').dataset.sensor;
    }

    if (clickedSensor == "" || clickedSensor == null) {
        ddElem.value = "select";
    } else {
        ddElem.value = clickedSensor;
    }

    document.getElementById("con-start-date").value = getCurPageStartDate();
    document.getElementById("con-end-date").value = getCurPageEndDate();
};

function getCurPageStartDate() {
    if (["view-map", "view-list", "view-graph"].includes(commentParent)) {
        return document.getElementById("sb-start-date").value+" 00:00";
    } else if (["building-data", "device-data"].includes(commentParent)) {
        return document.getElementById("b-start-date").value+" 00:00";
    } else {
        let setDate = new Date(Date.now());
        setDate.setDate(setDate.getDate()-7);
        //return setDate.toISOString().slice(0, 10)+" 00:00";
        return "2023-02-07 00:00";
    }
};

function getCurPageEndDate() {
    if (["view-map", "view-list", "view-graph"].includes(commentParent)) {
        return document.getElementById("sb-end-date").value+" 23:50";
    } else if (["building-data", "device-data"].includes(commentParent)) {
        return document.getElementById("b-end-date").value+" 23:50";
    } else {
        let setDate = new Date(Date.now());
        //return setDate.toISOString().slice(0, 10)+" 23:50";
        return "2023-02-13 23:50";
    }
};

function saveContext() {
    var submitType = document.querySelector('input[name="context-type"]:checked').value;
    if (submitType == "Other") {
        submitType = document.getElementById("context-other-text").value;
    }
    var toSubmit = {
        "author": (username != "") ? username : "(anonymous)",
        "sensor": document.getElementById("contextDD").value,
        "start": document.getElementById("con-start-date").value,
        "startfuzzy": document.getElementById("fuzzy-from").checked,
        "end": document.getElementById("con-end-date").value,
        "endfuzzy": document.getElementById("fuzzy-to").checked,
        "type": submitType,
        "comment": document.getElementById("context-comment").value
    }
    if (submitType == "Recurring") {
        toSubmit["recurring-number"] = document.getElementById("recurring-number").value;
        toSubmit["recurring-time"] = document.querySelector('input[name="context-recurring"]:checked').value;
    }

    var action = document.getElementById("context-button").getAttribute("action");
    toSubmit["id"] = document.getElementById("context-button").getAttribute("context-id");

    fetch(action+"context", {
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
            "id": m[varNameDevSensorID],
            "type": m[varNameDevSensorType],
            //"serving": m["Serving"] too long...
            "building": m[varNameDevMeasuringShort]
        })
    }
}

$(document).ready( function () {
    fetch("api/meter").then((response) => {
        if (response.ok) {
            return response.json()
        } else {
            return devices;
        }
    })
    .then(data => {
        fillDD(data);
    })
    .catch((error) => {
        fillDD(devices);
    });

    // to not bloat the CSS file do this
    for (e of document.querySelectorAll("div.gc-grid-element")) {
        e.style.gridArea = e.id;
    }

    document.getElementById("context-other-text").disabled = !$('#context-type-other').is(':checked');

    $('input#context-type-other').change(function(){
        document.getElementById("context-other-text").disabled = false;
    });
    $('input[type=radio]').not('#context-type-other').change(function(){
        document.getElementById("context-other-text").disabled = true;
    });

    document.getElementById("recurring-number").disabled = !$('#context-type-recurring').is(':checked');
    setRadioButtons("context-recurring", !$('#context-type-recurring').is(':checked'));

    $('input#context-type-recurring').change(function(){
        document.getElementById("recurring-number").disabled = !$('#context-type-recurring').is(':checked');
        setRadioButtons("context-recurring", !$('#context-type-recurring').is(':checked'));
    });
    $('input[type=radio]').not('#context-type-recurring').change(function(){
        document.getElementById("recurring-number").disabled = !$('#context-type-recurring').is(':checked');
        setRadioButtons("context-recurring", !$('#context-type-recurring').is(':checked'));
    });

    // https://xdsoft.net/jqplugins/datetimepicker/
    jQuery('#con-start-date').datetimepicker({
        value: "2023-02-02 00:00",
        format:'Y/m/d H:i'
    });
    jQuery('#con-end-date').datetimepicker({
        value: "2023-03-28 23:50",
        format:'Y/m/d H:i'
    });

    $( function() {
        $("#context-container").draggable({
            handle: "#context-header"
        });
    });
});
