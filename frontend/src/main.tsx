import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { listTemplates } from "./api/client";
import { DiagnosticsCard } from "./components/DiagnosticsCard";
import { GenerateForm } from "./components/GenerateForm";
import { TemplateLibrary } from "./components/TemplateLibrary";
import type { GenerateResult, TemplateSummary } from "./types";
import "./styles/md3.css";

type TabId = "system" | "templates" | "brief";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "system", label: "System", icon: "memory" },
  { id: "templates", label: "Templates", icon: "dashboard_customize" },
  { id: "brief", label: "Brief", icon: "edit_note" },
];

function useTheme() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return localStorage.getItem("theme") === "dark";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return { dark, toggle: () => setDark((value) => !value) };
}

function App() {
  const [templateId, setTemplateId] = useState("");
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [mode, setMode] = useState<"scratch" | "template">("scratch");
  const [, setResult] = useState<GenerateResult | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("brief");
  const [scrolled, setScrolled] = useState(false);
  const { dark, toggle: toggleTheme } = useTheme();

  useEffect(() => {
    listTemplates()
      .then(({ templates: loaded }) => {
        setTemplates(loaded);
        setTemplateId((current) => {
          if (current) {
            return current;
          }
          const defaultTemplate = loaded.find((item) => item.is_default) ?? loaded[0];
          return defaultTemplate?.id ?? "";
        });
      })
      .catch(() => {
        /* template library unavailable; GenerateForm will surface errors on submit */
      });
  }, []);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 4);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const selectedTemplate = templates.find((template) => template.id === templateId) ?? null;

  return (
    <div className="app-layout">
      <header className={`top-app-bar${scrolled ? " scrolled" : ""}`}>
        <button type="button" className="icon-button" aria-label="Menu">
          <span className="material-symbols-rounded">menu</span>
        </button>
        <div>
          <h1 className="top-app-bar__title">Presentations@Carmélites</h1>
          <span className="top-app-bar__subtitle">Local-first LLM presentation builder</span>
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={toggleTheme}
          aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
        >
          <span className="material-symbols-rounded">{dark ? "light_mode" : "dark_mode"}</span>
        </button>
      </header>

      <nav className="nav-tabs" role="tablist" aria-label="Main navigation">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className="nav-tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="material-symbols-rounded nav-tab__icon">{tab.icon}</span>
            <span className="nav-tab__text">{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="app-shell">
        {activeTab === "system" && (
          <div
            className="tab-panel"
            role="tabpanel"
            id="panel-system"
            aria-labelledby="tab-system"
          >
            <DiagnosticsCard />
          </div>
        )}
        {activeTab === "templates" && (
          <div
            className="tab-panel"
            role="tabpanel"
            id="panel-templates"
            aria-labelledby="tab-templates"
          >
            <TemplateLibrary
              selectedId={templateId}
              onSelect={setTemplateId}
              onModeHint={setMode}
            />
          </div>
        )}
        {activeTab === "brief" && (
          <div
            className="tab-panel"
            role="tabpanel"
            id="panel-brief"
            aria-labelledby="tab-brief"
          >
            <GenerateForm
              templateId={templateId}
              templateSourceType={selectedTemplate?.source_type ?? null}
              mode={mode}
              onModeChange={setMode}
              onResult={setResult}
            />
          </div>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
