import axios from "axios";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle, Check, CheckCircle2, Clock3, Download, FileText,
  LoaderCircle, LockKeyhole, RefreshCw, Save, Sparkles, Upload,
} from "lucide-react";
import { mandateGenerationsApi } from "../api/client";
import type { FieldEvidence, MandateGeneration } from "../types";

const LIST_KEY = ["mandate-generations"];

function errorText(error: unknown): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

function labelFor(field: string): string {
  return field.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function evidenceEntries(
  fields: Record<string, FieldEvidence> | null | undefined,
): Array<[string, FieldEvidence]> {
  return Object.entries(fields ?? {});
}

function EvidenceGrid({ fields }: { fields: Array<[string, FieldEvidence]> }) {
  return (
    <div className="evidence-grid">
      {fields.map(([name, evidence]) => (
        <article className="evidence-card" key={name}>
          <span>{labelFor(name)}</span>
          <strong className={evidence.status === "unavailable" ? "evidence-unavailable" : ""}>
            {evidence.status === "available" ? evidence.value : "Unavailable"}
          </strong>
          {evidence.source && (
            <details className="source-citation">
              <summary>{evidence.source.file_name} · {evidence.source.location}</summary>
              <blockquote>{evidence.source.quote}</blockquote>
            </details>
          )}
        </article>
      ))}
    </div>
  );
}

function statusLabel(status: MandateGeneration["status"]): string {
  return status.replaceAll("_", " ");
}

export function MandateGenerator() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState("");

  const listQuery = useQuery({
    queryKey: LIST_KEY,
    queryFn: async () => (await mandateGenerationsApi.list()).data,
  });
  const generations = listQuery.data ?? [];
  const activeId = selectedId || generations[0]?.id || "";

  const generationQuery = useQuery({
    queryKey: [...LIST_KEY, activeId],
    queryFn: async () => (await mandateGenerationsApi.get(activeId)).data,
    enabled: Boolean(activeId),
  });
  const generation = generationQuery.data;

  const uploadMutation = useMutation({
    mutationFn: (file: File) => mandateGenerationsApi.upload(file),
    onSuccess: async ({ data }) => {
      queryClient.setQueryData([...LIST_KEY, data.id], data);
      setSelectedId(data.id);
      await queryClient.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
  const processMutation = useMutation({
    mutationFn: (id: string) => mandateGenerationsApi.process(id),
    onSuccess: ({ data }) => queryClient.setQueryData([...LIST_KEY, data.id], data),
    onSettled: async (_data, _error, id) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: LIST_KEY }),
        queryClient.invalidateQueries({ queryKey: [...LIST_KEY, id] }),
      ]);
    },
  });
  const approveMutation = useMutation({
    mutationFn: (id: string) => mandateGenerationsApi.approve(id),
    onSuccess: ({ data }) => {
      queryClient.setQueryData([...LIST_KEY, data.id], data);
      void queryClient.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
  const downloadMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await mandateGenerationsApi.downloadSource(id);
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = generation?.source_document_name ?? "source-document";
      link.click();
      URL.revokeObjectURL(url);
    },
  });

  function uploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("source-document");
    if (!(input instanceof HTMLInputElement) || !input.files?.[0]) return;
    uploadMutation.mutate(input.files[0], {
      onSuccess: () => { form.reset(); },
    });
  }

  const review = generation?.quality_review;
  const approvalBlocked = Boolean(
    review?.unsupported_claims.length || review?.contradictions.length,
  );
  const listError = listQuery.error ? errorText(listQuery.error) : "";

  return (
    <div className="module-stack">
      <section className="panel mandate-upload-panel">
        <div className="mandate-intro">
          <span className="mandate-intro-icon"><Sparkles size={18} /></span>
          <div>
            <span className="eyebrow">DOCUMENT-TO-MANDATE WORKFLOW</span>
            <h2>Generate source-grounded deal drafts</h2>
            <p>Upload a PDF or DOCX to extract cited facts, structure a proposal, and prepare editable mandate and teaser drafts.</p>
          </div>
        </div>
        <form className="mandate-upload-form" onSubmit={uploadFile}>
          <label>
            <span>Source document</span>
            <input
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              name="source-document"
              required
              type="file"
            />
          </label>
          <button className="button button-primary" disabled={uploadMutation.isPending} type="submit">
            {uploadMutation.isPending ? <LoaderCircle className="spin-icon" size={15} /> : <Upload size={15} />}
            {uploadMutation.isPending ? "Uploading…" : "Upload document"}
          </button>
        </form>
        <p className="mandate-disclaimer">
          <LockKeyhole size={13} />
          Mock processing is deterministic when no LLM credentials are configured. Drafts are not legal advice or KYC/AML verification; human approval is required.
        </p>
        {listError && <div className="form-error" role="alert">{listError}</div>}
        {uploadMutation.error && <div className="form-error" role="alert">{errorText(uploadMutation.error)}</div>}
      </section>

      <div className="mandate-workspace">
        <section className="panel mandate-records-panel">
          <div className="panel-header">
            <div><span className="eyebrow">SOURCE DOCUMENTS</span><h2>Processing history</h2></div>
            <button
              aria-label="Refresh processing history"
              className="icon-button small-icon"
              disabled={listQuery.isFetching}
              onClick={() => void listQuery.refetch()}
              type="button"
            >
              <RefreshCw size={14} />
            </button>
          </div>
          {listQuery.isLoading ? (
            <div className="mandate-list-loading"><LoaderCircle className="spin-icon" size={17} /> Loading records…</div>
          ) : generations.length ? (
            <div className="generation-list">
              {generations.map((item) => (
                <button
                  aria-current={activeId === item.id ? "page" : undefined}
                  className={`generation-row${activeId === item.id ? " generation-row-active" : ""}`}
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  type="button"
                >
                  <FileText size={16} />
                  <span><strong>{item.source_document_name}</strong><small>{new Date(item.updated_at).toLocaleString()}</small></span>
                  <span className={`generation-status status-${item.status}`}>{statusLabel(item.status)}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="mandate-empty">No source documents yet. Upload a PDF or DOCX to begin.</div>
          )}
        </section>

        <section className="panel mandate-detail-panel">
          {!activeId ? (
            <div className="mandate-empty mandate-empty-detail">
              <FileText size={23} />
              <strong>Select or upload a source document</strong>
              <span>Extraction results, agent history, and editable drafts will appear here.</span>
            </div>
          ) : generationQuery.isLoading ? (
            <div className="mandate-list-loading"><LoaderCircle className="spin-icon" size={17} /> Loading document details…</div>
          ) : generationQuery.isError ? (
            <div className="form-error" role="alert">{errorText(generationQuery.error)}</div>
          ) : generation ? (
            <>
              <div className="panel-header mandate-detail-heading">
                <div>
                  <span className="eyebrow">AI PROCESSING RECORD</span>
                  <h2>{generation.source_document_name}</h2>
                </div>
                <span className={`generation-status status-${generation.status}`}>
                  {processMutation.isPending ? "processing" : statusLabel(generation.status)}
                </span>
              </div>
              {generation.error_message && (
                <div className="error-banner mandate-error">
                  <AlertCircle size={15} /><span>{generation.error_message}</span>
                </div>
              )}
              {processMutation.error && !generation.error_message && (
                <div className="error-banner mandate-error" role="alert">
                  <AlertCircle size={15} /><span>{errorText(processMutation.error)}</span>
                </div>
              )}
              {(approveMutation.error || downloadMutation.error) && (
                <div className="error-banner mandate-error" role="alert">
                  <AlertCircle size={15} />
                  <span>{errorText(approveMutation.error ?? downloadMutation.error)}</span>
                </div>
              )}
              <div className="mandate-detail-actions">
                <button
                  className="button button-secondary"
                  disabled={downloadMutation.isPending}
                  onClick={() => downloadMutation.mutate(generation.id)}
                  type="button"
                >
                  {downloadMutation.isPending ? <LoaderCircle className="spin-icon" size={14} /> : <Download size={14} />}
                  {downloadMutation.isPending ? "Downloading…" : "Source document"}
                </button>
                {["uploaded", "failed"].includes(generation.status) && (
                  <button
                    className="button button-primary"
                    disabled={processMutation.isPending}
                    onClick={() => processMutation.mutate(generation.id)}
                    type="button"
                  >
                    {processMutation.isPending
                      ? <LoaderCircle className="spin-icon" size={14} />
                      : <Sparkles size={14} />}
                    {processMutation.isPending ? "Processing document…" : "Run AI workflow"}
                  </button>
                )}
              </div>
              {generation.processing_mode && (
                <div className="processing-mode-note">
                  Processing mode: <strong>{generation.processing_mode === "mock" ? "Deterministic mock" : "LiteLLM provider"}</strong>
                </div>
              )}

              {generation.extracted_data && (
                <section className="mandate-result-section">
                  <div className="mandate-section-title"><div><span className="eyebrow">DOCUMENT EXTRACTION</span><h3>Source facts and citations</h3></div></div>
                  <EvidenceGrid fields={evidenceEntries(generation.extracted_data.facts)} />
                  {generation.extracted_data.conflicts.length > 0 && (
                    <div className="review-warning">
                      <AlertCircle size={15} />
                      <span>Conflicting values found: {generation.extracted_data.conflicts.map((item) => labelFor(item.field)).join(", ")}</span>
                    </div>
                  )}
                </section>
              )}

              {generation.deal_proposal && (
                <section className="mandate-result-section">
                  <div className="mandate-section-title"><div><span className="eyebrow">DEAL STRUCTURING AGENT</span><h3>{generation.deal_proposal.title}</h3></div></div>
                  <EvidenceGrid
                    fields={Object.entries(generation.deal_proposal).filter(
                      (entry): entry is [string, FieldEvidence] =>
                        !["title", "source_document_id", "description"].includes(entry[0]) &&
                        typeof entry[1] === "object" &&
                        entry[1] !== null &&
                        "status" in entry[1],
                    )}
                  />
                </section>
              )}

              {generation.quality_review && (
                <section className="mandate-result-section">
                  <div className="mandate-section-title">
                    <div><span className="eyebrow">QUALITY REVIEW AGENT</span><h3>Review findings</h3></div>
                    <span className={`review-result${generation.quality_review.passed ? " review-passed" : " review-attention"}`}>
                      {generation.quality_review.passed ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                      {generation.quality_review.passed ? "Source support passed" : "Review required"}
                    </span>
                  </div>
                  <div className="review-findings">
                    <span>Unavailable fields <strong>{generation.quality_review.missing_fields.length}</strong></span>
                    <span>Contradictions <strong>{generation.quality_review.contradictions.length}</strong></span>
                    <span>Unsupported claims <strong>{generation.quality_review.unsupported_claims.length}</strong></span>
                  </div>
                  {approvalBlocked && (
                    <div className="review-warning">
                      <AlertCircle size={15} />
                      <span>Resolve unsupported claims and source contradictions before approval.</span>
                    </div>
                  )}
                </section>
              )}

              {generation.agent_history.length > 0 && (
                <section className="mandate-result-section">
                  <div className="mandate-section-title"><div><span className="eyebrow">WORKFLOW TRACE</span><h3>Agent execution history</h3></div></div>
                  <ol className="agent-history">
                    {generation.agent_history.map((item, index) => (
                      <li key={`${item.agent}-${index}`}>
                        <span className="agent-history-icon">{item.status === "failed" ? <AlertCircle size={14} /> : <Check size={14} />}</span>
                        <span><strong>{item.agent}</strong><small>{item.summary ?? item.message ?? item.status}</small></span>
                        <time>{item.completed_at ? new Date(item.completed_at).toLocaleTimeString() : item.started_at ? new Date(item.started_at).toLocaleTimeString() : ""}</time>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {generation.status === "awaiting_review" && (
                <DraftReviewForm
                  approvalBlocked={approvalBlocked}
                  approvePending={approveMutation.isPending}
                  generation={generation}
                  key={generation.id}
                  onApprove={() => approveMutation.mutate(generation.id)}
                  reviewPassed={Boolean(review?.passed)}
                />
              )}
              {generation.status === "approved" && (
                <div className="approved-banner"><CheckCircle2 size={16} /><span>Approved by a human reviewer{generation.approved_at ? ` on ${new Date(generation.approved_at).toLocaleString()}` : ""}.</span></div>
              )}
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function DraftReviewForm({
  approvalBlocked,
  approvePending,
  generation,
  onApprove,
  reviewPassed,
}: {
  approvalBlocked: boolean;
  approvePending: boolean;
  generation: MandateGeneration;
  onApprove: () => void;
  reviewPassed: boolean;
}) {
  const queryClient = useQueryClient();
  const [mandateDraft, setMandateDraft] = useState(generation.mandate_draft ?? "");
  const [teaserDraft, setTeaserDraft] = useState(generation.teaser_draft ?? "");
  const saveMutation = useMutation({
    mutationFn: () => mandateGenerationsApi.update(generation.id, {
      mandate_draft: mandateDraft,
      teaser_draft: teaserDraft,
    }),
    onSuccess: ({ data }) => {
      queryClient.setQueryData([...LIST_KEY, data.id], data);
      void queryClient.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
  const hasDraftEdits = mandateDraft !== (generation.mandate_draft ?? "") ||
    teaserDraft !== (generation.teaser_draft ?? "");

  return (
    <form
      className="mandate-draft-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (hasDraftEdits) saveMutation.mutate();
      }}
    >
      <div className="mandate-section-title"><div><span className="eyebrow">HUMAN REVIEW REQUIRED</span><h3>Review and edit generated drafts</h3></div></div>
      <label>
        Mandate draft
        <textarea maxLength={50_000} onChange={(event) => setMandateDraft(event.target.value)} rows={13} value={mandateDraft} />
      </label>
      <label>
        Anonymized investment teaser
        <textarea maxLength={20_000} onChange={(event) => setTeaserDraft(event.target.value)} rows={9} value={teaserDraft} />
      </label>
      {saveMutation.error && <div className="form-error" role="alert">{errorText(saveMutation.error)}</div>}
      <div className="mandate-review-actions">
        <button className="button button-secondary" disabled={!hasDraftEdits || saveMutation.isPending} type="submit">
          {saveMutation.isPending ? <LoaderCircle className="spin-icon" size={14} /> : <Save size={14} />}
          {saveMutation.isPending ? "Saving…" : "Save edits"}
        </button>
        <button
          className="button button-primary"
          disabled={approvalBlocked || approvePending || !mandateDraft.trim() || !teaserDraft.trim()}
          onClick={onApprove}
          type="button"
        >
          {approvePending ? <LoaderCircle className="spin-icon" size={14} /> : <CheckCircle2 size={14} />}
          {approvePending ? "Approving…" : "Approve drafts"}
        </button>
      </div>
      {!reviewPassed && !approvalBlocked && (
        <p className="mandate-missing-note"><Clock3 size={13} /> Review the listed unavailable fields; missing information is not filled in by the workflow.</p>
      )}
    </form>
  );
}
