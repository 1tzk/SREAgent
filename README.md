# AI SRE Agent

AI SRE Agent 是一个面向微服务故障诊断与事故分析的平台。本项目采用前后端分离结构：后端使用 FastAPI，前端使用 React + TypeScript + Vite。

当前阶段只完成项目骨架和基础启动能力：

- FastAPI 后端骨架
- `GET /api/health` 健康检查接口
- SQLite 数据库连接配置
- React + TypeScript + Vite 前端骨架
- LLM 默认 mock 模式配置占位

本阶段不实现数据库表、Agent 工作流、RAG 逻辑或复杂 UI。

## 项目结构

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

## 后端启动

使用已有的 Anaconda 虚拟环境：

```bash
conda activate sre
```

安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

启动 API 服务：

```bash
uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://localhost:8000/api/health
```

预期返回：

```json
{"status":"ok"}
```

## 前端启动

安装依赖：

```bash
cd frontend
npm install
```

启动开发服务：

```bash
npm run dev
```

打开 Vite 输出的本地地址，通常是：

```text
http://localhost:5173
```

首页会显示：

```text
AI SRE Agent
```
