(() => {
    "use strict";

    const config = window.SWASTHYASAAR_WORKSPACE || {};
    const endpoints = config.endpoints || {};
    const page = config.page || "";
    const message = document.getElementById("workspace-message");
    let documentRefreshTimer = null;
    const token = () =>
        localStorage.getItem("access_token")
        || sessionStorage.getItem("access_token")
        || "";

    const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);

    const api = async (path, options = {}) => {
        const headers = new Headers(options.headers || {});
        if (token()) {
            headers.set("Authorization", `Bearer ${token()}`);
        }
        if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }

        const response = await fetch(path, { ...options, headers });
        const text = await response.text();
        let data = null;
        try {
            data = text ? JSON.parse(text) : null;
        } catch {
            data = text;
        }

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            sessionStorage.removeItem("access_token");
            window.location.assign("/login");
            return null;
        }

        if (!response.ok) {
            throw new Error(data?.detail || `Request failed (${response.status})`);
        }
        return data;
    };

    const reportError = error => {
        if (!message) return;
        message.classList.add("error");
        message.textContent = error.message || "The request failed.";
    };

    const setMessage = text => {
        if (!message) return;
        message.classList.remove("error");
        message.textContent = text || "";
    };

    const displayValue = value => value === null || value === undefined || value === "" ? "Not provided" : String(value);

    function setDocumentUploadProgress(text, { active = false, error = false } = {}) {
        const panel = document.getElementById("document-upload-progress");
        const output = document.getElementById("document-upload-progress-message");
        if (!panel || !output) return;
        panel.classList.toggle("hidden", !text);
        panel.classList.toggle("error", error || /failed|incomplete|review/i.test(text));
        const progress = panel.querySelector("progress");
        if (active) {
            progress?.removeAttribute("value");
        } else {
            progress?.setAttribute("value", "1");
            progress?.setAttribute("max", "1");
        }
        output.textContent = text || "";
    }

    function documentDetailPath(id) {
        return (endpoints.documentDetail || "/doc/{doc_id}")
            .replace("{doc_id}", encodeURIComponent(id));
    }

    async function waitForDocumentProcessing(id) {
        const timeoutAt = Date.now() + 10 * 60 * 1000;
        while (Date.now() < timeoutAt) {
            const result = await api(documentDetailPath(id));
            if (!result) throw new Error("Your session has expired. Sign in again to check this upload.");
            setDocumentUploadProgress(result.processing_message || "Processing your document…", { active: result.status === "processing" });
            if (result.status === "failed") {
                throw new Error(result.processing_message || "Document processing failed.");
            }
            if (result.status === "parsed" && ["complete", "safety_check_failed", "post_parse_failed"].includes(result.processing_stage)) {
                return result;
            }
            await new Promise(resolve => window.setTimeout(resolve, 1500));
        }
        throw new Error("Processing is taking longer than expected. You can check the document status again later.");
    }

    function documentOutcome(result) {
        if (result.document_type === "prescription") {
            const assessment = result.safety_assessment;
            if (!assessment || assessment.status === "pending" || assessment.status === "screening_failed") {
                return assessment?.message
                    || "The prescription was parsed, but medication safety screening has not completed. Do not treat this as an all-clear.";
            }
            if (assessment.status === "incomplete") {
                return `Prescription parsed. Safety screening is incomplete: ${assessment.message || "some checks could not be completed."} No complete safety conclusion can be drawn.`;
            }
            if (assessment.finding_count) {
                return `Prescription parsed. ${assessment.finding_count} potential safety finding(s) were recorded for clinician or pharmacist review.`;
            }
            return "Prescription parsed. No conflict was detected by the available safety checks; this does not prove the prescription is safe.";
        }

        const assessment = result.lab_assessment;
        if (result.processing_stage === "post_parse_failed") {
            return result.processing_message;
        }
        if (!assessment || assessment.status === "no_results_parsed") {
            return "Document parsed, but no lab values were extracted.";
        }
        if (assessment.flagged_count) {
            return `Lab report parsed. ${assessment.flagged_count} of ${assessment.test_count} result(s) were flagged high, low, or abnormal for clinician review.`;
        }
        return `Lab report parsed. No high, low, or abnormal flags were reported among ${assessment.test_count} parsed result(s). Unclassified results may not have been assessed.`;
    }

    const displayMedicationDate = item => {
        if (item.prescription_date) return item.prescription_date;
        if (!item.start_date) return "Not provided";
        const date = new Date(item.start_date);
        return Number.isNaN(date.getTime())
            ? String(item.start_date)
            : date.toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            });
    };

    async function loadProfile() {
        const user = await api(endpoints.profile || "/user/getUser");
        if (!user) return;

        if (page === "profile") {
            const entries = [
                ["Name", user.name],
                ["Email", user.email],
                ["Gender", user.gender],
                ["Year of birth", user.year_of_birth],
                ["Medical conditions", user.medical_condition],
                ["Allergies", user.allergy],
                ["Blood group", user.blood_group],
                ["Phone number", user.phone_number]
            ];
            document.getElementById("profile-details").innerHTML = entries.map(([label, value]) =>
                `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(displayValue(value))}</dd></div>`
            ).join("");
        } else {
            const form = document.getElementById("profile-form");
            for (const name of ["name", "year_of_birth", "medical_condition", "allergy", "blood_group", "phone_number"]) {
                form.elements[name].value = user[name] ?? "";
            }
        }
    }

    async function saveProfile(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form).entries());
        payload.year_of_birth = payload.year_of_birth ? Number(payload.year_of_birth) : null;

        try {
            await api(endpoints.profileUpdate || "/user/update", {
                method: "PUT",
                body: JSON.stringify(payload)
            });
            setMessage("Profile updated.");
        } catch (error) {
            reportError(error);
        }
    }

    async function updatePassword(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const password = form.elements.password.value;
        const confirmation = form.elements.confirm_password.value;

        if (password !== confirmation) {
            reportError(new Error("The passwords do not match."));
            return;
        }

        try {
            await api(endpoints.updatePassword || "/user/updatePassword", {
                method: "PUT",
                body: JSON.stringify({ password })
            });
            form.reset();
            setMessage("Password updated successfully.");
        } catch (error) {
            reportError(error);
        }
    }

    async function loadLabReports() {
        const target = document.getElementById("lab-reports-list");
        try {
            const reports = await api(endpoints.labReports || "/lab-tests/reports");
            if (!reports?.length) {
                target.innerHTML = '<p class="loading">No parsed lab reports are available yet. Upload a lab report to begin.</p>';
                return;
            }
            target.innerHTML = reports.map(report => `
                <article class="record-card">
                    <h3>${escapeHtml(report.lab_name || report.original_filename || "Lab report")}</h3>
                    <div class="record-meta">
                        <span>Report date: ${escapeHtml(displayValue(report.date))}</span>
                        <span>Uploaded: ${escapeHtml(displayValue(report.uploaded_at))}</span>
                        <span>Status: ${escapeHtml(report.status)}</span>
                    </div>
                    ${report.tests?.length ? `
                        <div class="table-scroll"><table>
                            <thead><tr><th>Test</th><th>Result</th><th>Reference range</th><th>Flag</th></tr></thead>
                            <tbody>${report.tests.map(test => `<tr>
                                <td>${escapeHtml(test.test_name)}</td>
                                <td>${escapeHtml(displayValue(test.value))} ${escapeHtml(test.unit || "")}</td>
                                <td>${escapeHtml(displayValue(test.reference_range))}</td>
                                <td>${escapeHtml(test.flag || "Not reported")}</td>
                            </tr>`).join("")}</tbody>
                        </table></div>
                    ` : '<p>No test values were parsed for this report.</p>'}
                </article>
            `).join("");
        } catch (error) {
            target.textContent = error.message;
        }
    }

    async function loadMedications() {
        const target = document.getElementById("medications-list");
        const status = document.getElementById("medication-status").value;
        const query = status === "ALL" ? "" : `?status_filter=${encodeURIComponent(status)}`;
        try {
            const medications = await api(`${endpoints.medications || "/medicine/display"}${query}`);
            if (!medications?.length) {
                target.innerHTML = '<tr><td colspan="5" class="loading">No medications are recorded for this filter.</td></tr>';
                return;
            }
            target.innerHTML = medications.map(item => `<tr>
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.status)}</td>
                <td>${escapeHtml(displayMedicationDate(item))}</td>
                <td>${escapeHtml(displayValue(item.end_date))}</td>
                <td>${escapeHtml(Array.isArray(item.ingredients) ? item.ingredients.join(", ") : displayValue(item.ingredients))}</td>
            </tr>`).join("");
        } catch (error) {
            target.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
        }
    }

    async function loadDocuments() {
        const target = document.getElementById("documents-list");
        try {
            const documents = await api(endpoints.documents || "/doc/");
            if (!documents?.length) {
                target.innerHTML = '<p class="loading">No documents have been uploaded yet.</p>';
                return;
            }
            target.innerHTML = documents.map(item => `
                <article class="record-card">
                    <h3>${escapeHtml(item.original_filename || "Medical document")}</h3>
                    <div class="record-meta">
                        <span>Type: ${escapeHtml(item.document_type)}</span>
                        <span>Status: ${escapeHtml(item.status)}</span>
                        <span>Uploaded: ${escapeHtml(displayValue(item.uploaded_at))}</span>
                    </div>
                    <p>${escapeHtml(item.review_summary || item.processing_message || "")}</p>
                    ${item.status === "parsed" ? `
                        <details class="document-inline-details" data-document-id="${escapeHtml(item.doc_id)}">
                            <summary>View parsed details</summary>
                            <pre class="result-panel document-detail-text">Loading parsed details…</pre>
                        </details>
                    ` : ""}
                    <div class="document-card-actions">
                        <button type="button" class="document-delete" data-document-id="${escapeHtml(item.doc_id)}" ${item.status === "processing" ? "disabled" : ""}>Delete</button>
                    </div>
                </article>
            `).join("");

            target.querySelectorAll(".document-inline-details").forEach(details => {
                details.addEventListener("toggle", () => {
                    if (details.open && details.dataset.loaded !== "true") {
                        loadDocumentDetail(
                            details.dataset.documentId,
                            details.querySelector(".document-detail-text"),
                            details
                        );
                    }
                });
            });
            target.querySelectorAll(".document-delete").forEach(button => {
                button.addEventListener("click", () =>
                    deleteDocument(button.dataset.documentId, button)
                );
            });
            if (documentRefreshTimer) {
                window.clearTimeout(documentRefreshTimer);
                documentRefreshTimer = null;
            }
            if (documents.some(item => item.status === "processing")) {
                documentRefreshTimer = window.setTimeout(loadDocuments, 2500);
            }
        } catch (error) {
            target.textContent = error.message;
        }
    }

    async function loadDocumentDetail(id, output, details) {
        try {
            const result = await api(documentDetailPath(id));
            output.textContent = [
                result?.parsed_text || "No parsed result is available for this document.",
                result?.safety_assessment ? `\nMedication safety screening: ${result.safety_assessment.message}` : "",
                result?.lab_assessment ? `\nLab result review: ${result.lab_assessment.flagged_count} flagged result(s) out of ${result.lab_assessment.test_count} parsed.` : "",
            ].filter(Boolean).join("\n");
            details.dataset.loaded = "true";
        } catch (error) {
            output.textContent = error.message || "Unable to load parsed details.";
        }
    }

    async function deleteDocument(id, button) {
        const selectedDocument = button.closest(".record-card");
        const filename = selectedDocument?.querySelector("h3")?.textContent || "this document";
        if (!window.confirm(
            `Delete "${filename}" and its parsed database records? Associated prescription medication records will also be removed. This action cannot be undone.`
        )) {
            return;
        }

        button.disabled = true;
        try {
            await api(`${documentDetailPath(id)}`, { method: "DELETE" });
            setMessage("Document and its associated parsed records were deleted.");
            await Promise.all([
                loadDocuments(),
                loadLabReports(),
                loadMedications(),
                loadSafety(),
                loadLabResultAlerts(),
            ]);
        } catch (error) {
            button.disabled = false;
            reportError(error);
        }
    }

    async function uploadDocument(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const file = form.elements.file.files[0];
        if (!file) return;
        if (file.size > 10 * 1024 * 1024) {
            reportError(new Error("Maximum file size is 10 MB."));
            return;
        }
        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = "Processing document…";
        submitButton.setAttribute("aria-busy", "true");
        setDocumentUploadProgress("Uploading your document…", { active: true });
        try {
            const accepted = await api(endpoints.uploadDocument || "/doc/doc_parse", {
                method: "POST",
                body: formData
            });
            if (!accepted?.doc_id) throw new Error("The upload was received without a document status identifier.");
            setDocumentUploadProgress(accepted.processing_message || "Upload received. Processing has started.", { active: true });
            const result = await waitForDocumentProcessing(accepted.doc_id);
            setDocumentUploadProgress(documentOutcome(result));
            form.reset();
            await loadDocuments();
        } catch (error) {
            reportError(error);
            setDocumentUploadProgress(error.message || "Document processing failed.", { error: true });
            await loadDocuments();
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
            submitButton.removeAttribute("aria-busy");
        }
    }

    function renderSafety(data) {
        const assessmentsNode = document.getElementById("safety-assessments");
        const alertsNode = document.getElementById("safety-alerts");
        const assessments = Array.isArray(data?.assessments) ? data.assessments : [];
        const alerts = Array.isArray(data?.alerts) ? data.alerts : [];

        if (!data?.assessment_available || !assessments.length) {
            assessmentsNode.innerHTML = '<article class="record-card"><h3>No recorded safety assessment</h3><p>This is not evidence that your medications are safe. A screening result is recorded only after a prescription has been processed by the safety pipeline.</p></article>';
        } else {
            assessmentsNode.innerHTML = assessments.map(item => {
                const incomplete = item.status === "incomplete";
                const noConflicts = item.status === "no_conflicts_detected";
                return `<article class="record-card">
                    <h3>${incomplete ? "Assessment incomplete" : noConflicts ? "No conflicts identified in this recorded check" : "Safety finding recorded"}</h3>
                    <div class="record-meta">
                        <span>Checked: ${escapeHtml(displayValue(item.created_at))}</span>
                        <span>Prescription: ${escapeHtml(item.document_name || item.doc_id)}</span>
                        <span>Result: ${incomplete ? "Incomplete — manual review needed" : noConflicts ? "No conflicts detected" : "Review findings below"}</span>
                    </div>
                    ${item.patient_alert_message ? `<p>${escapeHtml(item.patient_alert_message)}</p>` : ""}
                    ${item.action_required ? `<p><strong>Pipeline note:</strong> ${escapeHtml(item.action_required)}</p>` : ""}
                    ${item.conflicts?.length ? `<p>${item.conflicts.length} recorded finding(s).</p>` : ""}
                </article>`;
            }).join("");
        }

        if (!alerts.length) {
            alertsNode.innerHTML = !assessments.length
                ? '<p class="loading">There are no recorded findings because no assessment is available.</p>'
                : data.assessment_incomplete
                    ? '<p class="loading">No conflict or critical finding was recorded, but one or more checks were incomplete. A clinician or pharmacist should review the medication list manually.</p>'
                    : '<p class="loading">No conflict or critical finding was recorded in these assessments. This result is limited to the data and checks available to the pipeline; it is not a guarantee of safety.</p>';
            return;
        }

        alertsNode.innerHTML = alerts.map(item => `
            <article class="record-card">
                <h3>${escapeHtml(item.title || "Safety finding")} <span class="severity">${escapeHtml(item.severity || "REVIEW")}</span></h3>
                <div class="record-meta"><span>Recorded: ${escapeHtml(displayValue(item.created_at))}</span></div>
                <p>${escapeHtml(item.description || item.patient_alert_message || "Review this finding with a clinician or pharmacist.")}</p>
                ${item.action_required ? `<p><strong>Action recorded:</strong> ${escapeHtml(item.action_required)}</p>` : ""}
            </article>
        `).join("");
    }

    async function loadSafety() {
        try {
            renderSafety(await api(endpoints.alerts || "/safety/alerts"));
        } catch (error) {
            document.getElementById("safety-assessments").textContent = error.message;
            document.getElementById("safety-alerts").textContent = error.message;
        }
    }

    async function loadLabResultAlerts() {
        const target = document.getElementById("lab-result-alerts");
        try {
            const alerts = await api(endpoints.labAlerts || "/lab-tests/alerts");
            if (!Array.isArray(alerts)) {
                throw new Error("The lab alert response was not in the expected format.");
            }
            if (!alerts.length) {
                target.innerHTML = '<p class="loading">No parsed lab results currently carry a high, low, or abnormal flag. Unflagged or unclassified results are not a guarantee of normality; review the original report with your clinician.</p>';
                return;
            }
            target.innerHTML = alerts.map(item => `
                <article class="record-card">
                    <h3>${escapeHtml(item.title || "Lab result flagged for review")} <span class="severity">REVIEW</span></h3>
                    <div class="record-meta">
                        ${item.date ? `<span>Report date: ${escapeHtml(item.date)}</span>` : ""}
                        ${item.document_name ? `<span>Document: ${escapeHtml(item.document_name)}</span>` : ""}
                    </div>
                    <p>${escapeHtml(item.message || "Review this result with your clinician.")}</p>
                </article>
            `).join("");
        } catch (error) {
            target.textContent = `Unable to load lab result alerts: ${error.message}`;
        }
    }

    const speechSynthesis = window.speechSynthesis;
    let recognition = null;
    let activeSession = null;
    let isSubmittingAnswer = false;
    let pendingTranscript = "";

    function setSummaryStatus(text, state = "") {
        const target = document.getElementById("summary-status");
        target.classList.remove("busy", "error");
        if (state) target.classList.add(state);
        target.textContent = text;
    }

    function speak(text) {
        if (!text || !speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
            setSummaryStatus("Text-to-speech is not available in this browser. You can continue by reading the questions.");
            return;
        }
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = document.getElementById("speech-language").value;
        utterance.onstart = () => {
            document.getElementById("stop-speaking").disabled = false;
            setSummaryStatus("Speaking the next question…");
        };
        utterance.onend = () => {
            document.getElementById("stop-speaking").disabled = true;
            setSummaryStatus("Your turn. Speak your answer or type it below.");
            document.getElementById("summary-answer").focus();
        };
        utterance.onerror = event => {
            if (event.error === "canceled" || event.error === "interrupted") return;
            document.getElementById("stop-speaking").disabled = true;
            setSummaryStatus("Speech playback failed. The question is still shown on screen.");
        };
        speechSynthesis.speak(utterance);
    }

    function renderReport(report) {
        const target = document.getElementById("summary-report");
        if (!report || typeof report !== "object") {
            target.innerHTML = '<section class="report-section"><p>The interview finished, but a structured report was not returned. Please try again or share your answers directly with a clinician.</p></section>';
            return;
        }

        const patient = report.patient || {};
        const symptoms = Array.isArray(report.symptom_details) ? report.symptom_details : [];
        const field = (label, value) => value === null || value === undefined || value === ""
            ? ""
            : `<p><strong>${escapeHtml(label)}:</strong> ${escapeHtml(Array.isArray(value) ? value.join(", ") : value)}</p>`;
        const patientFields = [
            field("Name", patient.name),
            field("Age", patient.age),
            field("Gender", patient.gender),
            field("Medical conditions", patient.medical_condition),
            field("Allergies", patient.allergy)
        ].filter(Boolean).join("");
        const symptomCards = symptoms.map((symptom, index) => `
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

        target.innerHTML = `
            <section class="report-section">
                <h3>Patient</h3>
                ${patientFields || "<p>No patient details were provided.</p>"}
            </section>
            <section class="report-section">
                <h3>Main concern</h3>
                ${field("Chief complaint", report.chief_complaint) || "<p>Not provided.</p>"}
                ${field("Patient description", report.patient_description)}
                ${field("Additional information", report.additional_information)}
            </section>
            <section class="report-section">
                <h3>Reported symptoms</h3>
                ${symptomCards || "<p>No structured symptom details were returned.</p>"}
            </section>
        `;
    }

    function renderSummary(response) {
        const questionPanel = document.getElementById("question-panel");
        const reportPanel = document.getElementById("summary-report-panel");
        const emergencyNotice = document.getElementById("emergency-notice");
        const question = document.getElementById("summary-question");
        const conversation = document.getElementById("summary-conversation");

        activeSession = response.session_id || activeSession;
        if (activeSession) {
            sessionStorage.setItem("patient_summary_session_id", activeSession);
        }

        if (response.emergency) {
            emergencyNotice.textContent = response.emergency_message
                || "The interview identified a possible urgent symptom. Seek immediate medical care or contact local emergency services.";
            emergencyNotice.classList.remove("hidden");
            questionPanel.classList.add("hidden");
            conversation.classList.add("hidden");
            speakButtonDisabled(true);
            speak(emergencyNotice.textContent);
            return;
        }
        emergencyNotice.classList.add("hidden");

        if (response.completed) {
            questionPanel.classList.add("hidden");
            reportPanel.classList.remove("hidden");
            renderReport(response.report);
            const downloadButton = document.getElementById("download-current-summary");
            downloadButton.dataset.sessionId = response.session_id || activeSession || "";
            window.registerPatientSummaryReport?.(
                downloadButton.dataset.sessionId,
                response.report
            );
            if (window.loadPatientSummaryReports) {
                window.loadPatientSummaryReports();
            }
            setSummaryStatus("Interview complete. Review the summary carefully before sharing it.");
            return;
        }

        if (response.question) {
            question.textContent = response.question;
            questionPanel.classList.remove("hidden");
            conversation.classList.remove("hidden");
            conversation.insertAdjacentHTML("beforeend", `
                <div class="conversation-turn assistant">
                    <span class="conversation-avatar" aria-hidden="true">AI</span>
                    <div class="conversation-bubble">${escapeHtml(response.question)}</div>
                </div>
            `);
            reportPanel.classList.add("hidden");
            speakButtonDisabled(false);
            document.getElementById("repeat-question").disabled = false;
            conversation.scrollTop = conversation.scrollHeight;
            if (document.getElementById("auto-speak").checked) {
                speak(response.question);
            } else {
                setSummaryStatus("Your turn. Speak your answer or type it below.");
                document.getElementById("summary-answer").focus();
            }
        }
    }

    function speakButtonDisabled(disabled) {
        const button = document.getElementById("repeat-question");
        if (button) button.disabled = disabled;
    }

    async function startInterview() {
        const startButton = document.getElementById("start-interview");
        startButton.disabled = true;
        setSummaryStatus("Starting the interview…", "busy");
        document.getElementById("summary-conversation").innerHTML = "";
        document.getElementById("summary-conversation").classList.add("hidden");
        document.getElementById("question-panel").classList.add("hidden");
        document.getElementById("summary-report-panel").classList.add("hidden");
        document.getElementById("emergency-notice").classList.add("hidden");
        activeSession = null;
        sessionStorage.removeItem("patient_summary_session_id");
        try {
            const result = await api(endpoints.summaryStart || "/patient-summary/start", { method: "POST" });
            if (result) renderSummary(result);
        } catch (error) {
            setSummaryStatus(error.message, "error");
        } finally {
            startButton.disabled = false;
        }
    }

    async function resumeInterview() {
        const savedSession = sessionStorage.getItem("patient_summary_session_id");
        if (!savedSession) return;

        activeSession = savedSession;
        setSummaryStatus("Resuming your interview…", "busy");
        try {
            const result = await api(
                `/patient-summary/session/${encodeURIComponent(savedSession)}`
            );
            if (result) {
                renderSummary(result);
                setSummaryStatus(
                    result.completed
                        ? "Your completed summary is ready to review."
                        : "Your interview has been restored. Continue with your answer."
                );
            }
        } catch (error) {
            activeSession = null;
            sessionStorage.removeItem("patient_summary_session_id");
            setSummaryStatus(
                `${error.message} Start a new interview to continue.`,
                "error"
            );
        }
    }

    async function submitAnswer(event) {
        event.preventDefault();
        const field = document.getElementById("summary-answer");
        const answer = field.value.trim();
        if (!answer || !activeSession || isSubmittingAnswer) return;

        isSubmittingAnswer = true;
        const sendButton = document.querySelector(".send-answer-button");
        sendButton.disabled = true;
        document.getElementById("start-listening").disabled = true;
        document.getElementById("summary-conversation").insertAdjacentHTML("beforeend", `
            <div class="conversation-turn patient">
                <span class="conversation-avatar" aria-hidden="true">You</span>
                <div class="conversation-bubble">${escapeHtml(answer)}</div>
            </div>
        `);
        document.getElementById("summary-conversation").scrollTop =
            document.getElementById("summary-conversation").scrollHeight;
        setSummaryStatus("Checking your answer and screening for urgent symptoms…", "busy");
        try {
            const answerPath = (endpoints.summaryAnswer || "/patient-summary/answer/{session_id}")
                .replace("{session_id}", encodeURIComponent(activeSession));
            const result = await api(answerPath, {
                method: "POST",
                body: JSON.stringify({ answer })
            });
            field.value = "";
            if (result) renderSummary(result);
        } catch (error) {
            setSummaryStatus(`${error.message} Your answer is still in the box; check your connection, then send it again.`, "error");
            document.getElementById("summary-conversation").lastElementChild?.remove();
        } finally {
            isSubmittingAnswer = false;
            sendButton.disabled = false;
            document.getElementById("start-listening").disabled = false;
        }
    }

    function configureSpeechInput() {
        const button = document.getElementById("start-listening");
        const support = document.getElementById("speech-support");
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
            button.disabled = true;
            support.textContent = "Speech-to-text is not supported by this browser. You can type your answer instead.";
            return;
        }
        support.textContent = "Speech recognition requires microphone permission. Review the transcript before sending it.";
        recognition = new Recognition();
        recognition.interimResults = false;
        recognition.continuous = false;
        recognition.maxAlternatives = 1;
        recognition.onstart = () => {
            speechSynthesis?.cancel();
            document.getElementById("stop-speaking").disabled = true;
            pendingTranscript = "";
            button.disabled = true;
            setSummaryStatus("Listening… speak naturally, then pause.", "busy");
            support.textContent = "Listening…";
        };
        recognition.onresult = event => {
            const transcript = event.results?.[0]?.[0]?.transcript || "";
            const field = document.getElementById("summary-answer");
            pendingTranscript = transcript;
            field.value = `${field.value}${field.value ? " " : ""}${transcript}`.trim();
            field.focus();
        };
        recognition.onerror = event => {
            support.textContent = `Speech recognition error: ${event.error}. You can type your answer instead.`;
            setSummaryStatus("Speech recognition did not complete. Type your answer or try the microphone again.", "error");
        };
        recognition.onend = () => {
            button.disabled = false;
            if (pendingTranscript && document.getElementById("auto-submit-speech").checked) {
                setSummaryStatus("Speech captured. Sending your answer…", "busy");
                document.getElementById("answer-form").requestSubmit();
            } else if (pendingTranscript) {
                setSummaryStatus("Speech captured. Review the transcript, then send it when ready.");
            } else if (support.textContent === "Listening…") {
                support.textContent = "Listening stopped. You can type your answer instead.";
                setSummaryStatus("No speech was captured. Try again or type your answer.");
            }
        };
        button.addEventListener("click", () => {
            recognition.lang = document.getElementById("speech-language").value;
            try {
                recognition.start();
            } catch (error) {
                support.textContent = error.message;
            }
        });
    }

    function initialize() {
        document.getElementById("logout-button").addEventListener("click", () => {
            localStorage.removeItem("access_token");
            localStorage.removeItem("token_type");
            sessionStorage.removeItem("access_token");
            window.location.assign("/login");
        });

        if (!token()) {
            window.location.assign("/login");
            return;
        }

        if (page === "profile" || page === "profile-edit") {
            loadProfile().catch(reportError);
            if (page === "profile-edit") {
                document.getElementById("profile-form").addEventListener("submit", saveProfile);
            } else {
                document.getElementById("password-form").addEventListener("submit", updatePassword);
            }
        } else if (page === "lab-reports") {
            loadLabReports();
        } else if (page === "medications") {
            document.getElementById("medication-status").addEventListener("change", loadMedications);
            loadMedications();
        } else if (page === "documents") {
            document.getElementById("document-form").addEventListener("submit", uploadDocument);
            loadDocuments();
        } else if (page === "safety-alerts") {
            loadSafety();
            loadLabResultAlerts();
        } else if (page === "symptom-summary") {
            document.getElementById("start-interview").addEventListener("click", startInterview);
            document.getElementById("answer-form").addEventListener("submit", submitAnswer);
            document.getElementById("repeat-question").addEventListener("click", () =>
                speak(document.getElementById("summary-question").textContent)
            );
            document.getElementById("stop-speaking").addEventListener("click", () => {
                speechSynthesis?.cancel();
                document.getElementById("stop-speaking").disabled = true;
                setSummaryStatus("Speech stopped. You can answer when ready.");
            });
            document.getElementById("restart-interview").addEventListener("click", startInterview);
            document.getElementById("read-report").addEventListener("click", () => {
                const reportText = document.getElementById("summary-report").innerText;
                speak(reportText);
            });
            configureSpeechInput();
            resumeInterview();
        }
    }

    document.addEventListener("DOMContentLoaded", initialize);
})();
