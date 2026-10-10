const CONFIG =
    window.SWASTHYASAAR_CONFIG || {};


const API_BASE =
    CONFIG.apiBase || "";


const EP =
    CONFIG.endpoints || {};



/* =====================================================
   GLOBAL DATA
===================================================== */

let currentUser = null;

let labData = [];

let medications = [];

let safetyAlerts = [];

let safetyAssessments = [];

let assessmentAvailable = false;

let documents = [];

let documentsRefreshTimer = null;



/* =====================================================
   GET JWT TOKEN
===================================================== */

function getToken() {

    return (
        localStorage.getItem("access_token") ||
        sessionStorage.getItem("access_token") ||
        ""
    );

}



/* =====================================================
   GENERIC API FUNCTION
===================================================== */

async function apiFetch(
    path,
    options = {}
) {

    const headers =
        new Headers(
            options.headers || {}
        );


    const jwt =
        getToken();


    /*
        Send JWT to FastAPI
    */

    if (jwt) {

        headers.set(
            "Authorization",
            `Bearer ${jwt}`
        );

    }


    /*
        JSON content type
    */

    if (
        !(options.body instanceof FormData) &&
        options.body &&
        !headers.has("Content-Type")
    ) {

        headers.set(
            "Content-Type",
            "application/json"
        );

    }


    const response =
        await fetch(
            `${API_BASE}${path}`,
            {
                ...options,
                headers
            }
        );


    /*
        Unauthorized
    */

    if (response.status === 401) {

        localStorage.removeItem(
            "access_token"
        );

        sessionStorage.removeItem(
            "access_token"
        );

        window.location.href =
            "/login";

        return null;
    }


    const text =
        await response.text();


    let data = null;


    try {

        data =
            text
                ? JSON.parse(text)
                : null;

    }

    catch {

        data = text;

    }


    if (!response.ok) {

        throw new Error(
            data?.detail ||
            `Request failed: ${response.status}`
        );

    }


    return data;

}



/* =====================================================
   HTML ESCAPE
===================================================== */

function esc(value) {

    return String(
        value ?? ""
    ).replace(
        /[&<>"']/g,
        function (character) {

            return {

                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"

            }[character];

        }
    );

}



/* =====================================================
   MODALS
===================================================== */

function openModal(id) {

    document
        .getElementById(id)
        ?.classList
        .remove("hidden");

}


function closeModal(id) {

    document
        .getElementById(id)
        ?.classList
        .add("hidden");

}



/* =====================================================
   NAVIGATION
===================================================== */

function bindNavigation() {

    document
        .querySelectorAll(
            "[data-section]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const section =
                        document.getElementById(
                            button.dataset.section
                        );


                    if (section) {

                        section.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });

                    }


                    if (
                        button.classList.contains(
                            "nav-item"
                        )
                    ) {

                        document
                            .querySelectorAll(
                                ".nav-item"
                            )
                            .forEach(item =>
                                item.classList.remove(
                                    "active"
                                )
                            );


                        button.classList.add(
                            "active"
                        );

                    }

                }
            );

        });



    document
        .querySelectorAll(
            "[data-close]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    closeModal(
                        button.dataset.close
                    );

                }
            );

        });

}



/* =====================================================
   USER PROFILE
===================================================== */

async function loadProfile() {

    try {

        currentUser =
            await apiFetch(
                EP.profile ||
                "/user/getUser"
            );


        renderProfile(
            currentUser
        );

    }

    catch (error) {

        console.error(
            "Profile error:",
            error
        );

    }

}



function renderProfile(user) {

    const name =
        user?.name ||
        "User";


    document.getElementById(
        "welcomeName"
    ).textContent =
        name.split(" ")[0];


    document.getElementById(
        "headerUserName"
    ).textContent =
        name;


    document.getElementById(
        "avatarLetter"
    ).textContent =
        name
            .charAt(0)
            .toUpperCase();



    const fields = {

        profileName:
            user?.name,

        profileEmail:
            user?.email,

        profileGender:
            user?.gender,

        profileBirth:
            user?.year_of_birth,

        profileCondition:
            user?.medical_condition,

        profileAllergy:
            user?.allergy,

        profileBlood:
            user?.blood_group,

        profilePhone:
            user?.phone_number

    };


    Object.entries(fields)
        .forEach(
            ([id, value]) => {

                const element =
                    document.getElementById(
                        id
                    );


                if (element) {

                    element.value =
                        value ?? "";

                }

            }
        );

}



