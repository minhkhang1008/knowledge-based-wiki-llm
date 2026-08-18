# Frontend requirements and integration guide

This document is the implementation contract for the first product UI. The frontend is not included in this repository yet.

## 1. Product scope

The UI must let a user:

1. See the current knowledge-base status.
2. Upload and ingest a supported document.
3. Browse, inspect, search, and delete articles.
4. Run semantic search and inspect the matching source chunks.
5. Ask questions and see answers with citations.
6. Distinguish an empty result from an AI or server failure.

Authentication, user roles, collaborative editing, and public sharing are outside the MVP scope.

## 2. Required screens

### Dashboard

Display live values from `GET /api/stats`:

- Total articles.
- Total indexed chunks.
- Total QA interactions.

Also show quick links to Documents, Search, and Ask. Do not render invented sample metrics when the API is unavailable.

### Documents

The page must contain:

- A file picker or drop zone.
- An optional title input.
- The formats and file-size limit returned by the API.
- Upload progress or a clear processing state.
- The number of chunks created after a successful ingest.
- Article search by title.
- Article list with title, source filename, format, and updated time.
- Article detail with converted Markdown content.
- Delete confirmation that explains both the SQLite article and Chroma chunks are removed.

The UI must fetch supported formats. Never hardcode a list of file extensions.

### Semantic search

Submit a minimum two-character query to `POST /api/search`. Each result must show:

- Chunk text.
- Source filename.
- Page or slide number when present.
- Similarity information when `distance` is present.

If the result list is empty, show a no-context state. Do not report it as a server error.

### Ask

Submit a minimum five-character question to `POST /api/qa/ask`. The page must:

- Preserve local conversation history and send recent messages back to the API.
- Display the answer exactly as returned.
- Display every returned source under the answer.
- Show an explicit no-context state when `no_answer_reason` is `insufficient_context`.
- Keep the user's question visible when a request fails so it can be retried.

Citation labels such as `[S1]` in an answer map to the source order returned by the API.

## 3. API conventions

Local API origin: `http://localhost:8000`.

All main endpoints use this envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Human-readable message",
  "error": null
}
```

Error responses may expose a string `detail`, an object `detail`, or the standard envelope with `error.detail`. The frontend error parser must support all three during the migration to one error format.

### Health

```http
GET /health
```

Success:

```json
{"status":"ok"}
```

Use this for an optional connection indicator. Do not poll more often than once every 30 seconds.

### Supported ingest formats

```http
GET /api/v1/articles/supported-formats
```

Example:

```json
{
  "success": true,
  "data": {
    "extensions": [".docx", ".pptx", ".xlsm", ".xlsx"],
    "max_upload_size_mb": 25
  },
  "message": "Lấy định dạng ingest thành công",
  "error": null
}
```

PDF and image extensions will appear automatically after their chunkers are registered. The frontend must update its `accept` attribute and helper text from this response.

### Upload and ingest

```http
POST /api/v1/articles/upload
Content-Type: multipart/form-data
```

Fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | file | yes | Must use a currently supported extension |
| `title` | string | no | The filename stem is used when omitted |

Success status: `201`.

```json
{
  "success": true,
  "data": {
    "article": {
      "id": "uuid",
      "document_id": "sha256",
      "title": "Employee policy",
      "content": "# Employee policy\n...",
      "source_file": "employee-policy.docx",
      "created_at": "2026-08-18T08:00:00Z",
      "updated_at": "2026-08-18T08:00:00Z"
    },
    "document_id": "sha256",
    "chunk_count": 7
  },
  "message": "Ingest tài liệu thành công",
  "error": null
}
```

Expected errors:

| Status | Meaning | UI treatment |
| --- | --- | --- |
| `413` | File is larger than the configured limit | Keep the selected filename and show the limit |
| `415` | Format does not have both converter and chunker | Refresh supported formats and ask for another file |
| `422` | File was accepted but produced no usable chunks | Explain that content could not be extracted |
| `500` | Conversion, embedding, SQLite, or Chroma failed | Show retry; the service attempts to roll back partial writes |
| `502` | AI returned an invalid response or empty embedding | Show retry and keep the selected file or question |
| `503` | Ollama is unavailable | Tell the operator to start Ollama or pull the configured model |
| `504` | AI request timed out | Show retry without clearing user input |

`POST /api/v1/articles/upload-presentation` remains as a deprecated compatibility endpoint. New frontend code must use `/upload`.

### List articles

```http
GET /api/articles?skip=0&limit=20&search=policy
```

The `data` value is an array of article objects. `search` filters by title. The API caps `limit` at 100.

### Read, update, and delete an article

```http
GET /api/articles/{article_id}
PUT /api/articles/{article_id}
DELETE /api/articles/{article_id}
```

The update body requires `title`, `content`, and `source_file`. Updating content rebuilds the article's vectors. Deleting removes both the database record and all matching Chroma chunks.

### Semantic search

```http
POST /api/search
Content-Type: application/json

