import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    GEMINI_CHAT_MODEL: str = "models/gemini-1.5-flash"

    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    CHROMA_COLLECTION_NAME: str = "support_docs"

    KB_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    TOP_K_RETRIEVAL: int = 3

    ESCALATION_CONFIDENCE_THRESHOLD: float = 0.40

    MAX_CONVERSATION_HISTORY: int = 10

    @classmethod
    def get_log_level(cls) -> str:
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @classmethod
    def validate(cls) -> None:
        if not cls.GEMINI_API_KEY:
            logger.warning(
                "GEMINI_API_KEY is not set. "
                "Set it in .env or environment variables."
            )


settings = Settings()
