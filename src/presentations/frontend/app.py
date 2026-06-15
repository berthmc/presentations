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


async def _fetch_templates() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{_api_base()}/templates")
        response.raise_for_status()
        return response.json().get("templates", [])


async def _register_template(name: str, file_content: bytes, filename: str, is_default: bool) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{_api_base()}/templates",
            data={"name": name, "is_default": str(is_default).lower()},
            files={"file": (filename, file_content)},
        )
        response.raise_for_status()
        return response.json()


async def _delete_template(template_id: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{_api_base()}/templates/{template_id}")
        response.raise_for_status()


async def _set_default_template(template_id: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(f"{_api_base()}/templates/{template_id}/default")
        response.raise_for_status()


async def _generate_deck(
    brief: str,
    mode: str,
    title: str,
    run_qa: bool,
    template_id: str | None,
) -> dict:
    payload = {
        "brief": brief,
        "mode": mode,
        "title": title or None,
        "run_qa": run_qa,
        "template_id": template_id,
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(f"{_api_base()}/generate", json=payload)
        response.raise_for_status()
        return response.json()


def build_ui() -> None:
    """Build the NiceGUI page layout."""
    apply_md3_theme()
    state = {"result": None, "diagnostics": {}, "templates": []}

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
            ui.label("Template Library").classes("text-lg font-bold")
            library_status = ui.label("").classes("text-sm text-gray-600")
            template_select = ui.select({}, label="Saved template", with_input=True).classes("w-full")
            upload_name = ui.input("Template name", placeholder="e.g. Acme Corporate 2026").classes("w-full")
            upload_default = ui.checkbox("Set as default", value=False)

            async def refresh_templates() -> None:
                try:
                    state["templates"] = await _fetch_templates()
                    options = {
                        t["id"]: (
                            f"{t['name']} ({t['source_type']})"
                            f"{' *' if t.get('is_default') else ''}"
                        )
                        for t in state["templates"]
                    }
                    template_select.set_options(options, value=_default_template_id(state["templates"]))
                    library_status.text = f"{len(state['templates'])} template(s) in library"
                except httpx.HTTPError as exc:
                    library_status.text = f"Could not load templates: {exc}"

            def _default_template_id(templates: list[dict]) -> str | None:
                for item in templates:
                    if item.get("is_default"):
                        return item["id"]
                return templates[0]["id"] if templates else None

            async def on_upload(e) -> None:
                if not upload_name.value:
                    library_status.text = "Enter a template name before uploading."
                    return
                try:
                    content = e.content.read()
                    await _register_template(
                        upload_name.value,
                        content,
                        e.name,
                        upload_default.value,
                    )
                    library_status.text = f"Registered template '{upload_name.value}'"
                    upload_name.value = ""
                    await refresh_templates()
                except httpx.HTTPError as exc:
                    library_status.text = f"Upload failed: {exc}"

            ui.upload(on_upload=on_upload, auto_upload=True, label="Upload .pptx or .md template").classes("w-full")

            with ui.row().classes("gap-2"):
                async def on_set_default() -> None:
                    if not template_select.value:
                        return
                    try:
                        await _set_default_template(template_select.value)
                        library_status.text = "Default template updated."
                        await refresh_templates()
                    except httpx.HTTPError as exc:
                        library_status.text = f"Failed: {exc}"

                async def on_delete_template() -> None:
                    if not template_select.value:
                        return
                    try:
                        await _delete_template(template_select.value)
                        library_status.text = "Template deleted."
                        await refresh_templates()
                    except httpx.HTTPError as exc:
                        library_status.text = f"Delete failed: {exc}"

                ui.button("Set default", on_click=on_set_default).props("outline")
                ui.button("Delete", on_click=on_delete_template).props("outline color=negative")

            ui.timer(0.2, refresh_templates, once=True)

        with ui.card().classes("md3-card w-full p-4 gap-3"):
            ui.label("Generate Presentation").classes("text-lg font-bold")
            title_input = ui.input("Title").classes("w-full")
            mode_select = ui.select(["scratch", "template"], value="scratch", label="Mode").classes("w-full")
            brief_input = ui.textarea("Content brief", placeholder="Describe the presentation you want…").classes(
                "w-full"
            ).props("rows=8")
            run_qa = ui.checkbox("Run visual QA", value=False)
            status = ui.label("").classes("text-sm text-gray-600")
            qa_report = ui.markdown("")
            download_link = ui.link("Download", "#").classes("hidden")

            def _sync_mode_from_template() -> None:
                if not template_select.value:
                    return
                selected = next((t for t in state["templates"] if t["id"] == template_select.value), None)
                if selected and selected.get("source_type") == "pptx":
                    mode_select.value = "template"

            template_select.on("update:model-value", lambda _: _sync_mode_from_template())

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
                        template_id=template_select.value or None,
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
