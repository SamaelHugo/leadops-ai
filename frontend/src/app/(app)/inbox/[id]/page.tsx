"use client";

import {
  ArrowLeft,
  Check,
  ExternalLink,
  RefreshCw,
  Save,
  Send,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Button,
  Confidence,
  DemoBadge,
  ErrorNotice,
  Skeleton,
  StatusBadge,
  SuccessNotice,
  WarningNotice,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { ConversationDetail, SendResult, User } from "@/lib/types";

export default function ConversationPage() {
  const params = useParams<{ id: string }>();
  const conversationId = params.id;
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [members, setMembers] = useState<User[]>([]);
  const [draftBody, setDraftBody] = useState("");
  const [escalationNote, setEscalationNote] = useState("");
  const [escalationTarget, setEscalationTarget] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    const [detail, team] = await Promise.all([api.conversation(conversationId), api.members()]);
    setConversation(detail);
    setMembers(team);
    setDraftBody(detail.draft?.body || "");
    setEscalationTarget(detail.assigned_to_id || "");
  }, [conversationId]);

  useEffect(() => {
    let active = true;
    async function fetchConversation() {
      try {
        const [detail, team] = await Promise.all([api.conversation(conversationId), api.members()]);
        if (!active) return;
        setConversation(detail);
        setMembers(team);
        setDraftBody(detail.draft?.body || "");
        setEscalationTarget(detail.assigned_to_id || "");
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Conversation failed to load.");
      }
    }
    void fetchConversation();
    return () => { active = false; };
  }, [conversationId]);

  async function perform(label: string, action: () => Promise<unknown>, message?: string) {
    setBusy(label);
    setError("");
    setSuccess("");
    try {
      const result = await action();
      await load();
      if (message) setSuccess(message);
      return result;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The action failed.");
      return null;
    } finally {
      setBusy("");
    }
  }

  async function sendReply() {
    const result = (await perform("send", () => api.sendDraft(conversationId))) as SendResult | null;
    if (!result) return;
    const crm = result.crm_record
      ? `${labelize(result.crm_record.provider)} ${result.crm_record.object_type} ${result.crm_record.external_id}`
      : "No CRM sync was configured";
    const webhook = result.webhook_delivery
      ? `n8n webhook ${result.webhook_delivery.status}`
      : "No n8n webhook was configured";
    setSuccess(`Reply sent. ${crm}. ${webhook}.`);
  }

  if (!conversation && !error) {
    return (
      <>
        <Skeleton className="conversation-header-skeleton" />
        <div style={{ height: 18 }} />
        <div className="conversation-layout"><Skeleton /><Skeleton /></div>
      </>
    );
  }

  if (!conversation) {
    return <ErrorNotice message={error || "Conversation not found."} />;
  }

  const draft = conversation.draft;
  const isSent = conversation.status === "sent" || draft?.status === "sent";
  const isDirty = Boolean(draft && draftBody !== draft.body);

  return (
    <>
      <Link className="back-link" href="/inbox"><ArrowLeft size={15} />Back to inbox</Link>
      <header className="page-header">
        <div>
          <p className="eyebrow">Inquiry #{conversation.public_reference}</p>
          <h1>{conversation.subject}</h1>
          <p>{conversation.customer_name} · {conversation.customer_company || conversation.customer_email}</p>
          <div className="conversation-meta">
            <StatusBadge value={conversation.status} />
            <span className="status-badge">{labelize(conversation.category)}</span>
            <span className={`priority ${conversation.urgency}`}>{labelize(conversation.urgency)} urgency</span>
            {conversation.is_demo ? <DemoBadge /> : null}
          </div>
        </div>
        <div className="page-actions">
          <Button
            variant="secondary"
            busy={busy === "regenerate"}
            disabled={isSent}
            onClick={() => void perform("regenerate", () => api.regenerateDraft(conversationId), "A fresh draft is ready for review.")}
          >
            <RefreshCw size={15} />Regenerate
          </Button>
          <Button
            variant="danger"
            busy={busy === "escalate"}
            disabled={isSent}
            onClick={() => void perform("escalate", () => api.escalate(conversationId, escalationTarget || null, escalationNote), "The inquiry was escalated.")}
          >
            <ShieldAlert size={15} />Escalate
          </Button>
        </div>
      </header>

      {error ? <ErrorNotice message={error} /> : null}
      {success ? <SuccessNotice message={success} /> : null}
      {isDirty ? <WarningNotice message="The draft has unsaved edits. Save them before approving." /> : null}

      <div className="conversation-layout">
        <div style={{ display: "grid", gap: 18 }}>
          <section className="panel">
            <div className="panel-header">
              <div><h2>Conversation</h2><p>Customer messages and approved replies</p></div>
            </div>
            <div className="panel-body thread">
              {conversation.messages.map((message) => (
                <div className={`message-row ${message.role}`} key={message.id}>
                  <span className="message-avatar">
                    {message.role === "customer" ? conversation.customer_name.slice(0, 2).toUpperCase() : message.role === "internal" ? "IN" : "US"}
                  </span>
                  <div className="message-bubble">
                    {message.body}
                    <span className="message-time">{formatDate(message.created_at)} · {labelize(message.status)}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div><h2>Reply draft</h2><p>Edit the text, approve it, then send it</p></div>
              {draft ? <StatusBadge value={draft.status} /> : null}
            </div>
            <div className="panel-body">
              {draft ? (
                <>
                  <textarea
                    className="draft-editor"
                    aria-label="Reply draft"
                    value={draftBody}
                    onChange={(event) => setDraftBody(event.target.value)}
                    disabled={isSent}
                  />
                  <div className="draft-actions">
                    <Button
                      variant="secondary"
                      busy={busy === "save"}
                      disabled={!isDirty || isSent}
                      onClick={() => void perform("save", () => api.updateDraft(conversationId, draftBody), "Your edit was saved. Approval was reset for safety.")}
                    >
                      <Save size={15} />Save edit
                    </Button>
                    <Button
                      variant="secondary"
                      busy={busy === "approve"}
                      disabled={isDirty || isSent || draft.status === "approved"}
                      onClick={() => void perform("approve", () => api.approveDraft(conversationId), "Draft approved. It is ready to send.")}
                    >
                      <Check size={15} />Approve
                    </Button>
                    <Button
                      busy={busy === "send"}
                      disabled={isDirty || isSent || draft.status !== "approved"}
                      onClick={() => void sendReply()}
                    >
                      <Send size={15} />Send reply
                    </Button>
                  </div>
                </>
              ) : (
                <WarningNotice message="No draft is available. Generate one before sending a reply." />
              )}
            </div>
          </section>
        </div>

        <aside className="conversation-sidebar">
          {draft ? (
            <section className="panel">
              <div className="panel-header"><div><h3>AI review</h3><p>{labelize(draft.provider)} provider</p></div></div>
              <div className="panel-body">
                <Confidence value={draft.confidence} />
              </div>
            </section>
          ) : null}

          <section className="panel">
            <div className="panel-header"><div><h3>Sources</h3><p>Passages used in this draft</p></div></div>
            <div className="panel-body source-list">
              {draft?.sources.length ? draft.sources.map((source) => (
                <article className="source-card" key={source.id}>
                  <header>
                    <strong>[{source.rank}] {source.title}</strong>
                    {source.source_url ? <a href={source.source_url} target="_blank" rel="noreferrer" aria-label={`Open ${source.title}`}><ExternalLink size={13} /></a> : <span>{Math.round(source.score * 100)}%</span>}
                  </header>
                  <p>{source.quote}</p>
                </article>
              )) : <p style={{ color: "var(--muted)", fontSize: 10, margin: 0 }}>No source passage matched this inquiry. Treat the draft as a manual starting point.</p>}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header"><div><h3>Ownership</h3><p>Assign or escalate to a teammate</p></div></div>
            <div className="panel-body assignment">
              <div className="field">
                <label htmlFor="assignee">Assigned to</label>
                <select
                  id="assignee"
                  className="field-control"
                  value={conversation.assigned_to_id || ""}
                  disabled={busy !== "" || isSent}
                  onChange={(event) => void perform("assign", () => api.assign(conversationId, event.target.value || null), "Assignment updated.")}
                >
                  <option value="">Unassigned</option>
                  {members.map((member) => <option value={member.id} key={member.id}>{member.full_name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="escalation-target">Escalate to</label>
                <select id="escalation-target" className="field-control" value={escalationTarget} onChange={(event) => setEscalationTarget(event.target.value)} disabled={isSent}>
                  <option value="">Keep current owner</option>
                  {members.map((member) => <option value={member.id} key={member.id}>{member.full_name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="escalation-note">Internal note</label>
                <textarea id="escalation-note" className="field-control" value={escalationNote} onChange={(event) => setEscalationNote(event.target.value)} placeholder="Why does this need another person?" disabled={isSent} />
              </div>
              <div className="integration-status"><UserRound size={14} /><span style={{ fontSize: 10, color: "var(--muted)" }}>{conversation.assigned_to_id ? members.find((member) => member.id === conversation.assigned_to_id)?.full_name || "Assigned" : "No owner yet"}</span></div>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
