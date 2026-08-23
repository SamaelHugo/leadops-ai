import {
  AlertTriangle,
  Check,
  CircleAlert,
  LoaderCircle,
  type LucideIcon,
} from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { labelize } from "@/lib/format";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function Button({
  children,
  busy,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  variant?: "primary" | "secondary" | "danger" | "ghost";
}) {
  return (
    <button className={`button ${variant}`} disabled={busy || props.disabled} {...props}>
      {busy ? <LoaderCircle className="spin" size={16} /> : null}
      {children}
    </button>
  );
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={`status-badge status-${value}`}>{labelize(value)}</span>;
}

export function DemoBadge() {
  return <span className="demo-badge">Demo</span>;
}

export function Confidence({ value }: { value: number }) {
  const percent = Math.round(value * 100);
  const level = percent >= 75 ? "high" : percent >= 45 ? "medium" : "low";
  return (
    <div className="confidence" title={`${percent}% confidence`}>
      <span><i className={`confidence-dot ${level}`} />AI confidence</span>
      <strong>{percent}%</strong>
      <div className="confidence-track"><i style={{ width: `${percent}%` }} /></div>
    </div>
  );
}

export function MetricCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "violet",
}: {
  label: string;
  value: string | number;
  helper: string;
  icon: LucideIcon;
  tone?: "violet" | "blue" | "green" | "amber";
}) {
  return (
    <article className="metric-card">
      <span className={`metric-icon ${tone}`}><Icon size={19} /></span>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{helper}</small>
    </article>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span><Icon size={23} /></span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="notice error" role="alert">
      <CircleAlert size={17} />
      <span>{message}</span>
    </div>
  );
}

export function SuccessNotice({ message }: { message: string }) {
  return (
    <div className="notice success" role="status">
      <Check size={17} />
      <span>{message}</span>
    </div>
  );
}

export function WarningNotice({ message }: { message: string }) {
  return (
    <div className="notice warning" role="status">
      <AlertTriangle size={17} />
      <span>{message}</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

