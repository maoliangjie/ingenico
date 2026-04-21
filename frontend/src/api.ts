import type { ChatResponse, HealthResponse, SourceSnippet, UploadListResponse, UploadRecord } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail ?? "Request failed.");
  }
  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  return parseJson<HealthResponse>(response);
}

export async function fetchUploads(): Promise<UploadListResponse> {
  const response = await fetch(`${API_BASE}/uploads`);
  return parseJson<UploadListResponse>(response);
}

export async function createUpload(file: File): Promise<UploadRecord> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  return parseJson<UploadRecord>(response);
}

export async function replaceUpload(fileId: string, file: File): Promise<UploadRecord> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/uploads/${fileId}`, { method: "PUT", body: form });
  return parseJson<UploadRecord>(response);
}

export async function deleteUpload(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/uploads/${fileId}`, { method: "DELETE" });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail ?? "Delete failed.");
  }
}

type StreamHandlers = {
  onStart: (payload: { session_id: string; cache_hit: boolean }) => void;
  onToken: (text: string) => void;
  onSources: (sources: SourceSnippet[]) => void;
  onDone: (payload: ChatResponse) => void;
};

export async function streamChat(
  payload: { message: string; session_id?: string | null; top_k?: number },
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail ?? "Streaming request failed.");
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const block of events) {
      const event = parseEvent(block);
      if (!event) {
        continue;
      }
      if (event.name === "start") {
        handlers.onStart(event.data as { session_id: string; cache_hit: boolean });
      }
      if (event.name === "token") {
        handlers.onToken((event.data as { text: string }).text);
      }
      if (event.name === "sources") {
        handlers.onSources((event.data as { sources: SourceSnippet[] }).sources);
      }
      if (event.name === "done") {
        const donePayload = event.data as { session_id: string; answer: string; cache_hit: boolean };
        handlers.onDone({
          session_id: donePayload.session_id,
          answer: donePayload.answer,
          cache_hit: donePayload.cache_hit,
          sources: [],
        });
      }
    }
  }
}

function parseEvent(block: string): { name: string; data: unknown } | null {
  const lines = block.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) {
    return null;
  }
  return {
    name: eventLine.replace("event: ", "").trim(),
    data: JSON.parse(dataLine.replace("data: ", "")),
  };
}
