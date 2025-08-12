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
 
// Send update when user leaves the field
function onSettingChange(e) {
    const input = e.target;
    const key = input.dataset.key;
    const value = input.value;

    fetch(BASE_PATH + '/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value })
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to update setting");
        // flash green
        input.classList.add('input-saved');
        setTimeout(() => input.classList.remove('input-saved'), 3000);
    })
    .catch(err => {
        console.error("Error updating setting:", err);
    });
}

function createSettingRow(key, value) {
    const row = document.createElement('tr');

    const keyCell = document.createElement('td');
    keyCell.textContent = key;

    const valueCell = document.createElement('td');
    const input = document.createElement('input');
    input.value = value;
    input.dataset.key = key;
    input.addEventListener('blur', onSettingChange);
    valueCell.appendChild(input);

    row.appendChild(keyCell);
    row.appendChild(valueCell);

    return row;
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
            const tbody = document.getElementById('settings-rows');
            tbody.innerHTML = '';

            Object.entries(settings).forEach(([key, value]) => {
                const rows = document.getElementById('settings-rows');
                rows.appendChild(createSettingRow(key, value));
            });
        })
        .catch(err => {
            console.error("Failed to load settings:", err);
        });
}

function loadLogs() {
    // http://127.0.0.1:5000/api/logs?from_time=1754672345&exact_level=info&count=100&newest_first=False
    // http://127.0.0.1:5000/api/logs?to_time=1754672345&minimum_level=error

    fetch(BASE_PATH + '/api/logs')
        .then(res => {
            if (!res.ok) throw new Error("Not authorized");
            return res.json();
        })
        .then(logs => {
            $('#logsTable').DataTable({
                data: logs,
                pageLength: 25,
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
        fileInput.dataset.endpoint = '/api/settings/upload/metadata';
        fileInput.click();
    });

    document.getElementById('upload-benchmarks').addEventListener('click', () => {
        fileInput.dataset.endpoint = '/api/settings/upload/benchmarks';
        fileInput.click();
    });

    document.getElementById('upload-polygons').addEventListener('click', () => {
        fileInput.dataset.endpoint = '/api/settings/upload/polygons';
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

    document.getElementById('add-setting-btn').addEventListener('click', () => {
        const key = prompt('Enter setting name:');
        if (!key) return;

        const value = prompt('Enter setting value:');
        if (value === null) return;

        const rows = document.getElementById('settings-rows');
        rows.appendChild(createSettingRow(key, value));

        // TODO: Implement getting type and category
        setting_type = "string"
        category = null

        fetch('/api/settings/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: {"value": value, "type": setting_type, "category": category} })
        })
        .then(res => res.text())
        .then()
        .catch(err => console.error('Error saving setting:', err));
    });

    document.getElementById('viewToggle').addEventListener('click', function(event){
        viewToggled(this, event);

        if (event.target.tagName.toLowerCase() === 'input') {
            if (event.target.value === 'settings-users' && !document.getElementById('usersTable').dataset.loaded) {
                loadUsers();
            }
            if (event.target.value === 'settings-variables' && !document.getElementById('settings-container').dataset.loaded) {
                loadSettings();
            }
            if (event.target.value === 'settings-logs' && !document.getElementById('logsTable').dataset.loaded) {
                loadLogs();
            }
        }
    });

    loadUsers();
});
