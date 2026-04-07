# Telegram Second Brain MVP

A minimal, production-ready MVP where you can:

- capture thoughts via Telegram,
- store them in Supabase Postgres,
- retrieve them later with semantic search (embeddings),
- and receive reminders,
- and lock graph/search access behind a Telegram-issued token.

This project is intentionally simple so you can learn and extend it.

## Why FastAPI (instead of Node.js) for this MVP

- FastAPI gives typed request/response models out of the box, which is great for learning backend design.
- Python has strong AI ecosystem support (embedding and LLM APIs are straightforward).
- Scheduler + webhook + DB logic can stay in one small codebase.
- You still use standard web concepts (HTTP, JSON, SQL) that transfer to any stack.

## Architecture

```text
Telegram User
   |
   v
Telegram Bot API
   |
   v  (webhook)
FastAPI backend (app/main.py)
   |----> Postgres (Supabase)
   |         |-- messages
   |         |-- embeddings (pgvector)
   |         |-- reminders
   |
  |----> Embedding API (Gemini via OpenAI-compatible endpoint)
   |
   '---> APScheduler job (every 1 minute) -> checks due reminders -> sends Telegram message
```

## Project Structure

```text
Kortex/
  app/
    __init__.py
    ai.py
    config.py
    db.py
    main.py
    models.py
    routes.py
    scheduler.py
    telegram_api.py
    telegram_handlers.py
    services/
      __init__.py
      messages_service.py
      reminders_service.py
  scripts/
    set_webhook.py
  sql/
    schema.sql
  .env.example
  .gitignore
  render.yaml
  requirements.txt
  README.md
```

### File-by-file purpose

- `app/config.py`: Loads env variables into a typed settings object.
- `app/db.py`: Creates and manages Postgres connection pool.
- `app/models.py`: Pydantic request/response schemas for API safety.
- `app/ai.py`: Optional text cleanup + embedding generation.
- `app/services/messages_service.py`: Message insert + embedding insert + semantic search SQL.
- `app/services/reminders_service.py`: Create/list reminders + fetch due reminders + mark sent.
- `app/telegram_api.py`: Direct Telegram Bot API calls (`sendMessage`, callback ack).
- `app/telegram_handlers.py`: Logic for incoming Telegram messages and reminder button clicks.
- `app/scheduler.py`: Cron-like background job every minute.
- `app/routes.py`: Auth-protected API endpoints for message ingestion, search, reminders, and graph access.
- `app/main.py`: FastAPI app, startup/shutdown lifecycle, webhook route.
- `sql/schema.sql`: Full database schema + indexes.
- `scripts/set_webhook.py`: Helper script to point Telegram webhook to your deployed backend.
- `render.yaml`: Optional one-click Render configuration.

## Step-by-step implementation

## Step 1: Telegram bot setup

1. Open Telegram and chat with BotFather.
2. Run `/newbot` and follow prompts.
3. Save the bot token.
4. Put it in `.env` as `TELEGRAM_BOT_TOKEN`.

Why this matters:
The bot token is your app identity with Telegram. Without webhook registration, Telegram cannot deliver user messages to your backend.

## Step 2: Backend server setup

### Install and run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Key backend entry point: `app/main.py`

- `lifespan` starts DB pool + scheduler when app boots.
- `POST /telegram/webhook` receives Telegram updates.
- `GET /health` confirms service is alive.

Why this matters:
A clean app lifecycle prevents hidden bugs like DB connections leaking or scheduler starting multiple times.

## Step 3: Database schema (Supabase)

Run the SQL in `sql/schema.sql` inside Supabase SQL Editor.

### Tables

1. `messages`

- `id`: unique primary key.
- `telegram_user_id`: owner of the note.
- `chat_id`: where reminders should be sent.
- `message_text`: original user text.
- `cleaned_text`: optional cleaned version used for embeddings.
- `created_at`: creation timestamp.

2. `embeddings`

- `message_id`: links one embedding per message.
- `embedding vector(1536)`: numeric vector from embedding model.

3. `reminders`

- `message_id`: which message to remind about.
- `remind_at`: when it should fire.
- `status`: `pending/sent/cancelled`.
- `sent_at`: actual delivery time.

Why split messages and embeddings:

- Keeps raw content and vector math concerns separate.
- Easier to re-embed later if you change embedding model.

## Step 4: Message storage flow

When a Telegram message arrives (`app/telegram_handlers.py`):

1. Read text and user/chat IDs.
2. Call `create_message_and_embedding(...)`.
3. Save message in `messages`.
4. Generate embedding and save in `embeddings`.
5. Reply with reminder options.

