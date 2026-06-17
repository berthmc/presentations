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
    ollama_synthesis_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_SYNTHESIS_MODEL")
    ollama_vlm_model: str = Field(default="qwen2.5vl:7b", alias="OLLAMA_VLM_MODEL")
    ollama_supports_vlm: bool | None = Field(default=None, alias="OLLAMA_SUPPORTS_VLM")
    ollama_num_predict: int = Field(default=4096, alias="OLLAMA_NUM_PREDICT")
    ollama_num_ctx: int = Field(default=32768, alias="OLLAMA_NUM_CTX")
    ollama_temperature: float = Field(default=0.1, alias="OLLAMA_TEMPERATURE")
    ollama_max_source_context_chars: int = Field(default=32000, alias="OLLAMA_MAX_SOURCE_CONTEXT_CHARS")
    ollama_read_timeout_generate: float = Field(default=300.0, alias="OLLAMA_READ_TIMEOUT_GENERATE")
    ollama_read_timeout_vlm: float = Field(default=300.0, alias="OLLAMA_READ_TIMEOUT_VLM")

    google_cloud_project: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="europe-west1", alias="GOOGLE_CLOUD_LOCATION")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_vision_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_VISION_MODEL")

    allow_cloud_llm_default: bool = Field(default=False, alias="ALLOW_CLOUD_LLM_DEFAULT")
    hardware_profile: str = Field(default="auto", alias="HARDWARE_PROFILE")
    qa_max_iterations: int = Field(default=3, alias="QA_MAX_ITERATIONS")
    qa_render_dpi: int = Field(default=150, alias="QA_RENDER_DPI")

    ui_host: str = Field(default="0.0.0.0", alias="UI_HOST")
    ui_port: int = Field(default=8091, alias="UI_PORT")
    api_base_url: str = Field(default="http://localhost:8090", alias="API_BASE_URL")

    pdf_mcp_url: str = Field(default="http://localhost:3005/mcp", alias="PDF_MCP_URL")
    pdf_mcp_workspace_dir: Path = Field(
        default=Path("../pdf/mcp-workspace"),
        alias="PDF_MCP_WORKSPACE_DIR",
    )

    context7_mcp_url: str = Field(default="https://mcp.context7.com/mcp", alias="CONTEXT7_MCP_URL")
    context7_api_key: str = Field(default="", alias="CONTEXT7_API_KEY")
    context7_enabled: bool = Field(default=True, alias="CONTEXT7_ENABLED")
    context7_max_techs: int = Field(default=3, alias="CONTEXT7_MAX_TECHS")

    enable_digest_phase: bool = Field(default=True, alias="ENABLE_DIGEST_PHASE")
    digest_chunk_chars: int = Field(default=8000, alias="DIGEST_CHUNK_CHARS")

    vllm_base_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_BASE_URL")
    vllm_model: str = Field(
        default="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        alias="VLLM_MODEL",
    )
    vllm_max_model_len: int = Field(default=16384, alias="VLLM_MAX_MODEL_LEN")
    vllm_enabled: bool = Field(default=True, alias="VLLM_ENABLED")
    vllm_read_timeout: float = Field(default=300.0, alias="VLLM_READ_TIMEOUT")

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="pptx_research", alias="QDRANT_COLLECTION")
    embedding_model: str = Field(default="bge-m3", alias="EMBEDDING_MODEL")
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_top_k: int = Field(default=10, alias="RAG_TOP_K")
    rag_chunk_chars: int = Field(default=1500, alias="RAG_CHUNK_CHARS")

    use_docling: bool = Field(default=True, alias="USE_DOCLING")
    max_revisions: int = Field(default=3, alias="MAX_REVISIONS")
    qa_vlm_enabled: bool = Field(default=False, alias="QA_VLM_ENABLED")

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
