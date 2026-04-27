import { FormEvent, useEffect, useRef, useState } from "react";

import { createUpload, deleteUpload, fetchHealth, fetchUploads, replaceUpload, streamChat } from "./api";
import type { ChatMessage, HealthResponse, SourceSnippet, ToolCall, UploadRecord } from "./types";

const EMPTY_HEALTH: HealthResponse = {
  status: "starting",
  ready: false,
  document_count: 0,
  chunk_count: 0,
  redis_ready: false,
  upload_count: 0,
  tool_count: 0,
  fingerprint: null,
  startup_error: null,
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse>(EMPTY_HEALTH);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<SourceSnippet[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [uploads, setUploads] = useState<UploadRecord[]>([]);
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const replaceInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    void refreshOperationalState();
  }, []);

  async function refreshOperationalState() {
    try {
      const [healthResult, uploadsResult] = await Promise.all([fetchHealth(), fetchUploads()]);
      setHealth(healthResult);
      setUploads(uploadsResult.files);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh the console.");
    }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question.trim(),
    };
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setBusy(true);
    setError(null);
    setSources([]);
    setToolCalls([]);
    const currentQuestion = question.trim();
    setQuestion("");

    try {
      await streamChat(
        {
          message: currentQuestion,
          session_id: sessionId,
        },
        {
          onStart(payload) {
            setSessionId(payload.session_id);
          },
          onTools(nextToolCalls) {
            setToolCalls(nextToolCalls);
          },
          onToken(token) {
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId
                  ? { ...item, content: `${item.content}${token}` }
                  : item,
              ),
            );
          },
          onSources(nextSources) {
            setSources(nextSources);
          },
          onDone(payload) {
            setSessionId(payload.session_id);
            setSources(payload.sources);
            setToolCalls(payload.tool_calls);
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId
                  ? { ...item, content: payload.answer, cacheHit: payload.cache_hit }
                  : item,
              ),
            );
          },
        },
      );
      const freshHealth = await fetchHealth();
      setHealth(freshHealth);
    } catch (err) {
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? { ...item, content: "The request failed before a full answer arrived." }
            : item,
        ),
      );
      setError(err instanceof Error ? err.message : "Streaming request failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateUpload(file: File | null) {
    if (!file) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await createUpload(file);
      await refreshOperationalState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleReplaceUpload(fileId: string, file: File | null) {
    if (!file) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await replaceUpload(fileId, file);
      await refreshOperationalState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replace failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteUpload(fileId: string) {
    setUploading(true);
    setError(null);
    try {
      await deleteUpload(fileId);
      await refreshOperationalState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <h1>Ingenico</h1>
        <div className="status-strip">
          <span data-ready={health.ready}>{health.ready ? "Ready" : "Degraded"}</span>
          <span>{health.document_count} docs</span>
          <span>{health.chunk_count} chunks</span>
          <span>{health.tool_count} tools</span>
          <span>Redis {health.redis_ready ? "connected" : "offline"}</span>
          <span>{health.upload_count} uploads</span>
        </div>
        {health.startup_error ? <p className="notice">{health.startup_error}</p> : null}
        {error ? <p className="notice notice-error">{error}</p> : null}
      </section>

      <section className="workspace">
        <div className="column conversation">
          <div className="section-head">
            <h2>Conversation</h2>
            <p>Session {sessionId ?? "will be created on first send"}</p>
          </div>
          <div className="transcript">
            {messages.length === 0 ? (
              <p className="placeholder">
                Start with a question like "How do I start a new conversation?" and the stream will appear
                here.
              </p>
            ) : (
              messages.map((message) => (
                <article key={message.id} className={`bubble bubble-${message.role}`}>
                  <span className="bubble-role">{message.role}</span>
                  <p>{message.content || (busy && message.role === "assistant" ? "..." : "")}</p>
                  {message.role === "assistant" && message.cacheHit !== undefined ? (
                    <small>{message.cacheHit ? "Redis cache hit" : "Fresh generation"}</small>
                  ) : null}
                </article>
              ))
            )}
          </div>
          <form className="composer" onSubmit={handleAsk}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask the knowledge base a grounded question."
              rows={4}
            />
            <button type="submit" disabled={busy || !question.trim()}>
              {busy ? "Streaming..." : "Send"}
            </button>
          </form>
        </div>

        <div className="column sidecar">
          <div className="section-head">
            <h2>Sources</h2>
            <p>Latest retrieval evidence</p>
          </div>
          <div className="sources-list">
            {sources.length === 0 ? (
              <p className="placeholder">Retrieved snippets will appear here after each answer.</p>
            ) : (
              sources.map((source, index) => (
                <article key={`${source.file_name}-${index}`} className="source-block">
                  <div>
                    <strong>{source.file_name}</strong>
                    <span>{source.score?.toFixed(3) ?? "n/a"}</span>
                  </div>
                  <p>{source.content}</p>
                </article>
              ))
            )}
          </div>

          <div className="section-head uploads-head">
            <h2>Tools</h2>
            <p>Latest agent routing trace</p>
          </div>
          <div className="sources-list">
            {toolCalls.length === 0 ? (
              <p className="placeholder">Tool routing will appear here when stage 3 uses runtime tools.</p>
            ) : (
              toolCalls.map((toolCall) => (
                <article key={toolCall.tool_name} className="source-block">
                  <div>
                    <strong>{toolCall.tool_name}</strong>
                    <span>{toolCall.grounding_type}</span>
                  </div>
                  <p>{toolCall.result_preview}</p>
                </article>
              ))
            )}
          </div>

          <div className="section-head uploads-head">
            <h2>Uploads</h2>
            <label className="upload-button">
              {uploading ? "Processing..." : "Add file"}
              <input
                type="file"
                accept=".txt,.md,.json,.pdf"
                onChange={(event) => void handleCreateUpload(event.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <div className="uploads-list">
            {uploads.length === 0 ? (
              <p className="placeholder">No uploaded files yet. Static data still participates.</p>
            ) : (
              uploads.map((upload) => (
                <article key={upload.file_id} className="upload-row">
                  <div>
                    <strong>{upload.file_name}</strong>
                    <p>{new Date(upload.updated_at).toLocaleString()}</p>
                  </div>
                  <div className="upload-actions">
                    <button
                      type="button"
                      onClick={() => replaceInputRefs.current[upload.file_id]?.click()}
                      disabled={uploading}
                    >
                      Replace
                    </button>
                    <button type="button" onClick={() => void handleDeleteUpload(upload.file_id)} disabled={uploading}>
                      Delete
                    </button>
                    <input
                      ref={(node) => {
                        replaceInputRefs.current[upload.file_id] = node;
                      }}
                      type="file"
                      accept=".txt,.md,.json,.pdf"
                      hidden
                      onChange={(event) => void handleReplaceUpload(upload.file_id, event.target.files?.[0] ?? null)}
                    />
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
