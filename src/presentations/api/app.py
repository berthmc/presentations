"""FastAPI REST API for presentation generation."""

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from presentations.config.logging_config import configure_logging
from presentations.config.settings import get_settings
from presentations.core.profiles import run_hardware_diagnostics
from presentations.core.schemas import GenerateRequest, GenerationMode
from presentations.ingest.discover import discover_layout
from presentations.mcp.server import mcp as mcp_server
from presentations.qa.loop import run_qa_loop
from presentations.services.pipeline import generate_presentation

app = FastAPI(title="PPTX Generation Engine", version="0.1.0")
app.mount("/mcp", mcp_server.http_app())


@app.on_event("startup")
async def startup() -> None:
    """Configure logging and ensure data directories exist."""
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_dirs()
    logger.info("PPTX API started on {}:{}", settings.api_host, settings.api_port)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/diagnostics")
async def diagnostics() -> dict[str, object]:
    """Return hardware and model profile diagnostics."""
    return run_hardware_diagnostics()


@app.post("/discover-layout")
async def discover_layout_endpoint(template_path: str) -> dict:
    """Discover layout profile from a template path."""
    path = Path(template_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {template_path}")
    profile = discover_layout(path)
    return profile.model_dump()


@app.post("/generate")
async def generate_endpoint(request: GenerateRequest) -> dict:
    """Generate a presentation from a brief."""
    try:
        result = await generate_presentation(request)
        return result.model_dump()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/generate/upload")
async def generate_upload(
    brief: str = Form(...),
    mode: str = Form("scratch"),
    title: str | None = Form(None),
    run_qa: bool = Form(False),
    template: UploadFile | None = File(None),
) -> dict:
    """Generate a presentation with optional uploaded template."""
    settings = get_settings()
    template_path: str | None = None
    if template and template.filename:
        suffix = Path(template.filename).suffix.lower()
        dest = settings.uploads_dir / f"{Path(template.filename).stem}_{template.filename}"
        with dest.open("wb") as handle:
            shutil.copyfileobj(template.file, handle)
        template_path = str(dest)
        if suffix == ".pptx":
            mode = GenerationMode.TEMPLATE.value

    request = GenerateRequest(
        brief=brief,
        template_path=template_path,
        mode=GenerationMode(mode),
        title=title,
        run_qa=run_qa,
    )
    result = await generate_presentation(request)
    return result.model_dump()


@app.post("/qa/render")
async def qa_render(pptx_path: str) -> dict:
    """Run QA on an existing presentation."""
    path = Path(pptx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {pptx_path}")
    try:
        report = await run_qa_loop(path)
        return report.model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/download/{filename}")
async def download(filename: str) -> FileResponse:
    """Download a generated presentation."""
    settings = get_settings()
    path = settings.output_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


def create_app() -> FastAPI:
    """Factory for ASGI servers."""
    return app


def main() -> None:
    """Run the API server."""
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "presentations.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
