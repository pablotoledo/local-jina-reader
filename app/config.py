from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_port: int = 8000
    internal_token: str = ""

    hf_model_id: str = "jinaai/ReaderLM-v2"
    hf_home: str = "/root/.cache/huggingface"
    device: str = "cpu"
    max_new_tokens: int = 4096
    torch_dtype: str = "float32"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600

    fetch_timeout_seconds: int = 30
    fetch_user_agent: str = "intranet-reader/0.1"


settings = Settings()
