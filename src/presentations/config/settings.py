"""Runtime settings loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8090, alias="API_PORT")
    mcp_transport: str = Field(default="http", alias="MCP_TRANSPORT")

    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_synthesis_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_SYNTHESIS_MODEL")
    ollama_vlm_model: str = Field(default="qwen2.5-vl:7b", alias="OLLAMA_VLM_MODEL")

    google_cloud_project: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="europe-west1", alias="GOOGLE_CLOUD_LOCATION")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_vision_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_VISION_MODEL")

    hardware_profile: str = Field(default="auto", alias="HARDWARE_PROFILE")
    qa_max_iterations: int = Field(default=3, alias="QA_MAX_ITERATIONS")
    qa_render_dpi: int = Field(default=150, alias="QA_RENDER_DPI")

    ui_host: str = Field(default="0.0.0.0", alias="UI_HOST")
    ui_port: int = Field(default=8091, alias="UI_PORT")
    api_base_url: str = Field(default="http://localhost:8090", alias="API_BASE_URL")

    @property
    def staging_dir(self) -> Path:
        """Directory for intermediate render artefacts."""
        return self.data_dir / "staging"

    @property
    def output_dir(self) -> Path:
        """Directory for generated presentations."""
        return self.data_dir / "output"

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded templates and briefs."""
        return self.data_dir / "uploads"

    @property
    def qa_dir(self) -> Path:
        """Directory for QA slide images."""
        return self.data_dir / "qa"

    @property
    def templates_dir(self) -> Path:
        """Directory for bundled templates."""
        return self.data_dir / "templates"

    def ensure_dirs(self) -> None:
        """Create runtime data directories if missing."""
        for directory in (
            self.data_dir,
            self.staging_dir,
            self.output_dir,
            self.uploads_dir,
            self.qa_dir,
            self.templates_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
