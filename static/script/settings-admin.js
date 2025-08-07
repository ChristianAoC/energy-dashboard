
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
            // this used to return users if ok, but didn't do anything with it and was inconsistent anyways, so removed
            //return res.json();
        })
        .then(data => {
        })
        .catch(err => {
            alert("Error updating user level");
            console.error(err);
        });
    }
});

$(document).ready( function () {
    fetch(BASE_PATH + '/api/user/list')
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
                    { data: 'sessions', title: "Total sessions"},
                    {
                        data: null, title: "Actions",
                        render: function (u, type, row) {
                            return `<button class="btn-delete" data-email="${u.email}">Delete</button>`;
                        }
                    }                ]
            })
        })
        .catch(err => {
            console.error("Failed to load users:", err);
        });
});
