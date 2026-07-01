import { useRef, useState, type DragEvent } from 'react';
import { formatBytes, type DocumentInfo } from '../lib/api';

const ACCEPTED = '.pdf,.docx,.txt,.md';

interface SidebarProps {
  documents: DocumentInfo[];
  uploading: string[];
  open: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
}

export default function Sidebar({
  documents,
  uploading,
  open,
  onClose,
  onUpload,
  onDelete,
}: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 transform flex-col border-r border-white/10 bg-ink-surface transition-transform duration-200 md:static md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-3 px-5 pb-4 pt-5">
          <Logo />
          <div>
            <h1 className="text-base font-semibold tracking-tight text-white">DocuMind</h1>
            <p className="text-xs text-slate-400">Chat with your documents</p>
          </div>
          <button
            type="button"
            aria-label="Close sidebar"
            onClick={onClose}
            className="focus-ring ml-auto rounded-lg p-1.5 text-slate-400 hover:bg-white/5 md:hidden"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="px-4">
          <UploadDropzone onUpload={onUpload} />
        </div>

        <div className="mt-4 flex-1 overflow-y-auto px-4 pb-4">
          <h2 className="px-1 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Documents
          </h2>

          {uploading.map((name, index) => (
            <div
              key={`${name}-${index}`}
              className="mb-2 flex items-center gap-3 rounded-2xl border border-white/10 bg-ink-raised px-3 py-2.5"
            >
              <Spinner />
              <div className="min-w-0">
                <p className="truncate text-sm text-slate-300">{name}</p>
                <p className="text-xs text-slate-500">Processing…</p>
              </div>
            </div>
          ))}

          {documents.length === 0 && uploading.length === 0 && (
            <p className="px-1 text-sm leading-relaxed text-slate-500">
              No documents yet. Upload a file to start asking questions.
            </p>
          )}

          <ul className="space-y-2">
            {documents.map((document) => (
              <DocumentRow key={document.id} document={document} onDelete={onDelete} />
            ))}
          </ul>
        </div>

        <div className="border-t border-white/10 px-5 py-3">
          <p className="text-[11px] text-slate-500">
            Answers are grounded in your documents with page-level citations.
          </p>
        </div>
      </aside>
    </>
  );
}

function UploadDropzone({ onUpload }: { onUpload: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setDragging(false);
    onUpload(Array.from(event.dataTransfer.files));
  };

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`focus-ring flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-4 py-6 text-center transition-colors ${
          dragging
            ? 'border-indigo-400 bg-indigo-500/10'
            : 'border-white/15 bg-ink-raised/50 hover:border-indigo-500/60 hover:bg-ink-raised'
        }`}
      >
        <UploadIcon />
        <span className="text-sm font-medium text-slate-200">
          Drop files here <span className="text-slate-500">or click to browse</span>
        </span>
        <span className="text-xs text-slate-500">PDF, DOCX, TXT, MD · max 20 MB</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={(event) => {
          if (event.target.files) onUpload(Array.from(event.target.files));
          event.target.value = ''; // allow re-uploading the same file
        }}
      />
    </>
  );
}

function DocumentRow({
  document,
  onDelete,
}: {
  document: DocumentInfo;
  onDelete: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);

  return (
    <li className="group rounded-2xl border border-white/10 bg-ink-raised px-3 py-2.5">
      {confirming ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-slate-300">Delete this document?</span>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => onDelete(document.id)}
              className="focus-ring rounded-lg bg-red-500/20 px-2.5 py-1 text-xs font-medium text-red-300 hover:bg-red-500/30"
            >
              Delete
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="focus-ring rounded-lg px-2.5 py-1 text-xs text-slate-400 hover:bg-white/5"
            >
              Keep
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-3">
          <FileIcon />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-200" title={document.filename}>
              {document.filename}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              {document.pages} {document.pages === 1 ? 'page' : 'pages'} · {document.chunks} chunks
              · {formatBytes(document.size_bytes)}
            </p>
          </div>
          <button
            type="button"
            aria-label={`Delete ${document.filename}`}
            onClick={() => setConfirming(true)}
            className="focus-ring rounded-lg p-1.5 text-slate-500 opacity-0 transition-opacity hover:bg-white/5 hover:text-red-300 focus-visible:opacity-100 group-hover:opacity-100"
          >
            <TrashIcon />
          </button>
        </div>
      )}
    </li>
  );
}

function Logo() {
  return (
    <svg width="34" height="34" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="5" y="3" width="19" height="24" rx="4" className="fill-indigo-500" />
      <path
        d="M10 10h9M10 15h9M10 20h5"
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <circle cx="23.5" cy="23.5" r="6.5" className="fill-ink-surface" />
      <path
        d="M23.5 19.4l1.2 2.9 2.9 1.2-2.9 1.2-1.2 2.9-1.2-2.9-2.9-1.2 2.9-1.2z"
        className="fill-indigo-300"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 shrink-0 animate-spin text-indigo-400"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-indigo-400" aria-hidden="true">
      <path
        d="M12 16V4m0 0L7 9m5-5l5 5M4 20h16"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0 text-slate-500" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 7h16M10 11v6m4-6v6M6 7l1 13a1 1 0 0 0 1 .9h8a1 1 0 0 0 1-.9L18 7M9 7V4.8A.8.8 0 0 1 9.8 4h4.4a.8.8 0 0 1 .8.8V7"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