/* =====================================================
   MEDICATIONS
===================================================== */

async function loadMedications(
    status = "ALL"
) {

    try {

        let query = "";


        /*
            ALL

            GET /medications
        */

        if (status !== "ALL") {

            /*
                ACTIVE
                COMPLETED
                STOPPED
            */

            query =
                `?status_filter=${encodeURIComponent(
                    status
                )}`;

        }


        medications =
            await apiFetch(
                `${
                    EP.medications ||
                    "/medicine/display"
                }${query}`
            );


        /*
            Support different response formats
        */

        if (
            !Array.isArray(
                medications
            )
        ) {

            medications =
                medications?.items ||
                medications?.medications ||
                [];

        }


        renderMedications();

    }

    catch (error) {

        document.getElementById(
            "medicationTableBody"
        ).innerHTML = `

            <tr>

                <td
                    colspan="5"
                    class="loading"
                >

                    ${esc(error.message)}

                </td>

            </tr>

        `;

    }

}



/* =====================================================
   RENDER MEDICATIONS
===================================================== */

function renderMedications() {

    const search =
        document.getElementById(
            "medicationSearch"
        )
        .value
        .toLowerCase()
        .trim();


    const rows =
        medications.filter(
            medication => {

                const searchableText = [
                    medication.name,
                    medication.ingredients
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                return searchableText.includes(search);

            }
        );


    const table =
        document.getElementById(
            "medicationTableBody"
        );


    if (!rows.length) {

        table.innerHTML = `

            <tr>

                <td
                    colspan="5"
                    class="empty-state"
                >

                    No medications found.

                </td>

            </tr>

        `;

        return;

    }



    table.innerHTML =
        rows.map(
            medication => {

                const status =
                    String(
                        medication.status ||
                        "UNKNOWN"
                    ).toUpperCase();

                const prescriptionOnly = status === "PRESCRIPTION";

                /*
                    Backend:

                    STOPPED

                    Frontend:

                    Closed
                */

                const label =
                    prescriptionOnly
                        ? "Prescription only · verify use"
                        : status === "STOPPED"
                        ? "Closed"
                        : status
                            .charAt(0)
                            .toUpperCase()
                          +
                          status
                            .slice(1)
                            .toLowerCase();


                return `

                    <tr>

                        <td>

                            <strong>
                                ${esc(
                                    medication.name
                                )}
                            </strong>

                        </td>


                        <td>
                            ${esc(
                                medication.dosage ||
                                (Array.isArray(medication.ingredients)
                                    ? medication.ingredients.join(", ")
                                    : medication.ingredients) ||
                                [medication.frequency, medication.duration]
                                    .filter(Boolean)
                                    .join(" · ") ||
                                "Not listed"
                            )}
                        </td>


                        <td>

                            <span
                                class="
                                    status
                                    ${esc(status)}
                                "
                            >

                                ${esc(label)}

                            </span>

                        </td>


                        <td>

                            ${esc(
                                medication.prescription_date ||
                                formatDate(medication.start_date)
                            )}

                        </td>


                        <td>
                            ${esc(
                                formatDate(
                                    medication.end_date
                                )
                            )}
                        </td>

                    </tr>

                `;

            }
        )
        .join("");

}



/* =====================================================
   MEDICATION FILTER BUTTONS
===================================================== */

function bindMedicationFilters() {

    document
        .querySelectorAll(
            "#medicationFilters .filter"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                async () => {

                    /*
                        Remove active
                    */

                    document
                        .querySelectorAll(
                            "#medicationFilters .filter"
                        )
                        .forEach(
                            item =>
                                item.classList.remove(
                                    "active"
                                )
                        );


                    /*
                        Add active
                    */

                    button.classList.add(
                        "active"
                    );


                    /*
                        Call API

                        ALL
                        ACTIVE
                        COMPLETED
                        STOPPED
                    */

                    await loadMedications(
                        button.dataset.status
                    );

                }
            );

        });



    document
        .getElementById(
            "medicationSearch"
        )
        .addEventListener(
            "input",
            renderMedications
        );

}



/* =====================================================
   LAB DASHBOARD
===================================================== */

