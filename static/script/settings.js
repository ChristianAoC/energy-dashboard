document.addEventListener("click", function (e) {
    if (e.target.matches(".btn-delete")) {
        const email = e.target.dataset.email;
        if (confirm(`Delete user ${email}?`)) {
            fetch(`/admin-delete-user`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ email })
            }).then(res => {
                if (res.ok) {
                    alert("User deleted.");
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

        fetch('/admin-set-user-level', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, level: newLevel })
        })
        .then(res => {
            if (!res.ok) throw new Error("Failed to update user");
            return res.json();
        })
        .then(data => {
            console.log("Level updated:", data);
        })
        .catch(err => {
            alert("Error updating user level");
            console.error(err);
        });
    }
});

$(document).ready( function () {
    fetch('/admin/users')
        .then(response => {
            if (!response.ok) throw new Error("Not authorized");
            return response.json();
        })
        .then(users => {
            $('#usersTable').DataTable({
                data: users,
                "pageLength": 25,
                "columns": [
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
                    {
                        data: 'sessions', title: "Total sessions",
                        render: function (sessions) {
                            return sessions.length;
                            /*
                            return sessions.map(s => {
                                return `<div><code>${s.id}</code> <small>(${s.lastseen})</small></div>`;
                            }).join('');
                            */
                        }
                    },
                    {
                        data: null, title: "Actions",
                        render: function (u, type, row) {
                            return `<button class="btn-delete" data-email="${u.email}">Delete (TBD)</button>`;
                        }
                    }                ]
            })
        })
        .catch(err => {
            console.error("Failed to load users:", err);
        });
});
