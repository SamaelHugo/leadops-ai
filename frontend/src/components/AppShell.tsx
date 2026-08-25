"use client";

import {
  Activity,
  BarChart3,
  BookOpen,
  ChevronDown,
  Inbox,
  LogOut,
  Menu,
  Plug,
  Settings,
  Webhook,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { useAuth } from "./AuthProvider";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/knowledge", label: "Knowledge base", icon: BookOpen },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/automations", label: "Automations", icon: Webhook },
  { href: "/activity", label: "Activity log", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { user, organization, logout } = useAuth();

  const sidebar = (
    <aside className="sidebar">
      <div className="brand-row">
        <span className="brand-mark" aria-hidden="true">L/O</span>
        <div>
          <strong>LeadOps AI</strong>
          <span>Customer operations</span>
        </div>
        <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu">
          <X size={20} />
        </button>
      </div>

      <div className="workspace-switcher">
        <span>
          <strong>{organization?.name}</strong>
          <small>{organization?.is_demo ? "Demo workspace" : "Organization"}</small>
        </span>
        <ChevronDown size={15} />
      </div>

      <nav className="nav-list" aria-label="Main navigation">
        {navigation.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              className={active ? "nav-link active" : "nav-link"}
              href={item.href}
              onClick={() => setMobileOpen(false)}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="user-avatar">{user?.full_name.slice(0, 2).toUpperCase()}</div>
        <div className="user-copy">
          <strong>{user?.full_name}</strong>
          <span>{user?.role}</span>
        </div>
        <button className="icon-button subtle" onClick={logout} aria-label="Sign out">
          <LogOut size={17} />
        </button>
      </div>
    </aside>
  );

  return (
    <div className="app-shell">
      {sidebar}
      {mobileOpen ? <div className="mobile-sidebar">{sidebar}</div> : null}
      {mobileOpen ? <button className="mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close menu" /> : null}
      <div className="app-main">
        <header className="mobile-header">
          <button className="icon-button" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu size={21} />
          </button>
          <span className="brand-mark small" aria-hidden="true">L/O</span>
          <strong>LeadOps AI</strong>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
