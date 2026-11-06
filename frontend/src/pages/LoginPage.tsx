import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { isAxiosError } from "axios";
import { AlertCircle, ArrowLeft, ArrowRight, Eye, EyeOff, LoaderCircle, Lock } from "lucide-react";
import { useEditorialFonts } from "@/hooks/useEditorialFonts";
import { useAuth } from "@/context/auth";
import { serverContinuation } from "@/lib/serverContinuation";
import "@/components/v1/v1.css";
import "./LoginPage.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;


export default function LoginPage() {
  useEditorialFonts();
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Where to land after signing in — the page the guard bounced them from.
  const destination = (location.state as { from?: { pathname: string; search?: string; hash?: string } } | null)?.from;
  const from = destination
    ? `${destination.pathname}${destination.search ?? ""}${destination.hash ?? ""}`
    : "/";
  // Signing in on the way to the Content Atelier: continue the hand-off (a full page load, since it is a server route).
  const continuation = serverContinuation(location.search);

  useEffect(() => {
    if (status === "authenticated" && continuation) window.location.assign(continuation);
  }, [status, continuation]);

  if (status === "authenticated") {
    return continuation ? <div className="v1 v1-login" aria-busy="true" /> : <Navigate to={from} replace />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();

    const errors: typeof fieldErrors = {};
    if (!email.trim()) errors.email = "Enter your email address.";
    else if (!EMAIL_RE.test(email.trim()))
      errors.email = "That doesn't look like an email address.";
    if (!password) errors.password = "Enter your password.";
    setFieldErrors(errors);
    setFormError(null);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      if (continuation) window.location.assign(continuation);
      else navigate(from, { replace: true });
    } catch (err) {
      if (isAxiosError(err) && err.response) {
        const message = (err.response.data as { error?: string } | undefined)?.error;
        setFormError(message ?? "Something went wrong. Please try again.");
      } else {
        setFormError("Can't reach the server. Check your connection and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="v1 v1-login">
      <header className="login-header">
        <Link to="/" className="login-brand" aria-label="Wedding Industry Ads — Command Center home">
          <img src="/logos/wia_logo.webp" alt="Wedding Industry Ads" />
          <span>Command Center</span>
        </Link>
        <Link to="/" className="login-back" aria-label="Back to home">
          <ArrowLeft size={16} aria-hidden /><span>Back to home</span>
        </Link>
      </header>

      <main className="login-layout">
        <motion.section
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: .6, ease: [0.22, 1, 0.36, 1] }}
          className="login-form-col" aria-labelledby="login-title"
        >
          <p className="login-eyebrow">Your workspace awaits</p>
          <h1 id="login-title" className="login-title">Welcome <em>back.</em></h1>
          <p className="login-description">Sign in to your Command Center. Your team, clients and automations, all in one place.</p>

          <form onSubmit={onSubmit} noValidate className="login-form" aria-busy={submitting}>
            <div>
              <label htmlFor="email" className="login-label">Email</label>
              <input id="email" type="email" autoComplete="email" inputMode="email"
                autoCapitalize="none" spellCheck={false} required disabled={submitting}
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@weddingindustryads.com" className="login-field"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined} />
              {fieldErrors.email && <p id="email-error" role="alert" className="login-field-error">{fieldErrors.email}</p>}
            </div>
            <div>
              <label htmlFor="password" className="login-label">Password</label>
              <div className="login-password">
                <input id="password" type={showPassword ? "text" : "password"}
                  autoComplete="current-password" required disabled={submitting}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password" className="login-field"
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined} />
                <button type="button" className="login-toggle" disabled={submitting}
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                  {showPassword ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
                </button>
              </div>
              {fieldErrors.password && <p id="password-error" role="alert" className="login-field-error">{fieldErrors.password}</p>}
            </div>
            {formError && <div role="alert" className="login-form-error"><AlertCircle size={17} className="shrink-0" aria-hidden />{formError}</div>}
            <button type="submit" disabled={submitting || status === "loading"} className="login-submit">
              {submitting ? "Signing in…" : "Sign in"}
              {submitting ? <LoaderCircle size={17} className="animate-spin" aria-hidden /> : <ArrowRight size={17} aria-hidden />}
            </button>
          </form>
          <p className="login-access"><Lock size={13} className="mt-0.5 shrink-0" aria-hidden />For team members and invited clients.</p>
        </motion.section>

        <aside className="login-visual" aria-label="Wedding Industry Ads">
          <div className="login-scene" aria-hidden>
            <img className="login-scene-bg" src="/variant-1/scene-background.webp" alt="" />
            <img className="login-scene-flowers" src="/variant-1/flower-scene-poster-v2.webp" alt="" />
          </div>
          <div className="login-visual-caption">
            <p>A little more space<br />for the bigger picture.</p>
            <span>Connected. Considered. All in one place.</span>
          </div>
        </aside>
      </main>
      <footer className="login-footer">Building a stronger wedding industry</footer>
    </div>
  );
}
