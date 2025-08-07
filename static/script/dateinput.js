function onDateInputChange() {
    const startInput = document.getElementById("sb-start-date");
    const endInput = document.getElementById("sb-end-date");
    if (startInput && endInput) {
        const startDate = new Date(startInput.value);
        const endDate = new Date(endInput.value);
        if (!isNaN(startDate) && !isNaN(endDate)) {
            const params = new URLSearchParams(window.location.search);
            params.set("from_time", startInput.value);
            params.set("to_time", endInput.value);
            const newUrl = `${window.location.pathname}?${params.toString()}`;
            history.replaceState({}, "", newUrl);
        }
    }
}

function getCurPageStartDate() {
    if (document.getElementById("sb-start-date")) {
        return document.getElementById("sb-start-date").value+" 23:50";
    } else {
        return null;
    }
};

function getCurPageEndDate() {
    if (document.getElementById("sb-end-date")) {
        return document.getElementById("sb-end-date").value+" 23:50";
    } else {
        return null;
    }
};

$(async function () {
    const startInput = document.getElementById("sb-start-date");
    const endInput = document.getElementById("sb-end-date");

    if (!startInput || !endInput) {
        return;
    }

    function formatDate(date) {
        return date.toISOString().split("T")[0];
    }

    function parseDateOrNull(str) {
        if (!str) return null;
        const d = new Date(str);
        return isNaN(d.getTime()) ? null : d;
    }

    function getDateFromURL(key) {
        const params = new URLSearchParams(window.location.search);
        return parseDateOrNull(params.get(key));
    }

    function updateURLParams(fromDate, toDate) {
        const params = new URLSearchParams(window.location.search);
        params.set("from_time", formatDate(fromDate));
        params.set("to_time", formatDate(toDate));
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        history.replaceState({}, "", newUrl);
    }

    function setDateRange(startDate, endDate) {
        startInput.value = formatDate(startDate);
        endInput.value = formatDate(endDate);
        updateURLParams(startDate, endDate);
    }

    const urlStart = getDateFromURL("from_time");
    const urlEnd = getDateFromURL("to_time");

    if (urlStart && urlEnd) {
        setDateRange(urlStart, urlEnd);
        return;
    }

    const path = window.location.pathname.replace(BASE_PATH, '');
	const filename = path.split('/')[1];

    try {
        if (OFFLINE_MODE) {
            const { offlineMeta } = await getData({ offlineMeta: {} });
            browserData.offlineMeta = offlineMeta;

            if (offlineMeta?.end_time) {
                const endDate = new Date(offlineMeta.end_time);
                const startDate = new Date(endDate);
                startDate.setDate(endDate.getDate() - defaultDateRanges[filename]);
                setDateRange(startDate, endDate);
                return;
            }

            throw new Error("offlineMeta missing or malformed");
        } else {
            const endDate = new Date();
            const startDate = new Date(endDate);
            startDate.setDate(endDate.getDate() - defaultDateRanges[filename]);
            setDateRange(startDate, endDate);
        }
    } catch (err) {
        console.error("Failed to load or parse data", err);
        const endDate = new Date();
        const startDate = new Date(endDate);
        startDate.setDate(endDate.getDate() - defaultDateRanges[filename]);
        setDateRange(startDate, endDate);
    }
});
