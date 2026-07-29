# Automation Project Debugger

AI-Powered Root Cause Analysis for RPA Automation Projects.

Supports: **UiPath** · **Power Automate** · **Blue Prism** · **Automation Anywhere**

## Quick Start

### Option 1 — Docker Compose (Recommended)

```bash
git clone <this-repo>
cd automation-debugger

# Copy env file and set your OpenAI API key
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENAI_API_KEY (optional — heuristic fallback works without it)

# Start everything
docker-compose up -d

# App runs at:
# Frontend: http://localhost:80
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2 — Local Development

**Prerequisites**: Python 3.12+, Node.js 20+

#### Backend

```bash
cd automation-debugger/backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env           # Edit .env — set OPENAI_API_KEY if you have one
uvicorn main:app --reload      # Starts on http://localhost:8000
```

> **Database**: SQLite — automatically created as `backend/automation_debugger.db` on first run. No external DB required.

#### Frontend

```bash
cd automation-debugger/frontend
npm install
npm run dev
# Opens at http://localhost:3000 (proxies /api → :8000)
```

## Project Structure

```
automation-debugger/
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # App entry point
│   ├── config.py               # Settings (env-based)
│   ├── database.py             # SQLAlchemy async + SQLite auto-migrate
│   ├── models.py               # ORM models
│   ├── schemas.py              # Pydantic DTOs
│   ├── auth.py                 # JWT auth (bcrypt 4.0.1)
│   ├── routers/
│   │   ├── projects.py         # Project upload / platform detection
│   │   ├── analysis.py         # RCA trigger / results
│   │   └── reports.py          # PDF / Excel download
│   └── services/
│       ├── project_parser.py   # Multi-platform project parsing
│       ├── log_analyzer.py     # Log parsing & exception extraction
│       ├── rca_engine.py       # AI + heuristic RCA (log-first)
│       ├── standards_checker.py # 23+ coding standards rules
│       └── report_generator.py # PDF & Excel generation
├── frontend/                   # React TypeScript + Vite + Tailwind
│   └── src/
│       ├── pages/              # Login, Dashboard, Upload, Results, History
│       ├── components/         # Layout, PlatformBadge, ConfidenceGauge, …
│       ├── api/                # Axios API clients
│       └── store/              # Zustand auth store
├── test-samples/               # Sample projects + execution logs for all 4 platforms
│   ├── uipath/
│   ├── blue_prism/
│   ├── automation_anywhere/
│   └── power_automate/
├── database/
│   └── schema.sql              # Reference schema (SQLite used by default)
└── docker-compose.yml          # Full stack deployment
```

## Features

- 🔍 **Multi-platform support**: UiPath, Power Automate, Blue Prism, Automation Anywhere
- 🤖 **AI-powered analysis**: GPT-4 identifies root causes with 11-point structured output
- 🛡️ **Heuristic fallback**: Full analysis works without an OpenAI key
- 📋 **Log-first diagnosis**: Execution log is the primary evidence source — no guessing
- 📊 **5-tab results view**: Runtime Analysis · RCA · Coding Standards · Code Errors · Log Correlation
- 📥 **Report exports**: PDF and Excel downloads (runtime analysis + AI narrative included)
- 📈 **Rich dashboard**: Charts, platform breakdown, activity timeline, has-log ratio
- 👥 **JWT authentication**: Multi-user with role-based access
- 🐳 **Docker-ready**: One command deployment

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLite URL (or PostgreSQL for production) | `sqlite+aiosqlite:///./automation_debugger.db` |
| `OPENAI_API_KEY` | OpenAI API key (optional — heuristic fallback if not set) | empty |
| `JWT_SECRET` | Secret for JWT tokens | change-me |
| `UPLOAD_DIR` | File upload directory | `./uploads` |
| `REPORTS_DIR` | Report output directory | `./reports` |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |

## Default Login

- **Email**: `admin@automation-debugger.com`
- **Password**: `Admin1234`

> ⚠️ Change the admin password immediately after deploying to production.

## Test Samples

Ready-made project ZIPs and execution logs are in `test-samples/` for all four platforms.
See [`test-samples/README.md`](test-samples/README.md) for usage instructions and expected analysis outputs.

## API Documentation

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

## License

MIT
