# AI Agent / RAG 工程师面试知识手册

> 基于 Ingenico Stage-3 项目 + 任职要求梳理，持续更新中。

---

## 一、项目优势总览（已覆盖领域）

### 1. RAG 全链路
- 文档加载 → BGE 向量嵌入 → Chroma 检索 → LLM 生成
- 支持静态 (`data/`) + 动态上传 (`storage/uploads/`) 双知识源
- Manifest 增量索引机制，避免不必要的全量重建
- 支持格式：`.txt` / `.md` / `.json` / `.pdf`

### 2. Agent 工具层
- **4 个内置工具**：`search_knowledge`、`get_system_health`、`list_uploads`、`recall_session_history`
- **MCP 风格 API**：`GET /mcp/tools`（目录）、`POST /mcp/tools/{tool_name}`（调用）
- 关键词路由机制 + 结构化 Tool Call Trace 返回

### 3. 记忆与缓存
- **Redis 双通道**：
  - 会话多轮记忆（`rpush/lrange`，可配置历史窗口）
  - LLM 响应缓存（SHA256 cache key，含 tool 结果，TTL 过期）

### 4. 全栈实现
| 层级 | 技术选型 |
|------|----------|
| 后端 | FastAPI (REST + SSE) + Pydantic |
| LLM | OpenAI 兼容接口 (MiniMax-M2.1) |
| Embedding | HuggingFace BGE-small-zh-v1.5 (本地) |
| 向量库 | Chroma (持久化) |
| 缓存 | Redis |
| 前端 | Vite + React + TypeScript |
| 容器化 | Docker + Docker Compose |

---

## 二、知识掌握度自查表

**等级说明**：
- `★★★` = 能讲原理 + 有项目经验 + 能讨论 trade-off（面试目标）
- `★★☆` = 理解概念 + 能做基本实现
- `★☆☆` = 听说过 / 仅表面了解 / 未覆盖

### 2.1 核心能力

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| **RAG 基础流程** | ★★★ | 项目完整实现 |
| 文档切片策略 | ★★★ | RecursiveCharacterTextSplitter，chunk_size/chunk_overlap 可配置 |
| Embedding 选型 | ★★★ | 本地 BGE vs API OpenAI，双模式支持 |
| 向量检索 | ★★★ | Chroma similarity_search_with_score |
| 召回增强生成 | ★★★ | Source snippets 注入 Prompt，grounding 策略 |
| Manifest 增量索引 | ★★★ | fingerprint 对比避免全量重建 |

### 2.2 Agent 与 Tools

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| Tool 设计与定义 | ★★★ | Schema 定义、参数校验、结果结构化 |
| MCP 风格接口 | ★★★ | 目录 + 调用双端点实现 |
| 关键词路由 | ★★★ | 当前实现方式 |
| **LLM Function Calling** | ★☆☆ | 需补充：OpenAI tool_choice 格式 |
| ReAct Agent 模式 | ★☆☆ | 需补充：Think→Act→Observe 循环 |
| LangGraph 状态机 | ★☆☆ | 需补充：多步骤工作流编排 |
| 多 Agent 协作 | ☆☆☆ | AutoGen/CrewAI 模式 |
| Tool 错误恢复 | ★☆☆ | 基础 try/except，缺重试/降级策略 |

### 2.3 RAG 进阶优化

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| **Re-ranking 重排序** | ☆☆☆ | Cross-Encoder / CohereRerank |
| **Hybrid Search** | ☆☆☆ | BM25 + 向量混合检索 |
| Query 改写/分解 | ☆☆☆ | HyDE / Multi-query / Decomposition |
| 元数据过滤 | ★☆☆ | 基础 metadata 存储，未做过滤查询 |
| Context Compression | ☆☆☆ | 检索后压缩，减少 token 消耗 |
| RAG 效果评估 | ☆☆☆ | RAGAS / Recall@K / MRR / NDCG |

### 2.4 Prompt & Context Engineering

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| System Prompt 设计 | ★★★ | Grounding prompt，约束回答来源 |
| Reasoning Block 处理 | ★★★ | 过滤 `think` 标签，后端日志保留 |
| **Prompt 模板管理** | ★☆☆ | 缺 Jinja2 / ChatPromptTemplate 版本化 |
| Few-shot / CoT | ★☆☆ | 了解概念，未在项目中实践 |
| 结构化输出控制 | ☆☆☆ | JSON mode / Pydantic Output Parser |
| Long Context 管理 | ★☆☆ | 截断到 400 字符，缺摘要/滚动窗口策略 |

