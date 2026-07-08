# AI SRE Agent

AI SRE Agent is a microservice fault diagnosis and incident analysis platform. This repository uses a separated backend and frontend structure.

Current scope:

- FastAPI backend scaffold
- SQLite database connection configuration
- React + TypeScript + Vite frontend scaffold
- Mock-first LLM configuration placeholder

No database tables, Agent workflow, RAG logic, or complex UI are implemented in this phase.

## Project Structure

```text
ai-sre-agent/
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   ├── package.json
│   └── README.md
├── .env.example
└── README.md
```

## Backend Setup

Use the existing Anaconda environment:

```bash
conda activate sre
```

Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Start the API server:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Frontend Setup

Install dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

Open the URL printed by Vite, usually:

```text
http://localhost:5173
```

The home page displays:

```text
AI SRE Agent
```
