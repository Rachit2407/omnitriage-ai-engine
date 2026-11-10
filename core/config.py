import os
from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    
    CONFIDENCE_THRESHOLD: float = 0.85
    CHROMA_PERSIST_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")

    @classmethod
    def get_provider_details(cls) -> Tuple[str, Optional[str], str, Optional[str]]:
        """
        Auto-detects active LLM provider based on supplied keys.
        Priority: Groq -> Gemini -> OpenAI -> Offline Rule-Based
        Returns: (provider_display_name, api_key, model_name, base_url)
        """
        # 1. Groq (Free tier & ultra-fast inference)
        if cls.GROQ_API_KEY and not cls.GROQ_API_KEY.startswith("your_"):
            preferred_models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "llama3-70b-8192",
                "llama3-8b-8192",
                "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b"
            ]
            chosen_model = cls._resolve_groq_model(cls.GROQ_API_KEY, preferred_models, default="openai/gpt-oss-120b")
            return f"Groq ({chosen_model})", cls.GROQ_API_KEY, chosen_model, "https://api.groq.com/openai/v1"
        
        # 2. Google Gemini (Free tier via Google AI Studio)
        if cls.GEMINI_API_KEY and not cls.GEMINI_API_KEY.startswith("your_"):
            return "Google Gemini (gemini-1.5-flash)", cls.GEMINI_API_KEY, "gemini-1.5-flash", "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        # 3. OpenAI (GPT-4o-mini)
        if cls.OPENAI_API_KEY and not cls.OPENAI_API_KEY.startswith("your_"):
            return "OpenAI (GPT-4o-mini)", cls.OPENAI_API_KEY, "gpt-4o-mini", None
        
        # 4. Deterministic Offline Fallback
        return "Deterministic Fallback (Offline Mode)", None, "rule-based", None

    @staticmethod
    def _resolve_groq_model(api_key: str, preferred: list, default: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            available = {m.id for m in client.models.list().data}
            for model in preferred:
                if model in available:
                    return model
        except Exception:
            pass
        return default

settings = Settings()
