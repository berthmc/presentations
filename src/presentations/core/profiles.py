"""Hardware profile detection and model selection."""

import platform
import subprocess
from dataclasses import dataclass
from enum import StrEnum

from loguru import logger

from presentations.config.settings import Settings, get_settings


class HardwareProfileName(StrEnum):
    """Known hardware profiles from architecture.md."""

    INTEGRATED = "integrated"
    DISCRETE = "discrete"
    AUTO = "auto"


@dataclass(frozen=True)
class ModelProfile:
    """Models selected for a hardware profile."""

    name: HardwareProfileName
    synthesis_model: str
    vlm_model: str
    description: str
    supports_vlm: bool


INTEGRATED_PROFILE = ModelProfile(
    name=HardwareProfileName.INTEGRATED,
    synthesis_model="qwen2.5:3b",
    vlm_model="qwen2.5vl:7b",
    description="Integrated Radeon 780M — 3B synthesis, optional VLM",
    supports_vlm=False,
)

DISCRETE_PROFILE = ModelProfile(
    name=HardwareProfileName.DISCRETE,
    synthesis_model="deepseek-r1:14b",
    vlm_model="qwen2.5vl:7b",
    description="RTX 5070 Ti — 14B synthesis + 7B VLM",
    supports_vlm=True,
)


def _detect_discrete_gpu() -> bool:
    """Best-effort detection of a discrete NVIDIA GPU on the host."""
    if platform.system() != "Windows":
        return False
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA|RTX' }).Count -gt 0",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.stdout.strip().lower() == "true"
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("GPU detection failed: {}", exc)
        return False


def _detect_integrated_vram_gb() -> float | None:
    """Return allocated VRAM for integrated Radeon, if present."""
    if platform.system() != "Windows":
        return None
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$g = Get-CimInstance Win32_VideoController | "
                "Where-Object Name -like '*Radeon*' | Select-Object -First 1; "
                "if ($g) { [math]::Round($g.AdapterRAM / 1GB, 2) } else { '' }",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        value = result.stdout.strip()
        return float(value) if value else None
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.warning("VRAM detection failed: {}", exc)
        return None


def resolve_model_profile(settings: Settings | None = None) -> ModelProfile:
    """Resolve the active model profile from settings and host hardware."""
    settings = settings or get_settings()
    override = settings.hardware_profile.lower()

    if override == HardwareProfileName.DISCRETE:
        return DISCRETE_PROFILE
    if override == HardwareProfileName.INTEGRATED:
        return INTEGRATED_PROFILE

    if _detect_discrete_gpu():
        logger.info("Detected discrete GPU profile")
        return DISCRETE_PROFILE

    vram = _detect_integrated_vram_gb()
    if vram is not None:
        logger.info("Detected integrated GPU VRAM allocation: {} GB", vram)
    return INTEGRATED_PROFILE


def resolve_effective_supports_vlm(
    profile: ModelProfile,
    settings: Settings | None = None,
) -> bool:
    """Return whether VLM is enabled, honouring OLLAMA_SUPPORTS_VLM override."""
    settings = settings or get_settings()
    if settings.ollama_supports_vlm is not None:
        return settings.ollama_supports_vlm
    return profile.supports_vlm


def apply_profile_to_settings(profile: ModelProfile, settings: Settings | None = None) -> Settings:
    """Apply profile defaults to settings when env vars are unchanged."""
    settings = settings or get_settings()
    settings.ollama_synthesis_model = profile.synthesis_model
    settings.ollama_vlm_model = profile.vlm_model
    return settings


def run_hardware_diagnostics() -> dict[str, object]:
    """Return a diagnostic payload mirroring architecture.md §6."""
    total_ram_gb: float | None = None
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            total_ram_gb = float(result.stdout.strip())
        except (OSError, subprocess.SubprocessError, ValueError):
            total_ram_gb = None

    settings = get_settings()
    profile = resolve_model_profile(settings)
    return {
        "platform": platform.system(),
        "total_ram_gb": total_ram_gb,
        "integrated_vram_gb": _detect_integrated_vram_gb(),
        "discrete_gpu_detected": _detect_discrete_gpu(),
        "active_profile": profile.name,
        "synthesis_model": profile.synthesis_model,
        "vlm_model": profile.vlm_model,
        "supports_vlm": resolve_effective_supports_vlm(profile, settings),
    }
