/*
document.addEventListener("DOMContentLoaded", function() {
    username = getUsernameCookie();
    if (username != "") {
        document.getElementById("settings-loggedout").classList.add("hidden");
        document.getElementById("settings-container").classList.remove("hidden");
    }
    if (window.location.href.includes("#pwchanged")) {
        document.getElementById("pwChangeSuccess").innerHTML += "Password successfully changed.<br><br>";
    }
});
*/

function checkKeyPressPW(e) {
    if(e && e.keyCode == 13) {
        changePassword();
    }
};

function checkKeyPressReg(e) {
    if(e && e.keyCode == 13) {
        registerRequest();
    }
};

function changePassword() {
    let oldPW = document.getElementById("change-old-password").value;
    let password1 = document.getElementById("change-new-password1").value;
    let password2 = document.getElementById("change-new-password2").value;
    if (password1 != password2) {
        document.getElementById("pwChangeError").innerHTML = "Passwords don't match!<br><br>";
    } else if (password1 == oldPW) {
        document.getElementById("pwChangeError").innerHTML = "Old and new password are the same.<br><br>";
    } else if (password1.length < 6) {
        document.getElementById("pwChangeError").innerHTML = "Password too short - at least 6 characters.<br><br>";
    } else if (password1.length > 64) {
        document.getElementById("pwChangeError").innerHTML = "Password too long - at most 64 characters.<br><br>";
    } else {
        fetch("changepassword?username="+username+"&password="+oldPW+"&newPW="+password1, {method: 'POST'})
            .then(response => response.text())
            .then(data => {
                if (data == "Password changed") {
                    window.location.href = "settings.html#pwchanged";
                    location.reload();
                } else if (data == "Old password incorrect") {
                    document.getElementById("pwChangeError").innerHTML += "Old password incorrect.<br><br>";
                } else if (data == "Password wasn't updated") {
                    document.getElementById("pwChangeError").innerHTML += "Password not updated, unknown error.<br><br>";
                }
            });
    }
};

function registerRequest() {
    document.getElementById("registerError").innerHTML = "";
    let username = document.getElementById("new-username").value;
    let email = document.getElementById("new-email").value;
    let password1 = document.getElementById("new-password1").value;
    let password2 = document.getElementById("new-password2").value;
    if (username.length < 3) document.getElementById("registerError").innerHTML += "Username too short.<br>At least 3 characters.<br>";
    if (username.length > 32) document.getElementById("registerError").innerHTML += "Username too long.<br>At most 32 characters.<br>";
    if (!email.includes('@')) document.getElementById("registerError").innerHTML += "Email is not a valid email address.<br>";
    if (password1 != password2) document.getElementById("registerError").innerHTML += "Passwords don't match!<br>";
    if (password1.length < 6) document.getElementById("registerError").innerHTML += "Password too short.<br>At least 6 characters.<br>";
    if (password1.length > 64) document.getElementById("registerError").innerHTML += "Password too long.<br>At most 64 characters.<br>";

    if (password1.length > 64) document.getElementById("registerError").innerHTML += "Password too long.<br>At most 64 characters.<br>";
    if (document.getElementById("registerError").innerHTML == "") {
        document.getElementById("password").value = "";
        fetch("registerrequest?username="+username+"&password="+password1+"&email="+email, {method: 'POST'})
            .then(response => response.text())
            .then(data => {
                if (data == "User created") {
                    document.getElementById("loggedin-div").classList.remove("hidden");
                    document.getElementById("login-div").classList.add("hidden");
                    document.getElementById("failed-div").classList.add("hidden");
                    document.getElementById("username-span").innerHTML = username;
                    setCookie(username);
                    location.reload();
                } else {
                    document.getElementById("registerError").innerHTML = data+"<br>";
                }
        })
    }
};
