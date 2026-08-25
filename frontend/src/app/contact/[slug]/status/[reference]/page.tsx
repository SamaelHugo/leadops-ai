"use client";

import { CheckCircle2, Clock3, MailCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Button, ErrorNotice, StatusBadge } from "@/components/ui";
import { publicRequest } from "@/lib/api";
import { formatDate } from "@/lib/format";

interface InquiryStatus {
  reference: string;
  subject: string;
  status: string;
  replies: Array<{ body: string; sent_at: string }>;
}

export default function InquiryStatusPage() {
  const params = useParams<{ slug: string; reference: string }>();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<InquiryStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function checkStatus(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await publicRequest<InquiryStatus>(
        `/api/public/${params.slug}/inquiries/${params.reference}?email=${encodeURIComponent(email)}`,
      );
      setStatus(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The inquiry could not be found.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="public-page">
      <header className="public-topbar">
        <Link className="public-brand" href={`/contact/${params.slug}`}><span className="brand-mark small" aria-hidden="true">L/O</span>LeadOps AI</Link>
        <span className="public-safe">Inquiry {params.reference}</span>
      </header>
      <main style={{ width: "min(680px, 100%)", margin: "0 auto" }}>
        <section className="public-form-card">
          <p className="eyebrow">Customer reply portal</p>
          <h2>Check your inquiry</h2>
          <p>Enter the same email address you used on the contact form.</p>
          {error ? <ErrorNotice message={error} /> : null}
          <form onSubmit={checkStatus}>
            <div className="field">
              <label htmlFor="status-email">Email</label>
              <input id="status-email" className="field-control" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div className="form-actions"><Button type="submit" busy={busy}>Check status</Button></div>
          </form>

          {status ? (
            <div style={{ marginTop: 24, paddingTop: 22, borderTop: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16 }}>
                <div><strong style={{ fontSize: 13 }}>{status.subject}</strong><p style={{ margin: "5px 0 0", color: "var(--muted)", fontSize: 10 }}>Reference {status.reference}</p></div>
                <StatusBadge value={status.status} />
              </div>
              {status.replies.length ? status.replies.map((reply) => (
                <article className="source-card" key={reply.sent_at} style={{ marginTop: 10 }}>
                  <header><strong><MailCheck size={13} style={{ verticalAlign: "middle", marginRight: 6 }} />Team reply</strong><span>{formatDate(reply.sent_at)}</span></header>
                  <p style={{ display: "block", fontSize: 11, whiteSpace: "pre-wrap" }}>{reply.body}</p>
                </article>
              )) : (
                <div className="notice warning" style={{ margin: 0 }}><Clock3 size={16} /><span>The team is still reviewing the reply. Check again later with the same reference and email.</span></div>
              )}
              {status.replies.length ? <div className="notice success" style={{ margin: "12px 0 0" }}><CheckCircle2 size={16} /><span>This reply was approved by a team member before it was published.</span></div> : null}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}
