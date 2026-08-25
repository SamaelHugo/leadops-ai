"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ErrorNotice, Skeleton, StatusBadge } from "@/components/ui";
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
        setActivity(activityData.slice(0, 5));
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Dashboard failed to load."));
  }, []);

  if (!analytics && !error) {
    return (
      <div className="dashboard-loading">
        <Skeleton className="dashboard-intro-skeleton" />
        <Skeleton className="dashboard-work-skeleton" />
      </div>
    );
  }

  if (!analytics) return <ErrorNotice message={error || "Dashboard failed to load."} />;

  const reviewTitle = analytics.needs_review === 1
    ? "One reply needs your decision."
    : `${analytics.needs_review} replies need your decision.`;
  const chartMax = Math.max(1, ...analytics.last_seven_days.map((item) => item.count));
  const today = new Date().toLocaleDateString("en", { weekday: "long", month: "long", day: "numeric" });

  return (
    <>
      <header className="dashboard-intro">
        <div>
          <p className="eyebrow">{today} · Northstar Components</p>
          <h1>{reviewTitle}</h1>
          <p>Review the draft and its sources. Nothing is sent until you approve it.</p>
        </div>
        <Link className="dashboard-review-link" href="/inbox">
          Open review queue <ArrowUpRight size={17} />
        </Link>
      </header>

      {error ? <ErrorNotice message={error} /> : null}

      <section className="dashboard-stat-band" aria-label="Workspace summary">
        <div><span>Inbox</span><strong>{analytics.total_conversations.toString().padStart(2, "0")}</strong><small>Total inquiries</small></div>
        <div className="attention"><span>Review</span><strong>{analytics.needs_review.toString().padStart(2, "0")}</strong><small>Waiting for a person</small></div>
        <div><span>Sent</span><strong>{analytics.sent.toString().padStart(2, "0")}</strong><small>Approved replies</small></div>
        <div className={analytics.webhook_failures ? "error" : ""}><span>Delivery</span><strong>{analytics.webhook_failures.toString().padStart(2, "0")}</strong><small>Webhook failures</small></div>
      </section>

      <div className="dashboard-work-grid">
        <section className="work-queue">
          <header className="section-line-header">
            <div><p>01 / Work queue</p><h2>Latest inquiries</h2></div>
            <Link href="/inbox">See all <ArrowUpRight size={14} /></Link>
          </header>
          <div className="work-queue-list">
            {conversations.map((conversation, index) => (
              <Link className="work-queue-row" href={`/inbox/${conversation.id}`} key={conversation.id}>
                <span className="queue-index">{String(index + 1).padStart(2, "0")}</span>
                <span className="queue-main">
                  <strong>{conversation.subject}</strong>
                  <small>{conversation.customer_name} · {conversation.customer_company || conversation.customer_email}</small>
                </span>
                <StatusBadge value={conversation.status} />
                <time dateTime={conversation.created_at}>{formatDate(conversation.created_at)}</time>
                <ArrowUpRight className="queue-arrow" size={16} />
              </Link>
            ))}
          </div>
        </section>

        <aside className="dashboard-context">
          <section className="confidence-figure">
            <p>02 / Retrieval</p>
            <strong>{Math.round(analytics.average_confidence * 100)}<sup>%</sup></strong>
            <span>Average confidence across current drafts</span>
            <div className="mini-week" aria-label="Inquiry volume for the last seven days">
              {analytics.last_seven_days.map((item) => (
                <span key={item.date}>
                  <i style={{ height: `${Math.max(4, (item.count / chartMax) * 100)}%` }} />
                  <small>{new Date(`${item.date}T12:00:00`).toLocaleDateString("en", { weekday: "narrow" })}</small>
                </span>
              ))}
            </div>
          </section>

          <section className="dashboard-activity">
            <header><p>03 / Activity</p><Link href="/activity">Full log</Link></header>
            {activity.map((entry) => (
              <div className="dashboard-activity-row" key={entry.id}>
                <span className={entry.level === "error" ? "activity-mark error" : "activity-mark"} />
                <div><strong>{labelize(entry.action)}</strong><small>{formatDate(entry.created_at)}</small></div>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </>
  );
}
