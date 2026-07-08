# Backend

FastAPI backend for AI SRE Agent.

## Setup

```bash
conda activate sre
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## Health Check

```bash
curl http://localhost:8000/api/health
```