async function loadLabDashboard() {

    try {

        labData =
            await apiFetch(
                EP.labDashboard ||
                "/lab-tests/dashboard"
            );


        if (
            !Array.isArray(
                labData
            )
        ) {

            labData =
                labData?.tests ||
                labData?.items ||
                [];

        }


        populateLabTests();

    }

    catch (error) {

        const empty =
            document.getElementById(
                "labEmpty"
            );


        empty.classList.remove(
            "hidden"
        );


        empty.textContent =
            error.message;

    }

}



/* =====================================================
   LAB TEST DROPDOWN
===================================================== */

function populateLabTests() {

    const select =
        document.getElementById(
            "labTestSelect"
        );


    select.innerHTML = "";


    if (!labData.length) {

        select.innerHTML =
            "<option>No tests</option>";

        document
            .getElementById(
                "labEmpty"
            )
            .classList
            .remove("hidden");

        return;

    }


    labData.forEach(
        (test, index) => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                index;


            option.textContent =
                `${test.test_name || `Test ${index + 1}`}${
                    test.unit ? ` (${test.unit})` : ""
                }`;


            select.appendChild(
                option
            );

        }
    );


    select.addEventListener(
        "change",
        () => {

            drawLabChart(
                labData[
                    Number(
                        select.value
                    )
                ]
            );

        }
    );


    drawLabChart(
        labData[0]
    );

}



/* =====================================================
   LAB GRAPH
===================================================== */

function drawLabChart(test) {

    const canvas =
        document.getElementById(
            "labChart"
        );


    const empty =
        document.getElementById(
            "labEmpty"
        );


    const context =
        canvas.getContext(
            "2d"
        );


    const points =
        (test?.data || []).filter(
            point => Number.isFinite(Number(point.value))
        );


    if (!points.length) {

        empty.classList.remove(
            "hidden"
        );

        context.setTransform(1, 0, 0, 1, 0, 0);
        context.clearRect(
            0,
            0,
            canvas.width,
            canvas.height
        );

        return;

    }


    empty.classList.add(
        "hidden"
    );


    const rect =
        canvas.getBoundingClientRect();


    const ratio =
        window.devicePixelRatio || 1;


    canvas.width =
        rect.width * ratio;


    canvas.height =
        rect.height * ratio;

    context.setTransform(
        ratio,
        0,
        0,
        ratio,
        0,
        0
    );


    const width =
        rect.width;


    const height =
        rect.height;


    const padding = {

        left: 40,
        right: 15,
        top: 15,
        bottom: 48

    };


    const values =
        points
            .map(
                point =>
                    Number(
                        point.value
                    )
            )
            .filter(
                Number.isFinite
            );


    if (!values.length) {

        empty.classList.remove(
            "hidden"
        );

        context.clearRect(
            0,
            0,
            canvas.width,
            canvas.height
        );

        return;

    }


    const minimum =
        Math.min(
            ...values
        );


    const maximum =
        Math.max(
            ...values
        );


    const range =
        (maximum - minimum) ||
        1;


    const yMinimum =
        Math.max(
            0,
            minimum - range * .2
        );


    const yMaximum =
        maximum + range * .2;


    context.clearRect(
        0,
        0,
        width,
        height
    );


    /*
        Grid
    */

    context.strokeStyle =
        "#e5ebf4";

    context.lineWidth = 1;


    for (
        let i = 0;
        i < 5;
        i++
    ) {

        const y =
            padding.top +
            (
                (
                    height -
                    padding.top -
                    padding.bottom
                ) *
                i /
                4
            );


        context.beginPath();

        context.moveTo(
            padding.left,
            y
        );

        context.lineTo(
            width -
            padding.right,
            y
        );

        context.stroke();

        const tickValue =
            yMaximum -
            ((yMaximum - yMinimum) * i / 4);

        context.fillStyle = "#6b7890";
        context.font = "10px Arial";
        context.textAlign = "right";
        context.fillText(
            Number(tickValue.toPrecision(4)).toString(),
            padding.left - 7,
            y + 3
        );

    }


    /*
        Points
    */

    const coordinates =
        points.map(
            (point, index) => {

                const x =
                    padding.left +
                    (
                        (
                            width -
                            padding.left -
                            padding.right
                        ) *
                        index /
                        Math.max(
                            points.length - 1,
                            1
                        )
                    );


                const y =
                    padding.top +
                    (
                        (
                            yMaximum -
                            Number(
                                point.value
                            )
                        ) /
                        (
                            yMaximum -
                            yMinimum
                        )
                    ) *
                    (
                        height -
                        padding.top -
                        padding.bottom
                    );


                return {
                    x,
                    y
                };

            }
        );


    /*
        Line
    */

    const trendColor = points.some(point =>
        ["high", "low", "abnormal"].includes(
            String(point.flag || "").toLowerCase()
        )
    )
        ? "#c65d13"
        : "#2168e8";

    context.strokeStyle = trendColor;

    context.lineWidth = 3;

    context.beginPath();


    coordinates.forEach(
        (point, index) => {

            if (index === 0) {

                context.moveTo(
                    point.x,
                    point.y
                );

            }

            else {

                context.lineTo(
                    point.x,
                    point.y
                );

            }

        }
    );


    context.stroke();


    /*
        Points
    */

    coordinates.forEach(
        (point, index) => {

            const flag = String(points[index].flag || "").toLowerCase();
            const pointColor = ["high", "low", "abnormal"].includes(flag)
                ? "#c65d13"
                : "#2168e8";

            context.fillStyle = "#ffffff";

            context.strokeStyle = pointColor;

            context.lineWidth = 3;


            context.beginPath();

            context.arc(
                point.x,
                point.y,
                4.5,
                0,
                Math.PI * 2
            );

            context.fill();

            context.stroke();

            context.fillStyle = pointColor;
            context.font = "10px Arial";
            context.textAlign = "center";
            context.fillText(
                Number(points[index].value).toLocaleString("en-IN", {
                    maximumFractionDigits: 2
                }),
                point.x,
                point.y - 10
            );


            context.fillStyle =
                "#6b7890";

            context.font =
                "10px Arial";

            context.textAlign =
                "center";


            context.fillText(
                formatShortDate(
                    points[index].date
                ),
                point.x,
                height - 13
            );

        }
    );

}



