# 后端

AI SRE Agent 的 FastAPI 后端服务。

## 环境

使用已有的 Anaconda 虚拟环境：

```bash
conda activate sre
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 启动

在 `backend` 目录下运行：

```bash
uvicorn app.main:app --reload
```

默认服务地址：

```text
http://localhost:8000
```

## 健康检查

```bash
curl http://localhost:8000/api/health
```

预期返回：

```json
{"status":"ok"}
```
