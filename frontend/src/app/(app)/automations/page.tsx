"use client";

import { CheckCircle2, RefreshCw, Webhook, XCircle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button, DemoBadge, EmptyState, ErrorNotice, PageHeader, Skeleton, StatusBadge, SuccessNotice } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { WebhookDelivery } from "@/lib/types";

export default function AutomationsPage() {
  const [deliveries, setDeliveries] = useState<WebhookDelivery[] | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => api.webhooks().then(setDeliveries), []);
  useEffect(() => {
    load().catch((caught) => setError(caught instanceof Error ? caught.message : "Webhook history failed to load."));
  }, [load]);

  async function retry(delivery: WebhookDelivery) {
    setBusy(delivery.id);
    setError("");
    setSuccess("");
    try {
      const result = await api.retryWebhook(delivery.id);
      setSuccess(`Webhook delivered on attempt ${result.attempt_count}.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Webhook retry failed.");
      await load();
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Workflow delivery"
        title="Automations"
        description="Inspect every n8n call. A failed delivery keeps its payload and can be retried without resending the customer reply."
        actions={<Link className="button secondary" href="/integrations">Configure n8n</Link>}
      />
      {error ? <ErrorNotice message={error} /> : null}
      {success ? <SuccessNotice message={success} /> : null}
      <section className="panel">
        <div className="panel-header"><div><h2>Webhook deliveries</h2><p>Most recent first</p></div></div>
        {deliveries === null ? (
          <div className="panel-body"><Skeleton /><div style={{ height: 12 }} /><Skeleton /></div>
        ) : deliveries.length === 0 ? (
          <EmptyState icon={Webhook} title="No webhook calls yet" description="Enable n8n in Integrations, then send an approved reply. The delivery will appear here." />
        ) : deliveries.map((delivery) => (
          <article className="delivery-card" key={delivery.id}>
            <span className={delivery.status === "failed" ? "delivery-icon failed" : "delivery-icon"}>
              {delivery.status === "failed" ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
            </span>
            <div className="delivery-copy">
              <header>
                <strong>{labelize(delivery.event)}</strong>
                <StatusBadge value={delivery.status} />
                {delivery.is_demo ? <DemoBadge /> : null}
              </header>
              <p>{delivery.target_url}</p>
              <small>
                Attempt {delivery.attempt_count} · {formatDate(delivery.last_attempt_at || delivery.created_at)}
                {delivery.response_status ? ` · HTTP ${delivery.response_status}` : ""}
                {delivery.conversation_id ? <> · <Link className="panel-link" href={`/inbox/${delivery.conversation_id}`}>Open inquiry</Link></> : null}
              </small>
              {delivery.last_error ? <p className="error-detail">{delivery.last_error}</p> : null}
            </div>
            {delivery.status === "failed" ? (
              <Button variant="secondary" busy={busy === delivery.id} onClick={() => void retry(delivery)}><RefreshCw size={14} />Retry</Button>
            ) : null}
          </article>
        ))}
      </section>
    </>
  );
}

