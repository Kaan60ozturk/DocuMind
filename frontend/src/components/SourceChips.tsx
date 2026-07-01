import { useState } from 'react';
import type { Source } from '../lib/api';

/** Expandable citation chips shown under an assistant message. */
export default function SourceChips({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const active = sources.find((source) => source.n === expanded);

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source) => (
          <button
            key={source.n}
            type="button"
            aria-expanded={expanded === source.n}
            onClick={() => setExpanded(expanded === source.n ? null : source.n)}
            className={`focus-ring inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors ${
              expanded === source.n
                ? 'border-indigo-500/60 bg-indigo-500/15 text-indigo-200'
                : 'border-white/10 bg-ink-raised text-slate-400 hover:border-indigo-500/40 hover:text-slate-200'
            }`}
          >
            <span className="font-semibold text-indigo-300">[{source.n}]</span>
            <span className="max-w-[160px] truncate">{source.filename}</span>
            <span className="text-slate-500">·</span>
            <span>p.{source.page}</span>
          </button>
        ))}
      </div>

      {active && (
        <div className="mt-2 rounded-2xl border border-white/10 bg-ink-surface p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-xs font-medium text-slate-300">
              {active.filename} — page {active.page}
            </p>
            <span className="shrink-0 rounded-full bg-indigo-500/15 px-2 py-0.5 text-[11px] font-medium text-indigo-300">
              {Math.round(active.score * 100)}% match
            </span>
          </div>
          <p className="mt-2 border-l-2 border-indigo-500/40 pl-3 text-xs leading-relaxed text-slate-400">
            “{active.snippet.trim()}
            {active.snippet.length >= 300 ? '…' : ''}”
          </p>
        </div>
      )}
    </div>
  );
}
