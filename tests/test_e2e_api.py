"""End-to-end API smoke test for template library and generation wiring."""

from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from presentations.api.app import app


@pytest.mark.asyncio
async def test_templates_and_health_endpoints() -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        templates = await client.get("/templates")
        assert templates.status_code == 200
        payload = templates.json()
        assert "templates" in payload
        assert len(payload["templates"]) >= 1

        default_id = payload["templates"][0]["id"]
        detail = await client.get(f"/templates/{default_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == default_id


@pytest.mark.asyncio
async def test_qa_slide_image_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import presentations.config.settings as settings_module

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_module._settings = None
    settings = settings_module.get_settings()
    deck_dir = settings.qa_dir / "demo-deck"
    deck_dir.mkdir(parents=True, exist_ok=True)
    image = deck_dir / "slide-01.jpg"
    image.write_bytes(b"fakejpeg")

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/qa/slides/demo-deck/slide-01.jpg")
        assert response.status_code == 200
        assert response.content == b"fakejpeg"


@pytest.mark.asyncio
async def test_generate_with_template_id_uses_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Generate deck with template_id when synthesis is stubbed."""
    import presentations.config.settings as settings_module
    from presentations.compile.pptxgen_runner import compile_from_scratch
    from presentations.core.schemas import DeckSpec, GenerateResult, GenerationMode, PlaceholderMapping, SlideSpec

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_module._settings = None

    async def _fake_generate(request):
        deck = DeckSpec(
            title="E2E Deck",
            mode=GenerationMode.SCRATCH,
            slides=[
                SlideSpec(
                    layout_index=0,
                    mappings=[PlaceholderMapping(ph_idx=0, content="Title")],
                )
            ],
        )
        output = tmp_path / "output" / "e2e.pptx"
        output.parent.mkdir(parents=True, exist_ok=True)
        await compile_from_scratch(deck, output)
        return GenerateResult(
            output_path=str(output.resolve()),
            deck_spec=deck,
            qa_report=None,
            layout_profile=None,
        )

    monkeypatch.setattr("presentations.api.app.generate_presentation", _fake_generate)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        templates = await client.get("/templates")
        template_id = templates.json()["templates"][0]["id"]
        response = await client.post(
            "/generate",
            json={
                "brief": "Smoke test brief",
                "template_id": template_id,
                "mode": "scratch",
                "run_qa": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert Path(body["output_path"]).exists()
