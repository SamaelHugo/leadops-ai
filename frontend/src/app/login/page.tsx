"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { Button, ErrorNotice } from "@/components/ui";

export default function LoginPage() {
  const { login, registerOrganization, user, loading } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [organization, setOrganization] = useState("demo-leadops");
  const [organizationName, setOrganizationName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [email, setEmail] = useState("admin@demo.leadops.ai");
  const [password, setPassword] = useState("DemoLeadOps2026!");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, router, user]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        await registerOrganization({
          organization_name: organizationName,
          organization_slug: organization,
          admin_name: adminName,
          admin_email: email,
          password,
        });
      } else {
        await login(organization, email, password);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-visual">
        <div className="login-brand">
          <span className="brand-mark" aria-hidden="true">L/O</span>
          LeadOps AI
        </div>
        <div className="login-visual-copy">
          <span>Customer operations</span>
          <h1>Review every reply before it leaves.</h1>
          <p>
            LeadOps AI prepares replies from your knowledge base. Your team checks the source,
            edits the draft, and decides when to send it.
          </p>
        </div>
        <div className="login-proof">
          <span>Nothing reaches a customer or CRM until a teammate approves it.</span>
        </div>
      </section>

      <section className="login-form-side">
        <div className="login-card">
          <p className="eyebrow">Workspace access</p>
          <h2>{mode === "login" ? "Welcome back" : "Create an organization"}</h2>
          <p>{mode === "login" ? "Sign in to review the inbox and send approved replies." : "Set up a separate workspace and its first administrator account."}</p>
          {error ? <ErrorNotice message={error} /> : null}
          <form className="login-form" onSubmit={submit}>
            {mode === "register" ? (
              <>
                <div className="field">
                  <label htmlFor="organization-name">Organization name</label>
                  <input id="organization-name" className="field-control" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} required minLength={2} />
                </div>
                <div className="field">
                  <label htmlFor="admin-name">Administrator name</label>
                  <input id="admin-name" className="field-control" value={adminName} onChange={(event) => setAdminName(event.target.value)} required minLength={2} />
                </div>
              </>
            ) : null}
            <div className="field">
              <label htmlFor="organization">Organization URL</label>
              <input
                id="organization"
                className="field-control"
                value={organization}
                onChange={(event) => setOrganization(event.target.value)}
                autoComplete="organization"
                pattern="[a-z0-9-]+"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                className="field-control"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                className="field-control"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <Button type="submit" busy={busy}>{mode === "login" ? "Sign in" : "Create workspace"}</Button>
          </form>
          {mode === "login" ? (
            <div className="demo-credentials">
              <strong>Demo workspace</strong><br />
              The form is prefilled with the demo admin account. Every seeded record carries a Demo label.
            </div>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            style={{ width: "100%", marginTop: 12 }}
            onClick={() => {
              const nextMode = mode === "login" ? "register" : "login";
              setMode(nextMode);
              setError("");
              setOrganization(nextMode === "login" ? "demo-leadops" : "");
              setEmail(nextMode === "login" ? "admin@demo.leadops.ai" : "");
              setPassword(nextMode === "login" ? "DemoLeadOps2026!" : "");
            }}
          >
            {mode === "login" ? "Create a new organization" : "Back to sign in"}
          </Button>
        </div>
      </section>
    </div>
  );
}
