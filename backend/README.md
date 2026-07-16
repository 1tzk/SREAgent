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

## 数据库迁移

升级已有 SQLite 数据库后再启动服务：

    alembic upgrade head

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

## 自主 Agent Run

当前版本使用自研的持久化 Agent Loop；无 API Key 时自动使用 Mock Planner。
诊断请求会异步入队，模型只能选择注册表中的工具。模拟回滚、重启和扩缩容
由策略层限制在本地模拟环境，处置后会再次读取观测数据完成复查。

```bash
curl -X POST http://localhost:8000/api/agent/diagnose \
  -H "Content-Type: application/json" \
  -d '{"query":"订单接口最近响应很慢，请帮我排查原因并给出处理建议。"}'
```

Planner 会根据每轮观察结果选择下一项白名单工具。每次决策和工具调用都会记录输入、输出、耗时及执行状态；模拟处置只会作用于本地演示数据库。

主要接口：

- `POST /api/agent/runs`：创建异步 Run，返回 202。
- `GET /api/agent/runs`：查询 Run 列表。
- `GET /api/agent/runs/{run_id}`：查看步骤、审计、模拟处置和最终结论。
