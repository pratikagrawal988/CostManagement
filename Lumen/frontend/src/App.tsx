import { useState } from "react";
import AICostDashboard from "./pages/AICostDashboard";
import CloudCostExplorer from "./pages/CloudCostExplorer";
import ExecutiveOverview from "./pages/ExecutiveOverview";
import AnomaliesScreen from "./pages/AnomaliesScreen";
import BudgetsScreen from "./pages/BudgetsScreen";
import RecommendationsScreen from "./pages/RecommendationsScreen";
import CredentialManager from "./pages/CredentialManager";
import UserManagement from "./pages/UserManagement";
import CostDashboardRouter from "./pages/CostDashboards";
import Resources from "./pages/Resources";
import TagPolicy from "./pages/TagPolicy";
import DatabricksDashboard from "./pages/DatabricksDashboard";
import "./styles/tokens.css";

type ViewId = "overview" | "explorer" | "ai" | "databricks" | "anomalies" | "budgets" | "recommendations" | "resources" | "tags" | "teams" | "reports" | "settings";

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
      case "databricks": {
        const Db = DatabricksDashboard as any;
        return <Db onNavigate={navigate} />;
      }
      case "resources": {
        const Rs = Resources as any;
        return <Rs onNavigate={navigate} />;
      }
      case "tags": {
        const Tp = TagPolicy as any;
        return <Tp onNavigate={navigate} />;
      }
      case "teams": {
        const Um = UserManagement as any;
        return <Um onNavigate={navigate} />;
      }
      case "reports": {
        const Rp = CostDashboardRouter as any;
        return <Rp onNavigate={navigate} />;
      }
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
