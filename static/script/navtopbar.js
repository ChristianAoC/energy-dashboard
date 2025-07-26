function createNavbar() {
	const url = window.location.href;
	const filename = url.substring(url.lastIndexOf('/')+1).split("?")[0];

	var html = `<img id="logo" src="${STATIC_URLS.logo}" alt="Logo" />`;

	var navItems = []

	navItems.push(['Map', 'map']);
	navItems.push(['Benchmark', 'benchmark']);
	navItems.push(['Browser', 'browser']);
	navItems.push(['Health Check', 'health-check?hidden=;3;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;21;23;24;25;27;26;28;30;31;32;33;35;29;37;']);
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
