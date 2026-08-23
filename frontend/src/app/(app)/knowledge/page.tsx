"use client";

import { ClipboardPaste, FileText, Link2, Trash2, Upload, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import {
  Button,
  DemoBadge,
  EmptyState,
  ErrorNotice,
  PageHeader,
  Skeleton,
  StatusBadge,
  SuccessNotice,
  WarningNotice,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatBytes, formatDate, labelize } from "@/lib/format";
import type { KnowledgeSource } from "@/lib/types";

type AddMode = "url" | "text" | null;

export default function KnowledgePage() {
  const { user } = useAuth();
  const [sources, setSources] = useState<KnowledgeSource[] | null>(null);
  const [mode, setMode] = useState<AddMode>(null);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const canManage = user?.role === "admin";

  const load = useCallback(() => {
    setError("");
    return api.knowledge().then(setSources).catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Knowledge base failed to load.");
    });
  }, []);

  useEffect(() => {
    let active = true;
    async function fetchSources() {
      try {
        const rows = await api.knowledge();
        if (active) setSources(rows);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Knowledge base failed to load.");
      }
    }
    void fetchSources();
    return () => { active = false; };
  }, []);

  async function upload(file: File) {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const source = await api.uploadPdf(file);
      setSuccess(`${source.title} was indexed into ${source.chunk_count} passages.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The PDF could not be uploaded.");
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function addSource(event: React.FormEvent) {
    event.preventDefault();
    if (!mode) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const source = mode === "url" ? await api.addUrl(url, title) : await api.addText(title, content);
      setSuccess(`${source.title} was indexed into ${source.chunk_count} passages.`);
      setMode(null);
      setUrl("");
      setTitle("");
      setContent("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The source could not be indexed.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(source: KnowledgeSource) {
    if (!window.confirm(`Delete "${source.title}" and all of its indexed passages?`)) return;
    setBusy(true);
    setError("");
    try {
      await api.deleteKnowledge(source.id);
      setSuccess(`${source.title} was removed.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The source could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Grounded answers"
        title="Knowledge base"
        description="Add the material your team already trusts. Every draft keeps the exact passages it used."
      />
      {error ? <ErrorNotice message={error} /> : null}
      {success ? <SuccessNotice message={success} /> : null}
      {!canManage ? <WarningNotice message="Only an administrator can add or remove knowledge sources." /> : null}

      <input
        ref={fileInput}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(event) => event.target.files?.[0] && void upload(event.target.files[0])}
      />
      <div className="knowledge-actions">
        <button className="action-card" disabled={!canManage || busy} onClick={() => fileInput.current?.click()}>
          <span><Upload size={18} /></span>
          <strong>Upload a PDF</strong>
          <p>Policies, product manuals, and service documents up to the configured file limit.</p>
        </button>
        <button className="action-card" disabled={!canManage || busy} onClick={() => setMode("url")}>
          <span><Link2 size={18} /></span>
          <strong>Add a web page</strong>
          <p>Index readable text from a public HTTP or HTTPS page.</p>
        </button>
        <button className="action-card" disabled={!canManage || busy} onClick={() => setMode("text")}>
          <span><ClipboardPaste size={18} /></span>
          <strong>Paste text</strong>
          <p>Add a short FAQ or policy without preparing a file first.</p>
        </button>
      </div>

      <section className="panel">
        <div className="panel-header"><div><h2>Indexed sources</h2><p>{sources?.length || 0} sources in this workspace</p></div></div>
        {sources === null ? (
          <div className="panel-body"><Skeleton /><div style={{ height: 12 }} /><Skeleton /></div>
        ) : sources.length === 0 ? (
          <EmptyState icon={FileText} title="The knowledge base is empty" description="Upload a PDF or add a page. The first customer inquiry will use it as soon as indexing finishes." />
        ) : sources.map((source) => (
          <div className="source-row" key={source.id}>
            <span className="source-icon">{source.kind === "url" ? <Link2 size={17} /> : <FileText size={17} />}</span>
            <div className="source-copy">
              <strong>{source.title} {source.is_demo ? <DemoBadge /> : null}</strong>
              <p>{labelize(source.kind)} · {source.chunk_count} passages · {formatBytes(source.byte_size)} · {formatDate(source.created_at)}</p>
              {source.error ? <p style={{ color: "var(--red)" }}>{source.error}</p> : null}
            </div>
            <StatusBadge value={source.status} />
            <button className="icon-button subtle" disabled={!canManage || busy} onClick={() => void remove(source)} aria-label={`Delete ${source.title}`}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </section>

      {mode ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setMode(null)}>
          <form className="modal" onSubmit={addSource}>
            <header>
              <h2>{mode === "url" ? "Add a web page" : "Paste text"}</h2>
              <button type="button" className="icon-button subtle" onClick={() => setMode(null)} aria-label="Close"><X size={18} /></button>
            </header>
            <div className="panel-body">
              <div className="field-grid">
                {mode === "url" ? (
                  <>
                    <div className="field full">
                      <label htmlFor="source-url">Public URL</label>
                      <input id="source-url" className="field-control" type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/support" required />
                    </div>
                    <div className="field full">
                      <label htmlFor="source-title">Title (optional)</label>
                      <input id="source-title" className="field-control" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Use the page title" />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="field full">
                      <label htmlFor="text-title">Title</label>
                      <input id="text-title" className="field-control" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Support FAQ" required />
                    </div>
                    <div className="field full">
                      <label htmlFor="text-content">Text</label>
                      <textarea id="text-content" className="field-control" value={content} onChange={(event) => setContent(event.target.value)} placeholder="Paste the source text here" required minLength={20} />
                    </div>
                  </>
                )}
              </div>
              <div className="form-actions"><Button type="submit" busy={busy}>Index source</Button><Button type="button" variant="ghost" onClick={() => setMode(null)}>Cancel</Button></div>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}
