var url = window.location.href;
var filename = url.substring(url.lastIndexOf('/')+1);

var html = '<img id="logo" src="gfx/logo.png" alt="Logo" />';

var navItems = []

//navItems.push(['Tutorial', 'tutorial.html']);
navItems.push(['Overview', 'start.html']);
navItems.push(['View Devices', 'devices.html']);

if (iframe_capavis != "None") {
	navItems.push(['Anomaly Detection', 'anomaly.html']);
}
if (iframe_energy_usage != "None") {
	navItems.push(['Energy Usage', 'energy-usage.html']);
}

//navItems.push(['Health Check', 'health.html']);
//navItems.push(['Statistical Tools', 'statistics.html']);
navItems.push(['Context', 'context.html']);
navItems.push(['About', 'about.html']);

for (i = 0; i<navItems.length; i++){
	if (filename == navItems[i][1]) {
		html += '<div class="navlink active"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
	} else {
		html += '<div class="navlink"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
	}
}

html += '<a href="settings.html"><img id="settings-button" src="gfx/settings.png" alt="Settings" /></a>';
//html += '&nbsp;&nbsp;<img id="comment-button" src="gfx/comment.png" width="38" alt="Comment" onclick="commentButtonClicked()" />';
html += '<img id="user-button" src="gfx/user2.png" width="35" alt="User" onclick="userButtonClicked()" />';

document.getElementById("nav-top-bar").innerHTML = html;
