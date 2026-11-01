# DataPilot — Trustworthy AI-Powered Business Analytics

> **Business analytics you can verify.**  
> DataPilot bridges the gap between raw business data and reliable decision-making by anchoring every metric, calculation, and AI explanation to approved business definitions, schema-validated SQL, and deterministic calculations.

---

## 🌟 Key Architecture & Capabilities

1. **Deterministic Data Ingestion & Profiling**:
   - Ingests **CSV** and **XLSX** files directly into physical **DuckDB** analytical tables.
   - Non-parametric data profiling ($1.5 \times \text{IQR}$ outlier detection, candidate key inference, null rates, and exact duplicate detection).
2. **PostgreSQL Connector**:
   - Connects to external PostgreSQL instances over TLS with AES-256 encrypted credentials.
   - Introspects schemas and primary/foreign keys.
   - Attaches remote tables as queryable `DataSource` entities with read-only transaction isolation and statement timeouts.
3. **Business Knowledge & Metric Governance**:
   - Centralized business glossary (terms, plain-English definitions, and company synonyms).
   - Metrics layer with formal lifecycle: `draft` $\to$ `in_review` $\to$ `approved`.
   - Pre-approval AST validation: formula aggregations (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`), column binding checks, and filter operator whitelisting.
4. **Anti-Hallucination Natural Language Resolution (Ask Data)**:
   - Queries are semantically resolved strictly against approved business metrics.
   - Ambiguous inquiries trigger clarification requests.
   - Unapproved or undefined metrics return `needs_definition` — the LLM is strictly prohibited from inventing numbers or formulas.
5. **Reproducible Lineage & Dashboard Reports**:
   - Validates generated SQL AST using `sqlglot` (blocks DDL, multiple statements, and injection vectors).
   - Generates persistent audit logs (`QueryHistory`) with execution latency, rows, and calculation lineage.
   - Customizable dashboard reports with embedded verified query widgets.
6. **Multi-Tenant Workspace RBAC**:
   - Workspace ownership and role-based permissions (`owner`, `editor`, `viewer`) enforced across all API endpoints.

---

## 🏗️ Tech Stack

- **Backend**: FastAPI (Python 3.11+ / 3.14), DuckDB, PostgreSQL (`psycopg2`), SQLAlchemy 2.0, Pydantic v2, SQLGlot, OpenPyXL.
- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS, Lucide Icons.
- **Design System**: 3-family palette (Deep Navy `#142333`, Off-white `#F8FAFC`, Teal `#0F8B83`) with smooth Light/Dark mode toggle.

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and `pnpm`
- Python 3.11+ and `venv`
- (Optional) Local PostgreSQL instance

### 1. Clone & Setup Environment

```bash
git clone https://github.com/pragam-m25/data-pilot.git
cd data-pilot

cp .env.example .env
```

### 2. Backend Setup (FastAPI)

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs are available at `http://localhost:8000/docs`.

### 3. Frontend Setup (Next.js)

```bash
cd apps/web
pnpm install
pnpm dev
```

Open `http://localhost:3000` in your browser.

---

## 🧪 Testing

Run the full end-to-end integration and security test suite:

```bash
cd apps/api
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

Tests cover:
- File ingestion, XLSX table materialization, and `.xls` rejection.
- Data profiling, candidate keys, and IQR outlier detection.
- Metric draft, review, and approval lifecycle.
- Schema AST validation (blocking unaggregated and invalid column formulas).
- SQL injection prevention.
- Cross-workspace isolation (HTTP 403 checks).
- Production authentication without credentials (HTTP 401 checks).

---

## 📜 License

MIT License.
