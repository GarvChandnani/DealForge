import { useState, type FormEvent } from "react";
import {
  ArrowUpRight, BriefcaseBusiness, Check, ChevronRight, Eye, EyeOff,
  LockKeyhole, ShieldCheck, Sparkles, TrendingUp, Zap,
} from "lucide-react";
import { authApi } from "../api/client";

interface AuthPageProps {
  onAuthenticated: (token: string) => void;
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [organizationName, setOrganizationName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const { data } = isRegistering
        ? await authApi.register({
            organization_name: organizationName,
            full_name: fullName,
            email,
            password,
          })
        : await authApi.login(email, password);
      localStorage.setItem("dealforge_token", data.access_token);
      onAuthenticated(data.access_token);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to authenticate. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <div className="auth-brand">
          <span className="auth-brand-icon"><Zap size={19} fill="currentColor" /></span>
          <span><strong>dealforge</strong><small>CAPITAL WORKSPACE</small></span>
        </div>
        <div className="auth-story-content">
          <span className="auth-kicker"><span className="live-dot" /> PRIVATE MARKETS, IN FOCUS</span>
          <h1>From first look<br />to <span>final close.</span></h1>
          <p>One trusted workspace for the relationships, intelligence, and execution behind every exceptional deal.</p>
          <div className="auth-visual">
            <div className="auth-chart-head"><span>PORTFOLIO SIGNALS</span><span className="auth-chart-range">LAST 90 DAYS <ChevronRight size={12} /></span></div>
            <div className="auth-chart"><div className="chart-grid"><i /><i /><i /><i /></div><div className="chart-line"><svg viewBox="0 0 540 150" preserveAspectRatio="none" aria-label="Illustrative deal pipeline trend"><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#68aaff" stopOpacity=".25" /><stop offset="100%" stopColor="#68aaff" stopOpacity="0" /></linearGradient></defs><path className="chart-area" d="M0 126 C32 118 36 96 71 101 S113 116 147 91 S191 85 220 96 S271 80 298 69 S347 79 375 56 S411 65 440 48 S488 57 540 18 L540 150 L0 150 Z" /><path className="chart-stroke" d="M0 126 C32 118 36 96 71 101 S113 116 147 91 S191 85 220 96 S271 80 298 69 S347 79 375 56 S411 65 440 48 S488 57 540 18" /></svg></div><div className="chart-axis"><span>SEP 01</span><span>SEP 15</span><span>OCT 01</span><span>OCT 15</span><span>NOV 01</span></div></div>
            <div className="auth-chart-foot"><span><i /> Opportunity value</span><strong><TrendingUp size={14} /> 18.6% <small>Illustrative</small></strong></div>
          </div>
          <div className="auth-proof-row"><span><ShieldCheck size={15} /> Tenant-isolated</span><span><LockKeyhole size={14} /> Encrypted by design</span><span><Sparkles size={14} /> AI-assisted origination</span></div>
        </div>
        <div className="auth-story-footer"><span>DEALFORGE CAPITAL WORKSPACE</span><span>CONFIDENTIAL · SELECTION TASK DEVELOPMENT PLANNER</span></div>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-top"><span>Already a member?</span><button onClick={() => { setError(""); setIsRegistering((current) => !current); }} type="button">{isRegistering ? "Sign in" : "Create account"} <ArrowUpRight size={13} /></button></div>
        <div className="auth-card">
          <div className="auth-mobile-brand"><BriefcaseBusiness size={17} /> DEALFORGE</div>
          <span className="auth-eyebrow">{isRegistering ? "NEW ORGANIZATION" : "SECURE WORKSPACE ACCESS"}</span>
          <h2>{isRegistering ? "Build your workspace" : "Welcome back"}</h2>
          <p className="auth-subtitle">{isRegistering ? "Create your organization and invite your deal team when you’re ready." : "Sign in to continue to your organization’s private deal workspace."}</p>

          <form className="auth-form" onSubmit={submit}>
            {isRegistering && <>
              <label>Organization name<input autoComplete="organization" maxLength={200} minLength={2} onChange={(event) => setOrganizationName(event.target.value)} placeholder="e.g. Northstar Capital" required value={organizationName} /></label>
              <label>Your full name<input autoComplete="name" maxLength={200} onChange={(event) => setFullName(event.target.value)} placeholder="Name as it appears to your team" required value={fullName} /></label>
            </>}
            <label>Work email<input autoComplete="email" onChange={(event) => setEmail(event.target.value)} placeholder="you@organization.com" required type="email" value={email} /></label>
            <label>Password
              <span className="password-field"><input autoComplete={isRegistering ? "new-password" : "current-password"} minLength={8} onChange={(event) => setPassword(event.target.value)} placeholder={isRegistering ? "Create a secure password" : "Enter your password"} required type={showPassword ? "text" : "password"} value={password} /><button aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((current) => !current)} type="button">{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span>
            </label>

            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" disabled={isSubmitting} type="submit">{isSubmitting ? <span className="button-spinner" /> : <>{isRegistering ? "Create secure workspace" : "Sign in securely"}<ArrowUpRight size={15} /></>}</button>
          </form>

          <div className="auth-trust"><ShieldCheck size={15} /><span><strong>Your workspace stays yours.</strong><small>Organization-scoped access controls protect your deal data.</small></span></div>
          <div className="auth-divider"><span /> OR <span /></div>
          <button className="auth-switch" onClick={() => { setError(""); setIsRegistering((current) => !current); }} type="button">{isRegistering ? "Already have a workspace?" : "Setting up DealForge for your firm?"}<strong>{isRegistering ? " Sign in" : " Create an organization"}</strong></button>
        </div>
        <footer className="auth-legal"><span>© 2026 DealForge</span><span><Check size={12} /> Confidential workspace</span><a href="mailto:support@dealforge.example">Need assistance?</a></footer>
      </section>
    </main>
  );
}
