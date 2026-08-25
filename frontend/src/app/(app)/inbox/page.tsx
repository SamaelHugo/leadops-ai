"use client";

import { ArrowUpRight, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DemoBadge, EmptyState, ErrorNotice, Skeleton, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { Conversation, ConversationDetail } from "@/lib/types";

const filters = ["all", "needs_review", "approved", "sent", "escalated"];

export default function InboxPage() {
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [preview, setPreview] = useState<ConversationDetail | null>(null);
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setConversations(null);
      setError("");
      api.conversations(status, search)
        .then((rows) => {
          if (!active) return;
          setConversations(rows);
          setSelectedId((current) => rows.some((item) => item.id === current) ? current : rows[0]?.id || "");
        })
        .catch((caught) => {
          if (active) setError(caught instanceof Error ? caught.message : "Inbox failed to load.");
        });
    }, search ? 260 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [search, status]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    api.conversation(selectedId)
      .then((detail) => {
        if (!active) return;
        setPreviewError("");
        setPreview(detail);
      })
      .catch((caught) => active && setPreviewError(caught instanceof Error ? caught.message : "Preview failed to load."));
    return () => { active = false; };
  }, [selectedId]);

  const selected = conversations?.find((item) => item.id === selectedId);
  const customerMessage = preview?.messages.find((message) => message.role === "customer");
  const draft = preview?.draft;

  return (
    <div className="inbox-page">
      <header className="inbox-titlebar">
        <div>
          <p className="eyebrow">Customer operations / Inbox</p>
          <h1>Every inquiry, one decision at a time.</h1>
        </div>
        <p>AI prepares the draft. Your team decides what leaves the workspace.</p>
      </header>

      {error ? <ErrorNotice message={error} /> : null}

      <div className="inbox-workspace">
        <section className="inbox-list-pane" aria-label="Inquiry list">
          <header className="inbox-list-tools">
            <div className="inbox-search">
              <Search size={15} />
              <input
                aria-label="Search inquiries"
                placeholder="Search inbox"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <span>{conversations?.length ?? "–"}</span>
          </header>

          <div className="inbox-filter-row" aria-label="Inbox filters">
            {filters.map((filter) => (
              <button
                className={filter === status ? "active" : ""}
                key={filter}
                onClick={() => setStatus(filter)}
              >
                {labelize(filter)}
              </button>
            ))}
          </div>

          <div className="inbox-case-list">
            {conversations === null ? (
              <div className="inbox-list-loading"><Skeleton /><Skeleton /><Skeleton /></div>
            ) : conversations.length === 0 ? (
              <EmptyState title="No inquiries here" description="Try another filter or search term." icon={Search} />
            ) : conversations.map((conversation, index) => (
              <button
                className={conversation.id === selectedId ? "inbox-case active" : "inbox-case"}
                key={conversation.id}
                onClick={() => {
                  setPreviewError("");
                  setSelectedId(conversation.id);
                }}
                aria-pressed={conversation.id === selectedId}
              >
                <span className="case-number">{String(index + 1).padStart(2, "0")}</span>
                <span className="case-copy">
                  <strong>{conversation.subject}</strong>
                  <small>{conversation.customer_name} · {conversation.customer_company || conversation.customer_email}</small>
                  <span><StatusBadge value={conversation.status} /> · {labelize(conversation.intent)} · {labelize(conversation.urgency)}</span>
                </span>
                <time dateTime={conversation.created_at}>{formatDate(conversation.created_at)}</time>
              </button>
            ))}
          </div>
        </section>

        <section className="inbox-preview-pane" aria-label="Selected inquiry preview">
          {!selectedId ? (
            <div className="inbox-preview-empty">Select an inquiry to inspect it.</div>
          ) : previewError ? (
            <div className="inbox-preview-empty"><ErrorNotice message={previewError} /></div>
          ) : !preview || preview.id !== selectedId || !selected ? (
            <div className="inbox-preview-loading"><Skeleton /><Skeleton /></div>
          ) : (
            <>
              <header className="preview-header">
                <div>
                  <p>Inquiry #{preview.public_reference}</p>
                  <h2>{preview.subject}</h2>
                  <span>{preview.customer_name} · {preview.customer_company || preview.customer_email} {preview.is_demo ? <DemoBadge /> : null}</span>
                </div>
                <StatusBadge value={preview.status} />
              </header>

              <div className="preview-body">
                <section className="preview-message">
                  <header><span>Customer message</span><time>{customerMessage ? formatDate(customerMessage.created_at) : ""}</time></header>
                  <p>{customerMessage?.body || "No customer message is available."}</p>
                </section>

                <section className="preview-draft">
                  <header>
                    <span>Prepared reply</span>
                    {draft ? <StatusBadge value={draft.status} /> : null}
                  </header>
                  <p>{draft?.body || "No draft has been prepared yet."}</p>
                </section>

                <section className="preview-evidence">
                  <div><span>Confidence</span><strong>{draft ? `${Math.round(draft.confidence * 100)}%` : "–"}</strong></div>
                  <div><span>Sources</span><strong>{draft?.sources.length || 0}</strong></div>
                  <div><span>Owner</span><strong>{preview.assigned_to_id ? "Assigned" : "Unassigned"}</strong></div>
                </section>

                {draft?.sources.length ? (
                  <div className="preview-source-list">
                    {draft.sources.slice(0, 2).map((source) => (
                      <div key={source.id}>
                        <span>[{source.rank}] {source.title}</span>
                        <p>{source.quote}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>

              <footer className="preview-actions">
                <p>Open the full inquiry to edit, approve, send, assign, or escalate.</p>
                <Link className="button primary" href={`/inbox/${preview.id}`}>Open inquiry <ArrowUpRight size={14} /></Link>
              </footer>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
