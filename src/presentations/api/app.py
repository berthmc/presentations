"""FastAPI REST API for presentation generation."""

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

from presentations.config.logging_config import configure_logging
from presentations.config.settings import get_settings
from presentations.core.profiles import run_hardware_diagnostics
from presentations.core.schemas import GenerateRequest, GenerationMode
from presentations.ingest.discover import discover_layout
from presentations.ingest.pdf_ingest import extract_source_context_from_pdf
from presentations.llm.catalog import list_available_models
from presentations.mcp.server import mcp as mcp_server
from presentations.qa.loop import run_qa_loop
from presentations.services.pipeline import generate_presentation
from presentations.services.template_registry import get_template_registry

app = FastAPI(title="Presentations@Carmélites", version="0.1.0")
app.mount("/mcp", mcp_server.http_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8091",
        "http://127.0.0.1:8091",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    """Configure logging and ensure data directories exist."""
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_dirs()
    get_template_registry().seed_builtin_templates()
    logger.info("PPTX API started on {}:{}", settings.api_host, settings.api_port)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/diagnostics")
async def diagnostics() -> dict[str, object]:
    """Return hardware and model profile diagnostics."""
    return run_hardware_diagnostics()


@app.get("/models")
async def list_models() -> dict[str, object]:
    """Return synthesis model catalog with availability flags."""
    return await list_available_models()


@app.get("/templates")
async def list_templates() -> dict:
    """List all templates in the persistent library."""
    registry = get_template_registry()
    summaries = registry.list_templates()
    return {"templates": [item.model_dump(mode="json") for item in summaries]}


@app.get("/templates/{template_id}")
async def get_template(template_id: str) -> dict:
    """Return full metadata for one library template."""
    registry = get_template_registry()
    try:
        record = registry.get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/templates")
async def register_template(
    name: str = Form(...),
    is_default: bool = Form(False),
    file: UploadFile = File(...),
) -> dict:
    """Upload and register a template in the persistent library."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pptx", ".md"}:
        raise HTTPException(status_code=400, detail="Only .pptx and .md templates are supported")

    settings = get_settings()
    staging = settings.uploads_dir / f"register_{file.filename}"
    with staging.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    registry = get_template_registry()
    try:
        record = registry.register(
            name=name,
            source_path=staging,
            is_default=is_default,
            original_filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if staging.exists():
            staging.unlink()

    return record.summary().model_dump(mode="json")


@app.delete("/templates/{template_id}")
async def delete_template(template_id: str) -> dict:
    """Remove a template from the library."""
    registry = get_template_registry()
    try:
        registry.delete(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": template_id}


@app.patch("/templates/{template_id}/default")
async def set_default_template(template_id: str) -> dict:
    """Mark a template as the default selection."""
    registry = get_template_registry()
    try:
        record = registry.set_default(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.summary().model_dump(mode="json")


@app.post("/discover-layout")
async def discover_layout_endpoint(template_path: str) -> dict:
    """Discover layout profile from a template path."""
    path = Path(template_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {template_path}")
    profile = discover_layout(path)
    return profile.model_dump()


@app.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)) -> dict[str, str]:
    """Extract Markdown source context from an uploaded PDF for synthesis grounding."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    suffix = Path(file.filename).suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(status_code=400, detail="Only .pdf files are supported")

    settings = get_settings()
    staging = settings.uploads_dir / f"brief_{file.filename}"
    try:
        with staging.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        source_context = await extract_source_context_from_pdf(staging)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if staging.exists():
            staging.unlink()

    return {
        "source_context": source_context,
        "filename": file.filename,
        "text": source_context,
    }


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
    template_id: str | None = Form(None),
    synthesis_model: str | None = Form(None),
    source_context: str | None = Form(None),
    allow_cloud: bool = Form(False),
    template: UploadFile | None = File(None),
) -> dict:
    """Generate a presentation with optional library template or ad-hoc upload."""
    settings = get_settings()
    resolved_template_id = template_id
    template_path: str | None = None

    if template and template.filename:
        suffix = Path(template.filename).suffix.lower()
        dest = settings.uploads_dir / f"{Path(template.filename).stem}_{template.filename}"
        with dest.open("wb") as handle:
            shutil.copyfileobj(template.file, handle)
        registry = get_template_registry()
        record = registry.register(
            name=Path(template.filename).stem,
            source_path=dest,
            original_filename=template.filename,
        )
        resolved_template_id = record.id
        if suffix == ".pptx":
            mode = GenerationMode.TEMPLATE.value

    request = GenerateRequest(
        brief=brief,
        template_id=resolved_template_id,
        template_path=template_path,
        mode=GenerationMode(mode),
        title=title,
        run_qa=run_qa,
        synthesis_model=synthesis_model,
        source_context=source_context,
        allow_cloud=allow_cloud,
    )
    try:
        result = await generate_presentation(request)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@app.get("/qa/slides/{deck_stem}/{image_name}")
async def serve_qa_slide(deck_stem: str, image_name: str) -> FileResponse:
    """Serve rendered QA slide images to the web UI."""
    settings = get_settings()
    if ".." in deck_stem or ".." in image_name:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = settings.qa_dir / deck_stem / image_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Slide image not found")
    return FileResponse(path, media_type="image/jpeg")


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
