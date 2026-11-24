import { useMemo, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownToLine, Building2, CircleHelp, FileText, Filter, Pencil, Plus,
  Search, Trash2, Upload, X,
} from "lucide-react";
import { dealsApi } from "../api/client";
import type { Client, Deal, DealActivity, DealDocument, DealStage, Originator } from "../types";

type CurrencyFormatter = (value: number | null | undefined, sourceCurrency?: string) => string;
type AmountConverter = (value: number | null | undefined, sourceCurrency?: string) => number | null;
type DealValues = Omit<Partial<Deal>, "id" | "created_at" | "updated_at">;

const stages: { key: DealStage; label: string; tone: string }[] = [
  { key: "lead_identified", label: "Lead Identified", tone: "slate" },
  { key: "initial_screening", label: "Initial Screening", tone: "blue" },
  { key: "client_onboarding", label: "Client Onboarding", tone: "violet" },
  { key: "mandate_drafting", label: "Mandate Drafting", tone: "violet" },
  { key: "due_diligence", label: "Due Diligence", tone: "amber" },
  { key: "investor_matching", label: "Investor Matching", tone: "blue" },
  { key: "negotiation", label: "Negotiation", tone: "amber" },
  { key: "closed_won", label: "Closed Won", tone: "green" },
  { key: "closed_lost", label: "Closed Lost", tone: "red" },
];

function dealValue(deal: Deal) {
  return deal.transaction_size ?? deal.value ?? 0;
}

function sumValues(deals: Deal[], convertAmount: AmountConverter) {
  let total = 0;
  for (const deal of deals) {
    const converted = convertAmount(dealValue(deal), deal.currency);
    if (converted === null) return null;
    total += converted;
  }
  return total;
}

function assignedOriginator(deal: Deal, originators: Originator[]) {
  return originators.find((item) => item.id === deal.originator_id)?.full_name ?? "Unassigned";
}

function activityLabel(item: DealActivity) {
  return item.action.replace(/^deal\./, "").replace(/_/g, " ");
}

