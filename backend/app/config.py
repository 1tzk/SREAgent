from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI SRE Agent"
    app_env: str = "development"
    database_url: str = "sqlite:///./ai_sre_agent.db"
    llm_provider: str = "mock"
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    model_name: str = ""
    llm_timeout_seconds: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