### 2.5 Memory 系统

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| 会话短期记忆 | ★★★ | Redis List 存储多轮对话 |
| 缓存设计 | ★★★ | SHA256 hash key，含 sources + tool_results |
| TTL 过期策略 | ★★★ | redis setex 配置化 |
| **长期记忆 / 总结记忆** | ☆☆☆ | 对话摘要 / 用户画像持久化 |
| **跨会话记忆** | ☆☆☆ | 用户偏好 / 历史问答沉淀 |

### 2.6 Voice Agent（JD 要求 #11）

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| 三段式架构理解 | ★☆☆ | ASR → LLM → TTS 概念清晰 |
| 端到端 Voice Agent | ☆☆☆ | 如 GPT-4o-audio / Speech-to-Speech |
| 流式 ASR 集成 | ☆☆☆ | Whisper / 商业 ASR API |
| 流式 TTS 集成 | ☆☆☆ | Edge-TTS / Azure TTS |
| WebSocket 实时通信 | ☆☆☆ | fastapi-websocket |
| VAD 语音活动检测 | ☆☆☆ | |
| 端云协同架构 | ☆☆☆ | |

### 2.7 工程化与部署

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| Python + FastAPI | ★★★ | REST + SSE + CORS + 依赖注入 |
| React + TypeScript | ★★★ | 四面板 UI、SSE 流式渲染 |
| Redis | ★★★ | 记忆 + 缓存双通道 |
| Docker | ★★★ | Dockerfile + docker-compose.yml |
| **CI/CD 流水线** | ★☆☆ | 缺 GitHub Actions 自动化 |
| **代码质量门禁** | ☆☆☆ | ruff / mypy / pre-commit |
| **Kubernetes** | ☆☆☆ | Deployment / Service / HPA / Ingress |
| 监控告警 | ☆☆☆ | Prometheus / Grafana / 日志聚合 |
| 消息队列 | ☆☆☆ | Celery / Kafka 异步任务处理 |

### 2.8 多模态处理

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| 文本数据处理 | ★★★ | .txt/.md/.json/.pdf |
| 图片理解 | ☆☆☆ | CLIP / GPT-4o-vision / Qwen-VL |
| 表格数据提取 | ☆☆☆ | Excel / CSV 结构化解析 |
| HTML/网页清洗 | ☆☆☆ | |
| PDF 版式感知 | ☆☆☆ | 表格/图片区域识别 |

### 2.9 AI Coding 工具

| 知识点 | 掌握度 | 备注 |
|--------|:------:|------|
| Claude Code | ★☆☆ | 使用过，了解基本能力 |
| GitHub Copilot | ★☆☆ | 使用经验 |
| Cursor | ★☆☆ | 使用经验 |
| CodeBuddy（当前） | ★★★ | 日常使用 |

---

## 三、需要重点补充的方向

### 优先级 P0（面试核心考点）

#### 3.1 LLM 驱动的 Agent 升级
**现状**：`agent_tools.py` 用关键词硬编码路由（`if "health" in lowered`）
**目标**：升级为 LLM 自主决策的 Function Calling

```
学习路径:
1. 理解 OpenAI tools / function_calling 格式
2. 学习 LangChain @tool 装饰器 + create_tool_calling_agent
3. 改造 agent_tools.py：LLM 决定调哪个工具、传什么参数
4. 对比关键词路由 vs LLM 路由的 trade-off
```

**面试能讲的要点**：
- 为什么从规则驱动升级为 LLM 驱动？
- Tool Choice 的格式和协议（OpenAI / Anthropic 格式差异）
- 如何防止 LLM 幻觉性工具调用？（Schema 约束 + fallback）
- Tool 结果如何注入 Prompt？

#### 3.2 RAG 检索优化
**现状**：纯向量 similarity_search top-k
**目标**：Re-ranking + Hybrid Search

```
学习路径:
1. 加入 cross-encoder re-ranking 层
2. 实现 BM25 + Vector ensemble retriever
3. 了解 MMR (Maximal Marginal Relevance) 多样性检索
4. 用 RAGAS 做效果评估基线
```

### 优先级 P1（JD 明确要求）

#### 3.3 LangGraph 工作流
```
学习目标:
- 理解 State / Node / Edge / ConditionalEdge 概型
- 实现 Router → Retrieve → Generate 条件分支
- 实现 self-correction 循环（生成质量不满足时重新检索）
```

