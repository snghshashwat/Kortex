import logging
import hashlib
import math
import re

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client with Groq base URL
openai_client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

_EMBEDDING_DIMS = 768


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _stable_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _lightweight_embedding(text: str, dims: int = _EMBEDDING_DIMS) -> list[float]:
    # Signed hashing trick to create deterministic fixed-size vectors without heavy ML deps.
    vector = [0.0] * dims
    tokens = _tokenize(text)

    if not tokens:
        return vector

    for token in tokens:
        digest = _stable_hash(token)
        index = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (len(token) / 10.0)
        vector[index] += sign * weight

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector

    return [v / norm for v in vector]


def clean_text_optional(text: str) -> str:
    """
    Optional cleanup to remove noise using Groq LLM.
    If the model call fails, we safely fall back to the original text.
    """
    try:
        response = openai_client.chat.completions.create(
            model=settings.optional_cleaning_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that cleans up text. Remove noise without changing meaning. Keep it concise. Return only the cleaned text, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Clean this note:\n\n{text}"
                }
            ],
            max_tokens=120,
            temperature=0.1,
        )
        cleaned = response.choices[0].message.content.strip()
        return cleaned if cleaned else text
    except Exception:
        logger.exception("Text cleaning failed, returning original")
        return text


def embed_text(text: str) -> list[float]:
    """
    Generate lightweight deterministic embedding without heavy ML runtime.
    Returns a list of 768 floats to match pgvector column dimension.
    """
    try:
        return _lightweight_embedding(text)
    except Exception:
        logger.exception("Embedding generation failed")
        raise RuntimeError("Failed to generate embedding")
