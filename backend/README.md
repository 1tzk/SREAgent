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

## 初始化演示数据

首次运行或需要清空场景数据时执行：

```bash
curl -X POST http://localhost:8000/api/seed/reset
```

## 故障模拟

将下面的场景名替换为需要模拟的故障：

```bash
curl -X POST http://localhost:8000/api/scenarios/order-timeout
```

支持的场景：

- `order-timeout`
- `slow-sql`
- `payment-500`
- `redis-cache`
- `db-pool-exhausted`
- `release-regression`

每次调用会写入关联的告警、日志、指标、链路和事故数据，并返回本次场景的 `trace_id`、告警与事故信息。

## 证据查询

- `GET /api/logs?service_name=&keyword=`
- `GET /api/metrics?service_name=&metric_name=`
- `GET /api/traces`
- `GET /api/traces/{trace_id}`
- `GET /api/deployments?service_name=`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`

接口文档启动后可访问 `http://localhost:8000/docs`。
