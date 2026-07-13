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

## Mock Agent 诊断

当前版本固定使用确定性 Mock 工作流，不需要任何大模型 API Key。

```bash
curl -X POST http://localhost:8000/api/agent/diagnose \
  -H "Content-Type: application/json" \
  -d '{"query":"订单接口最近响应很慢，请帮我排查原因并给出处理建议。"}'
```

诊断会依次查询告警、指标、日志、链路、发布记录和 Runbook。每次工具调用都会记录输入、输出、耗时和执行状态。涉及回滚、重启、扩容或配置变更时只创建待审批单，不会执行实际操作。

相关接口：

- `GET /api/agent/sessions`
- `GET /api/agent/sessions/{session_id}`
- `GET /api/agent/sessions/{session_id}/tool-calls`
- `GET /api/approvals`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`
