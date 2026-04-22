# Ingenico 项目深度学习指南

> 基于 Stage-2 实现的本地文档 RAG 系统，完整的学习路径与架构解读

---

## 目录

1. [架构全景](#一架构全景)
2. [环境配置解读](#二环境配置解读)
3. [三大核心流程](#三三大核心流程)
   - [流程 1：一次完整对话请求](#流程1一次完整对话请求)
   - [流程 2：文档索引构建](#流程2文档索引构建)
   - [流程 3：SSE 流式输出](#流程3sse-流式输出)
4. [四大设计模式](#四四大设计模式)
5. [建议学习顺序](#五建议学习顺序)
6. [动手实验](#六动手实验)
7. [附录：关键代码位置速查](#附录关键代码位置速查)

---

## 一、架构全景

```
┌─────────────────────────────────────────────────────────────┐
│                     浏览器 (localhost:5173)                   │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐          │
│  │  对话面板     │  │ 来源证据  │  │ 文件管理      │          │
│  └──────┬───────┘  └──────────┘  └──────┬───────┘          │
└─────────┼────────────────────────────────┼──────────────────┘
          │ SSE (流式) / REST              │ multipart
          ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI 后端 (localhost:8000)                  │
│                                                             │
│  main.py ─── API 路由层                                      │
│    ├─ GET /health         → 健康检查                         │
│    ├─ POST /chat          → 非流式问答                       │
│    ├─ POST /chat/stream   → SSE 流式问答 ⭐                   │
│    ├─ POST/GET/PUT/DELETE /upload* → 文件 CRUD              │
│                                                             │
│  rag_service.py ─── 核心编排层 (最关键)                      │
│    ├─ initialize()       → 初始化嵌入模型+LLM+向量库          │
│    ├─ refresh_index()    → 文档分块→向量化→存入 Chroma        │
│    ├─ chat()             → 检索→查缓存→生成答案              │
│    └─ _generate_answer() → 组装 Prompt → 调用 LLM            │
│                                                             │
│  services/                                                  │
│    ├─ document_loader.py → 加载 .txt/.md/.json 文件          │
│    ├─ redis_store.py     → 会话记忆 + LLM 响应缓存           │
│    └─ upload_store.py    → 上传文件持久化                    │
│                                                             │
├──────────────┬──────────────────────────┬───────────────────┤
│   ChromaDB   │        Redis             │   本地文件系统     │
│ (向量数据库)  │  (会话记忆 + 缓存)       │ (data/ + storage/) │
└──────────────┴──────────────────────────┴───────────────────┘
```

### 技术栈总览

| 层级 | 技术 | 用途 |
|------|------|------|
| **后端框架** | FastAPI | REST API + SSE 流式输出 |
| **向量数据库** | Chroma | 本地存储文档嵌入向量 |
| **嵌入模型** | BGE-Small-ZH (本地) | 离线中文向量化，384 维 |
| **聊天模型** | MiniMax-M2.1 (OpenAI 兼容) | 对话生成（通过 `api.minimaxi.com`）|
| **缓存/会话** | Redis | LLM 响应缓存 + 多轮对话记忆 |
| **前端** | React + TypeScript + Vite | 操作控制台界面 |
| **编排** | Docker Compose | Redis + API + Frontend 三服务 |

---

## 二、环境配置解读

### `.env` 文件完整说明

```env
OPENAI_API_KEY=sk-api-IlXDTzHsKDh8ZpUzfJBqzYBSgoGRXlTXhXEkqNK8O_1N8XNTozR97jUr17HYOAdqs6CZnp-m2vVfRbSPGCf9dNAobUV0hI1f4t7FqVGB8HVcSyY3RVNkwrA
OPENAI_API_BASE=https://api.minimaxi.com/v1
OPENAI_CHAT_MODEL=MiniMax-M2.1
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=models/bge-small-zh-v1.5
LOCAL_EMBEDDING_DEVICE=cpu
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_DEFAULT_TOP_K=4
RAG_HISTORY_WINDOW=6
RAG_CHUNK_SIZE=900
RAG_CHUNK_OVERLAP=180
```

| 配置项 | 当前值 | 含义 | 说明 |
|--------|--------|------|------|
| `OPENAI_API_KEY` | `sk-api-...` | LLM API 密钥 | MiniMax 平台的密钥 |
| `OPENAI_API_BASE` | `https://api.minimaxi.com/v1` | LLM API 地址 | 使用 MiniMax 作为聊天模型提供商 |
| `OPENAI_CHAT_MODEL` | `MiniMax-M2.1` | 聊天模型名称 | 支持中文推理的对话模型 |
| `EMBEDDING_PROVIDER` | `local` | 嵌入模型提供方 | `local`=本地 BGE, `openai`=远程 API |
| `LOCAL_EMBEDDING_MODEL` | `models/bge-small-zh-v1.5` | 本地嵌入模型路径 | BAAI 出品的中文小模型，免费离线运行 |
| `LOCAL_EMBEDDING_DEVICE` | `cpu` | 推理设备 | 无 GPU 也能跑，有 GPU 可改为 `cuda` |
| `RAG_DEFAULT_TOP_K` | `4` | 检索返回数量 | 每次从向量库取回的最相关片段数 |
| `RAG_HISTORY_WINDOW` | `6` | 历史消息窗口 | 从 Redis 加载最近 N 轮对话作为上下文 |
| `RAG_CHUNK_SIZE` | `900` | 文档分块大小 | 将长文档切成的每块字符数 |
| `RAG_CHUNK_OVERLAP` | `180` | 分块重叠长度 | 相邻块之间重叠的字符数（保持语义连贯）|

### 配置加载逻辑 (`app/config.py`)

```python
@dataclass(slots=True)
class Settings:
    # 通过 os.getenv() 读取环境变量，均有默认值
    @classmethod
    def from_env(cls) -> "Settings":
        # 核心路径:
        storage_dir = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "storage"))
        data_dir = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
        uploads_dir = Path(os.getenv("RAG_UPLOADS_DIR", storage_dir / "uploads"))
```

---

## 三、三大核心流程

### 流程 1：一次完整对话请求

**入口**: 用户提问 → `POST /chat` 或 `POST /chat/stream`

**核心函数**: `rag_service.py` 的 `chat()` 方法 (第 141~180 行)

```
用户输入: "公司有哪些产品？"
         │
         ▼
   ① load_messages(session_id, window=6)
      └── 从 Redis 加载该会话最近 6 轮历史消息
         │
         ▼
   ② similarity_search_with_score(question, k=top_k)
      └── Chroma 向量相似度搜索，返回 top-k 个最相关文档片段
      └── 每个结果包含: document(内容+元数据) + score(相似度得分)
         │
         ▼
   ③ build_cache_key(model, question, history, sources)
      └── 用 md5 哈希生成唯一缓存 key
         │
         ▼
   ④ get_cached_answer(key) → 查询 Redis
      │
      ├── ★ 命中缓存 (cache_hit=true):
      │      直接返回缓存的答案，跳过 LLM 调用 ⚡
      │
      └── 未命中:
              ▼
           _generate_answer(question, history, sources)
             │
             ├── 组装 System Message (要求基于上下文回答)
             ├── 注入内容:
             │   ├── Conversation history (历史对话文本)
             │   ├── Retrieved context (来源片段 [1][2][3][4]...)
             │   └── Question (当前问题)
             │
             ▼
           ChatOpenAI.invoke([SystemMessage, HumanMessage])
             └── 调用 MiniMax-M2.1 生成回答
                │
                ▼
           _strip_reasoning_blocks(answer)
             └── 正则过滤掉  think... 标签内容
             └── 客户端收到干净答案
             └── 服务端日志保留完整 reasoning（调试用）
                │
                ▼
           set_cached_answer(key, answer, TTL=3600s)
             └── 答案写入 Redis 缓存，供后续相同问题复用
         │
         ▼
   ⑤ save_message(session_id, "user", message)
      save_message(session_id, "assistant", answer)
      └── 双方消息都写入 Redis 会话存储
         │
         ▼
   返回: {
       session_id: "uuid",
       answer: "...",
       sources: [{file_name, content, score}, ...],
       cache_hit: bool
   }
```

#### 关键代码位置

| 步骤 | 文件 | 行号 |
|------|------|------|
| 加载历史 | `rag_service.py` | :153 |
| 向量检索 | `rag_service.py` | :154 |
| 构建缓存 key | `rag_service.py` | :156-162 |
| 查/写缓存 | `rag_service.py` | :163-170 |
| 组装 Prompt + 调用 LLM | `rag_service.py` | :206-240 |
| 过滤 reasoning 标签 | `rag_service.py` | :242-258 |
| 保存会话 | `rag_service.py` | :172-173 |

---

### 流程 2：文档索引构建

**触发时机**: 服务启动时 (`initialize()`) / 文件上传后 (`create_upload/replace_upload/delete_upload`)

**核心函数**: `rag_service.py` 的 `refresh_index()` 方法 (第 78~139 行)

```
触发 refresh_index()
     │
     ▼
  ① _source_directories()
     └── 返回两个源目录:
         ├── SourceDirectory("static", data/)
         └── SourceDirectory("uploads", storage/uploads/)
     │
     ▼
  ② compute_sources_fingerprint(sources)
     └── 扫描目录下所有支持文件 (.txt/.md/.json)
     └── 计算文件名+大小+修改时间的 hash 指纹
     │
     ▼
  ③ load_manifest(manifest_path)
     └── 读取上次保存的 index_manifest.json
     │
     ▼
  ④ 判断是否需要重建 (should_rebuild):
     │
     ├── 需要重建的情况 (任一满足即可):
     │   ├── manifest 不存在 (首次启动)
     │   ├── fingerprint 变了 (文件增/删/改)
     │   ├── embedding_signature 变了 (换了嵌入模型或参数)
     │   └── vector_dir 不存在 (向量数据丢失)
     │
     └── 无需重建 → 直接加载已有 Chroma 库 (秒级!) ★ 性能优化点
          │
          ▼
       Chroma(collection_name, persist_directory, embedding_function)
       └── 更新 index_stats，直接返回
     │
     ▼ (需要全量重建)
  ⑤ load_documents_from_sources(sources)
     └── document_loader.py 处理:
         ├── *.txt   → TextLoader 逐行读取
         ├── *.md    → UnstructuredMarkdownLoader 解析
         └── *.json  → JsonLoader + 键扁平化处理
     └── 返回 Document 列表: [{page_content, metadata}, ...]
        │
        ▼
  ⑥ RecursiveCharacterTextSplitter
     ├── chunk_size=900      (每块最大字符数)
     ├── chunk_overlap=180   (块间重叠字符数)
     └── 将长文档切成有重叠的小块 (保证语义不被截断)
        │
        ▼
  ⑦ 构建嵌入模型 (_build_embeddings)
     │
     ├── EMBEDDING_PROVIDER=local 时:
     │   HuggingFaceEmbeddings(
     │       model_name="models/bge-small-zh-v1.5",
     │       model_kwargs={"device": "cpu"},
     │       encode_kwargs={"normalize_embeddings": True}
     │   )
     │   └── 每个文本块 → 384 维浮点向量 (归一化)
     │
     └── EMBEDDING_PROVIDER=openai 时:
         OpenAIEmbeddings(api_key, base_url, model)
         └── 远程 API 调用 (需联网、付费)
        │
        ▼
  ⑧ Chroma.from_documents()
     ├── documents=split_documents  (分块后的文档)
     ├── embedding=self.embeddings  (嵌入函数)
     ├── persist_directory=vector_dir (持久化到磁盘)
     └── collection_name="knowledge_base"
        │
        ▼
  ⑨ write_manifest()
     └── 保存新的 index_manifest.json:
         ├── fingerprint (文件指纹)
         ├── chunk_count (总块数)
         ├── document_count (文档数)
         └── embedding_signature (嵌入模型签名)
        │
        ▼
  ⑩ 更新 self.index_stats
     └── ready=True, document_count, chunk_count, fingerprint...
```

#### Manifest 机制 — 为什么这是重要的性能优化

```
❌ 没有机制: 每次启动都重新读取所有文件 → 分块 → 向量化 → 存入 Chroma
   → 启动耗时随文档数量线性增长

✅ 有 Manifest:
   启动时只需计算文件指纹 → 与上次对比
   ├── 相同 → 直接加载已有向量库 (< 1秒)
   └── 不同 → 触发重建 (只在必要时执行)
```

---

### 流程 3：SSE 流式输出

**路由**: `POST /chat/stream` (`main.py`:79-111)

**前端消费**: `frontend/src/api.ts` 的 `streamChat()` 函数 (:52-106)

#### 后端: SSE 事件生成器

`main.py` 的 `event_stream()` 函数是一个 Python **生成器 (generator)**:

```python
def event_stream():
    ensure_ready(request)                     # 检查服务就绪
    result = _run_chat(rag, message, ...)     # 执行完整 RAG 流程
    
    yield _sse("start", {...})                # ① 开始信号
    for token in result["answer"].split():    # ② 逐词推送
        yield _sse("token", {"text": token + " "})
    yield _sse("sources", {"sources": [...]}) # ③ 来源证据
    yield _sse("done", {...})                 # ④ 完成信号

return StreamingResponse(event_stream(), media_type="text/event-stream")
```

#### SSE 事件协议

| 事件名 | 触发时机 | 数据结构 | 说明 |
|--------|----------|----------|------|
| `start` | 立即发送 | `{session_id, cache_hit}` | 通知前端开始，附带会话 ID 和缓存状态 |
| `token` | 逐词循环 | `{text: "每个" }` | 打字机效果的核心——每次推一个词 |
| `sources` | 所有 token 发完后 | `{sources: [{file_name, content, score}]}` | 检索到的来源片段列表 |
| `done` | 全部结束 | `{session_id, answer, cache_hit}` | 完整的最终答案（用于修正可能拼接错误的结果）|
| `error` | 异常时 | `{detail, status_code}` | 错误信息 |

SSE 报文格式示例:
```
event: start
data: {"session_id": "abc-123", "cache_hit": false}

event: token
data: {"text": "公司 "}

event: token
data: {"text": "的主要产品"}

...

event: sources
data: {"sources": [{"file_name": "catalog.json", "content": "...", "score": 0.234}]}

event: done
data: {"session_id": "abc-123", "answer": "公司的主要产品是...", "cache_hit": false}
```

#### 前端: SSE 流解析 (`api.ts`:69-105)

```typescript
const reader = response.body.getReader();   // 获取流读取器
const decoder = new TextDecoder();          // UTF-8 解码器
let buffer = "";                           // 累积缓冲区

while (true) {
    const { done, value } = await reader.read();  // 读取一块数据
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");    // 按 SSE 协议双换行分割
    buffer = events.pop() ?? "";            // 最后一行可能不完整，放回缓冲区
    
    for (const block of events) {
        const event = parseEvent(block);    // 解析 event:/data: 行
        
        if (event.name === "start")   handlers.onStart(event.data);
        if (event.name === "token")   handlers.onToken(event.data.text);  // 逐词追加到 UI
        if (event.name === "sources") handlers.onSources(event.data.sources);
        if (event.name === "done")    handlers.onDone(event.data);
    }
}
```

`parseEvent()` 解析逻辑:
```typescript
function parseEvent(block: string) {
    const eventLine = lines.find(l => l.startsWith("event: "));
    const dataLine   = lines.find(l => l.startsWith("data: "));
    return { name: eventLine.replace("event: ", ""), data: JSON.parse(dataLine...) };
}
```

#### 前端 UI 更新 (`App.tsx`:68-100)

```typescript
await streamChat(payload, {
    onStart(payload) {
        setSessionId(payload.session_id);  // 保存会话 ID
    },
    onToken(token) {
        // 逐步追加文字到 assistant 消息气泡 (打字机效果)
        setMessages(current => current.map(item =>
            item.id === assistantId ? { ...item, content: item.content + token } : item
        ));
    },
    onSources(nextSources) {
        setSources(nextSources);  // 显示来源面板
    },
    onDone(payload) {
        // 用最终完整答案替换（防止逐词拼接误差）
        setMessages(current => current.map(item =>
            item.id === assistantId ? { ...item, content: payload.answer } : item
        ));
    },
});
```

---

## 四、四大设计模式

### 设计 1：双层 Redis 存储

**文件**: `app/services/redis_store.py`

Redis 中存储两种不同用途的数据:

```
Key 结构 (前缀由 REDIS_PREFIX="ingenico" 控制):

├── ingenico:cache:{MD5(model + question + history_hash + sources_hash)}
│   Value: LLM 生成的完整回答字符串
│   TTL:  3600 秒 (1 小时)
│   用途: 避免相同问题重复调用 LLM，节省成本和延迟
│
└── ingenico:session:{session_id}
    Value: List[MemoryMessage]  ← Redis List 类型
    Item:  {role: "user"|"assistant", content: "...", timestamp: "..."}
    用途: 保留多轮对话历史，实现上下文连贯
    窗口:  只取最近 N 条 (N = RAG_HISTORY_WINDOW, 默认 6)
```

**缓存 key 的构建逻辑** (`redis_store.py:build_cache_key`):
- 输入: 模型名称 + 问题文本 + 历史 messages + 来源列表 + top_k
- 输出: MD5 哈希值
- 特性: 只有所有因素完全一致才会命中缓存

**为什么不用纯问题作为缓存 key?**
因为同样的"它有什么特点？"在不同上下文中含义不同:
- 上下文 A: "公司主要产品是支付终端。它有什么特点？" → 回答支付终端的特点
- 上下文 B: "公司主要软件是SDK。它有什么特点？" → 回答 SDK 的特点

所以必须把历史和来源也纳入缓存 key。

---

### 设计 2：Reasoning Block 过滤

**文件**: `rag_service.py`:30 (正则定义), :242-258 (过滤函数)

```python
THINK_BLOCK_PATTERN = re.compile(r"think(.*?)think>", re.IGNORECASE | re.DOTALL)
```

**背景**: 部分 LLM 模型在返回答案时会附带 `think` 标签包裹的推理过程（类似 Chain-of-Thought）。
这种内容对终端用户无意义，但对调试有价值。

**处理策略**:

```python
def _strip_reasoning_blocks(self, answer: str, session_id: str) -> str:
    # 1. 提取所有 reasoning 内容
    reasoning_blocks = THINK_BLOCK_PATTERN.findall(answer)
    
    # 2. 记录到服务端日志 (不暴露给客户端!)
    for block in reasoning_blocks:
        LOGGER.info("Filtered reasoning block for session %s:\n%s", session_id, block)
    
    # 3. 从回答中移除  标签及其内容
    cleaned_answer = THINK_BLOCK_PATTERN.sub("", answer)
    
    # 4. 清理多余空行
    cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer).strip()
    
    return cleaned_answer or answer.strip()  # 如果清空了则返回原文
```

**效果示意**:
```
LLM 原始返回:
  "根据文档[1]，Ingenico 主要产品包括支付终端设备。think让我再检查一下其他来源...是的，文档[2]也提到了POS终端系列。think> 产品线覆盖低端到高端。"

客户端收到的答案 (干净版):
  "根据文档[1]，Ingenico 主要产品包括支付终端设备。产品线覆盖低端到高端。"

服务端日志记录 (完整版):
  [INFO] Filtered reasoning block for session abc-123 (block 1):
  让我再检查一下其他来源...是的，文档[2]也提到了POS终端系列。
```

---

### 设计 3：Source Grounding (来源追溯)

**文件**: `rag_service.py`:261-267 (`_build_source`), `schemas.py`:6-10 (`SourceSnippet`)

每次 RAG 回答都附带 `sources[]` 数组，让用户可以验证 AI 的回答是否有据可依。

```python
class SourceSnippet(BaseModel):
    source: str       # 完整文件路径
    file_name: str    # 文件名 (如 "company_overview.md")
    content: str      # 匹配到的原文截取 (前 400 字符)
    score: float      # 相似度得分 (越低越相关, 0=完美匹配)
```

**来源构建过程** (`rag_service.py`:154-155):

```python
retrieved = self.vector_store.similarity_search_with_score(cleaned_message, k=effective_top_k)
# retrieved 是 [(Document, score), ...] 元组列表

sources = [
    SourceSnippet(
        source=document.metadata.get("source", ""),
        file_name=document.metadata.get("file_name", ""),
        content=document.page_content[:400],  # 截取前 400 字符
        score=score,
    )
    for document, score in retrieved
]
```

**为什么 Source Grounding 很重要?**

| 场景 | 普通聊天机器人 | RAG + Source Grounding |
|------|---------------|------------------------|
| AI 说"公司有5000人" | 无法验证是否正确 | 点击来源查看原文确认 |
| AI 回答含幻觉 | 用户无法察觉 | 来源为空或分数很低 → 可疑 |
| 合规审计需求 | 无迹可寻 | 每条回答都有可追溯的证据链 |

**前端展示** (`App.tsx`:229-237):
```tsx
sources.map((source, index) => (
    <article className="source-block">
        <div>
            <strong>{source.file_name}</strong>
            <span>{source.score?.toFixed(3)}</span>  {/* 如 0.234 */}
        </div>
        <p>{source.content}</p>  {/* 截取的原文片段 */}
    </article>
))
```

---

### 设计 4：上传即索引

**文件**: `rag_service.py`:185-197

任何改变知识库内容的操作都会立即触发索引刷新:

```python
def create_upload(self, file_name, content):   # 上传新文件
    record = self.upload_store.create_upload(...)
    self.refresh_index()                        # ← 立即重建索引
    return ...

def replace_upload(self, file_id, file_name, content):  # 替换文件
    record = self.upload_store.replace_upload(...)
    self.refresh_index()                        # ← 立即重建索引
    return ...

def delete_upload(self, file_id):               # 删除文件
    self.upload_store.delete_upload(file_id)
    self.refresh_index()                        # ← 立即重建索引
```

**完整的上传生命周期**:

```
用户选择文件 → POST /upload (multipart/form-data)
     │
     ▼
main.py: upload_file()
  ├── 读取文件字节: content = await file.read()
  ├── 校验文件类型 (.txt/.md/.json) → 否则 400
  │
     ▼
rag_service: create_upload(file_name, content)
  │
  ├── upload_store.create_upload()
  │   ├── 生成 file_id (uuid4)
  │   ├── 生成 stored_name (uuid4 + 原扩展名)
  │   ├── 写入文件: storage/uploads/{stored_name}
  │   └── 更新元数据: storage/uploads.json
  │       └── {file_id, file_name, stored_name, status, source_path, updated_at}
  │
  ├── refresh_index()                          ← 重建向量索引
  │   └── 新文件的内容被纳入检索范围
  │
  └── 返回 UploadRecord 给前端
       └── 前端 uploads 列表自动刷新 (fetchUploads())
```

---

## 五、建议学习顺序

### 由浅入深的阅读路线

```
阶段 1: 入门基础 (~300 行)
├── app/config.py              (~75行)   ← 配置项全貌与环境变量映射
└── app/schemas.py             (~48行)   ← Pydantic 数据模型定义

阶段 2: API 层 (~230 行)
└── app/main.py               (~186行)  ← FastAPI 路由 / SSE 生成器 / 错误处理

阶段 3: 核心引擎 (~550 行) ★★★ 最重要
└── app/services/rag_service.py (~326行) ← RAG 编排全流程 (初始化/索引/对话/生成)

阶段 4: 前端交互 (~410 行)
├── frontend/src/api.ts        (~120行)  ← fetch 封装 + SSE 流解析 + 事件分发
└── frontend/src/App.tsx       (~291行)  ← React 组件 / 状态管理 / UI 交互

阶段 5: 服务层 (按需深入)
├── app/services/redis_store.py          ← Redis 操作 / 缓存策略 / 会话存储
├── app/services/document_loader.py      ← 多格式文档加载 / JSON 扁平化 / 指纹计算
└── app/services/upload_store.py         ← 上传 CRUD / 元数据持久化

阶段 6: 运维与部署
├── docker-compose.yml        (~48行)    ← 三服务编排与网络
├── Dockerfile                            ← 后端容器构建
└── AGENTS.md                             ← 项目规范与全局规则
```

### 各模块的核心知识点

| 模块 | 核心概念 | 学习价值 |
|------|----------|----------|
| `config.py` | dataclass + `from_env()` 工厂模式 | Python 项目配置的最佳实践 |
| `schemas.py` | Pydantic BaseModel + Field 校验 | API 数据校验与自动文档生成 |
| `main.py` | lifespan 上下文管理器 / StreamingResponse / CORS | FastAPI 高级特性 |
| `rag_service.py` | LangChain 编排链路 / Manifest 增量索引 / Prompt 工程 | **RAG 系统的核心精髓** |
| `api.ts` | ReadableStream / Generator 模式 / SSE 协议解析 | 前端流式数据处理 |
| `App.tsx` | useRef / useState / 事件回调模式 | React 异步状态管理 |
| `redis_store.py` | Redis Hash/List 数据结构 / TTL 策略 / 序列化 | 缓存与会话的设计权衡 |
| `document_loader.py` | 多格式适配器 / 文本分割策略 / 哈希指纹 | ETL 数据管道基础 |
| `docker-compose.yml` | 服务依赖 / 卷挂载 / 健康检查 / 环境注入 | 容器化部署实践 |

---

## 六、动手实验

### 实验 1：观察缓存命中机制

**目的**: 理解 Redis 缓存如何减少重复 LLM 调用

**步骤**:
1. 启动服务后打开前端 `http://localhost:5173`
2. 输入问题: "介绍一下公司" → 发送
3. 观察回答下方显示 **"Fresh generation"** (cache_hit=false)
4. **再次发送完全相同的问题**
5. 观察回答下方显示 **"Redis cache hit"** (cache_hit=true) ⚡
6. 等待 1 小时后再问同样问题 → 又变回 "Fresh generation" (TTL 过期)

**深入**: 在 `rag_service.py:163` 附近加日志观察缓存 key:
```python
cached_answer = self.redis_store.get_cached_answer(cache_key)
print(f"[DEBUG] cache_key={cache_key[:20]}..., hit={cached_answer is not None}")
```

---

### 实验 2：动态知识库

**目的**: 验证上传文件后立即可被检索到

**步骤**:
1. 创建一个 `test.txt`，内容:
   ```
   这是一个测试产品: Quantum-Pay 支付终端。
   它的特点是: 支持人脸识别支付，响应时间小于0.5秒。
   ```
2. 通过前端右侧 **"Add file"** 按钮上传此文件
3. 观察顶部状态栏: `upload_count` 从 0 变为 1
4. 提问: "Quantum-Pay 有什么特点？"
5. 验证回答中包含了 test.txt 中的内容
6. 查看 Sources 面板，确认引用来源包含 `test.txt`
7. 删除上传的文件，再问同样问题 → 回答变化（不再包含该信息）

---

### 实验 3：追踪一次完整请求链路

**目的**: 理解 RAG 内部每个环节的数据流转

**操作**: 在 `rag_service.py` 的 `chat()` 方法中加入调试日志:

```python
def chat(self, message, session_id=None, top_k=None):
    # ...existing code...
    
    # ★ 在向量检索后加日志
    retrieved = self.vector_store.similarity_search_with_score(cleaned_message, k=effective_top_k)
    print(f"\n[DEBUG] ===== 检索结果 =====")
    print(f"  问题: {cleaned_message}")
    for i, (doc, score) in enumerate(retrieved, 1):
        print(f"  [{i}] score={score:.4f} | file={doc.metadata.get('file_name')}")
        print(f"      内容: {doc.page_content[:120]}...")
    
    # ★ 在缓存查询后加日志
    cached_answer = self.redis_store.get_cached_answer(cache_key)
    print(f"\n[DEBUG] ===== 缓存状态 =====")
    print(f"  cache_hit={cached_answer is not None}")
    
    # ...existing code...
```

**预期输出**:
```
[DEBUG] ===== 检索结果 =====
  问题: 公司有哪些产品？
  [1] score=0.2341 | file=catalog.json
      内容: Ingenico 提供多种支付终端产品线，包括 POS 终端、移动支付设备...
  [2] score=0.3456 | file=company_overview.md
      内容: 公司主要面向银行和零售商提供支付解决方案...

[DEBUG] ===== 缓存状态 =====
  cache_hit=False
```

---

### 实验 4：理解文档分块效果

**目的**: 观察 chunk_size 和 chunk_overlap 如何影响检索质量

**操作**:
1. 在 `rag_service.py:99-102` 修改分块参数:
   ```python
   # 改成更小的块 (更精细但可能断裂语义)
   splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
   
   # 或者更大的块 (更完整但可能混入无关信息)
   splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
   ```
2. 重启服务，观察 `chunk_count` 变化
3. 同样的问题，对比检索到的来源片段差异
4. **还原为默认值**: chunk_size=900, overlap=180

---

### 实验 5：SSE 流式 vs 非流式对比

**目的**: 理解两种接口的区别和使用场景

**步骤**:

**非流式** (`POST /chat`):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "公司简介"}'
# → 等待完整生成后一次性返回 JSON
```

**流式** (`POST /chat/stream`):
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "公司简介"}'
# → 逐步看到 start → token token token ... → sources → done
# -N 参数禁用 curl 的缓冲，实时显示
```

| 维度 | `/chat` (非流式) | `/chat/stream` (流式) |
|------|-------------------|----------------------|
| 响应方式 | 一次性返回完整 JSON | SSE 逐词推送 |
| 首字延迟 | 需等待全部生成完 | 第一个 token 即刻返回 |
| 适用场景 | 程序间 API 调用 | 前端用户体验（打字机效果）|
| 取消请求 | 无法中途取消 | 可随时断开连接 |

---

## 附录：关键代码位置速查

### API 端点一览

| 方法 | 路径 | 功能 | 定义位置 |
|------|------|------|----------|
| GET | `/health` | 健康检查 | `main.py`:59-66 |
| POST | `/chat` | 非流式问答 | `main.py`:68-77 |
| POST | `/chat/stream` | SSE 流式问答 | `main.py`:79-111 |
| GET | `/uploads` | 列出已上传文件 | `main.py`:113-116 |
| POST | `/upload` | 上传新文件 | `main.py`:118-130 |
| PUT | `/uploads/{file_id}` | 替换文件 | `main.py`:132-147 |
| DELETE | `/uploads/{file_id}` | 删除文件 | `main.py`:149-156 |

### 数据模型一览

| 模型 | 字段 | 用途 | 定义位置 |
|------|------|------|----------|
| `SourceSnippet` | source, file_name, content, score | 检索来源片段 | `schemas.py`:6-10 |
| `ChatRequest` | message, session_id?, top_k? | 请求体 | `schemas.py`:13-16 |
| `ChatResponse` | session_id, answer, sources[], cache_hit | 回答响应 | `schemas.py`:19-23 |
| `UploadRecord` | file_id, file_name, stored_name, status, ... | 上传记录 | `schemas.py`:26-32 |
| `HealthResponse` | status, ready, document_count, chunk_count, ... | 健康状态 | `schemas.py`:39-47 |

### 存储层一览

| 存储 | 位置 | 数据类型 | 说明 |
|------|------|----------|------|
| **ChromaDB** | `storage/chroma/` | 向量数据库 | 文档嵌入向量的持久化存储 |
| **Redis Cache** | Key: `ingenico:cache:{hash}` | String + TTL | LLM 回复缓存 (3600s) |
| **Redis Session** | Key: `ingenico:session:{id}` | List | 对话历史消息 |
| **Upload Files** | `storage/uploads/{uuid}.ext` | 原始文件 | 用户上传的知识文件 |
| **Upload Metadata** | `storage/uploads.json` | JSON Array | 上传文件的元数据清单 |
| **Index Manifest** | `storage/index_manifest.json` | JSON Object | 索引指纹 (用于增量更新判断) |
| **Static Data** | `data/*.txt,*.md,*.json` | 原始文件 | 静态知识库 (内置) |
| **Local Model** | `models/bge-small-zh-v1.5/` | 模型权重 | 本地嵌入模型文件 |

### 目录结构速览

```
ingenico/
├── app/
│   ├── __init__.py
│   ├── config.py              # Settings dataclass, from_env() 工厂
│   ├── main.py                # FastAPI 应用创建, 路由注册, SSE 生成器
│   ├── schemas.py             # Pydantic 请求/响应模型
│   └── services/
│       ├── __init__.py
│       ├── rag_service.py     # ★ 核心: RagService 类
│       ├── redis_store.py     # RedisChatStore: 缓存 + 会话
│       ├── document_loader.py # 文档加载 + 分块 + 指纹计算
│       └── upload_store.py    # UploadStore: 文件 CRUD + 元数据
├── frontend/
│   ├── src/
│   │   ├── api.ts             # API 封装 + SSE 解析器
│   │   ├── App.tsx            # 主组件: 对话/来源/上传三个面板
│   │   ├── types.ts           # TypeScript 接口定义
│   │   ├── main.tsx           # React 入口
│   │   └── styles.css         # 样式
│   ├── package.json
│   └── vite.config.ts
├── data/                      # 静态知识库
│   ├── company_overview.md
│   ├── faq.txt
│   └── catalog.json
├── models/                    # 本地嵌入模型
├── storage/                   # 运行时数据 (gitignore)
│   ├── chroma/                # 向量数据库
│   ├── uploads/               # 上传的文件
│   ├── uploads.json           # 上传元数据
│   └── index_manifest.json    # 索引指纹
├── docs/
│   └── LEARNING_GUIDE.md      # ← 你正在阅读的这个文件
├── tests/                     # 自动化测试
├── scripts/verify/            # CLI 验证脚本
├── docker-compose.yml         # 三服务编排
├── Dockerfile                 # 后端镜像构建
├── requirements.txt           # Python 依赖
├── .env                       # 环境变量 (不提交 git)
├── .env.example               # 环境变量模板
├── plan.md                    # 分阶段路线图
└── AGENTS.md                  # 项目规范
```

---

> **提示**: 本指南基于项目 Stage-2 的实际代码编写。如代码发生变更，请以最新代码为准。
> 
> 建议配合 IDE 的「转到定义」功能使用本指南，在阅读时随时跳转到对应代码位置。
