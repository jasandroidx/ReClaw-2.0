"""
Central configuration for ReClaw.

Env-driven, works the same on:
- Local Windows dev mirror (point obsidian_path at your vault)
- Hetzner production (use /data/obsidian or Tailscale-mounted path, GPU enabled)

Never hardcode secrets or vault paths here.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RECLAW_",
        extra="ignore",
    )

    # Environment (RECLAW_ENV=prod from .env/compose/Dockerfile)
    env: str = Field(default="dev", description="dev | staging | prod")
    log_level: str = "INFO"

    # Paths (override via .env or env vars)
    # Local example: C:/Users/Jason/Desktop/Obsidian Claw/Rural Data
    # Hetzner example: /mnt/obsidian-vault/Rural-Data or /data/obsidian-exports
    obsidian_vault_path: Path = Field(
        default=Path("outputs/obsidian"),
        description="Directory where final .md packages are written. Must be writable."
    )

    data_dir: Path = Field(default=Path("data"))
    runs_dir: Path = Field(default=Path("data/runs"))
    seeds_dir: Path = Field(default=Path("data/seeds"))

    # Researcher behavior
    use_live_fetch: bool = Field(
        default=False,
        description="If true, Researcher will attempt HTTP fetches to county sites. Else use only seeds + cache."
    )
    fetch_timeout: int = 12  # seconds
    max_properties_per_county: int = 50

    # Analyst + Marketplace/ingest sources
    enable_llm_analysis: bool = Field(
        default=False,
        description="Future: when True, Analyst will call local LLM (Ollama / vLLM on GPU) for deeper synthesis. Currently heuristic only."
    )
    ingest_sources: list = Field(
        default=["marketplace_flips", "kimi_claw", "rural_data", "documents", "obsidian_vault"],
        description="Authorized sources for ingest_document, marketplace scans, Kimi distillation, and Oracle pipeline. Used by validate_oracle() and KnowledgeManager."
    )
    llm_model: str = "llama3.1:8b"  # or whatever is on the Hetzner box

    # Orchestrator / API
    job_timeout_seconds: int = 300
    max_concurrent_jobs: int = 2

    # Obsidian writer + Knowledge Vault (RAG SOT per task)
    obsidian_subdir: str = "Knowledge Vault"  # inside the vault root (configurable for RAG/ingest; was Rural Data)
    write_dry_run: bool = False  # if True, log what would be written but don't touch disk

    # Kimi (Moonshot/Kimi K) for ingestion/distillation (preferred, wired in kimi-claw)
    kimi_model: str = "moonshot-v1-8k"
    kimi_api_base: str = "https://api.moonshot.cn/v1"
    # Token pulled from env (XAI_API_KEY or KIMI_TOKEN) or openclaw kimi-claw config

    # API security (for cron, future Discord bot)
    reclaw_gateway_token: str = Field(
        default="supersecretchangemeinproduction1234567890abcdef",
        description="Bearer token for /trigger endpoints (change in .env)"
    )

    @property
    def effective_obsidian_path(self) -> Path:
        """Full path to the target subfolder in vault."""
        return self.obsidian_vault_path / self.obsidian_subdir

    def ensure_dirs(self) -> None:
        """Create expected runtime directories."""
        for p in [
            self.data_dir,
            self.runs_dir,
            self.seeds_dir,
            self.effective_obsidian_path,
            Path("outputs"),
        ]:
            p.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
