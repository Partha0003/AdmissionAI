# AdmissionAI — AI-Driven Smart Admission Automation & Transparent Onboarding Platform

> **PROTOTYPE / PROOF OF CONCEPT NOTICE:**  
> **AdmissionAI is an academic prototype developed for M.Tech AI & Data Science using synthetic demo data and mock external integrations.**  
> It is strictly **NOT** connected to the live Tamil Nadu Engineering Admissions (TNEA) system, live institutional ERPs, real payment gateways, or live student databases.

---

#### Terminal 1 — Backend (FastAPI + Python)

```bash
# 1. Ensure you are at the repository root
cd d:\ME-PROJECT

# 2. Activate Python Virtual Environment
# Windows PowerShell:
.\venv\Scripts\activate
# Windows Command Prompt (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# 3. Install/Update Backend Dependencies (FastAPI, OpenCV, PyMuPDF, Pytesseract, SQLAlchemy, etc.)
pip install -r backend/requirements.txt

# 4. Run Database Migrations (Alembic)
cd backend
alembic upgrade head
cd ..

# 5. Seed Database with Demo Accounts and Synthetic Student Personas
python scripts/seed_database.py

# 6. Start FastAPI Development Server
cd backend
uvicorn app.main:app --reload --port 8000
```

- **Backend API URL:** `http://localhost:8000`
- **Interactive Swagger API Documentation:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`

---

#### Terminal 2 — Frontend (React + TypeScript + Vite)

```bash
# 1. Open a new terminal and navigate to the frontend directory
cd d:\ME-PROJECT\frontend

# 2. Install NPM Packages (if not already installed)
npm install

# 3. Start Vite Development Server
npm run dev
```

- **Frontend Application URL:** `http://localhost:5173`

---


## 1. Project Overview & Vision

**AdmissionAI** coordinates and automates the higher education engineering admission journey from centralized counselling (TNEA) seat allotment to first-year classroom onboarding. The architecture delivers:

- **Configurable Institutional Identity:** Defaulted to **XYZ Engineering College** (Code: `XYZ`, Academic Year: `2026-27`).
- **Deterministic Finite State Machine (FSM):** 20 distinct lifecycle states with role-based transition assertions and immutable audit history.
- **Role-Based Access Control (RBAC):** Discrete portals and authorizations for `STUDENT`, `ADMIN_VERIFIER`, `FINANCE_OFFICER`, `ADMISSION_HEAD`, and `SUPER_ADMIN`.
- **Anti-IDOR Security:** Scoped session authorizations ensuring students can never access or modify another candidate's records.
- **Enterprise UI/UX:** Responsive React + Tailwind CSS dashboard with status timelines, metric cards, and audit telemetry.

---

## 2. Technology Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async/Sync), Alembic.
- **Security:** Argon2 password hashing (`passlib`), PyJWT (JSON Web Tokens), Role-Based Access Control.
- **Database:** PostgreSQL 16 (Relational & JSONB) with SQLite in-memory fallback for unit testing.
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Axios.
- **Containerization:** Docker, Docker Compose.

---

## 3. Repository Structure

```
AdmissionAI/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (auth, students, admissions, admin)
│   │   ├── core/            # Configuration, Security, State Machine Engine
│   │   ├── database/        # Session managers (Async & Sync), DeclarativeBase
│   │   ├── models/          # SQLAlchemy ORM models (Institution, Role, User, Student, Admission)
│   │   ├── schemas/         # Pydantic v2 request/response models
│   │   └── services/        # Business logic & state transition services
│   ├── migrations/          # Alembic database migration scripts
│   ├── tests/               # Pytest automated test suite (18 unit/integration tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # StatusBadge, StatusTimeline, MetricCard, ProtectedRoute, Header, Sidebar
│   │   ├── layouts/         # AuthLayout, StudentLayout, AdminLayout
│   │   ├── pages/           # LoginPage, StudentDashboard, AdminDashboard
│   │   ├── services/        # Axios API clients
│   │   ├── types/           # TypeScript data interfaces
│   │   └── config/          # Institution branding configuration
│   ├── Dockerfile
│   └── package.json
├── data/
│   └── synthetic/           # Synthetic student profiles (XYZ2026001 - XYZ2026005)
├── scripts/
│   └── seed_database.py     # Database seeder with demo accounts and personas
├── docs/                    # Architectural specifications and diagrams
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Quick Start & Execution Guide

### Running Locally (Step-by-Step)

The project consists of a FastAPI backend and a React + Vite frontend. Run them in two separate terminal windows from the repository root (`d:\ME-PROJECT`).

---


### Option B: Running with Docker Compose

To launch the multi-container stack with PostgreSQL:

```bash
# 1. Start all containers
docker compose up -d --build

# 2. Apply migrations & seed database inside backend container
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_database.py
```

- **Frontend Portal:** `http://localhost:5173`
- **Backend REST API:** `http://localhost:8000/docs`

---

## 5. Demo Credentials (XYZ Engineering College 2026-27)