#### 3.4 Voice Agent 基础
```
学习目标:
- 画清楚三段式架构图（ASR→LLM→TTS 各环节延迟预算）
- 在项目中加 WebSocket 端点
- 了解流式 ASR/TTS 的 API 和集成方式
- 理解端到端方案（如 GPT-4o-audio）的差异和适用场景
```

#### 3.5 CI/CD 工程
```
行动项:
- GitHub Actions: lint → test → build → deploy 流水线
- ruff + mypy + pre-commit hooks
- 测试覆盖率提升
```

### 优先级 P2（加分项）

#### 3.6 Kubernetes 部署
#### 3.7 多模态数据扩展
#### 3.8 RAG 可观测性与评估体系

---

## 四、技术选型理由（面试常问）

### 4.1 为什么 FastAPI 而不是 Flask/Django？
- **FastAPI**：原生异步支持（async/await）+ 自动 OpenAPI 文档 + Pydantic 校验 + 性能优（Starlette）
- Flask 同步模型不适合 SSE/流式场景；Django 太重量级
- AI 应用需要高并发流式输出，FastAPI 的 `StreamingResponse` 天然适配

### 4.2 为什么 Redis 而不是 SQLite 做记忆存储？
- **Redis**：内存级读写速度（亚毫秒），天然支持 List（对话历史有序）+ TTL（缓存过期）
- SQLite：磁盘 I/O，高并发下锁竞争，无原生 TTL
- Session 数据是"热数据"，适合内存；SQLite 更适合持久化元数据（如 upload_store）

### 4.3 为什么 SSE 而不是 WebSocket？
- **SSE**：单向服务端→客户端推送，HTTP 协议简单，自动重连，代理友好
- **WebSocket**：双向通信，适合实时对话/Voice Agent 场景
- 当前聊天场景是"请求-响应流"，SSE 够用且更简单；如果加语音对话再升级 WS

### 4.4 为什么本地 BGE 而不是 API Embedding？
- **离线优先**：启动不依赖外部网络，隐私安全
- **成本**：大量文档嵌入时 API 调用费用累积快
- **中文优化**：BGE-small-zh 对中文语义理解优于通用 multilingual 模型
- **权衡**：本地模型精度可能略低，但通过增大 top-k 或加 re-ranking 弥补

### 4.5 为什么 Chroma 而不是 Milvus/Pinecone？
- **轻量级**：嵌入式部署，无需额外服务进程，Docker Compose 单容器即可
- 开发调试阶段数据量不大（< 10 万 chunks），Chroma 够用
- 生产大规模场景才需 Milvus/Qdrant 等独立向量数据库

---

## 五、场景题准备

### 5.1 RAG 相关

**Q: 检索结果不准怎么办？**
```
排查链路:
1. 切片问题 → chunk_size 是否截断关键信息？重叠够不够？
2. Embedding 问题 → 模型是否匹配领域？是否需要 fine-tune？
3. 检索问题 → top_k 够不够？是否需要 hybrid search？
4. 重排序问题 → 加 cross-encoder re-ranking
5. Query 问题 → 用户问法和文档表述不一致 → query rewriting
```

**Q: 用户问的问题很模糊怎么办？**
- Query Expansion（多路查询改写）
- HyDE（假设性文档嵌入）：先生成一个假设答案，用它来检索
- Clarification Question（反问澄清）：Agent 主动追问

**Q: LLM 回答出现幻觉怎么缓解？**
- 强制 grounding（只基于检索到的上下文回答）
- 引用来源标注（每个回答附带 source snippet）
- 置信度阈值（similarity score 低于阈值时拒绝回答）
- 后处理事实核查

### 5.2 Agent 相关

**Q: Agent 进入死循环怎么办？**
- 设置最大迭代次数（max_turns / max_loops）
- 设置 termination condition（如连续两次相同 tool call 则终止）
- 观察模式：记录完整 trace 用于 debug

**Q: Tool 调用失败怎么处理？**
- 重试机制（指数退避）
- 降级策略（search_knowledge 失败则走无 RAG 生成）
- Fallback tool（主工具不可用时切换备用工具）

**Q: 如何设计一个新 Tool？**
1. 明确输入输出 Schema（Pydantic model）
2. 编写执行函数（同步/异步）
3. 注册到 catalog
4. 编写描述（LLM 靠描述决定何时调用）
5. 添加单元测试

### 5.3 工程相关

