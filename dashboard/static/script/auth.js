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
                if (location.href.split("/").slice(-1)[0].substring(0, 13) == "settings.html") {
                    location.reload();
                }
            } else {
                document.getElementById("loggedin-div").classList.add("hidden");
                document.getElementById("login-div").classList.remove("hidden");
                document.getElementById("failed-div").classList.remove("hidden");
                document.getElementById("username-span").innerHTML = "";
            }
        })
}

function backToLogin() {
    document.getElementById("login-div").classList.remove("hidden");
    document.getElementById("failed-div").classList.add("hidden");
    //document.getElementById("register-div").classList.add("hidden");
    document.getElementById("username-span").innerHTML = "";
};

function registerUser() {
    //document.getElementById("registererror-div").innerHTML = "";
    document.getElementById("login-div").classList.add("hidden");
    document.getElementById("failed-div").classList.add("hidden");
    //document.getElementById("register-div").classList.remove("hidden");
    document.getElementById("username-span").innerHTML = "";
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
    username = "";
    if (location.href.split("/").slice(-1)[0].substring(0, 13) == "settings.html") {
        location.reload();
    }
}

function checkKeyPressAuth(e) {
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
