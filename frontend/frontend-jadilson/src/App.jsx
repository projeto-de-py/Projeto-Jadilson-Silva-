import { MotionConfig } from "motion/react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./app/layouts/DashboardLayout";
import { ToastProvider } from "./components/ui";
import { AuthPage } from "./pages/Login/AuthPage";
import { DesignSystemPage } from "./pages/DesignSystem/DesignSystemPage";
import { Home } from "./pages/DashBoard/Home/Home";
import { Processos } from "./pages/DashBoard/Processos/Processos";
import { Prazos } from "./pages/DashBoard/Prazos/Prazos";
import { Agenda } from "./pages/DashBoard/Agenda/Agenda";
import { Clientes } from "./pages/DashBoard/Clientes/Clientes";
import { Configuracoes } from "./pages/DashBoard/Configuracoes/Configurations";

function App() {
  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthPage />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/design-system" element={<DesignSystemPage />} />

            <Route element={<DashboardLayout />}>
              <Route path="/home" element={<Home />} />
              <Route path="/processos" element={<Processos />} />
              <Route path="/prazos" element={<Prazos />} />
              <Route path="/agenda" element={<Agenda />} />
              <Route path="/clientes" element={<Clientes />} />
              <Route path="/configuracoes" element={<Configuracoes />} />
            </Route>

            <Route path="*" element={<Navigate to="/home" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </MotionConfig>
  );
}

export default App;