**Q: 并发量大时如何优化？**
- Redis 缓存层（已实现）+ 命中率监控
- LLM 调用批量化 / 异步队列（Celery / Redis Queue）
- 向量检索加速（Chroma 内存模式 / 索引优化）
- 连接池管理（Redis / HTTP client connection pool）
- Rate Limiting（令牌桶算法）

**Q: 如何保证服务稳定性？**
- Health Check 端点（已实现 `/health`）
- Graceful Shutdown（lifespan 管理）
- Startup Error 透支（已实现 startup_error 字段）
- Circuit Breaker（下游 LLM API 不可用时快速失败）
- 日志结构化 + 追踪 ID

---

## 六、推荐学习资源

### 6.1 文档 / 教程
| 资源 | 学什么 | 链接 |
|------|--------|------|
| LangChain Docs | Agents / Tools / LangGraph | python.langchain.com/docs |
| LlamaIndex Docs | Advanced RAG Patterns | docs.llamaindex.ai |
| OpenAI Cookbook | Function Calling / RAG Best Practices | cookbook.openai.com |
| RAGAS Docs | RAG 评估框架 | docs.ragas.ai |
| Dify GitHub | 生产级 LLM App Platform | github.com/langgenius/dify |

### 6.2 论文
| 论文 | 核心贡献 |
|------|----------|
| "Retrieval-Augmented Generation for Large Language Models" (Lewis et al., 2020) | RAG 奠基论文 |
| "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022) | ReAct Agent 模式 |
| "Lost in the Middle" (Liu et al., 2023) | 长上下文中信息位置对性能的影响 |

### 6.3 开源项目（推荐阅读模块）
| 项目 | 重点读什么 |
|------|-----------|
| **Dify** | Agent 编排引擎 / API Server / Workflow DAG 执行器 |
| **LangChain-Chatchat** | Knowledge Base Loader / Retrieval Chain / 前端交互 |
| **Open WebUI** | RAG Pipeline / Function Calling 集成 / 多模型支持 |
| **graph-rag (微软)** | Graph-based 知识抽取 / Community Detection / 全局检索 |

### 6.4 实践项目建议
1. **将 agent_tools.py 升级为 LLM Function Calling**（最直接提升面试竞争力）
2. **在项目中加入 Re-ranking**（展示 RAG 优化能力）
3. **做一个 Voice Agent demo**（匹配 JD #11 要求）
4. **用 LangGraph 重构 Agent 工作流**（展示进阶框架使用）

---

## 七、行动计划模板

### Week 1: 补齐核心差距
- [ ] Day 1-2: 通读 LangChain Agents + Tools 文档，做笔记
- [ ] Day 3: 手写一个最小 ReAct Agent（不用框架）
- [ ] Day 4-5: 改造 ingenico 的 `agent_tools.py` 为 LLM 驱动
- [ ] 周末: 整理改造前后的对比，写一篇技术总结

### Week 2: RAG 进阶 + Voice
- [ ] Day 1-2: 学习 Re-ranking + Hybrid Search，接入项目
- [ ] Day 3-4: 研究 Voice Agent 架构，做 WebSocket demo
- [ ] Day 5: 阅读 Dify Agent 模块源码
- [ ] 周末: 模拟面试练习

### Week 3: 工程化 + 刷题
- [ ] Day 1-2: 加 CI/CD 流水线 + 代码质量门禁
- [ ] Day 3: K8s 部署 manifest 编写
- [ ] Day 4-5: 场景题模拟回答 + 优化表达
- [ ] 周末: 全流程模拟面试

---

## 八、面试高频问题速查

| 问题类型 | 示例 | 回答要点 |
|----------|------|----------|
| **项目介绍** | "介绍一下你的项目" | 30 秒电梯演讲：做什么 → 用什么技术 → 解决什么问题 → 你的贡献 |
| **技术深挖** | "你的 RAG Pipeline 是怎样的？" | 画图 + 讲每一步的设计选择和 trade-off |
| **场景设计** | "如果要支持百万级文档怎么办？" | 分片 / 混合检索 / 缓存分层 / 异步索引 |
| **故障排查** | "用户反馈回答不准确你怎么排查？" | 分层排查：检索层 → 排序层 → 生成层 |
| **方案对比** | "为什么选 A 不选 B？" | 从性能 / 成本 / 复杂度 / 团队熟悉度四个维度分析 |
| **开放性** | "你觉得 Agent 的未来方向是什么？" | 展示思考深度：多模态 / 自进化 / 安全可控 |

---

> 最后更新: 2026-04-27
> 下一步: 按 Week 1 行动计划推进，完成 Agent 升级后更新本手册
