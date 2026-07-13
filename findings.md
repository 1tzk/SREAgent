# V2 开发发现

- 实际项目根目录为 `E:\develop\ai-sre-agent`，而当前 Codex 工作目录仍是移动前的 `E:\develop\SREagent`。
- V1 已有 alerts、logs、metrics、traces、deployments、incidents 等全部所需 ORM 模型。
- logs 和 metrics 的 service_name 外键要求场景服务必须先由 `/api/seed/reset` 初始化。
- 现有 API 使用独立 router 并统一挂载到 `/api`，V2 继续沿用该模式。
- 场景数据需要通过统一 trace_id 形成日志和 span 之间的证据链。
- 六个场景均创建告警和事故；slow-sql、release-regression 额外创建发布记录。
- 每个异常指标包含至少一个趋势或多服务对比点，方便后续 Agent 判断变化。
- V3 可直接复用现有 AgentSession、AgentToolCall、Approval 模型，无需新增表。
- AgentToolCall.session_id 和 Approval.session_id 都要求先 flush AgentSession 获取主键。
- slow-sql 场景通过同一 trace_id 关联 inventory-service 与 order-service 日志和 span。
- 工具通过 ContextVar 获取当前请求的 db/session_id，函数签名无需暴露基础设施参数。
- generate_incident_report 同样经过审计，保证最终结论可追溯到输入证据。
- 工作流根据日志关键词为 trace_id 评分，优先选择证据最强的异常链路。
