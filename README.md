# DealForge — AI-Native Enterprise CRM

> An AI-powered deal origination ecosystem built with FastAPI, React, LangGraph, and LiteLLM.

---

## 🏗️ Architecture

```
dealforge/
├── frontend/        React 18 + Vite 5 + TypeScript + Tailwind CSS v4
├── backend/         Python FastAPI + SQLAlchemy (async) + Pydantic Settings
├── agents/          LangGraph workflows + LiteLLM abstraction
├── database/        Alembic migrations + seed data
├── shared/          Cross-module constants (Python)
└── desktop/         Electron 33 desktop shell
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional for production) PostgreSQL 16+

---

### 1. Configure environment

```bash
# Windows PowerShell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env

# macOS/Linux
# cp .env.example .env
# cp frontend/.env.example frontend/.env
```

The backend reads the repository `.env` and, when present, `backend/.env`
(`backend/.env` takes precedence). The frontend reads `frontend/.env`.
SQLite is the default, so no database service or credentials are required for
local development. LLM keys are optional until an AI workflow is invoked;
add only the key for the provider you choose. Set `APP_SECRET_KEY` to a
random value of at least 32 characters before using authentication. Generate
one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

---

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
python -m pip install -r requirements.txt

# Run the development server (auto-reloads on changes)
python main.py
```

Backend is now running at **http://localhost:8000**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health
- Versioned health: http://localhost:8000/api/v1/health

---

### 3. Frontend

```bash
cd frontend

# Install dependencies (first run only)
npm install

# Start the Vite dev server
npm run dev
```

Frontend is now running at **http://localhost:5173**

The dashboard calls the backend using `VITE_API_URL` (default
`http://localhost:8000`). CORS origins are controlled by `ALLOWED_ORIGINS`.
Run the backend and frontend in separate terminals.

The authenticated workspace includes responsive navigation for deal origination,
investor matching, diligence, compliance, transactions, and AI operations. Deal,
client, and originator profiles connect to tenant-scoped APIs. The Clients screen
supports company details, onboarding status, assignment, interaction history,
and file uploads. TXT/CSV uploads support basic draft field extraction.
External MCA, DIN, KYC, or AML providers are not configured; available check
actions are explicitly simulated. Investor and transaction modules still show
clearly labeled fictional demonstration data until their backend APIs are
available.

