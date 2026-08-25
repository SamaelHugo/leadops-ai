"use client";

import { Check, LockKeyhole, MessageSquareText, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, DemoBadge, ErrorNotice, Skeleton } from "@/components/ui";
import { publicRequest } from "@/lib/api";

interface FormConfig {
  organization_name: string;
  organization_slug: string;
  is_demo: boolean;
}

interface InquiryResult {
  reference: string;
  status: string;
  message: string;
}

export default function PublicContactPage() {
  const params = useParams<{ slug: string }>();
  const [config, setConfig] = useState<FormConfig | null>(null);
  const [result, setResult] = useState<InquiryResult | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    publicRequest<FormConfig>(`/api/public/${params.slug}`)
      .then(setConfig)
      .catch((caught) => setError(caught instanceof Error ? caught.message : "This form is not available."));
  }, [params.slug]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await publicRequest<InquiryResult>(`/api/public/${params.slug}/inquiries`, {
        method: "POST",
        body: JSON.stringify({ name, email, company: company || null, subject, message }),
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your message could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  if (!config && !error) {
    return <div className="public-page"><div className="public-layout"><Skeleton /><Skeleton /></div></div>;
  }

  return (
    <div className="public-page">
      <header className="public-topbar">
        <div className="public-brand"><span className="brand-mark small" aria-hidden="true">L/O</span>LeadOps AI</div>
        <div className="public-safe"><LockKeyhole size={13} />Your message is reviewed by a person before a reply is sent</div>
      </header>
      <main className="public-layout">
        <section className="public-copy">
          <p className="eyebrow">Contact {config?.organization_name || "the team"}</p>
          <h1>Tell us what you need.</h1>
          <p>
            Share the details the team needs to handle your request. A person will review the reply
            and its sources before it is sent.
          </p>
          <div className="public-points">
            <div className="public-point"><span><Check size={13} /></span>Your message gets a clear reference number</div>
            <div className="public-point"><span><ShieldCheck size={13} /></span>A team member checks the reply</div>
            <div className="public-point"><span><MessageSquareText size={13} /></span>Urgent requests are flagged in the inbox</div>
          </div>
        </section>

        {result ? (
          <section className="public-form-card success-card">
            <span><Check size={25} /></span>
            <h2>Message received</h2>
            <p>{result.message}</p>
            <div className="success-reference">Reference {result.reference}</div>
            <Link className="button secondary" style={{ marginTop: 14 }} href={`/contact/${params.slug}/status/${result.reference}`}>Check reply status</Link>
          </section>
        ) : (
          <form className="public-form-card" onSubmit={submit}>
            <h2>Send a message {config?.is_demo ? <DemoBadge /> : null}</h2>
            <p>{config?.is_demo ? "This demo creates a real demo inquiry in the LeadOps AI inbox." : "Required fields are marked in the form."}</p>
            {error ? <ErrorNotice message={error} /> : null}
            <div className="field-grid">
              <div className="field"><label htmlFor="name">Name</label><input id="name" className="field-control" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} /></div>
              <div className="field"><label htmlFor="email">Email</label><input id="email" className="field-control" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div>
              <div className="field full"><label htmlFor="company">Company (optional)</label><input id="company" className="field-control" value={company} onChange={(event) => setCompany(event.target.value)} /></div>
              <div className="field full"><label htmlFor="subject">Subject</label><input id="subject" className="field-control" value={subject} onChange={(event) => setSubject(event.target.value)} required minLength={3} /></div>
              <div className="field full"><label htmlFor="message">How can we help?</label><textarea id="message" className="field-control" value={message} onChange={(event) => setMessage(event.target.value)} required minLength={10} placeholder="Include an order number, affected product, or deadline if it matters." /></div>
            </div>
            <div className="form-actions"><Button type="submit" busy={busy}>Send message</Button></div>
          </form>
        )}
      </main>
    </div>
  );
}
