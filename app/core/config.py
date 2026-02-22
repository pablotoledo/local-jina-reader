from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    REDIS_URL: str = "redis://localhost:6379/0"
    API_KEYS: list[str] = []
    DEFAULT_TIMEOUT_S: int = 15
    MAX_TIMEOUT_S: int = 60
    DEFAULT_CACHE_TTL_S: int = 300
    ENABLE_SSE: bool = True
    ENABLE_COOKIE_FORWARDING: bool = False
    ALLOW_PRIVATE_NETS: bool = False
    BROWSER_CONTEXTS_MAX: int = 4
    PAGES_PER_CONTEXT_MAX: int = 4
    USER_AGENT: str = "reader-clone/0.1"
    PLAYWRIGHT_BROWSER: str = "chromium"
    PLAYWRIGHT_HEADLESS: bool = True
    EXTRACTOR_VERSION: str = "1"


settings = Settings()