export function DealPipeline({
  deals, clients, originators, loading, error, onCreate, onRetry, onStageChange,
  onUpdate, onDelete, formatMoney, convertAmount,
}: {
  deals: Deal[];
  clients: Client[];
  originators: Originator[];
  loading: boolean;
  error: boolean;
  onCreate: () => void;
  onRetry: () => void;
  onStageChange: (deal: Deal, stage: DealStage) => Promise<void>;
  onUpdate: (dealId: string, values: DealValues) => Promise<void>;
  onDelete: (deal: Deal) => Promise<void>;
  formatMoney: CurrencyFormatter;
  convertAmount: AmountConverter;
}) {
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<DealStage | "all">("all");
  const [sectorFilter, setSectorFilter] = useState("");
  const [originatorFilter, setOriginatorFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");
  const sectors = Array.from(new Set([
    ...deals.map((deal) => deal.sector ?? clients.find((client) => client.id === deal.client_id)?.sector
      ?? clients.find((client) => client.id === deal.client_id)?.industry),
    ...clients.map((client) => client.sector ?? client.industry),
  ].filter((value): value is string => Boolean(value)))).sort();
  const visibleDeals = useMemo(() => {
    const term = search.trim().toLowerCase();
    return deals.filter((deal) => {
      const client = clients.find((item) => item.id === deal.client_id);
      const sector = deal.sector ?? client?.sector ?? client?.industry ?? "";
      const matchesSearch = !term || [
        deal.name, deal.company_name, deal.description, deal.industry, deal.sector,
      ].some((value) => value?.toLowerCase().includes(term));
      return matchesSearch
        && (stageFilter === "all" || deal.stage === stageFilter)
        && (!sectorFilter || sector === sectorFilter)
        && (!originatorFilter || deal.originator_id === originatorFilter);
    });
  }, [clients, deals, originatorFilter, search, sectorFilter, stageFilter]);
  const activeDeals = deals.filter((deal) => !["closed_won", "closed_lost"].includes(deal.stage));
  const selectedDeal = deals.find((deal) => deal.id === selectedId) ?? null;

  async function saveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDeal) return;
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) ?? "").trim();
    const number = (key: string) => value(key) === "" ? null : Number(value(key));
    const values: DealValues = {
      name: value("name"),
      company_name: value("company_name"),
      industry: value("industry") || null,
      sector: value("sector") || null,
      deal_type: value("deal_type") || null,
      stage: value("stage") as DealStage,
      transaction_size: number("transaction_size"),
      value: number("transaction_size"),
      revenue: number("revenue"),
      ebitda: number("ebitda"),
      funding_requirement: number("funding_requirement"),
      target_valuation: number("target_valuation"),
      currency: value("currency"),
      description: value("description") || null,
      originator_id: value("originator_id") || null,
    };
    try {
      await onUpdate(selectedDeal.id, values);
      setEditing(false);
      setMessage("Deal changes saved.");
    } catch {
      setMessage("Could not save deal changes. Please retry.");
    }
  }

  async function removeDeal() {
    if (!selectedDeal || !window.confirm(`Delete "${selectedDeal.name}" and its deal documents?`)) return;
    try {
      await onDelete(selectedDeal);
      setSelectedId(null);
      setMessage("");
    } catch {
      setMessage("Could not delete the deal. Please retry.");
    }
  }

  return (
    <div className="module-stack">
      <div className="module-stat-row">
        <MiniStat label="Total opportunities" value={deals.length.toString()} />
        <MiniStat label="Active pipeline" value={formatMoney(sumValues(activeDeals, convertAmount))} />
        <MiniStat label="Closed won" value={deals.filter((deal) => deal.stage === "closed_won").length.toString()} />
        <MiniStat label="Closed lost" value={deals.filter((deal) => deal.stage === "closed_lost").length.toString()} />
      </div>
      <section className="panel module-panel deal-pipeline-panel">
        <div className="panel-header crm-header">
          <div><span className="eyebrow">LIVE CRM DATA</span><h2>Deal pipeline</h2></div>
          <button className="button button-primary" onClick={onCreate} type="button"><Plus size={15} /> New deal</button>
        </div>
        <div className="pipeline-toolbar">
          <label className="inline-search"><Search size={14} /><input aria-label="Search deals" placeholder="Search deals or companies..." value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <label className="filter-control"><Filter size={14} /><select aria-label="Filter by deal stage" value={stageFilter} onChange={(event) => setStageFilter(event.target.value as DealStage | "all")}><option value="all">All stages</option>{stages.map((stage) => <option key={stage.key} value={stage.key}>{stage.label}</option>)}</select></label>
          <label className="filter-control"><select aria-label="Filter by sector" value={sectorFilter} onChange={(event) => setSectorFilter(event.target.value)}><option value="">All sectors</option>{sectors.map((sector) => <option key={sector}>{sector}</option>)}</select></label>
          <label className="filter-control"><select aria-label="Filter by originator" value={originatorFilter} onChange={(event) => setOriginatorFilter(event.target.value)}><option value="">All originators</option>{originators.map((originator) => <option key={originator.id} value={originator.id}>{originator.full_name}</option>)}</select></label>
        </div>
        {loading ? <div className="crm-loading">Loading pipeline…</div>
          : error ? <div className="crm-empty"><CircleHelp size={20} /><strong>Pipeline unavailable</strong><p>The deals endpoint could not be reached.</p><button className="button button-secondary" onClick={onRetry} type="button">Retry</button></div>
            : <div className="kanban-scroll"><div className="kanban-board">
              {stages.map((stage) => {
                const stageDeals = visibleDeals.filter((deal) => deal.stage === stage.key);
                return <section className="kanban-lane" key={stage.key}>
                  <div className="kanban-lane-heading">
                    <span className={`stage-indicator tone-${stage.tone}`} />
                    <strong>{stage.label}</strong><span className="kanban-count">{stageDeals.length}</span>
                    <small>{formatMoney(sumValues(stageDeals, convertAmount))}</small>
                  </div>
                  <div className="kanban-cards">
                    {stageDeals.map((deal) => <article className="kanban-card" key={deal.id}>
                      <button className="kanban-card-open" onClick={() => { setSelectedId(deal.id); setMessage(""); }} type="button">
                        <strong>{deal.name}</strong>
                        <span className="kanban-company"><Building2 size={12} /> {deal.company_name ?? deal.name}</span>
                        <span className="kanban-card-value">{formatMoney(dealValue(deal), deal.currency)}</span>
                        <span className="kanban-card-meta">{deal.sector ?? deal.industry ?? "Sector not set"} · {assignedOriginator(deal, originators)}</span>
                      </button>
                      <label className="kanban-stage-control"><span>Move to</span><select aria-label={`Move ${deal.name} to stage`} value={deal.stage} onChange={(event) => void onStageChange(deal, event.target.value as DealStage)}>{stages.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
                    </article>)}
                    {!stageDeals.length && <div className="kanban-empty">No deals in this stage</div>}
                  </div>
                </section>;
              })}
            </div></div>}
      </section>
      {selectedDeal && <DealDetail
        deal={selectedDeal}
        originators={originators}
        formatMoney={formatMoney}
        editing={editing}
        message={message}
        onClose={() => { setSelectedId(null); setEditing(false); }}
        onEdit={() => { setEditing(true); setMessage(""); }}
        onCancelEdit={() => { setEditing(false); setMessage(""); }}
        onSave={saveEdit}
        onDelete={() => void removeDeal()}
        onMessage={setMessage}
      />}
    </div>
  );
}

