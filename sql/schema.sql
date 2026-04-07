-- Enable extensions once in Supabase SQL editor.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Raw user notes/messages.
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id BIGINT NOT NULL,
  chat_id BIGINT NOT NULL,
  message_text TEXT NOT NULL,
  cleaned_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) Embeddings are stored separately to keep message table simple.
-- text-embedding-3-small returns 1536 dimensions.
CREATE TABLE IF NOT EXISTS embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
  embedding VECTOR(1536) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3) Reminder queue for background delivery.
CREATE TABLE IF NOT EXISTS reminders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  telegram_user_id BIGINT NOT NULL,
  chat_id BIGINT NOT NULL,
  remind_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(telegram_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reminders_pending_due ON reminders(status, remind_at);

-- Optional: speeds up vector search as your data grows.
-- ivfflat needs ANALYZE and enough rows to be useful.
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
