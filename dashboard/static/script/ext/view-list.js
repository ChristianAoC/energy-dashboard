//var data = masterList; // long one with all crap
//data = mlRedux; // short one with all data incl sqm

/*
var usage = usageFile;
var f = [];
for (d of data) {
	for (u of usage) {
		if (d["Planon Code"] == u["Property code"]) {
			d["Electricity Usage"] = u["ElectricityUsage"];
			d["Gas Usage"] = u["GasUsage"];
			d["Heat Usage"] = u["HeatUsage"];
			d["Water Usage"] = u["WaterUsage"];
			f.push(d);
		}
	}
}
*/

$(document).ready( function () {
    var table = $('#buildingsTable').DataTable({
		"data": masterList,
		"pageLength": 10,
		"columns": [
			{"data": 'Building Name', "title": "Building Name"},
			/*
			{"data": 'Property code', "title": "Planon Code"},
			{"data": 'sqm', "title": "Floor size"},
			{"data": 'Res/Non-Res', "title": "Res/Non-res"},
			{"data": 'Year of construction', "title": "Year Built"},
			{"data": 'Room Booking Ref', "title": "Campus Zone"},
			*/
			{"data": 'Planon Code', "title": "Planon Code"},
			{"data": 'Floor Size', "title": "Floor size [sqm]"},
			{"data": 'Type', "title": "Type"},
			{"data": 'Year Built', "title": "Year Built"},
			{"data": 'Campus Zone', "title": "Campus Zone"},

			{"data": 'Electricity', "title": "Electricity Meter"},
			{"data": 'Electricity Usage', "title": "Electricity Usage [kWh]"},
			{"data": 'Gas', "title": "Gas Meter"},
			{"data": 'Gas Usage', "title": "Gas Usage [m&sup3;]"},
			{"data": 'Heat', "title": "Heat Meter"},
			{"data": 'Heat Usage', "title": "Heat Usage [MWh]"},
			{"data": 'Water', "title": "Water Meter"},
			{"data": 'Water Usage', "title": "Water Usage [m&sup3;]"}
		]
	});
	
	$('#buildingsTable').on('click', 'tbody tr', function() {
        for (b of masterList) {
            if (b["Planon Code"] == table.row(this).data()["Planon Code"]) {
                viewBuilding(b);
            }
        }
	})
});
