let healthcheckTable;

let hctColumns = [
    {data: "meter_id_clean", title: "Meter ID", defaultContent: '', filterType: 'text', visible: true },
    {data: "meter_type", title: "Type", defaultContent: '', filterType: 'multi-select', visible: true },
    {data: "class", title: "Class", defaultContent: '', filterType: 'multi-select', visible: true },
    {data: "HC_class_check", title: "<abbr title='Checks if the class seems correct: If the ratio is higher than 80 to 20 then it is probably cumulative, otherwise probably rate'>Class Check</abbr>", defaultContent: '', filterType: 'multi-select', visible: true },
    {data: "obsolete", title: "<abbr title='Marked by facility management as a meter that is not longer needed/maintained, but kept in the database for now'>Obsolete</abbr>", defaultContent: '', filterType: 'multi-select', visible: true },

    {data: "serving", title: "Serving", defaultContent: '', filterType: 'text', visible: true },
    {data: "meter_level", title: "Level", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "building_level_meter", title: "<abbr title='Marked as building_level_meter'>Main</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "meter_location", title: "Meter location", defaultContent: '', filterType: 'text', visible: false },
    {data: "measured_units", title: "<abbr title='Measured units'>M. Units</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "tenant", title: "Tenant", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "tenant_name", title: "Tenant Name", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "to_be_invoiced", title: "Invoiced", defaultContent: '', filterType: 'multi-select', visible: false },

    {data: "serving_revised", title: "Serving (revised)", defaultContent: '', filterType: 'text', visible: false },
    {data: "building", title: "Building", defaultContent: '', filterType: 'text', visible: false },
    {data: "meter_id", title: "<abbr title='Raw meter ID, might contain slashes/hiphens'>Meter ID</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "unit_conversion_factor", title: "<abbr title='Unit conversion factor'>Conv.</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "units_after_conversion", title: "<abbr title='Units after conversion'>C. Units</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "resolution", title: "Resolution", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "adjustment_factor", title: "Adj. Factor", defaultContent: '', filterType: 'multi-select', visible: false },

    /*
    {data: "tenant_unit_id", title: "Tenant ID", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "parent", title: "Parent", defaultContent: '', filterType: 'text', visible: false },
    {data: "parent2", title: "Parent 2", defaultContent: '', filterType: 'text', visible: false },
    {data: "logger_channel", title: "Logger Channel", defaultContent: '', filterType: 'text', visible: false },
    {data: "modbus_address", title: "<abbr title='modbus_address'>Modbus</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "logger_id", title: "<abbr title='Logger ID'>L.ID</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "meter_make", title: "Meter Make", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "model", title: "Model", defaultContent: '', filterType: 'text', visible: false },
    {data: "serial_no", title: "Serial No", defaultContent: '', filterType: 'text', visible: false },
    {data: "config_checked_date", title: "Conf check date", defaultContent: '', filterType: 'text', visible: false },
    {data: "logger_label", title: "Logger Label", defaultContent: '', filterType: 'text', visible: false },
    {data: "logger_uuid", title: "Logger UUID", defaultContent: '', filterType: 'text', visible: false },
    {data: "raw_uuid", title: "Raw UUID", defaultContent: '', filterType: 'text', visible: false },
    */

    //{data: "redundant", title: "Redundant", defaultContent: '' }, // always empty
    //{data: "notes_issues", title: "Notes/Issues", defaultContent: '' }, // only data for 4 meters

    {data: "HC_count", title: "<abbr title='Total count of data points'>Data Points</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_count_perc", title: "<abbr title='Percentage of available data points for this period'>Data (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true },
    {data: "HC_zeroes", title: "<abbr title='Total count of zeroes'>Zeroes</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_zeroes_perc", title: "<abbr title='Percentage of zero readings'>Zeroes (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true },

    {data: "HC_diff_neg", title: "<abbr title='How many data points are declining (lower than the previous one)'>Diff: Neg.</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_diff_neg_perc", title: "<abbr title='Percentage of declining data points'>D.Neg. (perc)</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_diff_pos", title: "<abbr title='How many data points are increasing (higher than the previous one)'>Diff: Pos.</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_diff_pos_perc", title: "<abbr title='Percentage of increasing data points'>D.Pos. (perc)</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_diff_zero", title: "<abbr title='How many data points are the same as the previous one (no change)'>Diff: Zero</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_diff_zero_perc", title: "<abbr title='Percentage of non-changing data points'>D. Zero (perc)</abbr>", defaultContent: '', filterType: 'text', visible: false },
    //{data: "HC_class", title: "<abbr title='#'>#</abbr>", defaultContent: '' }, // this is more or less just internal for the API
    {data: "HC_median", title: "<abbr title='The median reading (converted to rate)'>Median</abbr>", defaultContent: '', filterType: 'text', visible: true },
    {data: "HC_mode", title: "<abbr title='The mode reading (converted to rate), i.e., most frequent value'>Mode</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_std", title: "<abbr title='Standard deviation (converted to rate)'>STD</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_min", title: "<abbr title='Min reading (converted to rate)'>Min</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_max", title: "<abbr title='Max reading (converted to rate)'>Max</abbr>", defaultContent: '', filterType: 'text', visible: false },

    {data: "HC_mean", title: "<abbr title='The mean (average) reading (converted to rate)'>Mean</abbr>", defaultContent: '', filterType: 'text', visible: true },
    {data: "HC_outliers", title: "<abbr title='Counts of outliers - defined as values 5 times higher than the average reading'>Outliers</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_outliers_perc", title: "<abbr title='Percentage of outliers'>Outliers (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true },
    {data: "HC_outliers_ignz", title: "<abbr title='Counts of outliers but ignore all zero values'>Outliers ign 0s</abbr>", defaultContent: '', filterType: 'text', visible: false },
    {data: "HC_outliers_ignz_perc", title: "<abbr title='Percentage of outliers (ignoring zeroes)'>Outliers ign 0s (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true },

    {data: "HC_count_score", title: "<abbr title='Score based on how many data points are available, from 0 for no data points to 5 for 100% availability'>Count score</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "HC_zeroes_score", title: "<abbr title='Score based on how many data points are zero, from 0 for all zeroes to 5 for no zeroes'>Zero score</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "HC_diff_pos_score", title: "<abbr title='Score based on how many data points are incremental, from 0 for all are incremental to 5 for none'>Diff pos score</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "HC_functional_matrix", title: "<abbr title='Functional matrix value - multiplying count score and zero score'>Func matrix</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "HC_cumulative_matrix", title: "<abbr title='Cumulative matrix value (only for cumulative meters) - multiplying count score, zero score, and diff pos score'>Cumu. matrix</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },
    {data: "HC_score", title: "<abbr title='Score from 0 (no or almost no useful data) to 5 (healthy meter)'>Score</abbr>", defaultContent: '', filterType: 'multi-select', visible: false },

    {data: null, title: "Comments", defaultContent: '', filterType: 'text', visible: true }
]

$(document).ready( function () {
    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "healthcheckTable";

    $('#healthcheckTable thead tr').clone(true).addClass('filters').appendTo('#healthcheckTable thead');

    healthcheckTable = $('#healthcheckTable').DataTable({
        data: hc_latest,
		pageLength: 25,
        lengthMenu: [
            [10, 25, 50, 100, -1],
            [10, 25, 50, 100, 'All']
        ],
        //paging: false,
        responsive: true,
        orderCellsTop: true,
        fixedHeader: true,
        columns: hctColumns,
        createdRow: function (row, data, dataIndex) {
            $(row).attr("data-sensor", data[varNameDevSensorID]);
            $(row).addClass('colorScore'+data["HC_score"]);

            // TODO: check date range applies
            for (c of context) {
                if (data[varNameDevSensorID] == c["sensor"]) {
                    if ($('td.lastCol', row).is(':empty')) {
                        $('td.lastCol', row).html("<b>"+c["author"].split('@')[0]+"</b>"+": "+c["comment"]);
                    } else {
                        $('td.lastCol', row).html($('td.lastCol', row).html() + "<br><b>" + c["author"].split('@')[0]+"</b>"+": "+c["comment"]);
                    }
                }
            }
        },
        layout: {
            topStart: {
                'pageLength': 25
            }
        },
        columnDefs: [
            { className: 'firstCol', targets: [0] },
            { className: 'lastCol', targets: [hctColumns.length - 1] }
        ],
        initComplete: function () {
            const api = this.api();

            api.columns().every(function (colIdx) {
                const column = this;
                const cell = $('.filters th').eq(colIdx);
                const title = cell.text();
                const filterType = hctColumns[colIdx].filterType || 'text';
                
                if (filterType === 'multi-select') {
                    let uniqueVals = [];

                    column.data().each(function (d) {
                        const val = (d || "").toString().trim().toLowerCase(); // normalize to lowercase
                        if (val && !uniqueVals.includes(val)) {
                            uniqueVals.push(val);
                        }
                    });

                    // Optionally title-case for display:
                    const titleCase = str => str.charAt(0).toUpperCase() + str.slice(1);
                    uniqueVals = uniqueVals.map(v => ({ raw: v, label: titleCase(v) }));

                    const select = $('<select multiple class="dt-filter"></select>');
                    uniqueVals.forEach(opt => {
                        select.append(`<option value="${opt.raw}">${opt.label}</option>`);
                    });

                    $(cell).html(select);
                    const select2 = select.select2({ placeholder: `Select ${title}` });

                    select.on('change', function () {
                        const selected = $(this).val();
                        if (selected && selected.length > 0) {
                            column.search(selected.join('|'), true, false).draw(); // regex OR match
                        } else {
                            column.search('').draw();
                        }
                    });
                }

                else if (filterType === 'text') {
                    $(cell).html(`<input type="text" class="dt-filter" placeholder="Filter ${title}" style="width: 100%;" />`);
                }

                else if (filterType === 'none') {
                    $(cell).html('');
                }

                // For single-value input/select filters
                if (filterType !== 'multi-select') {
                    $('input, select', cell).on('keyup change clear', function () {
                        const val = this.value;
                        if (api.column(colIdx).search() !== val) {
                            api.column(colIdx).search(val).draw();
                        }
                    });
                }
            });
                    
            // Initialize buttons and append them to a custom container
            new $.fn.dataTable.Buttons(api, {
                buttons: ['copy', 'csv', 'excel', 'pdf', 'print']
            });

            // Append to a custom div after the table
            $(api.table().container())
                .after('<div id="export-buttons" style="margin-top: 1em;"></div>');

            $(api.buttons().container()).appendTo('#export-buttons');
        }
    });

    document.querySelectorAll('button.toggle-vis').forEach((el) => {
        el.addEventListener('click', function (e) {
            e.preventDefault();
    
            let columnIdx = e.target.getAttribute('data-column');
            let column = healthcheckTable.column(columnIdx);
            column.visible(!column.visible());

            // Also toggle the visibility of the filter cell in the filters row
            let filterCell = document.querySelector(`#healthcheckTable thead tr.filters th:nth-child(${parseInt(columnIdx)+1})`);
            if (filterCell) {
                filterCell.style.display = isVisible ? '' : 'none';
            }

            el.classList.toggle("hidden");

            let urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('hidden')) {
                if (urlParams.get('hidden') == columnIdx) {
                    window.history.pushState({},"", "health-check.html");
                } else {
                    hiddenCols = ";" + urlParams.get('hidden') + ";";
                    if (hiddenCols.includes(";"+columnIdx+";")) {
                        hiddenCols = hiddenCols.replace(";"+columnIdx+";", ";");
                    } else {
                        hiddenCols += columnIdx;
                    }
                    hiddenCols = hiddenCols.replace(";;", ";");
                    window.history.pushState({},"", "health-check.html?hidden="+hiddenCols);
                }
            } else {
                window.history.pushState({},"", "health-check.html?hidden="+columnIdx);
            }
        });
    });

    let urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('hidden')) {
        let hiddenCols = urlParams.get('hidden').split(";");
        for (h of hiddenCols) {
            if (h != "") {
                healthcheckTable.column(h).visible(false);
                document.querySelector('[data-column="'+h+'"]').classList.toggle("hidden");
            }
        };
    };

    healthcheckTable.on('click', 'tbody tr td', function() {
        cell = healthcheckTable.cell(this);
        if (commentMode) return;
        if (cell.index()["column"] == 0) {
            console.log("hi")
            viewDevice(this.closest("tr").getAttribute("data-sensor"));
        } else if (this.classList.contains("lastCol")) {
            createContextDialog(
                this.closest("tr").getAttribute("data-sensor"),
                new Date(hc_meta["from_time"] * 1000).toISOString().slice(0, 10)+" 00:00",
                new Date(hc_meta["to_time"] * 1000).toISOString().slice(0, 10)+" 00:00"
            );
        }
    });

});
