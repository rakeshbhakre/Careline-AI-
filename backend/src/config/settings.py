from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_path: Path = ROOT / 'data' / 'appointments.sqlite3'
    frontend_origin: str = 'http://localhost:5173'
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = ''
    llm_provider: Literal['groq', 'google'] = 'groq'
    groq_api_key: str = ''
    groq_model: str = 'openai/gpt-oss-20b'
    google_api_key: str = ''
    google_model: str = 'gemini-3.1-flash-lite'
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')

    @property
    def llm_api_key(self) -> str:
        return self.groq_api_key if self.llm_provider == 'groq' else self.google_api_key

    @property
    def voice_configured(self) -> bool:
        return all((self.elevenlabs_api_key, self.elevenlabs_voice_id, self.llm_api_key))
