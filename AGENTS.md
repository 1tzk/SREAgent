# Project Constraints

## Code

- Add concise Chinese comments where necessary to explain important or non-obvious logic.

## Backend

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Uvicorn
- `python-dotenv` can be added later

## Frontend

- React + TypeScript + Vite
- Ant Design
- Axios
- ECharts can be added later

## Agent

- Do not force LangGraph in the first phase.
- First implement a stable self-developed Workflow.
- Later refactor to a LangGraph version.

## LLM

Must support:

- `LLM_PROVIDER=mock`
- Automatically use mock mode when no API key is available.
- Later extend support for OpenAI / DeepSeek / Qwen.

## Python Environment

- Use the existing Anaconda virtual environment named `sre`.
- The environment uses Python 3.11.
- Activate it with:

```bash
conda activate sre
```
