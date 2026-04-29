import logging
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client with Groq base URL
openai_client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

# Initialize local embedding model (lightweight, no API key needed)
# Using all-MiniLM-L6-v2 which produces 384-dimensional embeddings
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading local embedding model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Local embedding model loaded successfully")
    return _embedding_model


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
    Generate embedding using local sentence-transformers model.
    Returns a list of 384 floats (all-MiniLM-L6-v2 dimension).
    """
    try:
        model = _get_embedding_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception:
        logger.exception("Embedding generation failed")
        raise RuntimeError("Failed to generate embedding")
