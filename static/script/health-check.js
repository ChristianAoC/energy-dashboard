const hctColumns = [
    {data: metaLabel["meter_id"], title: "Meter ID", defaultContent: '', filterType: 'text', visible: true },
    {data: metaLabel["description"], title: "<abbr title='Internally known as `serving_revised`'>Description</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic info" },
    {data: metaLabel["utility_type"], title: "Utility Type", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Basic info" },
    {data: metaLabel["main_meter"], title: "<abbr title='Marked as building_level_meter'>Main Meter?</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Basic info" },
    {data: metaLabel["building_id"], title: "Building ID", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic info" },
    {data: metaLabel["units"], title: "<abbr title='Measured units'>Units</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Basic info" },

    {data: metaLabel["location"], title: "Meter location", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Advanced info" },
    {data: metaLabel["reading_type"], title: "Rate/Cumulative", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Advanced info" },
    {data: metaLabel["HC_class_check"], title: "<abbr title='Checks if the rate/cumulative info seems correct: If the ratio is higher than 80 to 20 then it is probably cumulative, otherwise probably rate'>Rate/Cu. Check</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Advanced info" },
    {data: metaLabel["tenant"], title: "Tenant Meter?", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Advanced info" },
    {data: metaLabel["resolution"], title: "Resolution", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Advanced info" },
    {data: metaLabel["scaling_factor"], title: "Scaling Factor", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Advanced info" },

    {data: metaLabel["HC_count"], title: "<abbr title='Total count of data points'>Data Points</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "General analysis" },
    {data: metaLabel["HC_zeroes"], title: "<abbr title='Total count of zeroes'>Zeroes</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "General analysis" },
    {data: metaLabel["HC_zeroes_perc"], title: "<abbr title='Percentage of zero readings'>Zeroes (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "General analysis" },

    {data: metaLabel["HC_diff_neg"], title: "<abbr title='How many data points are declining (lower than the previous one)'>Diff: Neg.</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },
    {data: metaLabel["HC_diff_neg_perc"], title: "<abbr title='Percentage of declining data points'>D.Neg. (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },
    {data: metaLabel["HC_diff_pos"], title: "<abbr title='How many data points are increasing (higher than the previous one)'>Diff: Pos.</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },
    {data: metaLabel["HC_diff_pos_perc"], title: "<abbr title='Percentage of increasing data points'>D.Pos. (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },
    {data: metaLabel["HC_diff_zero"], title: "<abbr title='How many data points are the same as the previous one (no change)'>Diff: Zero</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },
    {data: metaLabel["HC_diff_zero_perc"], title: "<abbr title='Percentage of non-changing data points'>D. Zero (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Point diff. analysis" },

    {data: metaLabel["HC_median"], title: "<abbr title='The median reading (converted to rate)'>Median</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },
    {data: metaLabel["HC_mode"], title: "<abbr title='The mode reading (converted to rate), i.e., most frequent value'>Mode</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },
    {data: metaLabel["HC_std"], title: "<abbr title='Standard deviation (converted to rate)'>STD</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },
    {data: metaLabel["HC_min_value"], title: "<abbr title='Min reading (converted to rate)'>Min</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },
    {data: metaLabel["HC_max_value"], title: "<abbr title='Max reading (converted to rate)'>Max</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },
    {data: metaLabel["HC_mean"], title: "<abbr title='The mean (average) reading (converted to rate)'>Mean</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Basic analysis" },

    {data: metaLabel["HC_outliers"], title: "<abbr title='Counts of outliers - defined as values 5 times higher than the average reading'>Outliers</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Outlier analysis" },
    {data: metaLabel["HC_outliers_ignz"], title: "<abbr title='Counts of outliers but ignore all zero values'>Outliers ign 0s</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Outlier analysis" },
    {data: metaLabel["HC_outliers_ignz_perc"], title: "<abbr title='Percentage of outliers (ignoring zeroes)'>Outliers ign 0s (perc)</abbr>", defaultContent: '', filterType: 'text', visible: true, toggleGroup: "Outlier analysis" },

    {data: metaLabel["HC_count_score"], title: "<abbr title='Score based on how many data points are available, from 0 for no data points to 5 for 100% availability'>Count score</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Score calculation" },
    {data: metaLabel["HC_zeroes_score"], title: "<abbr title='Score based on how many data points are zero, from 0 for all zeroes to 5 for no zeroes'>Zero score</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Score calculation" },
    {data: metaLabel["HC_diff_pos_score"], title: "<abbr title='Score based on how many data points are incremental, from 0 for all are incremental to 5 for none'>Diff pos score</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Score calculation" },
    {data: metaLabel["HC_functional_matrix"], title: "<abbr title='Functional matrix value - multiplying count score and zero score'>Func matrix</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Score calculation" },
    {data: metaLabel["HC_score"], title: "<abbr title='Score from 0 (no or almost no useful data) to 5 (healthy meter)'>Score</abbr>", defaultContent: '', filterType: 'multi-select', visible: true, toggleGroup: "Score calculation" },

    {data: null, title: "Comments", defaultContent: '', filterType: 'text', visible: true }
]

function initHCTable() {
    const headerRow = $('#healthcheckTable thead tr').first();
    hctColumns.forEach(col => {
        $('<th>').text(col.title).appendTo(headerRow);
    });

    let healthcheckTable = $('#healthcheckTable').DataTable({
        data: browserData.meterHealth,
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
            $(row).attr("data-meter", data[metaLabel["meter_id"]]);
            $(row).addClass('colorScore'+data[metaLabel["HC_score"]]);

            for (const c of browserData.context || []) {
                const startInputStr = document.getElementById("sb-start-date").value;
                const endInputStr = document.getElementById("sb-end-date").value;

                if (c.target_type === "meter" && data[metaLabel["meter_id"]] === c.target_id) {
                    const cell = $('td.lastCol', row);
                    const commentHTML = `<b>${c.author.split('@')[0]}</b>: ${c.comment}`;

                    if (cell.is(':empty')) {
                        cell.html(commentHTML);
                    } else {
                        cell.append("<br>" + commentHTML);
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

            setupFilters(api);

            // Rebuild filters every time visibility changes
            api.on('column-visibility', function () {
                setupFilters(api);
            });

            // Export buttons
            new $.fn.dataTable.Buttons(api, {
                buttons: ['copy', 'csv', 'excel', 'pdf', 'print']
            });

            $(api.table().container())
                .after('<div id="export-buttons" style="margin-top: 1em;"></div>');
            $(api.buttons().container()).appendTo('#export-buttons');
        }
    });

    document.querySelectorAll('button.toggle-vis').forEach((el) => {
        el.addEventListener('click', function (e) {
            e.preventDefault();

            // Always use the button element, not the child abbr
            const button = e.currentTarget;
            const columnIdx = button.getAttribute('data-column');

            const column = healthcheckTable.column(columnIdx);
            const isVisible = !column.visible();
            column.visible(isVisible);

            // Toggle filter cell
            const filterCell = document.querySelector(
                `#healthcheckTable thead tr.filters th:nth-child(${parseInt(columnIdx) + 1})`
            );
            if (filterCell) {
                filterCell.style.display = isVisible ? '' : 'none';
            }

            button.classList.toggle("hidden");

        const params = new URLSearchParams(window.location.search);
        const colStr = String(columnIdx);

        // Safely parse existing hidden list
        const rawHidden = params.get("hidden") || "";
        const hiddenSet = new Set(
            rawHidden.split(',').map(x => x.trim()).filter(x => x !== "")
        );

        if (hiddenSet.has(colStr)) {
            hiddenSet.delete(colStr);
        } else {
            hiddenSet.add(colStr);
        }

        if (hiddenSet.size > 0) {
            // Only valid numeric values, no leading/trailing commas
            const hiddenStr = Array.from(hiddenSet).sort((a, b) => a - b).join(',');
            params.set("hidden", hiddenStr);
        } else {
            params.delete("hidden");
        }

        const newUrl = `${BASE_PATH}/health-check?${params.toString()}`;
        window.history.pushState({}, "", newUrl);
        });
    });

    let urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('hidden')) {
        let hiddenCols = urlParams.get('hidden').split(",");
        for (let h of hiddenCols) {
            if (h !== "") {
                const colIdx = parseInt(h, 10);
                if (!isNaN(colIdx) && colIdx >= 0 && colIdx < hctColumns.length) {
                    // Hide the column in DataTables
                    healthcheckTable.column(colIdx).visible(false);

                    // Explicitly add the .hidden class to the button
                    const btn = document.querySelector('[data-column="'+colIdx+'"]');
                    if (btn) {
                        btn.classList.add("hidden");
                    }
                }
            }
        }
    }

    healthcheckTable.on('click', 'tbody tr td', function() {
        cell = healthcheckTable.cell(this);
        if (commentMode) return;
        if (cell.index()["column"] == 0) {
            window.location.href = BASE_PATH + "/browser?ref=health-check&meter_id=" + this.closest("tr").getAttribute("data-meter");
        } else if (this.classList.contains("lastCol")) {
            createContextDialog(
                this.closest("tr").getAttribute("data-meter")
            );
        }
    });    
};

function updateHCTable() {
    // Update DataTable contents
    const table = $('#healthcheckTable').DataTable();

    table.clear();
    table.rows.add(browserData.meterHealth);
    table.draw();
}

function setupFilters(api) {
    const headerRow = $('#healthcheckTable thead tr').first();
    $('#healthcheckTable thead tr.filters').remove(); // remove old filters
    const filterRow = $('<tr class="filters"></tr>');

    // Append one <th> per visible column
    api.columns().every(function () {
        if (this.visible()) {
            filterRow.append('<th></th>');
        }
    });
    headerRow.after(filterRow);

    // Now populate filters
    let visibleIndex = 0;
    api.columns().every(function () {
        const column = this;
        const colIdx = column.index();
        const config = hctColumns[colIdx];
        const filterType = config.filterType || 'text';
        const title = $('<div>').html(config.title).text(); // strip HTML

        if (!column.visible()) return;

        const cell = $('.filters th').eq(visibleIndex);

        if (filterType === 'multi-select') {
            let uniqueVals = [];

            column.data().each(function (d) {
                const val = (d || "").toString().trim();
                if (val && !uniqueVals.includes(val)) {
                    uniqueVals.push(val);
                }
            });

            const select = $('<select multiple class="dt-filter"></select>');
            uniqueVals.sort().forEach(opt => {
                select.append(`<option value="${opt}">${opt}</option>`);
            });

            $(cell).html(select);
            select.select2({ placeholder: `Select ${title}`, width: '100%' });

            select.on('change', function () {
                const selected = $(this).val();
                if (selected && selected.length > 0) {
                    column.search(selected.join('|'), true, false).draw();
                } else {
                    column.search('').draw();
                }
            });
        }

        else if (filterType === 'text') {
            $(cell).html(`<input type="text" class="dt-filter" placeholder="Filter ${title}" style="width: 100%;" />`);
            $('input', cell).on('keyup change clear', function () {
                if (column.search() !== this.value) {
                    column.search(this.value).draw();
                }
            });
        }

        else {
            $(cell).empty();
        }

        visibleIndex++;
    });
}

function buildColumnToggles() {
    const container = $('#dt-cols-toggles');
    container.empty(); // clear old content

    const grouped = {};

    hctColumns.forEach((col, idx) => {
        // Skip columns with no toggleGroup (they are "essential")
        if (!col.toggleGroup) return;

        if (!grouped[col.toggleGroup]) {
            grouped[col.toggleGroup] = [];
        }
        grouped[col.toggleGroup].push({ index: idx, title: col.title });
    });

    // Render each group
    Object.entries(grouped).forEach(([groupName, cols]) => {
        const groupDiv = $('<div style="margin-bottom:1em;"></div>');
        groupDiv.append(`<strong>${groupName}</strong><br>`);

        cols.forEach(c => {
            const btn = $(`<button type="button" class="toggle-vis" data-column="${c.index}">${c.title}</button><br>`);
            groupDiv.append(btn);
        });

        container.append(groupDiv);
    });
}

// Unified fetch + update function
async function fetchAndUpdateHealthCheck({ startDateStr, endDateStr, showStatus = true }) {
    if (showStatus) {
        $('#healthcheckStatus').text('Loading health check...');
    }

    try {
        const startDate = startDateStr || document.getElementById("sb-start-date").value;
        const endDate = endDateStr || document.getElementById("sb-end-date").value;

        const fromTime = Math.floor(new Date(startDate).getTime() / 1000);
        const toTime = Math.floor(new Date(endDate).getTime() / 1000);
        const timestamp = Date.now() / 1000;

        // Construct URL with query params if dates provided
        const url = new URL(apiEndpoints.meterHealth, window.location.origin);
        if (startDate && endDate) {
            url.searchParams.append('from_time', startDate);
            url.searchParams.append('to_time', endDate);
        }

        const meterHealthResponse = await fetch(url.toString());
        const cacheState = meterHealthResponse.headers.get('X-Cache-State');
        const meterHealth = await meterHealthResponse.json();

        const { hcMeta, getcontext } = await getData({
            hcMeta: {},
            getcontext: {}
        });

        browserData.meterHealth = meterHealth || [];
        browserData.hcMeta = hcMeta || {};
        browserData.context = getcontext || [];

        if (hcMeta?.from_time && hcMeta?.to_time) {
            document.getElementById("sb-start-date").value = new Date(hcMeta.from_time).toISOString().split("T")[0];
            document.getElementById("sb-end-date").value = new Date(hcMeta.to_time).toISOString().split("T")[0];
        }

        updateHCTable();

        if (cacheState === 'stale') {
            $('#healthcheckStatus').text('Updating health check... table will reload when done.');
            retryHealthCheckUpdate();
        } else {
            $('#healthcheckStatus').text('Health check loaded.');
        }

    } catch (err) {
        console.error("Failed to load health check", err);
        $('#healthcheckStatus').text('Error loading health check.');
    }
}

// Retry logic now reuses the unified fetcher
function retryHealthCheckUpdate() {
    const retryIntervalMs = 10000;
    setTimeout(() => {
        fetchAndUpdateHealthCheck({ showStatus: true });
    }, retryIntervalMs);
}

// Manual reload button handler now just calls the unified fetcher
async function getNewHealthCheck() {
    const startDateInput = document.getElementById("sb-start-date");
    const endDateInput = document.getElementById("sb-end-date");

    startDateInput.disabled = true;
    endDateInput.disabled = true;
    $('#healthcheckStatus').text('Reloading health check...');

    await fetchAndUpdateHealthCheck({
        startDateStr: startDateInput.value,
        endDateStr: endDateInput.value,
        showStatus: false
    });

    startDateInput.disabled = false;
    endDateInput.disabled = false;
}

// Document ready
$(async function () {
    document.getElementById("comment-bubble").classList.remove("hidden");
    commentParent = "healthcheckTable";

    // Always init browserData safely
    browserData.meterHealth = [];
    browserData.hcMeta = {};
    browserData.context = [];

    // Always init table once with empty data
    buildColumnToggles();
    initHCTable();

    // Kick off first load
    fetchAndUpdateHealthCheck({ showStatus: true });
});
