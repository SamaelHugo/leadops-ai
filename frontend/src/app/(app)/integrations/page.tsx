"use client";

import { DatabaseZap, FlaskConical, RefreshCw, Workflow } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { Button, ErrorNotice, PageHeader, Skeleton, StatusBadge, SuccessNotice, WarningNotice } from "@/components/ui";
import { api } from "@/lib/api";
import type { Integration } from "@/lib/types";

export default function IntegrationsPage() {
  const { user } = useAuth();
  const [integrations, setIntegrations] = useState<Integration[] | null>(null);
  const [crmProvider, setCrmProvider] = useState<"test" | "hubspot">("test");
  const [crmEnabled, setCrmEnabled] = useState(true);
  const [crmToken, setCrmToken] = useState("");
  const [createObject, setCreateObject] = useState<"ticket" | "deal">("ticket");
  const [pipeline, setPipeline] = useState("");
  const [stage, setStage] = useState("");
  const [n8nUrl, setN8nUrl] = useState("");
  const [n8nSecret, setN8nSecret] = useState("");
  const [n8nEnabled, setN8nEnabled] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const canManage = user?.role === "admin";

  const load = useCallback(async () => {
    const rows = await api.integrations();
    setIntegrations(rows);
    const crm = rows.find((item) => item.kind === "crm");
    if (crm) {
      setCrmProvider(crm.provider === "hubspot" ? "hubspot" : "test");
      setCrmEnabled(crm.enabled);
      setCreateObject(crm.config.create_object === "deal" ? "deal" : "ticket");
      setPipeline(String(crm.config.pipeline || ""));
      setStage(String(crm.config.stage || ""));
    }
    const workflow = rows.find((item) => item.kind === "workflow");
    if (workflow) {
      setN8nUrl(String(workflow.config.webhook_url || ""));
      setN8nEnabled(workflow.enabled);
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function fetchIntegrations() {
      try {
        const rows = await api.integrations();
        if (!active) return;
        setIntegrations(rows);
        const crm = rows.find((item) => item.kind === "crm");
        if (crm) {
          setCrmProvider(crm.provider === "hubspot" ? "hubspot" : "test");
          setCrmEnabled(crm.enabled);
          setCreateObject(crm.config.create_object === "deal" ? "deal" : "ticket");
          setPipeline(String(crm.config.pipeline || ""));
          setStage(String(crm.config.stage || ""));
        }
        const workflow = rows.find((item) => item.kind === "workflow");
        if (workflow) {
          setN8nUrl(String(workflow.config.webhook_url || ""));
          setN8nEnabled(workflow.enabled);
        }
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Integrations failed to load.");
      }
    }
    void fetchIntegrations();
    return () => { active = false; };
  }, []);

  async function saveCrm(event: React.FormEvent) {
    event.preventDefault();
    setBusy("crm");
    setError("");
    setSuccess("");
    try {
      await api.configureCrm({
        provider: crmProvider,
        access_token: crmToken || null,
        enabled: crmEnabled,
        create_object: createObject,
        pipeline: pipeline || null,
        stage: stage || null,
      });
      setCrmToken("");
      await load();
      setSuccess(`${crmProvider === "hubspot" ? "HubSpot" : "Test CRM"} settings were saved.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CRM settings could not be saved.");
    } finally {
      setBusy("");
    }
  }

  async function testCrm() {
    setBusy("crm-test");
    setError("");
    setSuccess("");
    try {
      const integration = await api.testCrm();
      await load();
      if (integration.last_test_status === "connected") setSuccess("CRM connection succeeded.");
      else setError(integration.last_test_error || "CRM connection failed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CRM connection failed.");
    } finally {
      setBusy("");
    }
  }

  async function saveN8n(event: React.FormEvent) {
    event.preventDefault();
    setBusy("n8n");
    setError("");
    setSuccess("");
    try {
      await api.configureN8n({ webhook_url: n8nUrl, signing_secret: n8nSecret || null, enabled: n8nEnabled });
      setN8nSecret("");
      await load();
      setSuccess("n8n webhook settings were saved. The next approved reply will use them.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "n8n settings could not be saved.");
    } finally {
      setBusy("");
    }
  }

  const crm = integrations?.find((item) => item.kind === "crm");
  const workflow = integrations?.find((item) => item.kind === "workflow");

  return (
    <>
      <PageHeader
        eyebrow="Systems / Destinations"
        title="Connect what happens next."
        description="Choose where approved inquiries go. Access tokens are encrypted by the backend and never returned to this page."
      />
      {error ? <ErrorNotice message={error} /> : null}
      {success ? <SuccessNotice message={success} /> : null}
      {!canManage ? <WarningNotice message="Only an administrator can change integration settings." /> : null}
      {integrations === null ? <div className="integration-grid"><Skeleton /><Skeleton /></div> : (
        <div className="integration-grid">
          <form className="panel integration-card" onSubmit={saveCrm}>
            <div className="panel-header">
              <div className="integration-heading">
                <span className="integration-logo"><DatabaseZap size={20} /></span>
                <div><h2>CRM</h2><p>Test adapter or HubSpot private app</p></div>
              </div>
              {crm?.last_test_status ? <StatusBadge value={crm.last_test_status} /> : <StatusBadge value={crmEnabled ? "connected" : "disabled"} />}
            </div>
            <div className="panel-body">
              <div className="segmented">
                <button type="button" className={crmProvider === "test" ? "active" : ""} onClick={() => setCrmProvider("test")} disabled={!canManage}>Test CRM</button>
                <button type="button" className={crmProvider === "hubspot" ? "active" : ""} onClick={() => setCrmProvider("hubspot")} disabled={!canManage}>HubSpot</button>
              </div>
              {crmProvider === "test" ? (
                <div className="secret-note"><FlaskConical size={14} style={{ verticalAlign: "middle", marginRight: 7 }} />The test adapter writes a clearly marked demo CRM record into LeadOps AI. It needs no external account.</div>
              ) : (
                <div className="field">
                  <label htmlFor="hubspot-token">Private app access token</label>
                  <input id="hubspot-token" className="field-control" type="password" value={crmToken} onChange={(event) => setCrmToken(event.target.value)} placeholder={crm?.has_secret ? "Token stored. Enter a new one to replace it." : "pat-na1-..."} disabled={!canManage} />
                  <small>Required scopes: contact read/write and ticket or deal write.</small>
                </div>
              )}
              <div className="field-grid">
                <div className="field">
                  <label htmlFor="crm-object">Create in CRM</label>
                  <select id="crm-object" className="field-control" value={createObject} onChange={(event) => setCreateObject(event.target.value as "ticket" | "deal")} disabled={!canManage}>
                    <option value="ticket">Ticket</option><option value="deal">Deal</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="pipeline">Pipeline</label>
                  <input id="pipeline" className="field-control" value={pipeline} onChange={(event) => setPipeline(event.target.value)} placeholder="Use provider default" disabled={!canManage} />
                </div>
                <div className="field full">
                  <label htmlFor="stage">Pipeline stage</label>
                  <input id="stage" className="field-control" value={stage} onChange={(event) => setStage(event.target.value)} placeholder="Use provider default" disabled={!canManage} />
                </div>
              </div>
              <div className="toggle-row">
                <div><strong>CRM sync</strong><span>Run after an approved reply is sent</span></div>
                <button type="button" className={crmEnabled ? "toggle on" : "toggle"} onClick={() => setCrmEnabled((value) => !value)} disabled={!canManage} aria-label="Toggle CRM sync"><i /></button>
              </div>
              {crm?.last_test_error ? <ErrorNotice message={crm.last_test_error} /> : null}
              <div className="form-actions">
                <Button type="submit" busy={busy === "crm"} disabled={!canManage}>Save CRM</Button>
                <Button type="button" variant="secondary" busy={busy === "crm-test"} disabled={!canManage} onClick={() => void testCrm()}><RefreshCw size={14} />Test connection</Button>
              </div>
            </div>
          </form>

          <form className="panel integration-card" onSubmit={saveN8n}>
            <div className="panel-header">
              <div className="integration-heading">
                <span className="integration-logo"><Workflow size={20} /></span>
                <div><h2>n8n</h2><p>Webhook after CRM sync</p></div>
              </div>
              <StatusBadge value={workflow?.enabled ? "connected" : "disabled"} />
            </div>
            <div className="panel-body">
              <div className="field">
                <label htmlFor="n8n-url">Production webhook URL</label>
                <input id="n8n-url" className="field-control" type="url" value={n8nUrl} onChange={(event) => setN8nUrl(event.target.value)} placeholder="http://n8n:5678/webhook/leadops-demo" disabled={!canManage} required />
                <small>LeadOps AI posts `conversation.sent` with the customer, classification, and reference.</small>
              </div>
              <div className="field">
                <label htmlFor="n8n-secret">Signing secret</label>
                <input id="n8n-secret" className="field-control" type="password" value={n8nSecret} onChange={(event) => setN8nSecret(event.target.value)} placeholder={workflow?.has_secret ? "Secret stored. Enter a new one to replace it." : "Optional HMAC secret"} disabled={!canManage} />
                <small>The signature is sent in `X-LeadOps-Signature` as SHA-256 HMAC.</small>
              </div>
              <div className="toggle-row">
                <div><strong>Webhook delivery</strong><span>Failures stay in Automations and can be retried</span></div>
                <button type="button" className={n8nEnabled ? "toggle on" : "toggle"} onClick={() => setN8nEnabled((value) => !value)} disabled={!canManage} aria-label="Toggle n8n webhook"><i /></button>
              </div>
              <div className="secret-note">The bundled Docker setup includes an n8n demo workflow. Enable this integration after n8n is running.</div>
              <div className="form-actions"><Button type="submit" busy={busy === "n8n"} disabled={!canManage}>Save n8n</Button></div>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
