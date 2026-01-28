"""Application settings and configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key for AI Tutor")
    polymarket_api_key: str = Field(default="", description="Polymarket API key (optional)")

    # Supabase (for cloud storage)
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase anon/public key")

    @property
    def use_supabase(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_key)

    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Data storage directory")

    # Binance
    binance_base_url: str = "https://api.binance.com"

    # Polymarket
    polymarket_base_url: str = "https://clob.polymarket.com"

    # AI Tutor
    ai_model: str = "claude-opus-4-5-20251101"
    ai_max_tokens: int = 2048

    # Trading defaults
    default_initial_capital: float = 1000.0
    default_max_position_pct: float = 0.02
    default_min_ev: float = 0.08
    default_min_confidence: float = 0.65

    model_config = {
        "env_prefix": "",  # No prefix - use variable names directly
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def simulations_dir(self) -> Path:
        return self.data_dir / "simulations"

    @property
    def insights_dir(self) -> Path:
        return self.data_dir / "insights"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
