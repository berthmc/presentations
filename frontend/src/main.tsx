import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { DiagnosticsCard } from "./components/DiagnosticsCard";
import { GenerateForm } from "./components/GenerateForm";
import { TemplateLibrary } from "./components/TemplateLibrary";
import type { GenerateResult } from "./types";
import "./styles/md3.css";

function App() {
  const [templateId, setTemplateId] = useState("");
  const [mode, setMode] = useState<"scratch" | "template">("scratch");
  const [, setResult] = useState<GenerateResult | null>(null);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Presentations@Carmélites</h1>
        <p>Local-first LLM presentation builder with MD3 styling and visual QA</p>
      </header>
      <DiagnosticsCard />
      <TemplateLibrary
        selectedId={templateId}
        onSelect={setTemplateId}
        onModeHint={setMode}
      />
      <GenerateForm
        templateId={templateId}
        mode={mode}
        onModeChange={setMode}
        onResult={setResult}
      />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
