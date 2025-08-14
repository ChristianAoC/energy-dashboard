function viewToggled(elem, event) {
    if (event.target.tagName.toLowerCase() == 'input') {
        let input = event.target;
        let slider = elem.querySelector('div');
        let inputs = elem.querySelectorAll('input');
        
        slider.style.transform = `translateX(${input.dataset.location})`;
        inputs.forEach(function(inp){
            if ( inp == input ) {
                document.getElementById(inp.value).hidden = false;
                inp.parentElement.classList.add('selected');
                if (inp.value == "view-map") {
                    let h2 = parseInt(document.getElementById("nav-top-bar").offsetHeight) + 24;
                    document.getElementById("map-sidebar").style.height = "calc(100vh - " + h2 + "px)";
                    highlightBuildingsList();
                }
            } else {
                document.getElementById(inp.value).hidden = true;
                inp.parentElement.classList.remove('selected');
            }
        });
    }
};
 
function switchClicked(e) {
    const currentState = e.getAttribute('aria-checked') === 'true';
    const newState = String(!currentState);
    const key = e.getAttribute("data-key");
    e.setAttribute('aria-checked', newState);

    fetch(BASE_PATH + '/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: !currentState })
    })
    .then(res => {
        if (!res.ok) {
            $("[data-key="+key+"]")[0].setAttribute('aria-checked', currentState);
            throw new Error("Failed to update setting");
        }
    })
    .catch(err => {
        console.error("Error updating bool setting:", err);
    });
}

// Send update when user leaves the input field/switches bool
function onSettingChange(input) {
    let value = htmlEscape(input.value);
    if (input.getAttribute("data-type") == "int") value = parseInt(value);
    if (input.getAttribute("data-type") == "float") value = parseFloat(value);

    fetch(BASE_PATH + '/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [input.getAttribute("data-key")]: value })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("Failed to update setting");
        }
        // flash green
        input.classList.add('input-saved');
        setTimeout(() => input.classList.remove('input-saved'), 3000);
    })
    .catch(err => {
        console.error("Error updating setting:", err);
    });
}

function loadUsers() {
    fetch(BASE_PATH + '/api/user/list')
        .then(res => {
            if (!res.ok) throw new Error("Not authorized");
            return res.json();
        })
        .then(users => {
            $('#usersTable').DataTable({
                data: users,
                pageLength: 25,
                columns: [
                    { data: "email", title: "Email"},
                    { data: "lastlogin", title: "Last login"},
                    {
                        data: "level",
                        render: function (level, type, row) {
                            const disabled = (row.email === currentUserEmail) ? "disabled" : "";
                            return `
                                <select class="user-level" data-email="${row.email}" ${disabled}>
                                    ${[1, 2, 3, 4, 5].map(val => `
                                        <option value="${val}" ${val == level ? "selected" : ""}>${val}</option>
                                    `).join("")}
                                </select>
                            `;
                        }
                    },
                    { data: "logincount", title: "Total logins"},
                    { data: "sessions", title: "Total sessions"},
                    {
                        data: null, title: "Actions",
                        render: function (u, type, row) {
                            return `<button class="btn-delete" data-email="${u.email}">Delete</button>`;
                        }
                    }
                ]
            });
            document.getElementById('usersTable').dataset.loaded = "true";
        })
        .catch(err => {
            console.error("Failed to load users:", err);
        });
}

function loadSettings() {
    fetch(BASE_PATH + '/api/settings')
        .then(res => {
            if (!res.ok) throw new Error("Not authorized");
            return res.json();
        })
        .then(settings => {
            $('#settingsTable').DataTable({
                data: settings,
                pageLength: 25,
                dom: 'lrtp',
                columns: [
                    { data: "category", title: "Category"},
                    { data: "key", title: "Key"},
                    { data: 'value', title: "Value",
                        render: function (data, type, row) {
                            if (row.setting_type === "str") {
                                return `<input type='text' class='dt-input-text' onchange='onSettingChange(this)' value='${data}' data-key='${row.key}' data-type='${row.setting_type}'>`;
                            } else if (row.setting_type === "int") {
                                return `<input type='number' class='dt-input-int' onchange='onSettingChange(this)' value='${data}' step='1' data-key='${row.key}' data-type='${row.setting_type}'>`;
                            } else if (row.setting_type === "float") {
                                return `<input type='number' class='dt-input-int' onchange='onSettingChange(this)' value='${data}' data-key='${row.key}' data-type='${row.setting_type}'>`;
                            } else if (row.setting_type === "bool") {
                                return `<div role="switch" aria-checked="${data}" tabindex="0" onclick="switchClicked(this)" data-key="${row.key}">
                                        <span class="switch">
                                            <span></span>
                                        </span>
                                        <span class="true" aria-hidden="true">True</span>
                                        <span class="false" aria-hidden="true">False</span>
                                        </div>`;
                            } else if (row.setting_type === "list") {
                                return `<input type='text' class='dt-input-text' onchange='onSettingChange(this)' value='${data}' step='1' data-key='${row.key}'>`;
                            } else {
                                return data;
                            }
                        }
                    },
                    { data: 'setting_type', title: "Type"}
                ],
                initComplete: function () {
                this.api()
                    .columns()
                    .every(function () {
                        let column = this;
        
                        if (this.header().classList.contains("select")) {
                            // Create select element
                            let select = document.createElement('select');
                            select.add(new Option(''));
                            column.header().replaceChildren(select);
            
                            // Apply listener for user change in value
                            select.addEventListener('change', function () {
                                column
                                    .search(select.value, {exact: true})
                                    .draw();
                            });
            
                            // Add list of options
                            column
                                .data()
                                .unique()
                                .sort()
                                .each(function (d, j) {
                                    select.add(new Option(d));
                                });
                        } else if (this.header().classList.contains("text")) {
                            var text = $('<input type="text" />')
                                    .appendTo($(column.header()).empty())
                                    .on('keyup change', function () {
                                        var val = $.fn.dataTable.util.escapeRegex(
                                            $(this).val()
                                            );
                                        if (column.search() !== this.value) {
                                            column
                                                    .search(val)
                                                    .draw();
                                        }
                                        return false;
                                    });
                        }
                    });
                }
            });
            document.getElementById('settingsTable').dataset.loaded = "true";
        })
        .catch(err => {
            console.error("Failed to load settings:", err);
        });
}

