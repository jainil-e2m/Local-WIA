import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RequireRole } from "./RequireRole";
import { AuthContext, type AuthContextValue } from "@/context/auth";
import type { AuthUser } from "@/services/api/auth";

const teamUser: AuthUser = { email: "team@wahha.design", name: "Team", role: "team" };
const clientUser: AuthUser = { email: "client@acme.com", name: "Client", role: "client" };

function renderGuarded(auth: Partial<AuthContextValue>, initialPath = "/secret") {
  const value: AuthContextValue = {
    status: "authenticated",
    user: null,
    login: async () => {},
    logout: async () => {},
    ...auth,
  };
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthContext.Provider value={value}>
        <Routes>
          <Route path="/" element={<div>home</div>} />
          <Route path="/login" element={<div>login</div>} />
          <Route element={<RequireRole allow={["team"]} />}>
            <Route path="/secret" element={<div>secret area</div>} />
          </Route>
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("<RequireRole />", () => {
  it("renders the route for an allowed role", () => {
    renderGuarded({ status: "authenticated", user: teamUser });
    expect(screen.getByText("secret area")).toBeInTheDocument();
  });

  it("redirects a signed-in but disallowed role to home", () => {
    renderGuarded({ status: "authenticated", user: clientUser });
    expect(screen.getByText("home")).toBeInTheDocument();
    expect(screen.queryByText("secret area")).not.toBeInTheDocument();
  });

  it("sends an unauthenticated visitor to login", () => {
    renderGuarded({ status: "unauthenticated", user: null });
    expect(screen.getByText("login")).toBeInTheDocument();
  });

  it("holds (renders nothing routable) while the session is loading", () => {
    renderGuarded({ status: "loading", user: null });
    expect(screen.queryByText("secret area")).not.toBeInTheDocument();
    expect(screen.queryByText("home")).not.toBeInTheDocument();
    expect(screen.queryByText("login")).not.toBeInTheDocument();
  });

  it("sends an authenticated-but-null user to login rather than crashing", () => {
    renderGuarded({ status: "authenticated", user: null });
    expect(screen.getByText("login")).toBeInTheDocument();
    expect(screen.queryByText("secret area")).not.toBeInTheDocument();
  });
});
