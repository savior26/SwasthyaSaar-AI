(() => {
    "use strict";

    const config = window.SWASTHYASAAR_CONFIG || {};
    const endpoint = config.endpoints?.summaryReports || "/patient-summary/reports";
    const apiBase = config.apiBase || "";
    const savedReports = new Map();
    const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);

    const formatDate = value => {
        if (!value) return "Date unavailable";
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? String(value)
            : date.toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            });
    };

    const reportMarkup = report => {
        const patient = report.patient || {};
        const field = (label, value) => {
            if (value === null || value === undefined || value === "") return "";
            const text = Array.isArray(value) ? value.join(", ") : value;
            return `<p><strong>${escapeHtml(label)}:</strong> ${escapeHtml(text)}</p>`;
        };
        const symptoms = Array.isArray(report.symptom_details) ? report.symptom_details : [];
        const symptomMarkup = symptoms.map((symptom, index) => `
            <div class="report-symptom">
                <h3>Symptom ${index + 1}: ${escapeHtml(symptom.symptom || "Not specified")}</h3>
                ${field("Location", symptom.location)}
                ${field("Onset", symptom.onset)}
                ${field("Duration", symptom.duration)}
                ${field("Severity", symptom.severity)}
                ${field("Character", symptom.character)}
                ${field("Frequency", symptom.frequency)}
                ${field("Aggravating factors", symptom.aggravating_factors)}
                ${field("Relieving factors", symptom.relieving_factors)}
                ${field("Associated symptoms", symptom.associated_symptoms)}
                ${field("Symptoms explicitly denied", symptom.negative_symptoms)}
            </div>
        `).join("");

        return `
            <div class="report-content">
                <section class="report-section">
                    <h3>Patient</h3>
                    ${field("Name", patient.name)}
                    ${field("Age", patient.age)}
                    ${field("Gender", patient.gender)}
                    ${field("Medical conditions", patient.medical_condition)}
                    ${field("Allergies", patient.allergy)}
                </section>
                <section class="report-section">
                    <h3>Main concern</h3>
                    ${field("Chief complaint", report.chief_complaint)}
                    ${field("Patient description", report.patient_description)}
                    ${field("Additional information", report.additional_information)}
                </section>
                <section class="report-section">
                    <h3>Reported symptoms</h3>
                    ${symptomMarkup || "<p>No structured symptom details were returned.</p>"}
                </section>
            </div>
        `;
    };

    async function loadReports() {
        const targets = document.querySelectorAll("[data-summary-reports]");
        if (!targets.length) return;

        try {
            const headers = new Headers();
            const token = localStorage.getItem("access_token")
                || sessionStorage.getItem("access_token")
                || "";
            if (token) headers.set("Authorization", `Bearer ${token}`);

            const response = await fetch(`${apiBase}${endpoint}`, { headers });
            if (response.status === 401) {
                targets.forEach(target => {
                    target.innerHTML = '<p class="loading">Sign in again to view saved symptom summaries.</p>';
                });
                return;
            }
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data?.detail || `Request failed (${response.status})`);
            }
            if (!Array.isArray(data)) {
                throw new Error("Saved symptom summaries were returned in an unexpected format.");
            }
            savedReports.clear();
            data.forEach(item => savedReports.set(item.session_id, item));

            const markup = data.length
                ? data.map(item => {
                    const sessionId = escapeHtml(item.session_id);
                    const report = item.report || {};
                    return `
                        <article class="summary-report-history-card">
                            <h3>${escapeHtml(report.chief_complaint || "Symptom summary")}</h3>
                            <p>Completed ${escapeHtml(formatDate(item.completed_at))}</p>
                            <details>
                                <summary>View full report</summary>
                                ${reportMarkup(report)}
                            </details>
                            <div class="summary-report-actions">
                                <button
                                    class="summary-report-download"
                                    type="button"
                                    data-summary-download
                                    data-session-id="${sessionId}"
                                >Download / Print PDF</button>
                            </div>
                        </article>
                    `;
                }).join("")
                : '<p class="loading">No completed symptom summaries yet. Complete a guided interview to save a report here.</p>';
            targets.forEach(target => {
                target.innerHTML = markup;
            });
        } catch (error) {
            targets.forEach(target => {
                target.innerHTML = `<p class="loading error-state">Unable to load saved symptom summaries: ${escapeHtml(error.message)}</p>`;
            });
        }
    }

    async function downloadReport(button) {
        const sessionId = button.dataset.sessionId;
        if (!sessionId) return;

        const saved = savedReports.get(sessionId);
        if (saved && hasExtendedCharacters(saved.report)) {
            openPrintView(saved.report, saved.completed_at);
            return;
        }

        button.disabled = true;
        const originalText = button.textContent;
        button.textContent = "Preparing PDF…";
        try {
            const headers = new Headers();
            const token = localStorage.getItem("access_token")
                || sessionStorage.getItem("access_token")
                || "";
            if (token) headers.set("Authorization", `Bearer ${token}`);
            const pdfEndpoint = (config.endpoints?.summaryPdf
                || "/patient-summary/reports/{session_id}/pdf")
                .replace("{session_id}", encodeURIComponent(sessionId));
            const response = await fetch(`${apiBase}${pdfEndpoint}`, { headers });
            if (!response.ok) {
                let detail = `PDF download failed (${response.status})`;
                try {
                    const data = await response.json();
                    detail = data?.detail || detail;
                } catch {
                    // Keep the status-based error when the response is not JSON.
                }
                throw new Error(detail);
            }

            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = `symptom-summary-${sessionId}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(objectUrl);
        } catch (error) {
            window.alert(error.message || "Unable to download the symptom summary.");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    function hasExtendedCharacters(report) {
        return JSON.stringify(report || {}).split("").some(
            character => character.codePointAt(0) > 255
        );
    }

    function openPrintView(report, completedAt) {
        const printWindow = window.open("", "_blank");
        if (!printWindow) {
            window.alert("Allow pop-ups for this site to print this report as a PDF.");
            return;
        }

        printWindow.document.open();
        printWindow.document.write(`
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Doctor-ready symptom summary</title>
                <style>
                    body { color: #17233d; font: 15px/1.55 Arial, sans-serif; margin: 40px auto; max-width: 780px; padding: 0 24px; }
                    h1 { border-bottom: 2px solid #176f66; padding-bottom: 12px; }
                    h2, h3 { color: #203653; }
                    .report-section { border: 1px solid #dfe7f1; border-radius: 8px; margin: 14px 0; padding: 14px; break-inside: avoid; }
                    .report-symptom { border-top: 1px solid #e8edf4; margin-top: 12px; padding-top: 10px; }
                    .report-section p { margin: 5px 0; }
                    .prepared { color: #687791; }
                    @media print { body { margin: 0; max-width: none; padding: 0; } }
                </style>
            </head>
            <body>
                <h1>Doctor-ready symptom summary</h1>
                <p class="prepared">Completed ${escapeHtml(formatDate(completedAt))}</p>
                ${reportMarkup(report)}
                <p class="prepared">This summary records patient-reported information. It is not a diagnosis or a substitute for clinical assessment.</p>
            </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        printWindow.setTimeout(() => printWindow.print(), 300);
    }

    document.addEventListener("click", event => {
        const button = event.target.closest("[data-summary-download]");
        if (button) downloadReport(button);
    });

    document.addEventListener("DOMContentLoaded", loadReports);
    window.loadPatientSummaryReports = loadReports;
    window.registerPatientSummaryReport = (sessionId, report) => {
        if (sessionId && report) {
            savedReports.set(sessionId, {
                session_id: sessionId,
                report,
                completed_at: new Date().toISOString()
            });
        }
    };
})();
