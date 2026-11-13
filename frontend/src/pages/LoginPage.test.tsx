import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LoginPage from "./LoginPage";
import { HeroCopy } from "@/components/v1/HeroCopy";
import { V1ActionContext } from "@/components/v1/useV1Action";
import { AuthContext, type AuthContextValue } from "@/context/auth";
import { AuthProvider } from "@/context/AuthContext";
import * as authApi from "@/services/api/auth";

afterEach(() => vi.restoreAllMocks());

function renderLogin(auth: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = {
    status: "unauthenticated",
    user: null,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
    ...auth,
  };
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthContext.Provider value={value}>
        <LoginPage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
  return value;
}

describe("<LoginPage />", () => {
  it("can reveal and hide the password without submitting", async () => {
    const user = userEvent.setup();
    const auth = renderLogin();
    const password = screen.getByLabelText("Password", { exact: true });
    await user.type(password, "some-password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");
    expect(password).toHaveValue("some-password");
    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password).toHaveAttribute("type", "password");
    expect(auth.login).not.toHaveBeenCalled();
  });
  it("renders email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Password", { exact: true })).toBeInTheDocument();
  });

  it("validates empty fields without calling the API", async () => {
    const user = userEvent.setup();
    const auth = renderLogin();

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText(/enter your email address/i)).toBeInTheDocument();
    expect(screen.getByText(/enter your password/i)).toBeInTheDocument();
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("rejects a malformed email address", async () => {
    const user = userEvent.setup();
    const auth = renderLogin();

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.type(screen.getByLabelText("Password", { exact: true }), "hunter2");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText(/doesn't look like an email address/i)).toBeInTheDocument();
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("shows the server's message when credentials are wrong", async () => {
    const user = userEvent.setup();
    // Shape matches an AxiosError with a 401 JSON body (isAxiosError checks
    // the flag, not the prototype).
    const rejection = Object.assign(new Error("Request failed"), {
      isAxiosError: true,
      response: { status: 401, data: { error: "Incorrect email or password." } },
    });
    renderLogin({ login: vi.fn().mockRejectedValue(rejection) });

    await user.type(screen.getByLabelText(/email/i), "team@wahha.design");
    await user.type(screen.getByLabelText("Password", { exact: true }), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/incorrect email or password/i)).toBeInTheDocument();
  });

  it("submits valid credentials", async () => {
    const user = userEvent.setup();
    const auth = renderLogin();

    await user.type(screen.getByLabelText(/email/i), "team@wahha.design");
    await user.type(screen.getByLabelText("Password", { exact: true }), "some-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(auth.login).toHaveBeenCalledWith("team@wahha.design", "some-password");
  });

  it("returns from the hero sign-in to the primary View automations button", async () => {
    vi.spyOn(authApi, "getSession").mockResolvedValue(null);
    vi.spyOn(authApi, "login").mockResolvedValue({
      email: "team@example.com",
      name: "Team",
      role: "team",
    });
    const user = userEvent.setup();
    const runAction = vi.fn();
    render(
      <MemoryRouter>
        <AuthProvider>
          <V1ActionContext.Provider value={runAction}>
            <Routes>
              <Route path="/" element={<HeroCopy />} />
              <Route path="/login" element={<LoginPage />} />
            </Routes>
          </V1ActionContext.Provider>
        </AuthProvider>
      </MemoryRouter>,
    );

    const enter = await screen.findByRole("link", { name: "Enter Command Center" });
    expect(enter).toHaveAttribute("href", "/login");
    expect(screen.getByRole("button", { name: /view automations/i })).toHaveClass("v1-watch");
    await user.click(enter);

    await user.type(screen.getByLabelText(/email/i), "team@example.com");
    await user.type(screen.getByLabelText("Password", { exact: true }), "some-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    const automations = await screen.findByRole("button", { name: /view automations/i });
    expect(automations).toHaveClass("v1-cta");
    expect(screen.queryByRole("link", { name: "Enter Command Center" })).not.toBeInTheDocument();
    await user.click(automations);
    expect(runAction).toHaveBeenCalledWith({ kind: "automations" });
  });
});

describe("serverContinuation", () => {
  it("follows only the Content Atelier hand-off routes", async () => {
    const { serverContinuation } = await import("@/lib/serverContinuation");
    const authorize = "/api/auth/content-atelier/authorize?redirect_uri=x&state=y";
    expect(serverContinuation(`?next=${encodeURIComponent(authorize)}`)).toBe(authorize);
    expect(serverContinuation("?next=%2Fapi%2Fauth%2Fcontent-atelier%2Flaunch")).toBe("/api/auth/content-atelier/launch");
    for (const next of ["https://evil.example/api/auth/content-atelier/launch", "//evil.example", "/api/auth/logout",
      "/api/auth/content-atelier/exchange", "/api/auth/content-atelier/launchx", "/api/auth/content-atelier/launch\\evil"]) {
      expect(serverContinuation(`?next=${encodeURIComponent(next)}`)).toBeNull();
    }
    expect(serverContinuation("")).toBeNull();
  });
});
