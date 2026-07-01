/** Typed API client + a small SSE stream parser over fetch/ReadableStream. */

export interface DocumentInfo {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface Source {
  n: number;
  doc_id: string;
  filename: string;
  page: number;
  snippet: string;
  score: number;
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export type ChatEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'token'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function throwApiError(response: Response): Promise<never> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') detail = body.detail;
  } catch {
    // Response body was not JSON; keep the generic message.
  }
  throw new ApiError(detail, response.status);
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch('/api/documents');
  if (!response.ok) await throwApiError(response);
  return (await response.json()) as DocumentInfo[];
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch('/api/documents', { method: 'POST', body: form });
  if (!response.ok) await throwApiError(response);
  return (await response.json()) as DocumentInfo;
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) await throwApiError(response);
}

/**
 * POST the question and yield chat events as they stream in.
 * EventSource cannot POST, so this parses `data:` frames off a ReadableStream.
 */
export async function* streamChat(
  question: string,
  history: ChatTurn[],
): AsyncGenerator<ChatEvent> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  });
  if (!response.ok || !response.body) {
    await throwApiError(response);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let separator: number;
      while ((separator = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        for (const line of frame.split('\n')) {
          if (line.startsWith('data: ')) {
            yield JSON.parse(line.slice('data: '.length)) as ChatEvent;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
