"use client";

import { AlertTriangle, Inbox, Send, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ErrorNotice, MetricCard, PageHeader, Skeleton, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, labelize } from "@/lib/format";
import type { ActivityEntry, Analytics, Conversation } from "@/lib/types";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.analytics(), api.conversations(), api.activity()])
      .then(([analyticsData, conversationData, activityData]) => {
        setAnalytics(analyticsData);
        setConversations(conversationData.slice(0, 5));
        setActivity(activityData.slice(0, 6));
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Dashboard failed to load."));
  }, []);

  if (!analytics && !error) {
    return (
      <>
        <PageHeader title="Dashboard" description="A quick read on the inbox and the work behind it." />
        <div className="metrics-grid">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} />)}</div>
        <Skeleton className="dashboard-skeleton" />
      </>
    );
  }

  const chartMax = Math.max(1, ...(analytics?.last_seven_days.map((item) => item.count) || [1]));

  return (
    <>
      <PageHeader
        eyebrow="Operations overview"
        title="Dashboard"
        description="See what needs a person, what was sent, and where a workflow needs attention."
      />
      {error ? <ErrorNotice message={error} /> : null}
      {analytics ? (
        <>
          <div className="metrics-grid">
            <MetricCard label="Total inquiries" value={analytics.total_conversations} helper="Across this workspace" icon={Inbox} tone="blue" />
            <MetricCard label="Needs review" value={analytics.needs_review} helper="Waiting for a person" icon={Sparkles} tone="amber" />
            <MetricCard label="Replies sent" value={analytics.sent} helper="Approved and delivered" icon={Send} tone="green" />
            <MetricCard label="Webhook failures" value={analytics.webhook_failures} helper="Available for retry" icon={AlertTriangle} tone="violet" />
          </div>

          <div className="dashboard-grid">
            <section className="panel">
              <div className="panel-header">
                <div><h2>Inbox volume</h2><p>New inquiries over the last seven days</p></div>
                <span className="status-badge">{Math.round(analytics.average_confidence * 100)}% avg. confidence</span>
              </div>
              <div className="panel-body">
                <div className="chart" aria-label="Seven day inquiry chart">
                  {analytics.last_seven_days.map((item) => (
                    <div className="chart-column" key={item.date}>
                      <span className="chart-value">{item.count}</span>
                      <span className="chart-bar-track">
                        <i className="chart-bar" style={{ height: `${Math.max(4, (item.count / chartMax) * 100)}%` }} />
                      </span>
                      <span className="chart-label">{new Date(`${item.date}T12:00:00`).toLocaleDateString("en", { weekday: "short" })}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div><h2>Recent activity</h2><p>Latest actions and errors</p></div>
                <Link className="panel-link" href="/activity">View log</Link>
              </div>
              <div className="panel-body activity-mini-list">
                {activity.map((entry) => (
                  <div className="activity-mini" key={entry.id}>
                    <span className={entry.level === "error" ? "event-dot error" : "event-dot"} />
                    <div>
                      <strong>{labelize(entry.action)}</strong>
                      <span>{formatDate(entry.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="panel" style={{ marginTop: 18 }}>
            <div className="panel-header">
              <div><h2>Recent inquiries</h2><p>The latest customer messages in this workspace</p></div>
              <Link className="panel-link" href="/inbox">Open inbox</Link>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead><tr><th>Customer</th><th>Subject</th><th>Status</th><th>Category</th><th>Received</th></tr></thead>
                <tbody>
                  {conversations.map((conversation) => (
                    <tr key={conversation.id}>
                      <td><Link className="primary-cell" href={`/inbox/${conversation.id}`}><strong>{conversation.customer_name}</strong><span>{conversation.customer_company || conversation.customer_email}</span></Link></td>
                      <td><Link href={`/inbox/${conversation.id}`}>{conversation.subject}</Link></td>
                      <td><StatusBadge value={conversation.status} /></td>
                      <td>{labelize(conversation.category)}</td>
                      <td>{formatDate(conversation.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}