/* =====================================================
   SAFETY ALERTS
===================================================== */

async function loadAlerts() {

    try {

        const data =
            await apiFetch(
                EP.alerts ||
                "/safety/alerts"
            );


        safetyAlerts =
            Array.isArray(data)
                ? data
                : (
                    data?.items ||
                    data?.alerts ||
                    []
                );

        safetyAssessments =
            Array.isArray(data?.assessments)
                ? data.assessments
                : [];

        assessmentAvailable =
            data?.assessment_available === true;


        renderAlerts();

    }

    catch (error) {

        document.getElementById(
            "alertsList"
        ).innerHTML = `

            <div class="empty-state">

                ${esc(error.message)}

            </div>

        `;

    }

}



function renderAlerts() {

    document.getElementById(
        "notificationDot"
    ).textContent =
        safetyAlerts.length;

    document.getElementById(
        "alertBadge"
    ).textContent =
        safetyAlerts.length;


    const list =
        document.getElementById(
            "alertsList"
        );


    if (!safetyAlerts.length) {
        const incomplete =
            safetyAssessments.some(
                assessment => assessment.status === "incomplete"
            );

        const heading =
            !assessmentAvailable
                ? "Safety assessment not available"
                : incomplete
                    ? "Safety screening incomplete"
                    : "No conflicts identified in recorded checks";

        const message =
            !assessmentAvailable
                ? "No safety assessment is recorded yet. This is not evidence that medications are safe."
                : incomplete
                    ? "At least one recorded safety assessment could not complete all checks. Review screening details before relying on the result."
                    : "No medication conflicts were identified in the recorded checks. These checks cover only information available to the screening system and do not guarantee medication safety.";

        list.innerHTML = `

            <div class="alert warning">

                <div class="alert-icon">i</div>
                <div>
                    <h4>${heading}</h4>
                    <p>${esc(message)}</p>
                    <a href="/safety-alerts">View screening details</a>
                </div>

            </div>

        `;

        return;

    }


    const incomplete =
        safetyAssessments.some(
            assessment => assessment.status === "incomplete"
        );

    const incompleteNotice =
        incomplete
            ? `
                <div class="alert warning">
                    <div class="alert-icon">!</div>
                    <div>
                        <h4>Safety screening incomplete</h4>
                        <p>At least one assessment could not complete all checks. Review it before relying on these findings.</p>
                        <a href="/safety-alerts">View screening details</a>
                    </div>
                </div>
            `
            : "";

    list.innerHTML =
        incompleteNotice +
        safetyAlerts
            .slice(0, 4)
            .map(
                alert => {

                    const severity =
                        String(
                            alert.severity ||
                            ""
                        ).toLowerCase();


                    const className =
                        severity.includes(
                            "high"
                        ) ||
                        severity.includes(
                            "critical"
                        )
                            ? "danger"

                            : severity.includes(
                                "medium"
                              ) ||
                              severity.includes(
                                "moderate"
                              )
                                ? "warning"

                                : "warning";


                    return `

                        <div
                            class="
                                alert
                                ${className}
                            "
                        >

                            <div
                                class="alert-icon"
                            >

                                ${
                                    className ===
                                    "danger"

                                    ? "!"

                                    : className ===
                                      "warning"

                                        ? "⚠"

                                        : "✓"
                                }

                            </div>


                            <div>

                                <h4>

                                    ${esc(
                                        alert.title ||
                                        alert.conflict_type ||
                                        "Safety Alert"
                                    )}

                                </h4>


                                <p>

                                    ${esc(
                                        alert.description ||
                                        alert.patient_alert_message ||
                                        alert.detail ||
                                        ""
                                    )}

                                </p>

                            </div>

                        </div>

                    `;

                }
            )
            .join("");

}



