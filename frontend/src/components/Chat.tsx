import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import type { Message } from '../App';
import MessageBubble from './MessageBubble';

const EXAMPLE_QUESTIONS = [
  'What is this document about?',
  'Summarize the key points with citations',
  'What conclusions does the author draw?',
];

interface ChatProps {
  messages: Message[];
  disabled: boolean;
  hasDocuments: boolean;
  onSend: (question: string) => void;
}

export default function Chat({ messages, disabled, hasDocuments, onSend }: ChatProps) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    // Follow the stream only while the user is already near the bottom;
    // never yank them back down while they are reading older messages.
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    if (distanceFromBottom < 160) element.scrollTop = element.scrollHeight;
  }, [messages]);

  const submit = (question: string) => {
    if (disabled || !question.trim()) return;
    onSend(question);
    setDraft('');
    const textarea = textareaRef.current;
    if (textarea) textarea.style.height = 'auto';
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // isComposing: Enter inside an IME composition confirms the characters,
    // it must not submit the message.
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(draft);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8">
          {messages.length === 0 ? (
            <EmptyState hasDocuments={hasDocuments} onPick={submit} />
          ) : (
            messages.map((message, index) => <MessageBubble key={index} message={message} />)
          )}
        </div>
      </div>

      <div className="border-t border-white/10 bg-ink/95 px-4 py-4 backdrop-blur">
        <div className="mx-auto flex w-full max-w-3xl items-end gap-3">
          <textarea
            ref={textareaRef}
            value={draft}
            rows={1}
            maxLength={4000}
            disabled={disabled}
            placeholder={
              hasDocuments ? 'Ask about your documents…' : 'Upload a document to get started…'
            }
            onChange={(event) => {
              setDraft(event.target.value);
              const textarea = event.target;
              textarea.style.height = 'auto';
              textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
            }}
            onKeyDown={handleKeyDown}
            className="focus-ring max-h-[200px] min-h-[48px] flex-1 resize-none rounded-2xl border border-white/10 bg-ink-raised px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 disabled:opacity-60"
          />
          <button
            type="button"
            aria-label="Send question"
            disabled={disabled || !draft.trim()}
            onClick={() => submit(draft)}
            className="focus-ring flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-500 text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-slate-500"
          >
            {disabled ? <PendingDots /> : <SendIcon />}
          </button>
        </div>
        <p className="mx-auto mt-2 w-full max-w-3xl text-[11px] text-slate-600">
          Enter to send · Shift+Enter for a new line
        </p>
      </div>
    </div>
  );
}

function EmptyState({
  hasDocuments,
  onPick,
}: {
  hasDocuments: boolean;
  onPick: (question: string) => void;
}) {
  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-ink-raised">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" className="text-indigo-400" aria-hidden="true">
          <path
            d="M8 10h8m-8 4h5m-8.6 5.1L4 21l1.2-3.6A8 8 0 1 1 8.4 19.1z"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <div>
        <h2 className="text-lg font-semibold text-white">Ask your documents anything</h2>
        <p className="mt-1 max-w-md text-sm leading-relaxed text-slate-400">
          {hasDocuments
            ? 'Every answer is grounded in your uploads and cites the exact file and page.'
            : 'Upload a PDF, DOCX, TXT or Markdown file in the sidebar, then ask away.'}
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {EXAMPLE_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onPick(question)}
            className="focus-ring rounded-full border border-white/10 bg-ink-raised px-4 py-2 text-sm text-slate-300 transition-colors hover:border-indigo-500/60 hover:text-white"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4.5 12L3 4l18 8-18 8 1.5-8zm0 0h8"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PendingDots() {
  return (
    <span className="flex gap-1" aria-hidden="true">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
    </span>
  );
}
