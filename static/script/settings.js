function requestLogin() {
    //let email = document.getElementById("email").value;
    let email = document.getElementById("login-request-email").value;
    fetch(BASE_PATH + "/api/user/login?email="+email, {method: 'POST'})
        .then(response => response.text())
        .then(data => {
            document.getElementById("login-request-div").innerHTML = data;
        })
}

function logout() {
    fetch(BASE_PATH + "/api/user/logout?email="+getCookie("Email"), {method: 'POST'})
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

function logoutAll() {
    const email = getCookie("Email");

    fetch(BASE_PATH + `/api/user/invalidate-session`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email })
        }).then(res => {
            location.reload();
        });
}