Reminder buttons:

- Tomorrow
- Next week
- No

Why this matters:
This pattern gives immediate capture and gently prompts the user for reminder intent while context is fresh.

## Step 5: Embedding generation

Code lives in `app/ai.py`:

```python
response = client.embeddings.create(model=settings.embedding_model, input=text)
embedding = response.data[0].embedding
```

What embeddings are:

- An embedding is a list of numbers representing meaning.
- Similar meanings are close together in vector space.

Example intuition:

- “Build AI startup idea” and “new machine learning business concept” get nearby vectors.
- Keyword search might miss this if exact words differ.

Why this matters:
Embeddings let you search by intent/meaning, not only exact words.

## Step 6: Semantic search

Search endpoint: `GET /search?q=ideas about ai&limit=5` with `Authorization: Bearer <token>`

SQL logic in `messages_service.py`:

- Convert query text -> query embedding.
- Compute distance with `<=>` (cosine distance in pgvector).
- Order by smallest distance (most similar first).
- Return top-k rows.

Formula used conceptually:

$$
\text{similarity} = 1 - \text{cosine\_distance}(q, d)
$$

Why better than keyword search:

- Keyword: depends on exact words.
- Semantic: finds conceptually related notes even with different wording.

## Step 7: Reminder system

Scheduler in `app/scheduler.py` runs every minute:

1. Query pending reminders where `remind_at <= NOW()`.
2. Send Telegram message.
3. Mark reminder as `sent`.

Why this matters:
The `status` update avoids duplicate reminder sends.

## API design

### `POST /message`

Manual ingestion (for testing without Telegram)

Request:

```json
{
  "user_id": 123,
  "chat_id": 123,
  "text": "Read paper on retrieval-augmented generation"
}
```

Response:

```json
{
  "id": "uuid",
  "user_id": 123,
  "chat_id": 123,
  "text": "Read paper on retrieval-augmented generation",
  "created_at": "2026-04-07T10:00:00Z"
}
```

### `GET /search`

Requires `Authorization: Bearer <token>`.

Example:
`/search?q=ideas about ai&limit=3`

Response:

```json
[
  {
    "message_id": "uuid",
    "text": "Build AI note summarizer",
    "created_at": "2026-04-01T08:00:00Z",
    "similarity": 0.86
  }
]
```

### `GET /reminders`

Requires `Authorization: Bearer <token>`.

Example:
`/reminders`

Response:

```json
[
  {
    "id": "uuid",
    "message_id": "uuid",
    "remind_at": "2026-04-08T10:00:00Z",
    "status": "pending"
  }
]
```

## Telegram integration details

Webhook route: `POST /telegram/webhook`

- Telegram sends updates to your backend.
- Message updates trigger note capture + reminder prompt.
- Callback updates (button clicks) trigger reminder creation.

Security:

- Telegram includes `X-Telegram-Bot-Api-Secret-Token` header.
- We verify it in `verify_secret(...)`.
- Graph, search, reminders, and manual message ingestion now require a signed Telegram access token.

Why this matters:
Without secret verification, anyone could fake webhook requests to your API.

## Deployment guide (Render + Supabase)

1. Push this project to GitHub.
2. Create a Supabase project.
3. In Supabase SQL editor, run `sql/schema.sql`.
4. In Supabase project settings, copy pooled `DATABASE_URL`.
5. On Render:

- Create new Web Service from repo.
- Use Python runtime.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

6. Add env vars from `.env.example`.
7. Set `PUBLIC_BASE_URL` to your Render URL.
8. Run webhook script once:

```bash
python scripts/set_webhook.py
```

9. Open health check:
   `https://your-service.onrender.com/health`

If it returns `{"ok": true}`, your backend is live.

## Low-cost notes

- Supabase free tier for Postgres + pgvector.
- Render free tier for backend (may sleep when idle).
- `text-embedding-004` is a good default for Gemini-backed
- Access control is stateless, so no extra auth table is needed for the MVP.semantic search.
- Optional cleanup call can be disabled to reduce AI costs.

## Learning notes (backend + AI)

- FastAPI gives typed contracts, so your API is self-documenting and safer.
- Using one SQL DB for both transactional and vector data simplifies architecture.
- Scheduler decouples reminder delivery from user request handling.
- Semantic search is retrieval by meaning, which is core to “second brain” UX.

## Next extensions after MVP

1. Add user auth beyond Telegram ID (for web dashboard).
2. Add pagination for search results.
3. Add tags and filtering.
4. Add note editing and soft delete.
5. Add daily digest reminders.
