Template-Driven PPTX Generation & Visual Validation Engine: System Specification

This specification defines the functional architecture, dependency matrix, and hardware requirement protocols for a containerized, local-first PowerPoint (.pptx) orchestration service. The engine allows users to ingest complex corporate guidelines, dynamically match layouts, map structural content via local LLMs, and programmatically verify design integrity via a local Vision-Language Model (VLM).

1. Executive Summary & Design Principles

Enterprise PowerPoint creation is traditionally bottlenecked by manual formatting loops, misaligned design patterns, and high cloud API token costs. This architecture automates the pipeline entirely on local silicon using a three-tier system of Layout Discovery, Structured Content Synthesis, and Local Vision-Based Quality Assurance.

Key Architecture Targets

Template Fidelity: Preserve $100\%$ of pre-defined corporate themes, font hierarchies, color schemas, and native master slide placeholders.

Layout Decoupling: Isolate content generation logic from design placement. The LLM acts as an orchestrator, mapping textual content blocks directly into pre-rendered visual slots.

Closed-Loop Visual Validation: Leverage headless rendering to output slide preview images, using a local VLM to identify overlapping boundaries and contrast failures before final delivery.

2. Dynamic Structural Pipeline

The application executes generation and validation in four distinct stages:

┌─────────────────────────────────┐
│  Phase 1: Layout Discovery      │ <── Ingests corporate template (.pptx)
└────────────────┬────────────────┘     Parses Slide Masters and extracts `ph_idx` mappings
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 2: Semantic Synthesis   │ <── Generates strict JSON schema via local LLM
└────────────────┬────────────────┘     Matches content blocks to designated master indices
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 3: Programmatic Compile  │ <── Assembles slide binaries using python-pptx
└────────────────┬────────────────┘     Outputs intermediate raw branded deck
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 4: Visual QA Loop        │ <── Headless LibreOffice renders to vector PDF
└─────────────────────────────────┘     pdftoppm rasterizes to Slide-XX.jpg
                                        Local VLM checks layout contrast & text collisions


3. Detailed Component Specifications

3.1 Layout Discovery Parser

The discovery parser extracts metadata from the template slide masters. Instead of guessing shape coordinates, the system reads embedded corporate designs and translates their placeholder footprints into a machine-readable format.

from pptx import Presentation
import json

def generate_layout_map(template_path: str) -> dict:
    """
    Analyzes master slides in a target presentation template and returns
    a mapping profile of available layouts and text placeholders.
    """
    prs = Presentation(template_path)
    layout_profile = {}
    
    for idx, layout in enumerate(prs.slide_layouts):
        placeholders = []
        for ph in layout.placeholders:
            placeholders.append({
                "index": ph.placeholder_format.idx,
                "name": ph.name,
                "type": str(ph.placeholder_format.type)
            })
        
        layout_profile[idx] = {
            "name": layout.name,
            "placeholders": placeholders
        }
    return layout_profile


3.2 Dynamic Context Prompting & Generation

The backend passes the output of the layout discovery parser directly into the system prompt of the local LLM. The LLM must yield a strict JSON format that maps user input parameters to the discovered slide master indices.

{
  "slides": [
    {
      "layout_index": 2,
      "mappings": [
        { "ph_idx": 0, "content": "Q3 Technical Pipeline Milestones" },
        { "ph_idx": 1, "content": "• Migration of document extraction pipeline from cloud endpoints to local silicon.\n• Execution of 8GB UMA BIOS optimization parameters." }
      ]
    }
  ]
}


3.3 Multi-Stage Visual QA Rendering Loop

Once compile-level code generates the new slides, the backend must programmatically render the presentation to detect styling defects. Because the application runs headlessly within a Docker sandbox, it handles rendering using two light system dependencies:

# Step 1: Headless LibreOffice Compilation
# Converts the raw .pptx file into vector PDF sheets using the headless graphics pipeline
soffice --headless --convert-to pdf --outdir /data/staging /data/output.pptx

# Step 2: High-Density Image Rasterization
# Extracts pages into independent, crisp JPEG images at 150 DPI for visual inspection
pdftoppm -jpeg -r 150 /data/staging/output.pdf /data/staging/slide


3.4 Local VLM Layout Auditing

