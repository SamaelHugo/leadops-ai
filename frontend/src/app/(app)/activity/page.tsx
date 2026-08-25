"use client";

import { Activity, CircleAlert, Clock3 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DemoBadge, EmptyState, ErrorNotice, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { ActivityEntry } from "@/lib/types";

export default function ActivityPage() {
  const [entries, setEntries] = useState<ActivityEntry[] | null>(null);
  const [level, setLevel] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function fetchEntries() {
      try {
        const rows = await api.activity(level);
        if (active) setEntries(rows);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Activity log failed to load.");
      }
    }
    void fetchEntries();
    return () => { active = false; };
  }, [level]);

  return (
    <>
      <PageHeader
        eyebrow="Activity / Audit trail"
        title="Nothing happens off the record."
        description="Customer submissions, team decisions, CRM updates, and delivery errors stay visible here."
        actions={
          <div className="filter-tabs">
            {[
              ["all", "All"],
              ["info", "Actions"],
              ["error", "Errors"],
            ].map(([value, label]) => <button key={value} className={level === value ? "filter-tab active" : "filter-tab"} onClick={() => setLevel(value)}>{label}</button>)}
          </div>
        }
      />
      {error ? <ErrorNotice message={error} /> : null}
      <section className="panel">
        {entries === null ? (
          <div className="panel-body"><Skeleton /><div style={{ height: 12 }} /><Skeleton /></div>
        ) : entries.length === 0 ? (
          <EmptyState icon={Activity} title="No activity matches this filter" description="Actions appear here as the team works through inquiries." />
        ) : (
          <div className="activity-list">
            {entries.map((entry) => (
              <article className="activity-row" key={entry.id}>
                <span className={entry.level === "error" ? "activity-icon error" : "activity-icon"}>
                  {entry.level === "error" ? <CircleAlert size={16} /> : <Clock3 size={16} />}
                </span>
                <div className="activity-copy">
                  <strong>{labelize(entry.action)} {entry.is_demo ? <DemoBadge /> : null}</strong>
                  <p>
                    {entry.entity_type}{entry.entity_id ? ` · ${entry.entity_id.slice(0, 10)}` : ""}
                    {entry.conversation_id ? <> · <Link className="panel-link" href={`/inbox/${entry.conversation_id}`}>Open inquiry</Link></> : null}
                  </p>
                  {Object.keys(entry.details).length ? <p>{JSON.stringify(entry.details)}</p> : null}
                </div>
                <time dateTime={entry.created_at}>{formatDate(entry.created_at)}</time>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
