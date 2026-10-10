# SwasthyaSaar

SwasthyaSaar is a FastAPI web application for organizing a patient's medical
documents and presenting extracted health information. It includes account
management, lab-report and prescription parsing, medication and lab views,
medication safety screening, and a guided symptom-summary interview.

> **Clinical safety notice:** This application is an information and screening
> aid, not a medical device, diagnosis, or prescribing system. OCR and AI
> extraction can be incomplete or incorrect. A missing alert or a result with
> no detected conflict does not prove that a medicine or lab result is safe.
> Patients and clinicians should verify information against the original
> document and consult a qualified clinician or pharmacist.

## Features

- Patient registration, login, profile editing, and password updates.
- Upload and parse prescriptions and lab reports (PDF, PNG, JPG/JPEG, DOCX,
  and TXT; maximum 10 MB per upload).
- Show upload acknowledgement and processing stages, followed by parsed
  details, lab flags, or medication-screening status.
- View lab reports, numeric lab trends, recorded medication entries, and
  safety assessments.
- Run medication screening against available RxNorm, FDA drug-label, allergy,
  and patient-context information.
- Conduct a guided symptom interview and save completed summaries for later
  review and PDF/print export.
- View and delete a patient's own uploaded document and its associated parsed
  data from the document views.

## Project structure

```text
.
├── agent/                 # Persistent symptom-summary interview runtime
├── data/                  # Local runtime/checkpoint data (not source code)
├── models/                # SQLAlchemy database models
├── routes/                # FastAPI API routes and dashboard page routes
├── safety/                # Medication normalization and safety screening
├── schemas/               # Pydantic request, response, and parser schemas
├── services/              # AI model setup, alerts, and summary PDF creation
│   └── prompts/           # Document parsing and clinical prompts
├── static/
│   ├── css/               # Dashboard and workspace styles
│   └── js/                # Dashboard, workspace, and report-history behavior
├── templates/             # Jinja2 HTML templates
├── uploads/               # Sample/local upload assets
├── utils/
│   ├── orchestrator/      # Document parsing and prescription safety flow
│   └── tools/             # File validation and parsed-text formatting
├── database.py            # SQLAlchemy engine and session dependency
├── main.py                # FastAPI app, schema setup, and router registration
├── settings.py            # Environment-backed application settings
└── requirements.txt       # Python dependencies
```

`main.py` creates the database tables at startup and includes the application
routers. It also adds the `processing_stage` column to an existing
`medical_documents` table when that column is absent. This is a small
compatibility adjustment, not a general database migration system; use a
versioned migration tool before deploying larger schema changes.


## Requirements

- Python 3.10 or newer.
- PostgreSQL. The models use PostgreSQL UUID and JSONB column types.
- A Google AI API key for document parsing and the symptom-summary agent.
- Network access to configured third-party services for AI, RxNorm, and FDA
  drug-label lookups.


## Configuration

Create a local `.env` file in the project root. Set these variables there or
through the process environment:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy connection URL. |
| `SECRET_KEY` | Private signing key used for authentication tokens. |
| `ALGORITHM` | JWT signing algorithm configured for this deployment. |
| `GOOGLE_API_KEY` | Credential used by the Google GenAI client. |
| `EXPIRY` | Token lifetime in minutes; defaults to `30` if omitted. |



```dotenv
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>
SECRET_KEY=<generate-a-long-random-secret>
ALGORITHM=HS256
GOOGLE_API_KEY=<your-provider-key>
EXPIRY=30
```

Keep `.env` private. It is excluded by `.gitignore`; never paste credentials
into source files, screenshots, issue reports, or committed documentation.
Generate a unique, high-entropy `SECRET_KEY` for each environment and use
deployment secret management for production.

## Local setup (Windows PowerShell)

From the project root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure `.env`, create an application database in PostgreSQL, and make sure
the database URL points to it. Then start the development server:

```powershell
uvicorn main:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/login`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

The app initializes the tables during startup. The Google AI client and OCR
reader are initialized as application modules load, so valid configuration
and installed dependencies are required for startup.

## Main routes

### Web pages

| Path | Page |
| --- | --- |
| `/` | Dashboard |
| `/login` | Login page |
| `/profile` | Patient profile |
| `/profile/edit` | Profile editor |
| `/lab-reports` | Lab reports |
| `/medications` | Medication records |
| `/documents` | Medical document upload and history |
| `/symptom-summary` | Guided symptom interview and saved reports |
| `/safety-alerts` | Medication screening assessments and lab flags |

### API groups

| Prefix | Purpose |
| --- | --- |
| `/auth` | Registration, login, and authentication |
| `/user` | Read/update profile and update password |
| `/doc` | Upload, list, retrieve, and delete medical documents |
| `/medicine` | Patient medication records |
| `/lab-tests` | Lab reports, flags, and trend data |
| `/safety` | Recorded medication safety assessments and alerts |
| `/patient-summary` | Start/resume interviews, submit answers, list reports, and download PDFs |

Most patient-data endpoints require the authenticated user's bearer token.
See `/docs` for the exact request fields and response schemas.

## Document processing

1. The authenticated user uploads a file and selects prescription or lab
   report.
2. The API validates the extension and 10 MB size limit, creates a document
   record, and responds with HTTP `202 Accepted`.
3. The UI polls the patient-scoped document endpoint for the current stage:
   upload received, parsing, saving results, medication screening or lab
   review, and completion/failure.
4. Images and scanned PDFs use EasyOCR and/or the configured AI vision parser;
   structured results are saved to PostgreSQL.
5. Prescription processing runs the medication-safety pipeline. Lab reports
   expose extracted flags for review.
6. The temporary processing file is removed after the worker finishes; this
   implementation does not provide a permanent original-document download.

Deleting a document removes its parsed report/prescription and associated
safety records. Prescription-linked medication rows are also removed.
Deletion is restricted to the owning patient and is not allowed while
processing is active.

## Privacy and external services

Medical information is sensitive. Document parsing sends extracted document
text or page images to the configured Google GenAI service. Medication checks
send medicine identifiers/names or ingredient names to RxNorm and FDA public
drug-label endpoints. Review those providers' privacy terms and your
organization's regulatory/security obligations before using real patient
information. Do not use sample credentials or sample patient records in
production.

The application currently stores patient profile, parsed health data,
medications, safety checks, and summary sessions in the configured PostgreSQL
database. Secure the database, transport, backups, logs, deployment secrets,
and access controls appropriately. Do not log or expose authentication
credentials or unnecessary patient data.

