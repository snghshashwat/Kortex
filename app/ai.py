from openai import OpenAI

from app.config import settings

client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def clean_text_optional(text: str) -> str:
    """
    Optional cleanup to remove noise. If the model call fails,
    we safely fall back to the original text.
    """
    try:
        response = client.responses.create(
            model=settings.optional_cleaning_model,
            input=(
                "Clean this note without changing meaning. "
                "Keep it concise and return only cleaned text:\n\n"
                f"{text}"
            ),
            max_output_tokens=120,
        )
        cleaned = (response.output_text or "").strip()
        return cleaned if cleaned else text
    except Exception:
        return text


def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(model=settings.embedding_model, input=text)
    return response.data[0].embedding
