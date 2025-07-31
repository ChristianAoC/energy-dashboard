function requestLogin() {
    //let email = document.getElementById("email").value;
    let email = document.getElementById("login-request-email").value;
    fetch("loginrequest?email="+email, {method: 'POST'})
        .then(response => response.text())
        .then(data => {
            document.getElementById("login-request-div").innerHTML = data;
        })
}

function logout() {
    fetch("logout?email="+getCookie("Email"), {method: 'POST'})
        .then(response => response.text())
        .then(data => {
            location.reload();
        })
}

function checkKeyPressAuth(e) {
    if(e && e.keyCode == 13) {
        requestLogin();
    }
}

document.addEventListener("click", function (e) {
    if (e.target.matches(".btn-delete")) {
        const email = e.target.dataset.email;
        if (confirm(`Delete user ${email}?`)) {
            fetch(`/admin/delete_user`, {
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

        fetch('/admin/set_user_level', {
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
    fetch('/admin/list_users')
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
                            return `<button class="btn-delete" data-email="${u.email}">Delete</button>`;
                        }
                    }                ]
            })
        })
        .catch(err => {
            console.error("Failed to load users:", err);
        });
});
