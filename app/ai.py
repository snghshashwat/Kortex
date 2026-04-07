import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.llm_api_key)


def clean_text_optional(text: str) -> str:
    """
    Optional cleanup to remove noise using Gemini.
    If the model call fails, we safely fall back to the original text.
    """
    try:
        model = genai.GenerativeModel(settings.optional_cleaning_model)
        response = model.generate_content(
            f"Clean this note without changing meaning. "
            f"Keep it concise and return only cleaned text:\n\n{text}",
            generation_config=genai.types.GenerationConfig(max_output_tokens=120),
        )
        cleaned = (response.text or "").strip()
        return cleaned if cleaned else text
    except Exception:
        return text


def embed_text(text: str) -> list[float]:
    """
    Generate embedding using Gemini's native embedding API.
    Returns a list of 768 floats (Gemini embedding dimension).
    """
    result = genai.embed_content(
        model="models/embedding-001",
        content=text,
    )
    return result["embedding"]
