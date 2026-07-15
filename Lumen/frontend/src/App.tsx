import { useEffect, useState } from "react";
import AICostDashboard from "./pages/AICostDashboard";
import CloudCostExplorer from "./pages/CloudCostExplorer";
import ExecutiveOverview from "./pages/ExecutiveOverview";
import AnomaliesScreen from "./pages/AnomaliesScreen";
import BudgetsScreen from "./pages/BudgetsScreen";
import RecommendationsScreen from "./pages/RecommendationsScreen";
import CredentialManager from "./pages/CredentialManager";
import UserManagement from "./pages/UserManagement";
import "./styles/tokens.css";

type ViewId = "overview" | "explorer" | "ai" | "anomalies" | "budgets" | "recommendations" | "resources" | "tags" | "teams" | "reports" | "settings";

export default function AppRoot() {
  return <App user={null} onLogout={() => {}} />;
}

function App({ user, onLogout }: { user: any; onLogout: () => void }) {
  const [activeView, setActiveView] = useState<ViewId>("overview");

  function navigate(id: string) {
    setActiveView(id as ViewId);
  }

  function renderView() {
    switch (activeView) {
      case "overview": {
        const Ov = ExecutiveOverview as any;
        return <Ov onNavigate={navigate} />;
      }
      case "explorer": {
        const Ex = CloudCostExplorer as any;
        return <Ex onNavigate={navigate} />;
      }
      case "ai": {
        const Ai = AICostDashboard as any;
        return <Ai onNavigate={navigate} />;
      }
      case "anomalies": {
        const An = AnomaliesScreen as any;
        return <An onNavigate={navigate} />;
      }
      case "budgets": {
        const Bu = BudgetsScreen as any;
        return <Bu onNavigate={navigate} />;
      }
      case "recommendations": {
        const Re = RecommendationsScreen as any;
        return <Re onNavigate={navigate} />;
      }
      case "resources":
        return (
          <div className="lumen" style={{ height: "100vh" }}>
            <WIPContent title="Resources" navigate={navigate} active="resources" />
          </div>
        );
      case "tags":
        return (
          <div className="lumen" style={{ height: "100vh" }}>
            <WIPContent title="Tag Policy" navigate={navigate} active="tags" />
          </div>
        );
      case "teams": {
        const Um = UserManagement as any;
        return <Um onNavigate={navigate} />;
      }
      case "reports":
        return (
          <div className="lumen" style={{ height: "100vh" }}>
            <WIPContent title="Reports" navigate={navigate} active="reports" />
          </div>
        );
      case "settings": {
        const Cm = CredentialManager as any;
        return <Cm onNavigate={navigate} />;
      }
      default: {
        const Ov = ExecutiveOverview as any;
        return <Ov onNavigate={navigate} />;
      }
    }
  }

  return <>{renderView()}</>;
}

// WIP placeholder for screens not yet fully built
function WIPScreen({ title }: { title: string }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "var(--muted)", padding: 40 }}>
      <div style={{ fontSize: 36 }}>🚧</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "var(--ink)" }}>{title}</div>
      <div style={{ fontSize: 12, textAlign: "center", maxWidth: 360, color: "var(--text)" }}>
        Data infrastructure is ready — this UI screen is coming soon.
      </div>
      <span style={{ padding: "3px 10px", borderRadius: 4, background: "var(--warning-soft)", color: "var(--warning)", fontFamily: "var(--font-num)", fontSize: 11, fontWeight: 500 }}>Coming soon</span>
    </div>
  );
}

// WIP screen wrapper with sidebar
function WIPContent({ title, navigate, active }: { title: string; navigate: (id: string) => void; active: string }) {
  // Lazy import to avoid circular deps
  const [Sidebar, setSidebar] = useState<any>(null);
  const [Topbar, setTopbar] = useState<any>(null);

  useEffect(() => {
    import("./components/Shared.jsx").then(m => {
      setSidebar(() => m.Sidebar);
      setTopbar(() => m.Topbar);
    });
  }, []);

  if (!Sidebar || !Topbar) return null;

  return (
    <>
      <Sidebar active={active} onNavigate={navigate} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar crumbs={["Workspace", title]} />
        <WIPScreen title={title} />
      </div>
    </>
  );
}