The generated JPG slide images are routed directly into a local Vision Model (such as qwen2.5-vl:7b via Ollama) with a target inspection prompt:

"Inspect this rendered slide image for visual bugs. Identify if any text overlaps other text, if bullet points collide with shapes, or if text contrast is illegible. Return a strict boolean 'passed' value, along with a 'reasons' array if errors are detected."

4. System Requirements & Dependency Matrix

4.1 System Software Stack

These components must be compiled directly into the backend Docker container (python:3.11-slim-bookworm):

System Tools:

libreoffice-draw & libreoffice-impress (headless rendering core)

poppler-utils (compiled vector parsing tools containing pdftoppm)

Python Environments:

python-pptx (direct presentation manipulation)

fastmcp (native SSE container interface)

ollama (local LLM communications)

pymupdf4llm (unstructured source PDF parsing)

4.2 Local Hardware Configuration Profiles

The application scales its execution boundaries dynamically based on host hardware configurations.

                  ┌──────────────────────────────────────────────┐
                  │ Target Physical System Memory: 32 GB DDR5    │
                  └──────────────────────┬───────────────────────┘
                                         │
                   Is external GPU (OCuLink) active?
                   ├─── Yes ──► [ RTX 5070 Ti Profile ]
                   │            • VRAM: 16 GB GDDR7 Dedicated
                   │            • Models: qwen2.5:7b + qwen2.5vl:7b
                   │            • Pipeline Capacity: High-speed local visual audit
                   │
                   └─── No ───► [ Integrated Radeon 780M Profile ]
                                • UMA Buffer: 8 GB Allocated (BIOS Spec)
                                • Host OS RAM: ~20 GB (Docker Overhead)
                                • Models: qwen2.5:7b (default) or qwen2.5:3b / llama3.2:3b (lightweight)
                                • Pipeline Capacity: Generation & layout discovery


Memory Sizing Validation Formulas

The system uses a strict threshold formula to calculate local model memory footprints ($W$, in GB), factoring in a $15\%$ context overhead limit:

$$W \approx P \cdot \frac{Q}{8} \cdot 1.15$$

Where $P$ is the parameter count in billions and $Q$ is the quantization depth in bits.

The generation throughput limit ($T$, in tokens per second) is bounded by active hardware memory bandwidth ($B$, in GB/s) relative to active weight size ($W$, in GB):

$$T \approx \frac{B}{W}$$

5. Technical Trade-offs Analysis

Architectural Design

Pros

Cons / Mitigations

Blueprint Replication Execution

• Inherits $100\%$ of template styling assets without manual canvas positioning logic.



• Retains vector layers.

• Requires designers to rigorously name and index their Master Slide elements beforehand.

Headless LibreOffice Rendering

• Allows automated validation of layout files completely within a Linux container sandbox.

• Minor formatting rendering discrepancies may appear compared to native Windows Microsoft PowerPoint.

Local Vision QA Verification Loop

• Cuts out external network delays and eliminates cloud data exposure during QA reviews.

• Demands high compute resources; requires a dedicated CUDA card to execute under production time-limits.

6. Automated Diagnostic Procedures

To verify that the underlying host system meets the necessary memory footprints and is prepared to process local models, run the following unified hardware-verification script in an administrative PowerShell console:

# Verify available operating system memory
$SysInfo = Get-CimInstance Win32_ComputerSystem
$TotalRAM = [math]::round($SysInfo.TotalPhysicalMemory / 1GB, 2)
Write-Output "Visible Operating System RAM: $TotalRAM GB"

# Verify active integrated Radeon graphics reservation thresholds
$GPUInfo = Get-CimInstance Win32_VideoController | Where-Object Name -like "*Radeon*"
if ($GPUInfo) {
    $VRAM = [math]::round($GPUInfo.AdapterRAM / 1GB, 2)
    Write-Output "AMD Radeon 780M VRAM Allocation: $VRAM GB"
    if ($VRAM -lt 8.0) {
        Write-Warning "System VRAM is set below 8.00 GB. Adjust your BIOS settings to avoid local LLM execution failures."
    } else {
        Write-Output "VRAM Allocation is optimal for local 3B/8B execution loops."
    }
} else {
    Write-Output "Physical Integrated Radeon 780M was not discovered on host."
}
