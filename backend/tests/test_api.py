"""API contract tests: upload -> list -> chat (SSE) -> delete, plus error paths."""

import json

DOC_TEXT = (
    "DocuMind supports PDF, DOCX, TXT and Markdown uploads. "
    "The retrieval pipeline uses cosine similarity over Chroma. " * 4
)
DOC_BYTES = DOC_TEXT.encode("utf-8")


def _upload(client, name="guide.txt", content=DOC_BYTES):
    return client.post("/api/documents", files={"file": (name, content, "text/plain")})


def _read_sse_events(response) -> list[dict]:
    events = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_list_chat_delete_flow(client, app, fake_llm):
    # Upload
    response = _upload(client)
    assert response.status_code == 201
    document = response.json()
    assert document["filename"] == "guide.txt"
    assert document["status"] == "ready"
    assert document["pages"] == 1
    assert document["chunks"] > 0
    assert document["size_bytes"] == len(DOC_BYTES)

    # The raw file is stored under a UUID name, not the user-supplied one.
    uploads = list(app.state.settings.uploads_dir.iterdir())
    assert len(uploads) == 1
    assert uploads[0].name == f"{document['id']}.txt"

    # List
    listed = client.get("/api/documents").json()
    assert [d["id"] for d in listed] == [document["id"]]

    # Chat: SSE order must be sources -> token(s) -> done
    with client.stream(
        "POST",
        "/api/chat",
        json={"question": "What formats are supported?", "history": []},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _read_sse_events(response)

    assert events[0]["type"] == "sources"
    assert len(events[0]["sources"]) > 0
    source = events[0]["sources"][0]
    assert source["filename"] == "guide.txt"
    assert source["page"] == 1
    assert 0.0 <= source["score"] <= 1.0
    assert source["snippet"]

    token_events = [event for event in events[1:-1] if event["type"] == "token"]
    assert len(token_events) == len(fake_llm.tokens)
    assert events[-1] == {"type": "done"}

    # The prompt sent to the LLM contains the excerpts and the question.
    assert len(fake_llm.prompts) == 1
    assert "guide.txt" in fake_llm.prompts[0]
    assert "What formats are supported?" in fake_llm.prompts[0]

    # Delete
    response = client.delete(f"/api/documents/{document['id']}")
    assert response.status_code == 204
    assert client.get("/api/documents").json() == []
    assert app.state.vectorstore.count() == 0
    assert list(app.state.settings.uploads_dir.iterdir()) == []


def test_chat_with_empty_store_never_calls_llm(client, fake_llm, fake_embedder):
    with client.stream(
        "POST", "/api/chat", json={"question": "Anything?", "history": []}
    ) as response:
        events = _read_sse_events(response)

    assert events[0] == {"type": "sources", "sources": []}
    assert events[1]["type"] == "token"
    assert "upload" in events[1]["text"].lower()
    assert events[-1] == {"type": "done"}
    assert fake_llm.prompts == []
    assert fake_embedder.calls == []


def test_upload_rejects_unsupported_extension(client):
    response = _upload(client, name="malware.exe", content=b"binary")
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_oversized_file(client, settings):
    oversized = b"x" * (settings.max_file_bytes + 1)
    response = _upload(client, name="big.txt", content=oversized)
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = _upload(client, name="empty.txt", content=b"")
    assert response.status_code == 400


def test_delete_unknown_document_returns_404(client):
    response = client.delete("/api/documents/does-not-exist")
    assert response.status_code == 404


def test_chat_rejects_overlong_question(client):
    response = client.post("/api/chat", json={"question": "x" * 4001, "history": []})
    assert response.status_code == 422


def test_history_is_truncated_server_side(client, fake_llm):
    _upload(client)
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn-{i}"} for i in range(10)
    ]
    with client.stream(
        "POST", "/api/chat", json={"question": "What is DocuMind?", "history": history}
    ) as response:
        _read_sse_events(response)

    prompt = fake_llm.prompts[-1]
    # Only the last 6 turns may appear in the prompt.
    assert "turn-3" not in prompt
    assert "turn-4" in prompt
    assert "turn-9" in prompt
