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
        extra="ignore",
    )

    # Environment
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

    # Analyst
    enable_llm_analysis: bool = Field(
        default=False,
        description="Future: when True, Analyst will call local LLM (Ollama / vLLM on GPU) for deeper synthesis. Currently heuristic only."
    )
    llm_model: str = "llama3.1:8b"  # or whatever is on the Hetzner box

    # Orchestrator / API
    job_timeout_seconds: int = 300
    max_concurrent_jobs: int = 2

    # Obsidian writer
    obsidian_subdir: str = "Rural Data"  # inside the vault root
    write_dry_run: bool = False  # if True, log what would be written but don't touch disk

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
