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
# Edit backend/.env and set OPENAI_API_KEY

# Start everything
docker-compose up -d

# App runs at:
# Frontend: http://localhost:80
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2 — Local Development

**Prerequisites**: Python 3.12+, Node.js 20+, PostgreSQL 14+

#### Backend
```bash
cd automation-debugger/backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Edit .env with your DB + OpenAI settings
uvicorn main:app --reload
```

#### Frontend
```bash
cd automation-debugger/frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

#### Database
```bash
# Create database
psql -U postgres -c "CREATE DATABASE automation_debugger;"

# Run schema
psql -U postgres -d automation_debugger -f database/schema.sql
```

## Project Structure

```
automation-debugger/
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # App entry point
│   ├── config.py               # Settings (env-based)
│   ├── database.py             # SQLAlchemy async
│   ├── models.py               # ORM models
│   ├── schemas.py              # Pydantic DTOs
│   ├── auth.py                 # JWT auth
│   ├── routers/
│   │   ├── projects.py         # Project upload/manage
│   │   ├── analysis.py         # RCA trigger/results
│   │   └── reports.py          # PDF/Excel download
│   └── services/
│       ├── project_parser.py   # Multi-platform project parsing
│       ├── log_analyzer.py     # Log parsing & exception extraction
│       ├── rca_engine.py       # AI + heuristic RCA
│       └── report_generator.py # PDF & Excel generation
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── pages/              # Login, Dashboard, Upload, Results, History
│   │   ├── components/         # Layout, PlatformBadge, ConfidenceGauge, etc.
│   │   ├── api/                # Axios API clients
│   │   └── store/              # Zustand auth store
│   └── ...config files
├── database/
│   └── schema.sql              # PostgreSQL schema
└── docker-compose.yml          # Full stack deployment
```

## Features

- 🔍 **Multi-platform support**: UiPath, Power Automate, Blue Prism, Automation Anywhere
- 🤖 **AI-powered analysis**: GPT-4 identifies root causes with confidence scores
- 🛡️ **Heuristic fallback**: Works without OpenAI key for basic analysis
- 📊 **Rich dashboard**: Charts, statistics, recent analyses
- 📥 **Report exports**: PDF and Excel downloads
- 👥 **Team sharing**: Multi-user with JWT authentication
- 🐳 **Docker-ready**: One command deployment

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection URL | localhost |
| `OPENAI_API_KEY` | OpenAI API key (optional) | empty |
| `JWT_SECRET` | Secret for JWT tokens | change-me |
| `UPLOAD_DIR` | File upload directory | ./uploads |
| `REPORTS_DIR` | Report output directory | ./reports |

## Default Login

- **Email**: admin@debugger.local
- **Password**: Admin1234

> ⚠️ Change the admin password immediately after first login.

## API Documentation

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

## License

MIT
