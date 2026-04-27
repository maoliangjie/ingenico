from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from app.schemas import SourceSnippet
from app.services.redis_store import MemoryMessage
from app.services.upload_store import UploadRecord


class AgentRuntime(Protocol):
    def health(self) -> dict[str, Any]: ...
    def list_upload_records(self) -> list[UploadRecord]: ...
    def search_knowledge(self, query: str, top_k: int) -> list[SourceSnippet]: ...


@dataclass(slots=True)
class PlannedToolCall:
    tool_name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolExecutionResult:
    tool_name: str
    status: str
    grounding_type: str
    arguments: dict[str, Any]
    result_preview: str
    payload: dict[str, Any] | list[dict[str, Any]] | list[str] | str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolDescriptor:
    name: str
    title: str
    description: str
    grounding_type: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "grounding_type": self.grounding_type,
            "input_schema": self.input_schema,
        }


TOOL_DESCRIPTORS = [
    ToolDescriptor(
        name="search_knowledge",
        title="Search Knowledge Base",
        description="Retrieve the most relevant static or uploaded knowledge snippets for a user query.",
        grounding_type="retrieval",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    ),
    ToolDescriptor(
        name="get_system_health",
        title="Get System Health",
        description="Read current readiness, Redis, document, chunk, and upload counts from the runtime.",
        grounding_type="system",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolDescriptor(
        name="list_uploads",
        title="List Uploads",
        description="List dynamically uploaded knowledge files and their update timestamps.",
        grounding_type="uploads",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolDescriptor(
        name="recall_session_history",
        title="Recall Session History",
        description="Return recent user and assistant turns for the active session.",
        grounding_type="memory",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            "additionalProperties": False,
        },
    ),
]


class AgentToolbox:
    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime

    def catalog(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in TOOL_DESCRIPTORS]

    def route(
        self,
        *,
        message: str,
        session_id: str,
        top_k: int,
        history: list[MemoryMessage],
    ) -> list[PlannedToolCall]:
        lowered = message.casefold()
        planned: list[PlannedToolCall] = [
            PlannedToolCall(
                tool_name="search_knowledge",
                arguments={"query": message, "top_k": top_k},
            )
        ]

        if self._mentions_any(
            lowered,
            "health",
            "ready",
            "status",
            "redis",
            "fingerprint",
            "chunk",
            "chunks",
            "document",
            "documents",
            "startup error",
        ):
            planned.append(PlannedToolCall(tool_name="get_system_health", arguments={}))

        if self._mentions_any(
            lowered,
            "upload",
            "uploads",
            "uploaded",
            "file",
            "files",
            "knowledge base",
            "knowledgebase",
        ):
            planned.append(PlannedToolCall(tool_name="list_uploads", arguments={}))

        if history and self._mentions_any(
            lowered,
            "earlier",
            "before",
            "previous",
            "history",
            "session",
            "last question",
            "last answer",
            "what did i ask",
            "what did you say",
        ):
            planned.append(
                PlannedToolCall(
                    tool_name="recall_session_history",
                    arguments={"limit": min(max(len(history), 1), 6)},
                )
            )

        return self._deduplicate(planned)

    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        session_id: str,
        history: list[MemoryMessage],
    ) -> ToolExecutionResult:
        if tool_name == "search_knowledge":
            query = str(arguments.get("query", "")).strip()
            top_k = int(arguments.get("top_k", 4))
            sources = self.runtime.search_knowledge(query, top_k)
            payload = {
                "query": query,
                "top_k": top_k,
                "count": len(sources),
                "sources": [source.model_dump() for source in sources],
            }
            return ToolExecutionResult(
                tool_name=tool_name,
                status="completed",
                grounding_type="retrieval",
                arguments={"query": query, "top_k": top_k},
                result_preview=f"Retrieved {len(sources)} knowledge snippet(s) for the active question.",
                payload=payload,
            )

        if tool_name == "get_system_health":
            health = self.runtime.health()
            return ToolExecutionResult(
                tool_name=tool_name,
                status="completed",
                grounding_type="system",
                arguments={},
                result_preview=(
                    "System readiness is "
                    f"{'ready' if health.get('ready') else 'not ready'} with "
                    f"{health.get('document_count', 0)} documents and "
                    f"{health.get('upload_count', 0)} uploads."
                ),
                payload=health,
            )

        if tool_name == "list_uploads":
            uploads = self.runtime.list_upload_records()
            payload = {
                "count": len(uploads),
                "files": [self._upload_payload(item) for item in uploads],
            }
            return ToolExecutionResult(
                tool_name=tool_name,
                status="completed",
                grounding_type="uploads",
                arguments={},
                result_preview=f"Found {len(uploads)} uploaded knowledge file(s).",
                payload=payload,
            )

        if tool_name == "recall_session_history":
            limit = int(arguments.get("limit", 4))
            payload = {
                "session_id": session_id,
                "count": min(limit, len(history)),
                "messages": [
                    {"role": item.role, "content": item.content}
                    for item in history[-limit:]
                ],
            }
            return ToolExecutionResult(
                tool_name=tool_name,
                status="completed",
                grounding_type="memory",
                arguments={"limit": limit},
                result_preview=f"Loaded {payload['count']} prior message(s) for the active session.",
                payload=payload,
            )

        raise KeyError(f"Unknown tool '{tool_name}'.")

    @staticmethod
    def _upload_payload(record: UploadRecord) -> dict[str, str]:
        return {
            "file_id": record.file_id,
            "file_name": record.file_name,
            "status": record.status,
            "updated_at": record.updated_at,
        }

    @staticmethod
    def _deduplicate(planned: list[PlannedToolCall]) -> list[PlannedToolCall]:
        seen: set[str] = set()
        result: list[PlannedToolCall] = []
        for item in planned:
            if item.tool_name in seen:
                continue
            seen.add(item.tool_name)
            result.append(item)
        return result

    @staticmethod
    def _mentions_any(lowered: str, *tokens: str) -> bool:
        return any(token in lowered for token in tokens)
