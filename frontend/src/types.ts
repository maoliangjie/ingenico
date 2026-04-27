export type SourceSnippet = {
  source: string;
  file_name: string;
  content: string;
  score?: number | null;
};

export type HealthResponse = {
  status: string;
  ready: boolean;
  document_count: number;
  chunk_count: number;
  fingerprint?: string | null;
  redis_ready: boolean;
  upload_count: number;
  tool_count: number;
  startup_error?: string | null;
};

export type ToolCall = {
  tool_name: string;
  status: string;
  grounding_type: string;
  arguments: Record<string, unknown>;
  result_preview: string;
  payload?: Record<string, unknown> | unknown[] | string | null;
};

export type ChatResponse = {
  session_id: string;
  answer: string;
  sources: SourceSnippet[];
  cache_hit: boolean;
  tool_calls: ToolCall[];
};

export type UploadRecord = {
  file_id: string;
  file_name: string;
  stored_name: string;
  status: string;
  source_path: string;
  updated_at: string;
};

export type UploadListResponse = {
  files: UploadRecord[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  cacheHit?: boolean;
};