/* =====================================================
   DOCUMENTS
===================================================== */

async function loadDocuments() {

    try {

        const data =
            await apiFetch(
                EP.documents ||
                "/doc/"
            );


        documents =
            Array.isArray(data)
                ? data
                : (
                    data?.items ||
                    data?.documents ||
                    []
                );


        renderDocuments();
        if (documentsRefreshTimer) {
            window.clearTimeout(documentsRefreshTimer);
            documentsRefreshTimer = null;
        }
        if (documents.some(item => item.status === "processing")) {
            documentsRefreshTimer = window.setTimeout(loadDocuments, 2500);
        }

    }

    catch (error) {

        document.getElementById("documentTableBody").innerHTML =
            `<div class="loading">${esc(error.message)}</div>`;

    }

}



/* =====================================================
   DOCUMENT TABLE
===================================================== */

function renderDocuments() {

    const body =
        document.getElementById(
            "documentTableBody"
        );


    if (!documents.length) {

        body.innerHTML = `<div class="empty-state">No documents uploaded yet.</div>`;

        return;

    }


    body.innerHTML = documents.slice(0, 8).map(document => {
        const documentId = document.doc_id || document.id || "";
        const filename = document.original_filename || document.filename || "Document";
        return `
            <article class="dashboard-document-card">
                <div class="dashboard-document-card-heading">
                    <h3>${esc(filename)}</h3>
                    <span class="status ${esc(String(document.status || "UNKNOWN").toUpperCase())}">
                        ${esc(document.status || "Unknown")}
                    </span>
                </div>
                <div class="dashboard-document-meta">
                    <span>${esc(document.document_type || "Medical document")}</span>
                    <span>Uploaded ${esc(formatDate(document.uploaded_at))}</span>
                </div>
                ${document.review_summary || document.processing_message
                    ? `<p class="document-processing-note">${esc(document.review_summary || document.processing_message)}</p>`
                    : ""}
                <div class="dashboard-document-actions">
                    <button class="eye-btn" type="button" aria-label="View parsed details for ${esc(filename)}"
                        onclick="viewDocument('${esc(documentId)}')" ${document.status !== "parsed" ? "disabled" : ""}>
                        View details
                    </button>
                    <button class="document-delete-button" type="button" data-delete-document="${esc(documentId)}"
                        ${document.status === "processing" ? "disabled" : ""} aria-label="Delete ${esc(filename)}">
                        Delete
                    </button>
                </div>
            </article>
        `;
    }).join("");

    body.querySelectorAll("[data-delete-document]").forEach(button => {
        button.addEventListener("click", () =>
            deleteDashboardDocument(button.dataset.deleteDocument, button)
        );
    });

}

async function deleteDashboardDocument(documentId, button) {
    const selectedDocument = documents.find(item =>
        (item.doc_id || item.id) === documentId
    );
    const filename = selectedDocument?.original_filename || "this document";
    if (!window.confirm(
        `Delete "${filename}" and its parsed database records? Associated prescription medication records will also be removed. This action cannot be undone.`
    )) {
        return;
    }
    button.disabled = true;
    const path = (EP.documentDetail || "/doc/{doc_id}")
        .replace("{doc_id}", encodeURIComponent(documentId));
    try {
        await apiFetch(path, { method: "DELETE" });
        await Promise.all([
            loadDocuments(),
            loadMedications("ALL"),
            loadLabDashboard(),
            loadAlerts(),
            loadLabAlerts(),
        ]);
    } catch (error) {
        button.disabled = false;
        alert(`Could not delete document: ${error.message}`);
    }
}



