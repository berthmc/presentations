import { StrictMode, useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { healthCheck, listTemplates } from "./api/client";
import { DiagnosticsCard } from "./components/DiagnosticsCard";
import { GenerateForm } from "./components/GenerateForm";
import { TemplateLibrary } from "./components/TemplateLibrary";
import type { GenerateResult, TemplateSummary } from "./types";
import "./styles/md3.css";

type TabId = "system" | "templates" | "brief";

const TABS: { id: TabId; label: string }[] = [
  { id: "system", label: "System" },
  { id: "templates", label: "Templates" },
  { id: "brief", label: "Brief" },
];

const STATUS_POLL_MS = 15_000;

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
  const [apiBadge, setApiBadge] = useState("…");
  const { dark, toggle: toggleTheme } = useTheme();

  const refreshApiBadge = useCallback(async () => {
    try {
      await healthCheck();
      setApiBadge("API online");
    } catch {
      setApiBadge("Backend offline");
    }
  }, []);

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
    refreshApiBadge();
    const id = window.setInterval(refreshApiBadge, STATUS_POLL_MS);
    return () => window.clearInterval(id);
  }, [refreshApiBadge]);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const selectedTemplate = templates.find((template) => template.id === templateId) ?? null;

  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className={`site-header${scrolled ? " is-scrolled" : ""}`} role="banner">
        <div className="header-inner">
          <span className="site-logo site-logo--gradient">Presentations@Carmélites</span>
          <nav className="main-nav" aria-label="Main navigation">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`md3-nav-link${activeTab === tab.id ? " is-active" : ""}`}
                aria-current={activeTab === tab.id ? "page" : undefined}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="header-actions">
            <span className="model-badge" title="API status">
              {apiBadge}
            </span>
            <button
              type="button"
              className="md3-icon-btn"
              onClick={toggleTheme}
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            >
              <span className="material-symbols-rounded">{dark ? "light_mode" : "dark_mode"}</span>
            </button>
          </div>
        </div>
      </header>

      <main id="main-content" className="site-main" role="main">
        {activeTab === "system" && (
          <div className="tab-panel" role="tabpanel" id="panel-system" aria-labelledby="tab-system">
            <DiagnosticsCard />
          </div>
        )}
        {activeTab === "templates" && (
          <div className="tab-panel" role="tabpanel" id="panel-templates" aria-labelledby="tab-templates">
            <TemplateLibrary
              selectedId={templateId}
              onSelect={setTemplateId}
              onModeHint={setMode}
            />
          </div>
        )}
        {activeTab === "brief" && (
          <div className="tab-panel" role="tabpanel" id="panel-brief" aria-labelledby="tab-brief">
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

      <footer className="site-footer" role="contentinfo">
        <div className="site-footer__inner">
          <p className="site-footer__brand">Presentations@Carmélites</p>
          <p className="site-footer__tagline">Local-first LLM presentation builder</p>
        </div>
      </footer>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
