"use client";

import { Inbox as InboxIcon, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DemoBadge, EmptyState, ErrorNotice, PageHeader, Skeleton, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { Conversation } from "@/lib/types";

const filters = ["all", "needs_review", "approved", "sent", "escalated"];

export default function InboxPage() {
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setConversations(null);
      setError("");
      api.conversations(status, search)
        .then(setConversations)
        .catch((caught) => setError(caught instanceof Error ? caught.message : "Inbox failed to load."));
    }, search ? 260 : 0);
    return () => window.clearTimeout(timer);
  }, [search, status]);

  return (
    <>
      <PageHeader
        eyebrow="Customer operations"
        title="Inbox"
        description="Every AI reply stays here until a team member decides what happens next."
      />
      {error ? <ErrorNotice message={error} /> : null}
      <div className="toolbar">
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="Search inquiries"
            placeholder="Search customer, subject, email, or reference"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="filter-tabs" aria-label="Inbox filters">
          {filters.map((filter) => (
            <button
              className={filter === status ? "filter-tab active" : "filter-tab"}
              key={filter}
              onClick={() => setStatus(filter)}
            >
              {labelize(filter)}
            </button>
          ))}
        </div>
      </div>

      <section className="panel">
        {conversations === null ? (
          <div className="panel-body"><Skeleton /><div style={{ height: 12 }} /><Skeleton /></div>
        ) : conversations.length === 0 ? (
          <EmptyState icon={InboxIcon} title="No inquiries here" description="Try another filter or submit a message through the public contact form." />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead><tr><th>Customer</th><th>Subject</th><th>Status</th><th>Intent</th><th>Urgency</th><th>Received</th></tr></thead>
              <tbody>
                {conversations.map((conversation) => (
                  <tr key={conversation.id}>
                    <td>
                      <Link className="primary-cell" href={`/inbox/${conversation.id}`}>
                        <strong>{conversation.customer_name} {conversation.is_demo ? <DemoBadge /> : null}</strong>
                        <span>{conversation.customer_company || conversation.customer_email}</span>
                        <span className="reference">#{conversation.public_reference}</span>
                      </Link>
                    </td>
                    <td><Link href={`/inbox/${conversation.id}`}>{conversation.subject}</Link></td>
                    <td><StatusBadge value={conversation.status} /></td>
                    <td>{labelize(conversation.intent)}</td>
                    <td><span className={`priority ${conversation.urgency}`}>{conversation.urgency}</span></td>
                    <td>{formatDate(conversation.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

