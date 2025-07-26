function createNavbar() {
	const url = window.location.href;
	const filename = url.substring(url.lastIndexOf('/')+1).split("?")[0];

	var html = `<img id="logo" src="${STATIC_URLS.logo}" alt="Logo" />`;

	var navItems = []

	navItems.push(['Map', 'map']);
	navItems.push(['Benchmark', 'benchmark']);
	navItems.push(['Browser', 'browser']);
	navItems.push(['Health Check', 'health-check?hidden=;4;7;8;9;13;14;15;16;17;18;19;20;21;22;25;26;27;28;31;32;33;35;37;']);
	navItems.push(['Context', 'context']);
	navItems.push(['About', 'about']);

	for (i = 0; i<navItems.length; i++){
		if (filename == navItems[i][1].split("?")[0]) {
			html += '<div class="navlink active"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
		} else {
			html += '<div class="navlink"><a href="' + navItems[i][1] + '">' + navItems[i][0] + '</a></div>'
		}
	}

	html += `<a href="settings"><img id="settings-button" src="${STATIC_URLS.settings}" alt="Settings" /></a>`;
	return html;
};

document.getElementById("nav-top-bar").innerHTML = createNavbar();
