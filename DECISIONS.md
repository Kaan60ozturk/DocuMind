# Decisions

Tradeoffs made during the build, in the spirit of "pick the simpler robust option and write it down".

1. **Synchronous ingestion in the upload request.** Parsing + embedding a typical document takes a few seconds; the UI shows a per-file spinner. Background jobs with progress events are a roadmap item, not a v1 need.

2. **`uvicorn --factory` instead of a module-level `app`.** A module-level app would require `GEMINI_API_KEY` just to *import* `app.main`, which would break offline tests. The factory also gives tests a clean injection point for fake providers.

3. **One `GeminiProvider` class implements both protocols.** Embeddings and chat share a client and retry logic. Splitting into two classes buys nothing until a second vendor exists.

4. **`embed_texts` has no document/query task-type distinction.** The protocol stays exactly as specced (`list[str] -> list[list[float]]`). Gemini supports task-type hints that can improve retrieval; adopting them is a provider-level change and lives on the roadmap.

5. **DOCX/TXT/MD count as one page.** Word processors have no stable page concept without rendering the document. Citations still point at the right file; PDFs keep real page numbers.

6. **Overlap is unit-aligned at natural boundaries, exact for hard cuts.** When chunks split on paragraphs/sentences, the carried context is whole trailing units up to `CHUNK_OVERLAP` chars (never splitting a sentence mid-way); only unstructured hard cuts share exactly `CHUNK_OVERLAP` characters. Chunks never exceed `CHUNK_SIZE`.

7. **SQLite via stdlib, connection per operation.** The registry sees a handful of queries per user action; a pooled ORM would be pure ceremony. Per-operation connections are trivially thread-safe.

8. **Chat errors arrive as SSE `error` events, not HTTP status codes.** Once streaming headers are sent the status is fixed, so mid-stream failures (e.g. Gemini rate limits) become a typed event with a user-safe message. Upload errors, which happen before any streaming, use real status codes (400/413/502).

9. **Question length enforced by Pydantic (422).** FastAPI's native validation with its standard error shape beats a hand-rolled 400 for one field; the UI also caps the textarea at 4,000 chars.

10. **Two additions to the specced file tree:** `frontend/src/main.tsx` (Vite requires an entry module) and `.dockerignore` (keeps `node_modules`/`.venv`/`data` out of the build context).

11. **Editable pip install inside Docker.** `pip install -e ./backend` keeps the package importable from `/app/backend`, so the app's relative path to `/app/frontend/dist` (static mount) works identically in dev and in the container.

12. **The empty-store message is static English.** It is served without calling the LLM (that is the point of the short-circuit), so it cannot adapt to the question's language. Real answers follow the prompt rule "answer in the same language as the user's question".

13. **Similarity below `MIN_SIMILARITY` still answers.** Retrieval always passes the excerpts through; the grounding prompt forces an honest "not found in the uploaded documents" when they're irrelevant. Scores are exposed in the `sources` payload so the UI (and a curious reviewer) can see exactly what the model saw. The threshold itself only flags low-confidence retrievals in the server log.

14. **Uploads are read in bounded chunks with an early size reject.** The declared size is used only to reject early, never to accept; reading stops the moment `MAX_FILE_MB` is exceeded, so an oversized body cannot balloon process memory. A separate cap on *extracted* text (5M chars) defuses decompression-bomb DOCX files that are small on the wire.

15. **History is clamped, not rejected.** Per-turn content over 4,000 chars is silently truncated server-side (a long earlier answer must never brick the conversation with a 422), the endpoint keeps only the last 6 turns, and the client only ever sends completed, successful question/answer pairs.

16. **The chat SSE generator has a last-resort catch-all.** Provider failures become typed `error` events inside the pipeline; anything else (vector store faults, genuine bugs) is caught at the endpoint boundary and still emits a terminal `error` event, because a silently dying stream is the worst possible client experience. Transport-level network failures (DNS, resets, timeouts) are retried like 5xx responses.

17. **Linux bind-mount ownership.** The container runs as a non-root user, and `docker compose` bind-mounts `./data`. On native Linux, a daemon-created mount dir would be root-owned, so the README's Docker path pre-creates `./data` as the invoking user (uid 1000 matches the image's first user in the common case). A named volume or entrypoint chown would be the heavier, fully general fix.
