import { useCallback, useEffect, useRef, useState } from 'react';
import Chat from './components/Chat';
import Sidebar from './components/Sidebar';
import ToastStack, { type ToastItem } from './components/Toast';
import {
  ApiError,
  deleteDocument,
  fetchDocuments,
  streamChat,
  uploadDocument,
  type ChatTurn,
  type DocumentInfo,
  type Source,
} from './lib/api';

export interface UserMessage {
  role: 'user';
  content: string;
}

export interface AssistantMessage {
  role: 'assistant';
  content: string;
  sources: Source[];
  streaming: boolean;
  error?: string;
}

export type Message = UserMessage | AssistantMessage;

const MAX_HISTORY_TURNS = 6;
const MAX_TURN_CHARS = 4000; // mirrors the backend's per-turn limit

/** Completed, successful question/answer pairs only — a failed turn
 *  contributes nothing (keeping its question would confuse the model). */
function buildHistory(messages: Message[]): ChatTurn[] {
  const turns: ChatTurn[] = [];
  for (let i = 0; i < messages.length - 1; i++) {
    const question = messages[i];
    const answer = messages[i + 1];
    if (
      question.role === 'user' &&
      answer.role === 'assistant' &&
      answer.content &&
      !answer.error &&
      !answer.streaming
    ) {
      turns.push({ role: 'user', content: question.content.slice(0, MAX_TURN_CHARS) });
      turns.push({ role: 'assistant', content: answer.content.slice(0, MAX_TURN_CHARS) });
    }
  }
  return turns.slice(-MAX_HISTORY_TURNS);
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastId = useRef(0);

  const addToast = useCallback((message: string, kind: ToastItem['kind'] = 'error') => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, message, kind }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const refreshDocuments = useCallback(async () => {
    try {
      setDocuments(await fetchDocuments());
    } catch (error) {
      addToast(
        error instanceof ApiError
          ? error.message
          : 'Could not reach the server. Is the backend running?',
      );
    }
  }, [addToast]);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  const handleUpload = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        setUploading((prev) => [...prev, file.name]);
        try {
          const document = await uploadDocument(file);
          setDocuments((prev) => [document, ...prev]);
          addToast(`Added ${document.filename} (${document.chunks} chunks)`, 'info');
        } catch (error) {
          addToast(error instanceof ApiError ? error.message : `Could not upload ${file.name}.`);
        } finally {
          setUploading((prev) => {
            const index = prev.indexOf(file.name);
            return index === -1 ? prev : prev.filter((_, i) => i !== index);
          });
        }
      }
    },
    [addToast],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteDocument(id);
        setDocuments((prev) => prev.filter((document) => document.id !== id));
        addToast('Document removed.', 'info');
      } catch (error) {
        addToast(error instanceof ApiError ? error.message : 'Could not delete the document.');
      }
    },
    [addToast],
  );

  const updateLastAssistant = useCallback(
    (update: (message: AssistantMessage) => AssistantMessage) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          const message = next[i];
          if (message.role === 'assistant') {
            next[i] = update(message);
            break;
          }
        }
        return next;
      });
    },
    [],
  );

  const handleSend = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      if (!question || isStreaming) return;

      const history = buildHistory(messages);

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: '', sources: [], streaming: true },
      ]);
      setIsStreaming(true);

      try {
        for await (const event of streamChat(question, history)) {
          if (event.type === 'sources') {
            updateLastAssistant((message) => ({ ...message, sources: event.sources }));
          } else if (event.type === 'token') {
            updateLastAssistant((message) => ({
              ...message,
              content: message.content + event.text,
            }));
          } else if (event.type === 'error') {
            updateLastAssistant((message) => ({ ...message, error: event.message }));
            addToast(event.message);
          }
        }
      } catch (error) {
        const message =
          error instanceof ApiError
            ? error.message
            : 'The connection was interrupted. Please try again.';
        updateLastAssistant((assistant) => ({ ...assistant, error: message }));
        addToast(message);
      } finally {
        updateLastAssistant((message) => ({ ...message, streaming: false }));
        setIsStreaming(false);
      }
    },
    [addToast, isStreaming, messages, updateLastAssistant],
  );

  return (
    <div className="flex h-full overflow-hidden">
      <Sidebar
        documents={documents}
        uploading={uploading}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-white/10 px-4 py-3 md:hidden">
          <button
            type="button"
            aria-label="Open sidebar"
            onClick={() => setSidebarOpen(true)}
            className="focus-ring rounded-lg p-2 text-slate-300 hover:bg-white/5"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M4 6h16M4 12h16M4 18h16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <span className="text-sm font-semibold text-white">DocuMind</span>
        </header>

        <Chat
          messages={messages}
          disabled={isStreaming}
          hasDocuments={documents.length > 0}
          onSend={(question) => void handleSend(question)}
        />
      </main>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