The Deal Pipeline supports tenant-scoped deal CRUD, search and stage/sector/
originator filters, a nine-stage Kanban board, per-stage transaction totals,
originator reassignment, deal details, activity history, and document upload,
download, and deletion. Deal stages are Lead Identified, Initial Screening,
Client Onboarding, Mandate Drafting, Due Diligence, Investor Matching,
Negotiation, Closed Won, and Closed Lost. The corresponding REST routes are
`/api/v1/deals/`, `/api/v1/deals/{deal_id}/activity`, and
`/api/v1/deals/{deal_id}/documents` (with nested document file routes).
Use the currency selector beside the profile menu to choose any of the 251
supported country/territory settings. Financial values are converted from each
record's stored currency using daily INR-based rates (INR is selected by
default). Exchange rates are fetched from the public
[currency-api dataset](https://github.com/fawazahmed0/exchange-api); an internet
connection is required for conversion, and the selector reports rate failures
instead of displaying amounts in the wrong currency. This display preference
is saved in the current browser.

The Mandate Generator accepts PDF and DOCX source documents and runs a six-agent
LangGraph workflow for extraction, financial mapping, deal structuring, mandate
and anonymized teaser drafting, and quality review. Extracted values retain
source quotes and page/paragraph/table locations; absent values remain
unavailable. The UI supports reviewing and editing drafts, viewing the agent
execution history, downloading the source file, and recording a human approval.
Without provider credentials it uses deterministic mock extraction; set
`AI_MOCK_MODE=true` to force mock processing. Mock mode is clearly identified in
the record. Scanned PDFs require OCR and currently fail with a visible message.
Generated documents are drafts and do not represent legal advice or external
MCA, KYC, or AML verification.

---

### 4. Database Migrations

```bash
# From the repository root; SQLite paths are resolved relative to backend/
cd database
..\backend\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head

# Create a new migration after changing models:
..\backend\.venv\Scripts\python.exe -m alembic -c alembic.ini revision --autogenerate -m "describe_your_change"
```

---

Fresh local databases also create missing tables at backend startup. Run the
migration first when upgrading an existing database; existing contacts and
deals are moved into a dedicated legacy workspace without dropping their IDs.

### 5. Seed Fictional Demo Data

```bash
# Windows PowerShell, from the repository root
$env:DEALFORGE_DEMO_PASSWORD = "<choose a local demo password>"
backend\.venv\Scripts\python.exe database\seeds\seed_data.py
```

The seed is idempotent and only creates clearly labelled fictional records.
It never clears existing CRM data. The demo administrator uses
`demo-admin@example.com` and the password supplied in `DEALFORGE_DEMO_PASSWORD`.

---

### 6. Desktop (Electron)

```bash
cd desktop
npm install
npm run dev    # Requires frontend dev server on port 5173
```

---

## 🤖 AI Agents

The `agents/` module provides LangGraph-powered deal workflows.
It loads `backend/.env` and then the root `.env` when imported; process
environment variables take precedence, and AI provider keys are only needed
when an AI workflow is invoked.

```bash
cd agents
pip install -r requirements.txt
```

The **Deal Origination Graph** (`agents/graph/deal_graph.py`) runs:
1. **Research** — gather intel on the target company  
2. **Qualify** — BANT-score the opportunity  
3. **Draft** — generate a personalized outreach email  

```python
from agents.graph.deal_graph import deal_graph

result = await deal_graph.ainvoke({
    "company": "Acme Corp",
    "contact_email": "ceo@acme.com",
    "research_notes": "",
    "qualification_score": 0,
    "qualification_rationale": "",
    "draft_outreach": "",
    "messages": [],
    "status": "running",
})
print(result["draft_outreach"])
```

---

## 🗄️ Database

The tenant-aware schema includes Users, Organizations, Originators, Clients,
Deals, Investors, Documents, Deal Matches, Mandates, Compliance Records,
Transactions, and Activity Logs. Existing Contacts remain supported. All
organization-owned entities carry an `organization_id`; CRM API reads and
writes are scoped to the authenticated user's organization.

| Setting | Value |
|---------|-------|
| **Dev (default)** | SQLite — `dealforge.db` created automatically |
| **Production** | PostgreSQL via `DATABASE_URL=postgresql+asyncpg://...` |

Tables are created automatically on first backend start.  
Use Alembic for schema migrations in production.

---

## 🔧 Configuration

All configuration is environment-driven. **Never hardcode secrets.**

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy async DB URL | `sqlite+aiosqlite:///./dealforge.db` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | localhost and 127.0.0.1 dev ports |
| `APP_SECRET_KEY` | JWT signing secret (minimum 32 characters) | Required for auth |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes | `30` |
| `DEALFORGE_DEMO_PASSWORD` | Local seed administrator password | Required only to seed |
| `AI_MOCK_MODE` | Force deterministic document extraction instead of an LLM provider | `false` |
| `LITELLM_DEFAULT_MODEL` | Default LLM model | `gpt-4o-mini` |
| `OPENAI_API_KEY` | OpenAI provider key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic provider key | Optional |
| `GOOGLE_API_KEY` | Google AI provider key | Optional |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | `console` or `json` | `console` |
| `VITE_API_URL` | Backend URL for frontend | `http://localhost:8000` |

---

## 📡 API Reference

Registration creates an organization and its first administrator. Login uses
OAuth2 form fields (`username` is the account email and `password` is the
password); the returned JWT is sent as `Authorization: Bearer <token>`.
JWTs expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (30 by default). Admins can
create teammates inside their organization and choose among the `admin`,
`originator`, `analyst`, and `investor` roles. CRM contacts and deals require
authentication and are always scoped to the caller's organization.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with DB status |
| GET | `/api/v1/health` | Versioned health check (backward-compatible) |
| POST | `/api/v1/auth/register` | Register organization and first admin |
| POST | `/api/v1/auth/login` | Exchange email/password for a JWT |
| GET | `/api/v1/auth/me` | Get current user's profile |
| PATCH | `/api/v1/auth/me` | Update current user's profile |
| POST | `/api/v1/auth/change-password` | Change current user's password |
| GET | `/api/v1/auth/users` | List organization users (admin only) |
| POST | `/api/v1/auth/users` | Add organization user (admin only) |
| GET | `/api/v1/deals/` | List deals |
| POST | `/api/v1/deals/` | Create a deal |
| GET | `/api/v1/deals/{id}` | Get deal by ID |
| PATCH | `/api/v1/deals/{id}` | Update a deal |
| DELETE | `/api/v1/deals/{id}` | Delete a deal |
| GET | `/api/v1/contacts/` | List contacts |
| POST | `/api/v1/contacts/` | Create a contact |
| GET | `/api/v1/contacts/{id}` | Get contact by ID |
| PATCH | `/api/v1/contacts/{id}` | Update a contact |
| DELETE | `/api/v1/contacts/{id}` | Delete a contact |
| GET/POST | `/api/v1/clients/` | List or create tenant-scoped client profiles |
| GET/PATCH/DELETE | `/api/v1/clients/{id}` | Read, update, or delete a client |
| GET/POST | `/api/v1/clients/{id}/interactions` | List or record client interactions |
| GET/POST | `/api/v1/clients/{id}/documents` | List or upload client documents (10 MB max) |
| DELETE | `/api/v1/clients/{id}/documents/{document_id}` | Delete a client document |
| GET | `/api/v1/clients/{id}/documents/{document_id}/file` | Download a tenant-scoped client document |
| GET/POST | `/api/v1/clients/{id}/verification-checks` | Read or create explicitly simulated checks |
| GET/POST | `/api/v1/originators/` | List or create tenant-scoped originator profiles |
| GET/PATCH/DELETE | `/api/v1/originators/{id}` | Read, update, or delete an originator |
| GET | `/api/v1/mandates/?originator_id=...` | List tenant-scoped mandates |
| GET | `/api/v1/deals/?stage=...&sector=...&originator_id=...` | Filter tenant-scoped pipeline deals |
| GET/POST | `/api/v1/mandate-generations/` | List processing records or upload a PDF/DOCX source |
| GET | `/api/v1/mandate-generations/{id}` | Read extraction, analysis, drafts, review, and agent history |
| GET | `/api/v1/mandate-generations/{id}/source` | Download the tenant-scoped source document |
| POST | `/api/v1/mandate-generations/{id}/process` | Run or retry the six-agent workflow |
| PATCH | `/api/v1/mandate-generations/{id}` | Edit mandate and teaser drafts before approval |
| POST | `/api/v1/mandate-generations/{id}/approve` | Record human approval after quality checks |

Full OpenAPI spec: http://localhost:8000/openapi.json

Client document files are saved under `backend/uploads` by default; configure
`DOCUMENT_STORAGE_DIR` for another local path. For existing databases, apply
the Alembic migrations before starting the updated backend.

The mandate-generation workflow can be exercised with the focused backend tests:
`cd backend; .venv\Scripts\python.exe -m pytest tests\test_auth.py -k mandate_generation`.
The tests use fictional PDF and DOCX samples and do not require external LLM
credentials.

---

## 🏛️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS v4 |
| State | TanStack Query (React Query) |
| Routing | React Router v6 |
| Backend | FastAPI, Python 3.11+ |
| ORM | SQLAlchemy 2.0 (async) |
| Password hashing | Passlib + bcrypt |
| Authentication | JWT Bearer tokens |
| Migrations | Alembic |
| DB (dev) | SQLite + aiosqlite |
| DB (prod) | PostgreSQL + asyncpg |
| Config | Pydantic Settings |
| Logging | structlog |
| AI Orchestration | LangGraph |
| LLM Abstraction | LiteLLM |
| Desktop | Electron 33 |

---

## 📁 Module Guide for AI Assistants

> This section documents module boundaries to assist AI-aided development.

- **`backend/app/config.py`** — Single source of truth for all config. Add new settings here.
- **`backend/app/models/`** — Add new SQLAlchemy models here. Each model gets its own file.
- **`backend/app/schemas/`** — Add Pydantic request/response schemas alongside models.
- **`backend/app/api/v1/`** — Add new API endpoint routers here, then register in `router.py`.
- **`agents/graph/`** — Add new LangGraph workflows here.
- **`agents/llm/litellm_client.py`** — All LLM calls go through this client.
- **`shared/constants.py`** — Cross-module constants used by both backend and agents.
- **`frontend/src/api/client.ts`** — All frontend API calls go through this Axios instance.
- **`frontend/src/types/index.ts`** — Frontend TypeScript types must stay in sync with backend schemas.
