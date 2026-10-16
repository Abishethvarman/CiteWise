import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Landing } from "./pages/Landing";
import { Library } from "./pages/Library";
import { Research } from "./pages/Research";
import { SettingsPage } from "./pages/Settings";
import { Verify } from "./pages/Verify";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/app" element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="library" element={<Library />} />
        <Route path="research" element={<Research />} />
        <Route path="research/:sessionId" element={<Research />} />
        <Route path="verify/:turnId" element={<Verify />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