### Administrative & Staff Accounts
| Role | Email | Password | Access / Primary Responsibilities |
|---|---|---|---|
| **Admin / Verifier** | `admin@xyz.edu.demo` | `Admin@1234` | Full Scrutiny Desk, AI Scrutiny, Visual Comparison, OCR Inspector |
| **Document Verifier** | `verifier@xyz.edu.demo` | `Verifier@1234` | Document Scrutiny Desk & Verification Actions |
| **Finance Officer** | `finance@xyz.edu.demo` | `Finance@1234` | Fee Verification, Payment Ledgers |
| **Admission Head** | `head@xyz.edu.demo` | `Head@1234` | Admission Approvals, Quota Overrides, Executive Reporting |
| **Super Admin** | `superadmin@xyz.edu.demo` | `SuperAdmin@1234` | User Management, System Configuration, Audits |

### Synthetic Student Accounts (Default Password: `Student@1234`)
| TNEA App No. | Candidate Name | Allotted Branch | Lifecycle State | Email |
|---|---|---|---|---|
| `XYZ2026001` | Karthikeyan S | Computer Science & Engineering | `ACTIVATED` | `karthik.xyz2026001@demo.admissionai.local` |
| `XYZ2026002` | Ananya Ramesh | Electronics & Communication | `APPLICATION_IN_PROGRESS` | `ananya.xyz2026002@demo.admissionai.local` |
| `XYZ2026003` | Praveen Kumar M | Information Technology | `APPLICATION_SUBMITTED` | `praveen.xyz2026003@demo.admissionai.local` |
| `XYZ2026004` | Divya Bharathi K | AI & Data Science | `ACTIVATION_PENDING` | `divya.xyz2026004@demo.admissionai.local` |
| `XYZ2026005` | Mohammed Riyaz A | Electrical & Electronics | `DOCUMENT_REVIEW` | `riyaz.xyz2026005@demo.admissionai.local` |

---

## 6. Running Automated Tests & Quality Checks

### Run Backend Regression Suite (Pytest)
```bash
# From repository root with virtual environment activated:
pytest backend/tests -v
```
**Test Suite Coverage (54 Passing Tests across Phases 1–4C):**
- Authentication, Argon2id hashing, and JWT lifecycle.
- Role-Based Access Control (RBAC) and Anti-IDOR scoping.
- Finite State Machine (FSM) assertions and audit history logging.
- Phase 2 Mock TNEA batch ingestion adapter and activation token lifecycle.
- Phase 3 Dynamic quota document checklist, versioned uploads, and application wizard.
- Phase 4A Document Classifier abstraction and heuristic classification jobs.
- Phase 4B OpenCV image preprocessing pipeline (Grayscale, CLAHE, Deskew, Thresholding, rasterization).
- Phase 4C OCR Engine abstraction, `TesseractOCREngine`, `MockOCREngine`, coordinate normalization, and bounding box visualizer integration.

### Run Frontend Production Build Check
```bash
cd frontend
npm run build
```

---

## 7. Implementation Roadmap & Status

- **Phase 1 (Complete):** Core architecture, database models, Argon2/JWT auth, RBAC, admission state machine, React frontend shell, Student & Admin dashboards.
- **Phase 2 (Complete):** Mock TNEA allotment batch ingestion adapter (`MockTNEAAdapter`), idempotent student creation, single-use activation token lifecycle, candidate activation portal (`/activate`), Admin TNEA Import studio.
- **Phase 3 (Complete):** Online multi-step application wizard, dynamic quota document checklist, private versioned document storage, application submission workflow, and admin scrutiny desk.
- **Phase 4A (Complete):** AI Document Processing foundation, `DocumentClassifier` abstraction, `RuleBasedDocumentClassifier`, heuristic scoring, and admin AI scan trigger.
- **Phase 4B (Complete):** OpenCV Document Image Preprocessing foundation (`OpenCVDocumentPreprocessor` v1.0.0-opencv), PDF rasterization, contrast enhancement, deskewing, thresholding, and side-by-side visual comparison modal.
- **Phase 4C (Complete):** OCR Engine Abstraction, `TesseractOCREngine` (v1.0.0 via pytesseract), `MockOCREngine` (v1.0.0-mock), standardized `[x, y, w, h]` bounding box contract, preprocessed image dependency, and interactive OCR Inspection & Bounding Box Visualizer modal.
- **Phase 4D (Next):** Structured Field Extraction from OCR Results (parsing Name, DOB, Community, HSC Marks with confidence scoring and human review flags).
- **Phase 5:** Deterministic rule validation, confidence scoring, duplicate detection, and cross-document reconciliation.
- **Phase 6:** Human-in-the-Loop (HITL) administrative exception desk and correction resubmission.
- **Phase 7:** Dynamic QR token appointment booking & on-campus physical verification desk.
- **Phase 8:** Mock Payment gateway & Demand Draft finance reconciliation ledger.
- **Phase 9:** 2-Way ERP staging synchronization adapter.
- **Phase 10:** Notification engine and immutable event audit timeline.
- **Phase 11:** Context-Aware RAG Conversational Assistant.
- **Phase 12:** Student onboarding, parent dashboard, and induction module.
- **Phase 13:** Academic research evaluation metrics (OCR CER/WER, extraction precision/recall, latency).