/* =====================================================
   VIEW PARSED DOCUMENT
===================================================== */

async function viewDocument(
    documentId
) {

    if (
        !documentId ||
        !EP.documentDetail
    ) {

        alert(
            "Document detail endpoint is not configured."
        );

        return;

    }


    try {

        const data =
            await apiFetch(
                EP.documentDetail.replace(
                    "{doc_id}",
                    encodeURIComponent(
                        documentId
                    )
                )
            );

        showParsedDocument(
            [
                data?.parsed_text || data?.processing_message || "No parsed result is available for this document.",
                data?.safety_assessment ? `Medication safety screening: ${data.safety_assessment.message}` : "",
                data?.lab_assessment ? `Lab review: ${data.lab_assessment.flagged_count} flagged result(s) out of ${data.lab_assessment.test_count} parsed.` : ""
            ].filter(Boolean).join("\n\n")
        );

    }

    catch (error) {

        alert(
            error.message
        );

    }

}



/* =====================================================
   UPLOAD DOCUMENT
===================================================== */

async function uploadDocument(
    file
) {

    if (!file) {
        return;
    }


    /*
        10 MB limit
    */

    if (
        file.size >
        10 * 1024 * 1024
    ) {

        alert(
            "Maximum file size is 10 MB."
        );

        return;

    }


    const form =
        new FormData();


    form.append(
        "file",
        file
    );

    form.append(
        "doc_type",
        document.getElementById("documentType").value
    );

    const submitButton = document.getElementById("uploadDocumentBtn");
    if (submitButton) submitButton.disabled = true;
    setDashboardUploadProgress("Uploading your document…", true);

    try {

        const result =
            await apiFetch(
                EP.uploadDocument ||
            "/doc/doc_parse",
            {
                method: "POST",
                body: form
            }
        );

        if (!result?.doc_id) {
            throw new Error("The upload was received without a document status identifier.");
        }
        setDashboardUploadProgress(
            result.processing_message || "Upload received. Processing has started.",
            true
        );
        const processed = await waitForDashboardDocument(result.doc_id);
        showParsedDocument(
            [
                processed.parsed_text || "No parsed result is available for this document.",
                dashboardDocumentOutcome(processed)
            ].filter(Boolean).join("\n\n")
        );
        setDashboardUploadProgress(dashboardDocumentOutcome(processed), false);
        await loadDocuments();
        await Promise.all([loadAlerts(), loadLabAlerts()]);

    }

    catch (error) {

        setDashboardUploadProgress(error.message || "Document processing failed.", false, true);
        await loadDocuments();
        alert(
            `Upload failed: ${error.message}`
        );

    } finally {
        if (submitButton) submitButton.disabled = false;
        document.getElementById("documentInput").value = "";
    }

}

function setDashboardUploadProgress(message, active = false, error = false) {
    const panel = document.getElementById("dashboard-upload-progress");
    const output = document.getElementById("dashboard-upload-progress-message");
    if (!panel || !output) return;
    panel.classList.toggle("hidden", !message);
    panel.classList.toggle("error", error);
    const progress = panel.querySelector("progress");
    if (active) {
        progress?.removeAttribute("value");
    } else {
        progress?.setAttribute("value", "1");
        progress?.setAttribute("max", "1");
    }
    output.textContent = message || "";
}

