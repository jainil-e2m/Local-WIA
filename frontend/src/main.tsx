import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { RequireAuth } from "./components/RequireAuth";
import "./index.css";

// Route-level code splitting (Frontend SOP §7.1): the hub landing (App) loads
// eagerly; secondary pages are lazy-loaded so they don't bloat the main bundle.
const ToolPage = lazy(() => import("./pages/ToolPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const LeadMagnetDashboardPage = lazy(() => import("./pages/LeadMagnetDashboardPage"));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage"));
const InternalMeetingPage = lazy(() => import("./pages/InternalMeetingPage"));
const RollCallPage = lazy(() => import("./pages/RollCallPage"));

// Load the annotation toolbar only in development, across every route and variant.
const Agentation = import.meta.env.DEV
  ? lazy(() => import("agentation").then((module) => ({ default: module.Agentation })))
  : null;

// Minimal, on-brand fallback while a lazy route chunk loads.
const routeFallback = <div className="bg-hero min-h-[100svh]" aria-hidden />;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={routeFallback}>
          <Routes>
            {/* Public: landing + login. Everything else requires a session. */}
            <Route path="/" element={<App />} />
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/automations/:toolId" element={<ToolPage />} />
              <Route path="/history" element={<HistoryPage />} />
              {/* The lead console is for every signed-in account, not just team.
                  Mirrored by requireSession (and no role gate) on the
                  /api/leadmagnet/leads routes, which is the real boundary. */}
              <Route path="/leadmagnetdashboard" element={<LeadMagnetDashboardPage />} />
              {/* Client Onboarding has its own console rather than the generic
                  /automations/<id> audit stub — it is a review queue, not an
                  audit runner. Mirrored by requireSession on /api/onboarding/*. */}
              <Route path="/onboarding" element={<OnboardingPage />} />
              {/* Internal Meeting + Action Items runs entirely client-side: paste
                  intake, a local ledger, and a review that terminates at the
                  ledger write. There is deliberately no /api/* counterpart. */}
              <Route path="/internal-meeting" element={<InternalMeetingPage />} />
              {/* Roll call is client-side for the same reason: paste intake, a
                  local session store, and flags that terminate in the UI. */}
              <Route path="/roll-call" element={<RollCallPage />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
      {Agentation && (
        <Suspense fallback={null}>
          <Agentation />
        </Suspense>
      )}
    </BrowserRouter>
  </React.StrictMode>,
);
