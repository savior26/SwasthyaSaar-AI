(function () {
    "use strict";

    const config = window.SWASTHYASAAR_CONFIG || {};
    const endpoint = config.endpoints?.labDashboard || "/lab-tests/dashboard";
    const base = config.apiBase || "";
    const timeline = document.getElementById("timeline-range");
    const chartGrid = document.getElementById("trend-chart-grid");
    const status = document.getElementById("trend-status");
    let groupedTests = [];

    function getToken() {
        return localStorage.getItem("access_token") ||
            sessionStorage.getItem("access_token") || "";
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[character]);
    }

    function parseDate(value) {
        if (!value) return null;
        const text = String(value).trim();
        let match = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:$|T)/);
        if (match) return validDate(Number(match[1]), Number(match[2]), Number(match[3]));
        match = text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
        if (match) return validDate(Number(match[3]), Number(match[2]), Number(match[1]));
        return null;
    }

    function validDate(year, month, day) {
        const date = new Date(year, month - 1, day);
        if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
            return null;
        }
        return date;
    }

    function formatDate(value) {
        const date = parseDate(value);
        return date
            ? new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "2-digit" }).format(date)
            : "Date not recorded";
    }

    function getVisiblePoints(test) {
        const days = timeline.value === "all" ? null : Number(timeline.value);
        const cutoff = days === null ? null : new Date(Date.now() - days * 86400000);
        return (test.data || [])
            .map((point, index) => ({
                ...point,
                value: Number(point.value),
                parsedDate: parseDate(point.date),
                originalIndex: index
            }))
            .filter(point => Number.isFinite(point.value))
            .filter(point => point.parsedDate && (cutoff === null || point.parsedDate >= cutoff))
            .sort((a, b) => {
                return a.parsedDate - b.parsedDate || a.originalIndex - b.originalIndex;
            });
    }

    function formatValue(value) {
        return Number(value).toLocaleString(undefined, { maximumSignificantDigits: 5 });
    }

    function makeChart(test, points, chartIndex) {
        const width = 680;
        const height = 232;
        const pad = { top: 18, right: 16, bottom: 40, left: 54 };
        const plotWidth = width - pad.left - pad.right;
        const plotHeight = height - pad.top - pad.bottom;
        const values = points.map(point => point.value);
        const minimum = Math.min(...values);
        const maximum = Math.max(...values);
        const spread = maximum - minimum;
        const buffer = spread ? spread * 0.16 : Math.max(Math.abs(maximum) * 0.12, 1);
        const low = minimum - buffer;
        const high = maximum + buffer;
        const x = index => pad.left + (points.length === 1 ? plotWidth / 2 : plotWidth * index / (points.length - 1));
        const y = value => pad.top + (high - value) / (high - low) * plotHeight;
        const ticks = Array.from({ length: 4 }, (_, index) => high - (high - low) * index / 3);
        const path = points.map((point, index) =>
            `${index === 0 ? "M" : "L"} ${x(index).toFixed(2)} ${y(point.value).toFixed(2)}`
        ).join(" ");
        const labelIndices = points.length <= 3
            ? points.map((_, index) => index)
            : [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
        const grid = ticks.map(tick => `
            <line class="trend-gridline" x1="${pad.left}" y1="${y(tick)}" x2="${width - pad.right}" y2="${y(tick)}"></line>
            <text x="${pad.left - 8}" y="${y(tick) + 3}" text-anchor="end">${escapeHtml(formatValue(tick))}</text>
        `).join("");
        const line = points.length > 1 ? `<path class="trend-line" d="${path}"></path>` : "";
        const circles = points.map((point, index) => {
            const isFlagged = ["high", "low", "abnormal"].includes(String(point.flag || "").toLowerCase());
            return `<circle class="trend-point${isFlagged ? " trend-point-flagged" : ""}" cx="${x(index)}" cy="${y(point.value)}" r="4">
                <title>${escapeHtml(formatDate(point.date))}: ${escapeHtml(formatValue(point.value))}${test.unit ? ` ${escapeHtml(test.unit)}` : ""}${point.flag ? ` (${escapeHtml(point.flag)})` : ""}</title>
            </circle>`;
        }).join("");
        const dateLabels = labelIndices.map(index => `
            <text x="${x(index)}" y="${height - 12}" text-anchor="${index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}">${escapeHtml(formatDate(points[index].date))}</text>
        `).join("");

        return `<svg class="trend-svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="trend-chart-title-${chartIndex}">
            <title id="trend-chart-title-${chartIndex}">${escapeHtml(test.test_name)} trend graph${test.unit ? ` in ${escapeHtml(test.unit)}` : ""}</title>
            ${grid}${line}${circles}${dateLabels}
        </svg>`;
    }

    function render() {
        const testsWithPoints = groupedTests.map(test => ({ ...test, visiblePoints: getVisiblePoints(test) }));
        const visibleTests = testsWithPoints.filter(test => test.visiblePoints.length);
        const pointCount = visibleTests.reduce((count, test) => count + test.visiblePoints.length, 0);
        const flaggedCount = visibleTests.reduce((count, test) =>
            count + test.visiblePoints.filter(point => ["high", "low", "abnormal"].includes(String(point.flag || "").toLowerCase())).length, 0);
        const undatedCount = groupedTests.reduce((count, test) =>
            count + (test.data || []).filter(point => Number.isFinite(Number(point.value)) && !parseDate(point.date)).length, 0);
        const undatedNote = document.getElementById("trend-undated-note");

        document.getElementById("trend-test-count").textContent = String(visibleTests.length);
        document.getElementById("trend-point-count").textContent = String(pointCount);
        document.getElementById("trend-flag-count").textContent = String(flaggedCount);
        undatedNote.hidden = undatedCount === 0;
        undatedNote.textContent = undatedCount
            ? ` ${undatedCount} numeric ${undatedCount === 1 ? "result has" : "results have"} no usable report date and ${undatedCount === 1 ? "is" : "are"} excluded from the timeline.`
            : "";

        if (!visibleTests.length) {
            chartGrid.innerHTML = "";
            status.hidden = false;
            const hasUndatedResults = undatedCount > 0 && timeline.value === "all";
            status.innerHTML = hasUndatedResults
                ? `<div class="trend-chart-empty"><strong>Lab results are missing usable dates</strong>We found ${undatedCount} numeric ${undatedCount === 1 ? "result" : "results"}, but cannot place them on a timeline. Review them in <a href="/lab-reports">Lab Reports</a>.</div>`
                : `<div class="trend-chart-empty"><strong>No numeric lab results in this timeline</strong>Try a longer date range or upload a lab report with numeric results.</div>`;
            return;
        }

        status.hidden = true;
        chartGrid.innerHTML = visibleTests.map((test, index) => {
            const latest = test.visiblePoints[test.visiblePoints.length - 1];
            const latestUnit = latest.unit || test.unit || "";
            return `<article class="trend-chart-card">
                <header class="trend-chart-head">
                    <div>
                        <h2>${escapeHtml(test.test_name)}</h2>
                        <p class="trend-chart-meta">${test.visiblePoints.length} ${test.visiblePoints.length === 1 ? "result" : "results"}${test.unit ? ` · ${escapeHtml(test.unit)}` : ""}</p>
                    </div>
                    <div class="trend-latest">${escapeHtml(formatValue(latest.value))}${latestUnit ? ` ${escapeHtml(latestUnit)}` : ""}<small>Latest shown</small></div>
                </header>
                ${makeChart(test, test.visiblePoints, index)}
                <div class="trend-chart-foot">Flag markers reflect the uploaded report</div>
            </article>`;
        }).join("");
    }

    function normalizeTests(data) {
        const series = new Map();
        for (const test of Array.isArray(data) ? data : data?.tests || data?.items || []) {
            if (!test?.test_name || !Array.isArray(test.data)) continue;
            for (const point of test.data) {
                const unit = String(point.unit || test.unit || "").trim();
                const key = `${String(test.test_name).trim().toLocaleLowerCase()}|${unit.toLocaleLowerCase()}`;
                if (!series.has(key)) series.set(key, { test_name: String(test.test_name).trim(), unit, data: [] });
                series.get(key).data.push(point);
            }
        }
        return [...series.values()].sort((a, b) => a.test_name.localeCompare(b.test_name));
    }

    async function load() {
        const headers = new Headers();
        const token = getToken();
        if (token) headers.set("Authorization", `Bearer ${token}`);

        try {
            const response = await fetch(`${base}${endpoint}`, { headers });
            if (response.status === 401) {
                localStorage.removeItem("access_token");
                sessionStorage.removeItem("access_token");
                window.location.assign("/login");
                return;
            }
            if (!response.ok) throw new Error(`Could not load lab history (HTTP ${response.status}).`);
            groupedTests = normalizeTests(await response.json());
            if (!groupedTests.length) {
                status.hidden = false;
                status.innerHTML = `<div class="trend-chart-empty"><strong>No numeric lab results yet</strong>Upload a lab report to see available trends here.</div>`;
                document.getElementById("trend-test-count").textContent = "0";
                document.getElementById("trend-point-count").textContent = "0";
                document.getElementById("trend-flag-count").textContent = "0";
                return;
            }
            render();
        } catch (error) {
            status.hidden = false;
            status.textContent = error.message || "Unable to load lab results. Please try again later.";
        }
    }

    timeline.addEventListener("change", render);
    load();
}());
