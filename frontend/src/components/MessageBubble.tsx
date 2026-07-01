import type { ReactNode } from 'react';
import type { Message } from '../App';
import SourceChips from './SourceChips';

export default function MessageBubble({ message }: { message: Message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-indigo-500 px-4 py-3 text-sm leading-relaxed text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        <div
          className={`whitespace-pre-wrap rounded-2xl rounded-bl-md border px-4 py-3 text-sm leading-relaxed text-slate-200 ${
            message.error
              ? 'border-red-500/30 bg-red-500/10'
              : 'border-white/10 bg-ink-raised'
          }`}
        >
          {message.content ? renderRichText(message.content) : null}
          {message.streaming && <Caret />}
          {message.error && (
            <p className={`text-red-300 ${message.content ? 'mt-2' : ''}`}>
              {message.error} <span className="text-red-400/70">Please try again.</span>
            </p>
          )}
        </div>
        {message.sources.length > 0 && <SourceChips sources={message.sources} />}
      </div>
    </div>
  );
}

// Matches **bold**, `code`, and [n] citation markers.
const INLINE_TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+\])/g;

function renderRichText(text: string): ReactNode[] {
  return text.split(INLINE_TOKEN).map((part, index) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return (
        <strong key={index} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (/^`[^`]+`$/.test(part)) {
      return (
        <code
          key={index}
          className="rounded bg-white/10 px-1 py-0.5 font-mono text-[0.85em] text-indigo-200"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (/^\[\d+\]$/.test(part)) {
      return (
        <sup
          key={index}
          className="mx-0.5 inline-flex items-center rounded bg-indigo-500/20 px-1 text-[0.75em] font-semibold text-indigo-300"
        >
          {part}
        </sup>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

function Caret() {
  return <span className="ml-0.5 inline-block animate-pulse text-indigo-400">▍</span>;
}
