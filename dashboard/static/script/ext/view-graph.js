/*
function convertMLToPlotly(barType, meterType) {
	let x = [];
	let y = [];
	let i = 0;
	do {
        //console.log(masterList[i]["Electricity Usage"]);
        if(masterList[i][meterType+" Usage"] != null) {
            x.push(Math.round(parseFloat(masterList[i][meterType+" Usage"])));
            y.push(masterList[i]["Building Name"]);
        }
		i++;
	} while (i < masterList.length);

	return {
		'x': x,
		'y': y,
		'type': barType,
        orientation: 'h'
	};
}
*/

function convertMLToPlotly(barType) {
	let x = [];
	let y = [];
	let i = 0;
    if (narrowML.length > 0) {
        do {
            //console.log(masterList[i]["Electricity Usage"]);
            if(narrowML[i][activeTab+" Usage"] != null) {
                x.push(Math.round(parseFloat(narrowML[i][activeTab+" Usage"])));
                y.push(narrowML[i]["Building Name"]);
            }
            i++;
        } while (i < narrowML.length);
    }

	return {
		'x': x,
		'y': y,
		'type': barType,
        orientation: 'h'
	};
};

function redrawGraph() {
    //isLoading = true;
    var pData = convertMLToPlotly("bar");
    pLayout["title"] = activeTab;

//    Plotly.react("comparison-plot", [pData]).then(function() {
    Plotly.newPlot("comparison-plot", [pData], pLayout, pConfig).then(function() {
        isLoading = false;
    });
};

var pConfig = { displayModeBar: false };
var pLayout = { barmode: 'group',
    title: activeTab,
    xaxis: {
        title: {
            text: 'Consumption'
            }
        },
    yaxis: {
        automargin: true
        }
    };
var isLoading = true;

$(document).ready( function () {
    var pData = convertMLToPlotly("bar", activeTab);

    Plotly.newPlot("comparison-plot", [pData], pLayout, pConfig).then(function() {
        isLoading = false;
    });;
});
