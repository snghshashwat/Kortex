import httpx

from app.config import settings


def _gemini_post(path: str, payload: dict) -> dict:
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/{path}",
        params={"key": settings.llm_api_key},
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def clean_text_optional(text: str) -> str:
    """
    Optional cleanup to remove noise using Gemini.
    If the model call fails, we safely fall back to the original text.
    """
    try:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Clean this note without changing meaning. "
                                "Keep it concise and return only cleaned text:\n\n"
                                f"{text}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 120},
        }
        result = _gemini_post(f"models/{settings.optional_cleaning_model}:generateContent", payload)
        candidates = result.get("candidates") or []
        if candidates:
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            cleaned = "".join(part.get("text", "") for part in parts).strip()
            return cleaned if cleaned else text
        return text
    except Exception:
        return text


def embed_text(text: str) -> list[float]:
    """
    Generate embedding using Gemini's native embedding API.
    Returns a list of 768 floats (Gemini embedding dimension).
    """
    for model_name in (settings.embedding_model, "embedding-001"):
        try:
            result = _gemini_post(
                f"models/{model_name}:embedContent",
                {
                    "content": {"parts": [{"text": text}]},
                },
            )
            embedding = result.get("embedding") or {}
            values = embedding.get("values") or embedding.get("value") or embedding
            if isinstance(values, list) and values:
                return values
        except Exception:
            continue

    raise RuntimeError("Failed to generate Gemini embedding")