{"query":"How many annual leave days are available?"}
```

Success data:

```json
{
  "results": [
    {
      "text": "Employees receive 12 annual leave days.",
      "article_id": "uuid",
      "source_file": "employee-policy.docx",
      "page_number": null,
      "distance": 0.42
    }
  ]
}
```

Smaller distance means closer semantic similarity. The frontend should not invent a percentage unless the team defines and validates that mapping.

### Ask with conversation history

```http
POST /api/qa/ask
Content-Type: application/json
```

```json
{
  "question": "How many annual leave days are available?",
  "chat_history": [
    {"role":"user","content":"Tell me about the employee policy."},
    {"role":"assistant","content":"What part would you like to know?"}
  ]
}
```

Success data:

```json
{
  "answer": "Employees receive 12 annual leave days [S1].",
  "sources": [
    {
      "text": "Employees receive 12 annual leave days.",
      "article_id": "uuid",
      "source_file": "employee-policy.docx",
      "page_number": null,
      "distance": 0.42
    }
  ],
  "no_answer_reason": null
}
```

No-context success:

```json
{
  "answer": "Tôi không tìm thấy thông tin này trong tài liệu.",
  "sources": [],
  "no_answer_reason": "insufficient_context"
}
```

### Statistics

```http
GET /api/stats
```

```json
{
  "success": true,
  "data": {
    "total_articles": 8,
    "total_qa_logs": 12,
    "total_indexed_chunks": 47
  },
  "message": "Lấy stats thành công",
  "error": null
}
```

Values above are only a response-shape example. Always render the live response.

## 4. UI state requirements

Every network-backed surface must implement:

| State | Required behavior |
| --- | --- |
| Initial loading | Skeleton matching the final content layout |
| Empty | Explain how the user can populate or broaden the result |
| Success | Render the response without invented fallback data |
| Validation error | Keep form input and show the error next to the field |
| Server error | Keep user work, show retry, and include a short actionable message |
| Ollama offline | Separate AI availability from general API availability |
| Processing | Disable duplicate submission and show what is being processed |

Destructive actions require confirmation. Buttons, fields, dialogs, and navigation must be keyboard accessible and have visible focus states.

## 5. Suggested frontend structure

The team may use React, Vue, or another framework. Keep API concerns separate from views:

```text
src/
  api/
    client
    articles
    search
    qa
    stats
  components/
    async states
    source viewer
    upload field
  pages/
    dashboard
    documents
    search
    ask
  types/
    api contracts
```

Recommended client behavior:

- Configure the API origin with an environment variable.
- Do not send a manual `Content-Type` header for `FormData`.
- Use request cancellation when a view unmounts or a new search replaces an old one.
- Keep chat history bounded on the client; the backend also limits history.
- Refresh Articles and Stats after successful upload or deletion.
- Fetch supported formats when the Documents page opens.

## 6. Acceptance checklist

- [ ] A clean frontend can connect to the API using only environment configuration.
- [ ] Supported extensions come from the API.
- [ ] Upload shows processing and cannot be submitted twice.
- [ ] A successful upload appears in Articles and changes Stats.
- [ ] A failed index operation does not produce a visible partial article.
- [ ] Search displays source filename and chunk text.
- [ ] QA displays citation labels and matching sources in the same order.
- [ ] No-context is different from an error.
- [ ] Deleting an article removes it from Articles and future search results.
- [ ] The UI works at 360 px width and with keyboard-only navigation.
- [ ] Light and dark themes, if both are implemented, meet WCAG AA contrast.
- [ ] No real API response is replaced by mock production data.