function DealDetail({
  deal, originators, formatMoney, editing, message, onClose, onEdit, onCancelEdit,
  onSave, onDelete, onMessage,
}: {
  deal: Deal;
  originators: Originator[];
  formatMoney: CurrencyFormatter;
  editing: boolean;
  message: string;
  onClose: () => void;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
  onMessage: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const activitiesQuery = useQuery({
    queryKey: ["deal-activity", deal.id],
    queryFn: async () => (await dealsApi.activity(deal.id)).data,
  });
  const documentsQuery = useQuery({
    queryKey: ["deal-documents", deal.id],
    queryFn: async () => (await dealsApi.documents(deal.id)).data,
  });

  async function upload(file?: File) {
    if (!file) return;
    try {
      await dealsApi.uploadDocument(deal.id, file);
      await queryClient.invalidateQueries({ queryKey: ["deal-documents", deal.id] });
      await queryClient.invalidateQueries({ queryKey: ["deal-activity", deal.id] });
      onMessage("Document uploaded.");
    } catch {
      onMessage("Could not upload this document. Check the file type and 10 MB limit.");
    }
  }

  async function deleteDocument(document: DealDocument) {
    try {
      await dealsApi.deleteDocument(deal.id, document.id);
      await queryClient.invalidateQueries({ queryKey: ["deal-documents", deal.id] });
      await queryClient.invalidateQueries({ queryKey: ["deal-activity", deal.id] });
      onMessage("Document deleted.");
    } catch {
      onMessage("Could not delete the document. Please retry.");
    }
  }

  async function downloadDocument(document: DealDocument) {
    try {
      const response = await dealsApi.downloadDocument(deal.id, document.id);
      const url = URL.createObjectURL(response.data);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      onMessage("Could not download the document. Please retry.");
    }
  }

  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="create-modal deal-detail-modal" role="dialog" aria-modal="true" aria-labelledby="deal-detail-title">
      <div className="modal-heading">
        <div><span className="eyebrow">DEAL DETAILS</span><h2 id="deal-detail-title">{deal.name}</h2></div>
        <button className="icon-button" aria-label="Close deal details" onClick={onClose} type="button"><X size={18} /></button>
      </div>
      {!editing ? <>
        <div className="deal-detail-actions">
          <button className="button button-secondary" onClick={onEdit} type="button"><Pencil size={14} /> Edit deal</button>
          <button className="button button-danger" onClick={onDelete} type="button"><Trash2 size={14} /> Delete</button>
        </div>
        {message && <p className="deal-message" role="status">{message}</p>}
        <div className="deal-facts">
          <Fact label="Company" value={deal.company_name ?? "—"} />
          <Fact label="Industry / sector" value={[deal.industry, deal.sector].filter(Boolean).join(" · ") || "—"} />
          <Fact label="Deal type" value={deal.deal_type ?? "—"} />
          <Fact label="Current stage" value={stages.find((stage) => stage.key === deal.stage)?.label ?? deal.stage} />
          <Fact label="Transaction size" value={formatMoney(deal.transaction_size ?? deal.value, deal.currency)} />
          <Fact label="Revenue" value={formatMoney(deal.revenue, deal.currency)} />
          <Fact label="EBITDA" value={formatMoney(deal.ebitda, deal.currency)} />
          <Fact label="Funding requirement" value={formatMoney(deal.funding_requirement, deal.currency)} />
          <Fact label="Target valuation" value={formatMoney(deal.target_valuation, deal.currency)} />
          <Fact label="Assigned originator" value={originators.find((item) => item.id === deal.originator_id)?.full_name ?? "Unassigned"} />
        </div>
        {deal.description && <p className="deal-description">{deal.description}</p>}
        <section className="deal-detail-section">
          <div className="detail-section-title"><FileText size={15} /><strong>Documents</strong>
            <label className="button button-secondary file-upload-button"><Upload size={13} /> Upload<input aria-label="Upload deal document" accept=".pdf,.docx,.txt,.csv,.xlsx" type="file" onChange={(event) => { void upload(event.currentTarget.files?.[0]); event.currentTarget.value = ""; }} /></label>
          </div>
          {documentsQuery.isLoading ? <p className="crm-muted">Loading documents…</p> : documentsQuery.isError ? <p className="crm-muted">Documents could not be loaded.</p> : documentsQuery.data?.length ? documentsQuery.data.map((document) => <div className="client-document-row" key={document.id}><FileText size={14} /><span>{document.name}</span><small>{document.size_bytes ? `${Math.ceil(document.size_bytes / 1024)} KB` : ""}</small><button className="icon-button small-icon" aria-label={`Download ${document.name}`} onClick={() => void downloadDocument(document)} type="button"><ArrowDownToLine size={14} /></button><button className="icon-button small-icon" aria-label={`Delete ${document.name}`} onClick={() => void deleteDocument(document)} type="button"><Trash2 size={14} /></button></div>) : <p className="crm-muted">No documents uploaded.</p>}
        </section>
        <section className="deal-detail-section">
          <div className="detail-section-title"><strong>Activity history</strong></div>
          {activitiesQuery.isLoading ? <p className="crm-muted">Loading activity…</p> : activitiesQuery.isError ? <p className="crm-muted">Activity could not be loaded.</p> : activitiesQuery.data?.length ? activitiesQuery.data.map((activity) => <div className="deal-activity-row" key={activity.id}><strong>{activityLabel(activity)}</strong><span>{new Date(activity.created_at).toLocaleString()}</span></div>) : <p className="crm-muted">No activity recorded yet.</p>}
        </section>
      </> : <form className="create-form deal-edit-form" onSubmit={onSave}>
        <DealFields deal={deal} originators={originators} />
        {message && <div className="form-error" role="alert">{message}</div>}
        <div className="modal-actions"><button className="button button-secondary" onClick={onCancelEdit} type="button">Cancel</button><button className="button button-primary" type="submit">Save changes</button></div>
      </form>}
    </section>
  </div>;
}

function DealFields({ deal, originators }: { deal: Deal; originators: Originator[] }) {
  return <>
    <label>Deal title<input autoFocus defaultValue={deal.name} maxLength={255} name="name" required /></label>
    <label>Company name<input defaultValue={deal.company_name ?? ""} maxLength={255} name="company_name" required /></label>
    <div className="form-two"><label>Industry<input defaultValue={deal.industry ?? ""} maxLength={120} name="industry" /></label><label>Sector<input defaultValue={deal.sector ?? ""} maxLength={120} name="sector" /></label></div>
    <div className="form-two"><label>Deal type<input defaultValue={deal.deal_type ?? ""} maxLength={100} name="deal_type" /></label><label>Current stage<select defaultValue={deal.stage} name="stage">{stages.map((stage) => <option key={stage.key} value={stage.key}>{stage.label}</option>)}</select></label></div>
    <div className="form-two"><label>Transaction size<input defaultValue={deal.transaction_size ?? deal.value ?? ""} min="0" name="transaction_size" step="any" type="number" /></label><label>Currency<select defaultValue={deal.currency} name="currency"><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="INR">INR</option></select></label></div>
    <div className="form-two"><label>Revenue<input defaultValue={deal.revenue ?? ""} min="0" name="revenue" step="any" type="number" /></label><label>EBITDA<input defaultValue={deal.ebitda ?? ""} name="ebitda" step="any" type="number" /></label></div>
    <div className="form-two"><label>Funding requirement<input defaultValue={deal.funding_requirement ?? ""} min="0" name="funding_requirement" step="any" type="number" /></label><label>Target valuation<input defaultValue={deal.target_valuation ?? ""} min="0" name="target_valuation" step="any" type="number" /></label></div>
    <label>Originator assignment<select defaultValue={deal.originator_id ?? ""} name="originator_id"><option value="">Unassigned</option>{originators.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></label>
    <label>Deal description<textarea defaultValue={deal.description ?? ""} maxLength={10000} name="description" rows={3} /></label>
  </>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><small>{label}</small><strong>{value}</strong></div>;
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return <article className="mini-stat"><span>{label}</span><strong>{value}</strong></article>;
}
