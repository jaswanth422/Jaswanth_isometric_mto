import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()
GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "120"))
GEMINI_FAILURE_COOLDOWN_SECONDS: int = int(os.getenv("GEMINI_FAILURE_COOLDOWN_SECONDS", "600"))
MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://0.0.0.0:3000",
    ).split(",")
    if origin.strip()
]

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}


def provider_context() -> tuple[str, str | None]:
    model_provider = os.getenv("MODEL_PROVIDER", MODEL_PROVIDER).strip().lower()
    gemini_api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()

    if model_provider == "mock":
        return "mock", "configured_mock_provider"
    if not gemini_api_key:
        return "mock", "missing_api_key"
    return "gemini", None

# If no key is present, we always fall back to mock regardless of MODEL_PROVIDER,
# so the app can never crash on a missing-credential path.
def resolve_provider() -> str:
    return provider_context()[0]