async function waitForDashboardDocument(documentId) {
    const path = (EP.documentDetail || "/doc/{doc_id}")
        .replace("{doc_id}", encodeURIComponent(documentId));
    const timeoutAt = Date.now() + 10 * 60 * 1000;
    while (Date.now() < timeoutAt) {
        const result = await apiFetch(path);
        if (!result) throw new Error("Your session has expired. Sign in again to check this upload.");
        setDashboardUploadProgress(
            result.processing_message || "Processing your document…",
            result.status === "processing"
        );
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

function dashboardDocumentOutcome(result) {
    if (result.document_type === "prescription") {
        const assessment = result.safety_assessment;
        if (!assessment || ["pending", "screening_failed"].includes(assessment.status)) {
            return assessment?.message
                || "Prescription parsed, but medication safety screening is not complete. Do not treat this as an all-clear.";
        }
        if (assessment.status === "incomplete") {
            return `Prescription parsed. Safety screening is incomplete: ${assessment.message || "some checks could not be completed."} No complete safety conclusion can be drawn.`;
        }
        if (assessment.finding_count) {
            return `Prescription parsed. ${assessment.finding_count} potential safety finding(s) need clinician or pharmacist review.`;
        }
        return "Prescription parsed. No conflict was detected by the available safety checks; this does not prove the prescription is safe.";
    }
    const assessment = result.lab_assessment;
    if (result.processing_stage === "post_parse_failed") {
        return result.processing_message;
    }
    if (!assessment || assessment.status === "no_results_parsed") {
        return "Lab report parsed, but no lab values were extracted.";
    }
    if (assessment.flagged_count) {
        return `Lab report parsed. ${assessment.flagged_count} of ${assessment.test_count} result(s) were flagged high, low, or abnormal for clinician review.`;
    }
    return `Lab report parsed. No high, low, or abnormal flags were reported among ${assessment.test_count} parsed result(s). Unclassified results may not have been assessed.`;
}


function showParsedDocument(parsedText) {
    const output =
        document.getElementById("documentDetailText");

    output.textContent =
        parsedText ||
        "No parsed result is available for this document.";

    openModal("documentDetailModal");
}


/* =====================================================
   PATIENT SUMMARY
===================================================== */

async function startPatientSummary() {
    window.location.assign("/symptom-summary");

}



/* =====================================================
   DATE FUNCTIONS
===================================================== */

function formatDate(
    value
) {

    if (!value) {

        return "—";

    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return String(
            value
        );

    }


    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );

}



function formatShortDate(
    value
) {

    if (!value) {

        return "";

    }


    const rawDate = String(value).trim();
    const dayFirst = rawDate.match(
        /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/
    );
    const date = dayFirst
        ? new Date(
            Number(dayFirst[3]),
            Number(dayFirst[2]) - 1,
            Number(dayFirst[1])
        )
        : new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return String(
            value
        ).slice(0, 8);

    }


    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );

}



async function loadLabAlerts() {
    const target = document.getElementById("labAlertsList");

    try {
        const alerts = await apiFetch(
            EP.labAlerts || "/lab-tests/alerts"
        );

        if (!Array.isArray(alerts)) {
            throw new Error("The lab alert response was not in the expected format.");
        }

        if (!alerts.length) {
            target.innerHTML = `
                <div class="empty-state">
                    No parsed lab results currently carry a high, low, or abnormal flag.
                    Unflagged or unclassified results are not a guarantee of normality;
                    review the original report with your clinician.
                </div>
            `;
            return;
        }

        target.innerHTML = alerts.map(alert => `
            <article class="lab-result-alert">
                <strong>${esc(alert.title || "Lab result flagged for review")}</strong>
                <p>${esc(alert.message || "Review this result with your clinician.")}</p>
                ${alert.date ? `<small>Report date: ${esc(alert.date)}</small>` : ""}
                ${alert.document_name ? `<small>Document: ${esc(alert.document_name)}</small>` : ""}
            </article>
        `).join("");
    } catch (error) {
        target.innerHTML = `
            <div class="empty-state error-state">
                Unable to load lab result alerts: ${esc(error.message)}
            </div>
        `;
    }
}


/* =====================================================
   PAGE INITIALIZATION
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        bindNavigation();

        bindMedicationFilters();



        /*
            Document upload
        */

        document
            .getElementById(
                "uploadDocumentBtn"
            )
            .addEventListener(
                "click",
                () =>
                    document
                        .getElementById(
                            "documentInput"
                        )
                        .click()
            );


        document
            .getElementById(
                "documentInput"
            )
            .addEventListener(
                "change",
                event =>
                    uploadDocument(
                        event.target.files[0]
                    )
            );



        /*
            Patient Summary
        */

        document
            .getElementById(
                "startSummaryBtn"
            )
            .addEventListener(
                "click",
                startPatientSummary
            );



        /*
            Check JWT
        */

        if (!getToken()) {

            window.location.href =
                "/login";

            return;

        }



        /*
            Load dashboard data
            simultaneously
        */

        await Promise.all([

            loadProfile(),

            loadMedications(
                "ALL"
            ),

            loadLabDashboard(),

            loadAlerts(),

            loadLabAlerts(),

            loadDocuments()

        ]);

    }
);