function loadLogs() {
    fetch(BASE_PATH + '/api/logs')
        .then(res => {
            if (!res.ok) throw new Error("Not authorized");
            return res.json();
        })
        .then(logs => {
            $('#logsTable').DataTable({
                data: logs,
                pageLength: 25,
                dom: 'lrtp',
                columns: [
                    { data: 'timestamp', title: "Timestamp"},
                    { data: "level", title: "Level"},
                    { data: "message", title: "Message"},
                    { data: "info", title: "Info"}
                ],
                initComplete: function () {
                this.api()
                    .columns()
                    .every(function () {
                        let column = this;
        
                        if (this.header().classList.contains("select")) {
                            // Create select element
                            let select = document.createElement('select');
                            select.add(new Option(''));
                            column.header().replaceChildren(select);
            
                            // Apply listener for user change in value
                            select.addEventListener('change', function () {
                                column
                                    .search(select.value, {exact: true})
                                    .draw();
                            });
            
                            // Add list of options
                            column
                                .data()
                                .unique()
                                .sort()
                                .each(function (d, j) {
                                    select.add(new Option(d));
                                });
                        } else if (this.header().classList.contains("text")) {
                            var text = $('<input type="text" />')
                                    .appendTo($(column.header()).empty())
                                    .on('keyup change', function () {
                                        var val = $.fn.dataTable.util.escapeRegex(
                                            $(this).val()
                                            );
                                        if (column.search() !== this.value) {
                                            column
                                                    .search(val)
                                                    .draw();
                                        }
                                        return false;
                                    });
                        }
                    });
                }
            });
            document.getElementById('logsTable').dataset.loaded = "true";
        })
        .catch(err => {
            console.error("Failed to load logs:", err);
        });
}

$(document).ready(function () {
    const fileInput = document.getElementById('file-input');

    document.getElementById('upload-metadata').addEventListener('click', () => {
        fileInput.dataset.endpoint = BASE_PATH + '/api/settings/upload/metadata';
        fileInput.click();
    });

    document.getElementById('upload-benchmarks').addEventListener('click', () => {
        fileInput.dataset.endpoint = BASE_PATH + '/api/settings/upload/benchmarks';
        fileInput.click();
    });

    document.getElementById('upload-polygons').addEventListener('click', () => {
        fileInput.dataset.endpoint = BASE_PATH + '/api/settings/upload/polygons';
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        fetch(BASE_PATH + fileInput.dataset.endpoint, {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error("Upload failed");
            alert("File uploaded successfully!");
        })
        .catch(err => {
            console.error(err);
            alert("Error uploading file");
        })
        .finally(() => {
            fileInput.value = '';
        });
    });

    document.addEventListener("click", function (e) {
        if (e.target.matches(".btn-delete")) {
            const email = e.target.dataset.email;
            if (confirm(`Delete user ${email}?`)) {
                fetch(BASE_PATH + `/api/user/delete`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ email })
                }).then(res => {
                    if (res.ok) {
                        location.reload();
                    }
                });
            }
        }
    });

    document.addEventListener("change", function (e) {
        if (e.target.matches(".user-level")) {
            const newLevel = parseInt(e.target.value);
            const email = e.target.dataset.email;

            fetch(BASE_PATH + '/api/user/set-level', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, level: newLevel })
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to update user");
            })
            .then(data => {
            })
            .catch(err => {
                alert("Error updating user level");
                console.error(err);
            });
        }
    });

    document.getElementById('viewToggle').addEventListener('click', function(event){
        viewToggled(this, event);

        if (event.target.tagName.toLowerCase() === 'input') {
            if (event.target.value === 'settings-users' && !document.getElementById('usersTable').dataset.loaded) {
                loadUsers();
            }
            if (event.target.value === 'settings-variables' && !document.getElementById('settingsTable').dataset.loaded) {
                loadSettings();
            }
            if (event.target.value === 'settings-logs' && !document.getElementById('logsTable').dataset.loaded) {
                loadLogs();
            }
        }
    });

    loadUsers();
});
