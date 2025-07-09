var url = window.location.href;
var filename = url.substring(url.lastIndexOf('/')+1).split(".")[0];

var html = `<img id="logo" src="${STATIC_URLS.logo}" alt="Logo" />`;

var navItems = []

//navItems.push(['Tutorial', 'tutorial.html']);
//navItems.push(['Overview', 'start.html']);
navItems.push(['Map', 'map.html']);
navItems.push(['Benchmark', 'benchmark.html']);
navItems.push(['Browser', 'browser.html']);
navItems.push(['Health Check', 'health-check.html?hidden=;3;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;21;23;24;25;27;26;28;30;31;32;33;35;29;37;']);

if (iframe_capavis != "None") {
	navItems.push(['Anomaly Detection', 'anomaly.html']);
}
if (iframe_energy_usage != "None") {
	navItems.push(['Energy Usage', 'energy-usage.html']);
}

navItems.push(['Context', 'context.html']);
navItems.push(['About', 'about.html']);

for (i = 0; i<navItems.length; i++){
	if (filename == navItems[i][1].split(".")[0]) {
		html += '<div class="navlink active"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
	} else {
		html += '<div class="navlink"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
	}
}

html += `<a href="settings.html"><img id="settings-button" src="${STATIC_URLS.settings}" alt="Settings" /></a>`;

document.getElementById("nav-top-bar").innerHTML = html;
