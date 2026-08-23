"use client";

import { Copy, ExternalLink, Plus, Settings, UserPlus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { Button, DemoBadge, ErrorNotice, PageHeader, Skeleton, SuccessNotice, WarningNotice } from "@/components/ui";
import { api } from "@/lib/api";
import type { Organization, User } from "@/lib/types";

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<User[] | null>(null);
  const [organizationName, setOrganizationName] = useState("");
  const [memberName, setMemberName] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberPassword, setMemberPassword] = useState("");
  const [memberRole, setMemberRole] = useState<"admin" | "employee">("employee");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const canManage = user?.role === "admin";

  const load = useCallback(async () => {
    const [organizationData, memberData] = await Promise.all([api.organization(), api.members()]);
    setOrganization(organizationData);
    setOrganizationName(organizationData.name);
    setMembers(memberData);
  }, []);

  useEffect(() => {
    let active = true;
    async function fetchSettings() {
      try {
        const [organizationData, memberData] = await Promise.all([api.organization(), api.members()]);
        if (!active) return;
        setOrganization(organizationData);
        setOrganizationName(organizationData.name);
        setMembers(memberData);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Settings failed to load.");
      }
    }
    void fetchSettings();
    return () => { active = false; };
  }, []);

  async function saveOrganization(event: React.FormEvent) {
    event.preventDefault();
    setBusy("organization");
    setError("");
    setSuccess("");
    try {
      await api.updateOrganization(organizationName);
      await Promise.all([load(), refresh()]);
      setSuccess("Organization name updated.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Organization could not be updated.");
    } finally {
      setBusy("");
    }
  }

  async function addMember(event: React.FormEvent) {
    event.preventDefault();
    setBusy("member");
    setError("");
    setSuccess("");
    try {
      await api.createMember({
        full_name: memberName,
        email: memberEmail,
        password: memberPassword,
        role: memberRole,
      });
      setMemberName("");
      setMemberEmail("");
      setMemberPassword("");
      setMemberRole("employee");
      await load();
      setSuccess("Team member created. Share the organization URL and temporary password securely.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Team member could not be created.");
    } finally {
      setBusy("");
    }
  }

  const formPath = organization ? `/contact/${organization.slug}` : "";
  const formUrl = typeof window !== "undefined" && formPath ? `${window.location.origin}${formPath}` : formPath;

  return (
    <>
      <PageHeader
        eyebrow="Workspace administration"
        title="Settings"
        description="Manage the organization, team access, and the public intake address."
      />
      {error ? <ErrorNotice message={error} /> : null}
      {success ? <SuccessNotice message={success} /> : null}
      {!canManage ? <WarningNotice message="You can view these settings. Only an administrator can change them." /> : null}
      {!organization || !members ? (
        <div className="settings-grid"><Skeleton /><Skeleton /></div>
      ) : (
        <div className="settings-grid">
          <div style={{ display: "grid", gap: 18 }}>
            <form className="panel" onSubmit={saveOrganization}>
              <div className="panel-header"><div><h2>Organization</h2><p>Workspace identity and public URL</p></div>{organization.is_demo ? <DemoBadge /> : null}</div>
              <div className="panel-body">
                <div className="field-grid">
                  <div className="field full">
                    <label htmlFor="organization-name">Organization name</label>
                    <input id="organization-name" className="field-control" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} disabled={!canManage} />
                  </div>
                  <div className="field full">
                    <label htmlFor="organization-slug">Organization URL</label>
                    <input id="organization-slug" className="field-control" value={organization.slug} readOnly />
                    <small>The slug stays fixed so public forms and saved links do not break.</small>
                  </div>
                </div>
                <div className="form-actions"><Button type="submit" busy={busy === "organization"} disabled={!canManage || organizationName === organization.name}>Save changes</Button></div>
              </div>
            </form>

            <section className="panel">
              <div className="panel-header"><div><h2>Public contact form</h2><p>Share this link or embed it in your site navigation</p></div><Settings size={17} /></div>
              <div className="panel-body">
                <div className="field">
                  <label htmlFor="public-form-url">Form URL</label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input id="public-form-url" className="field-control" value={formUrl} readOnly />
                    <button className="icon-button" onClick={() => void navigator.clipboard.writeText(formUrl)} aria-label="Copy form URL"><Copy size={16} /></button>
                    <Link className="icon-button" href={formPath} target="_blank" aria-label="Open public form"><ExternalLink size={16} /></Link>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div style={{ display: "grid", gap: 18 }}>
            <section className="panel">
              <div className="panel-header"><div><h2>Team</h2><p>{members.length} active members</p></div><UserPlus size={17} /></div>
              <div className="panel-body">
                {members.map((member) => (
                  <div className="member-row" key={member.id}>
                    <div className="user-avatar">{member.full_name.slice(0, 2).toUpperCase()}</div>
                    <div className="member-copy"><strong>{member.full_name} {member.is_demo ? <DemoBadge /> : null}</strong><span>{member.email}</span></div>
                    <span className="status-badge">{member.role}</span>
                  </div>
                ))}
              </div>
            </section>

            <form className="panel" onSubmit={addMember}>
              <div className="panel-header"><div><h2>Add a team member</h2><p>Create an admin or employee account</p></div><Plus size={17} /></div>
              <div className="panel-body">
                <div className="field-grid">
                  <div className="field full"><label htmlFor="member-name">Name</label><input id="member-name" className="field-control" value={memberName} onChange={(event) => setMemberName(event.target.value)} disabled={!canManage} required /></div>
                  <div className="field full"><label htmlFor="member-email">Email</label><input id="member-email" className="field-control" type="email" value={memberEmail} onChange={(event) => setMemberEmail(event.target.value)} disabled={!canManage} required /></div>
                  <div className="field full"><label htmlFor="member-password">Temporary password</label><input id="member-password" className="field-control" type="password" value={memberPassword} onChange={(event) => setMemberPassword(event.target.value)} minLength={8} disabled={!canManage} required /></div>
                  <div className="field full"><label htmlFor="member-role">Role</label><select id="member-role" className="field-control" value={memberRole} onChange={(event) => setMemberRole(event.target.value as "admin" | "employee")} disabled={!canManage}><option value="employee">Employee</option><option value="admin">Administrator</option></select></div>
                </div>
                <div className="form-actions"><Button type="submit" busy={busy === "member"} disabled={!canManage}>Create member</Button></div>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
