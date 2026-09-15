import os
from dataclasses import dataclass

@dataclass
class Settings:
    app_name: str = os.getenv('APP_NAME', 'SAT-SA Offline Audit Platform')
    secret_key: str = os.getenv('SECRET_KEY', 'local-demo-secret-change-me')
    ollama_url: str = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'mistral:7b-instruct')

settings = Settings()
