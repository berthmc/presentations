"""NiceGUI web application for presentation generation."""

import httpx
from nicegui import ui

from presentations.config.logging_config import configure_logging
from presentations.config.settings import get_settings
from presentations.frontend.theme import apply_md3_theme


def _api_base() -> str:
    return get_settings().api_base_url.rstrip("/")


async def _fetch_diagnostics() -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{_api_base()}/diagnostics")
        response.raise_for_status()
        return response.json()


async def _generate_deck(brief: str, mode: str, title: str, run_qa: bool, template_path: str | None) -> dict:
    payload = {
        "brief": brief,
        "mode": mode,
        "title": title or None,
        "run_qa": run_qa,
        "template_path": template_path or None,
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(f"{_api_base()}/generate", json=payload)
        response.raise_for_status()
        return response.json()


def build_ui() -> None:
    """Build the NiceGUI page layout."""
    apply_md3_theme()
    state = {"result": None, "diagnostics": {}}

    with ui.column().classes("w-full max-w-5xl mx-auto p-6 gap-4"):
        ui.label("PPTX Generation Engine").classes("text-3xl md3-title")
        ui.label("Local-first LLM presentation builder with MD3 styling and visual QA").classes("text-gray-600")

        with ui.card().classes("md3-card w-full p-4"):
            ui.label("Hardware Profile").classes("text-lg font-bold")
            diag_label = ui.markdown("_Loading diagnostics…_")

            async def load_diag() -> None:
                try:
                    state["diagnostics"] = await _fetch_diagnostics()
                    d = state["diagnostics"]
                    diag_label.set_content(
                        f"**Profile:** {d.get('active_profile')}  \n"
                        f"**Synthesis model:** {d.get('synthesis_model')}  \n"
                        f"**VLM model:** {d.get('vlm_model')}  \n"
                        f"**RAM:** {d.get('total_ram_gb', 'n/a')} GB"
                    )
                except httpx.HTTPError as exc:
                    diag_label.set_content(f"_Diagnostics unavailable: {exc}_")

            ui.timer(0.1, load_diag, once=True)

        with ui.card().classes("md3-card w-full p-4 gap-3"):
            ui.label("Generate Presentation").classes("text-lg font-bold")
            title_input = ui.input("Title").classes("w-full")
            mode_select = ui.select(["scratch", "template"], value="scratch", label="Mode").classes("w-full")
            template_input = ui.input("Template path (.pptx or .md)", placeholder="Optional for scratch mode").classes(
                "w-full"
            )
            brief_input = ui.textarea("Content brief", placeholder="Describe the presentation you want…").classes(
                "w-full"
            ).props("rows=8")
            run_qa = ui.checkbox("Run visual QA", value=False)
            status = ui.label("").classes("text-sm text-gray-600")
            qa_report = ui.markdown("")
            download_link = ui.link("Download", "#").classes("hidden")

            async def on_generate() -> None:
                status.text = "Generating…"
                qa_report.set_content("")
                download_link.classes(add="hidden")
                try:
                    result = await _generate_deck(
                        brief=brief_input.value,
                        mode=mode_select.value,
                        title=title_input.value,
                        run_qa=run_qa.value,
                        template_path=template_input.value or None,
                    )
                    state["result"] = result
                    output = result.get("output_path", "")
                    status.text = f"Generated: {output}"
                    if result.get("qa_report"):
                        qa = result["qa_report"]
                        passed = qa.get("passed", False)
                        issues = qa.get("issues", [])
                        qa_report.set_content(
                            f"**QA passed:** {passed}  \n"
                            + "\n".join(f"- Slide {i.get('slide')}: {i.get('message')}" for i in issues[:10])
                        )
                    filename = output.split("\\")[-1].split("/")[-1]
                    download_link.target = f"{_api_base()}/download/{filename}"
                    download_link.text = f"Download {filename}"
                    download_link.classes(remove="hidden")
                except httpx.HTTPError as exc:
                    status.text = f"Error: {exc}"

            ui.button("Generate", on_click=on_generate).props("color=primary unelevated").classes("self-start")

        with ui.card().classes("md3-card w-full p-4"):
            ui.label("Slide Preview").classes("text-lg font-bold")
            preview = ui.column().classes("gap-2")

            @ui.refreshable
            def render_preview() -> None:
                preview.clear()
                result = state.get("result")
                if not result or not result.get("qa_report"):
                    ui.label("Run generation with QA enabled to preview slides.").classes("text-gray-500")
                    return
                for image_path in result["qa_report"].get("slide_images", [])[:6]:
                    ui.image(image_path).classes("max-w-full rounded-lg border")

            ui.timer(1.0, render_preview.refresh)


def main() -> None:
    """Launch the NiceGUI frontend."""
    settings = get_settings()
    configure_logging(settings.log_level)
    build_ui()
    ui.run(host=settings.ui_host, port=settings.ui_port, title="PPTX Engine", reload=False)


if __name__ == "__main__":
    main()
