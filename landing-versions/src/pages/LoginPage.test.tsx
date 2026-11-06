import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "./LoginPage";
import { AuthContext, type AuthContextValue } from "@/context/auth";

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
});
