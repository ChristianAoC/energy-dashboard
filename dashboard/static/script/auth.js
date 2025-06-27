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

function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for(let i = 0; i <ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) == ' ') {
        c = c.substring(1);
      }
      if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
      }
    }
    return "";
};
