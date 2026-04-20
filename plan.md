# RAG + Agent 学习计划（优化版｜去除上传依赖）

## 🎯 总目标
基于 LangChain + FastAPI + React 搭建一个**可部署的 RAG 系统**，逐步扩展：
* 支持多文档问答
* 支持对话记忆
* 支持 Agent 工具调用（含 MCP）
* 最终具备语音交互能力（Voice Agent）

---
# 🚀 阶段1：RAG 最小可用系统（必须打穿）
## 🎯 目标
实现一个**基于本地数据的可用 RAG 问答系统（MVP）**
---

## 🧩 功能范围（精简版）
* 本地文档加载（txt / md / json）
* 文档切分（Text Split）
* 向量化（Embedding）
* 向量检索（Retriever）
* 基于上下文生成回答（LLM）
* 基础对话记忆（本地 Memory）
* FastAPI 封装 `/chat` 接口
* Docker 部署
---

## 📂 数据组织方式（替代上传）
```plaintext
/data
  ├── doc1.txt
  ├── doc2.md
  └── knowledge.json
```

---
## 🔄 RAG 流程
```plaintext
本地文件 → 加载 → 切分 → embedding → 向量库 → 检索 → LLM生成
```

---

## 🔌 API 设计
### 问答接口
```http
POST /chat
```

---

## 🏗 技术选型
* LangChain（RAG 主流程）
* FastAPI（后端服务）
* Chroma（本地向量数据库）
* OpenAI / 本地模型（LLM）
* Docker Compose

---

## 📌 学习要点
* RAG 核心流程（切分 / embedding / 检索 / 生成）
* LangChain 核心组件：
  * Model
  * Prompt
  * Chain
  * Retriever
  * Memory
* FastAPI 基础：
  * 路由
  * 异步
  * 请求处理

---

## ✅ 完成标准（必须满足）
* 能加载本地文档
* 能提问并返回答案
* 回答基于文档内容（非幻觉）
* 支持基础多轮对话
* 一条 Docker 命令启动服务

---

# 🚀 阶段2：工程增强（让它像产品）
## 🎯 目标
提升系统**可用性 + 性能 + 交互体验**

---

## 🧩 功能扩展
* 多文档支持（动态加载）
* Redis：
  * 对话记忆存储
  * LLM Cache（减少重复调用）
* 流式输出（SSE）
* React 简单聊天界面
* 👉 新增：文件上传接口 `/upload`（此阶段再实现）

---

## 🏗 技术选型
* Redis
* React + TypeScript
* SSE（优先于 WebSocket，简单稳定）

---

## 📌 学习要点

* Redis 使用：
  * Cache vs Memory
* 流式输出实现
* 前后端联调

---

## ✅ 完成标准
* 支持多个文档问答
* 响应更快（cache 生效）
* 前端可聊天
* 支持流式返回

---

# 🚀 阶段3：Agent + MCP（能力扩展）
## 🎯 目标
让系统具备**工具调用能力**

---

## 🧩 功能扩展
* LangChain Agent
* 自定义 Tool（函数调用）
* MCP Server（Python 实现）：

  * 示例：计算器 / 天气查询
* Agent 调用 MCP 工具

---

## 📌 学习要点
* Agent 原理（ReAct / Tool Calling）
* Tool Schema 设计
* MCP 协议基础

---

## ✅ 完成标准
* Agent 能自动选择工具
* 能成功调用 MCP 服务
* 工具结果参与最终回答

---

# 🚀 阶段4：系统能力进阶（高级）
## 🎯 目标
构建**完整 AI 应用能力**

---

## 🧩 功能扩展

### 1️⃣ Voice Agent（语音能力）
实现流程：
```plaintext
语音 → ASR → 文本 → RAG → 文本 → TTS → 语音
```

#### 分阶段：
1. 上传音频 → 返回语音（非实时）
2. 实时流（WebSocket）

---

### 2️⃣ 工程规范（轻量版）
* docs/architecture.md（架构说明）
* docs/execution_plan.md（执行计划）
* 基础 CI：
  * lint
  * test

---

## 📌 学习要点
* ASR / TTS 基础
* WebSocket 通信
* 基础工程治理

---

## ✅ 完成标准
* 支持语音问答
* 系统结构清晰
* 可持续迭代

---

# 🧠 推荐执行顺序（关键）
```plaintext
阶段1（打穿RAG）
   ↓
阶段2（增强体验）
   ↓
阶段3（Agent能力）
   ↓
阶段4（系统进阶）
```

---

# ⚠️ 注意事项（避免踩坑）
* 阶段1不要引入 Redis（先跑通）
* 阶段1不要做上传接口（降低复杂度）
* 优先保证 RAG 正确性，而不是工程复杂度
* Voice Agent 一定最后做（难度最高）

---

# 🏁 最终成果能力
你将能够：
* 独立实现 RAG 系统
* 构建 AI 后端服务
* 实现 Agent + Tool 调用
* 理解 MCP 架构
* 初步具备 AI 工程能力

---