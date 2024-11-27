// TODO: better logic for register user
// TODO: delete user account
// TODO: settings page (change password)

function userButtonClicked() {
    document.getElementById("login-container").classList.toggle("hidden");
}

function checkLogin() {
    let username = document.getElementById("username").value;
    let password = document.getElementById("password").value;
    document.getElementById("password").value = "";
    fetch("loginrequest?username="+username+"&password="+password, {method: 'POST'})
        .then(response => response.text())
        .then(data => {
            if (data == "loginok") {
                document.getElementById("loggedin-div").classList.remove("hidden");
                document.getElementById("login-div").classList.add("hidden");
                document.getElementById("failed-div").classList.add("hidden");
                document.getElementById("username-span").innerHTML = username;
                setCookie(username);
            } else {
                document.getElementById("loggedin-div").classList.add("hidden");
                document.getElementById("login-div").classList.remove("hidden");
                document.getElementById("failed-div").classList.remove("hidden");
                document.getElementById("username-span").innerHTML = "";
            }
        })
}

function registerUser() {
    document.getElementById("registererror-div").innerHTML = "";
    document.getElementById("login-div").classList.add("hidden");
    document.getElementById("failed-div").classList.add("hidden");
    document.getElementById("register-div").classList.remove("hidden");
    document.getElementById("username-span").innerHTML = "";
}

function registerRequest() {
    document.getElementById("registererror-div").innerHTML = "";
    let password1 = document.getElementById("new-password1").value;
    let password2 = document.getElementById("new-password2").value;
    let username = document.getElementById("new-username").value;
    if (password1 != password2) {
        document.getElementById("registererror-div").innerHTML += "Passwords don't match!<br>";
    } else if (password1.length < 6) {
        document.getElementById("registererror-div").innerHTML += "Password too short.<br>At least 6 characters.<br>";
    } else if (password1.length > 64) {
        document.getElementById("registererror-div").innerHTML += "Password too long.<br>At most 64 characters.<br>";
    } else if (username.length < 3) {
        document.getElementById("registererror-div").innerHTML += "Username too short.<br>At least 3 characters.<br>";
    } else if (username.length > 32) {
        document.getElementById("registererror-div").innerHTML += "Username too long.<br>At most 32 characters.<br>";
    } else {
        document.getElementById("password").value = "";
        fetch("registerrequest?username="+username+"&password="+password1, {method: 'POST'})
            .then(response => response.text())
            .then(data => {
                if (data == "Username exists already!") {
                    document.getElementById("registererror-div").innerHTML = "User exists already!<br>";
                } else if (data == "Couldn't create user") {
                    document.getElementById("registererror-div").innerHTML = "Error creating user.<br>";
                } else if (data == "User created") {
                    document.getElementById("loggedin-div").classList.remove("hidden");
                    document.getElementById("login-div").classList.add("hidden");
                    document.getElementById("register-div").classList.add("hidden");
                    document.getElementById("failed-div").classList.add("hidden");
                    document.getElementById("username-span").innerHTML = username;
                    setCookie(username);
                }
        })
    }
}

function setCookie(username) {
    const d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000));
    let expires = "expires="+ d.toUTCString();
    document.cookie = "username=" + username + ";" + expires + "; SameSite=Strict";
}

function getUsernameCookie() {
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for(let i = 0; i <ca.length; i++) {
        let c = ca[i];
            while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf('username=') == 0) {
            return c.substring(9, c.length);
        }
    }
    return "";
}

function logout() {
    document.cookie = "username=" + getUsernameCookie() + "; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Strict";
    document.getElementById("loggedin-div").classList.add("hidden");
    document.getElementById("login-div").classList.remove("hidden");
    document.getElementById("username-span").innerHTML = "";
}

function checkKeyPress(e) {
    if(e && e.keyCode == 13) {
        if (!document.getElementById("login-div").classList.contains("hidden")) {
            checkLogin();
        } else if (!document.getElementById("register-div").classList.contains("hidden")) {
            registerRequest();
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    username = getUsernameCookie();
    if (username != "") {
        document.getElementById("loggedin-div").classList.remove("hidden");
        document.getElementById("login-div").classList.add("hidden");
        document.getElementById("username-span").innerHTML = username;
    }
});
