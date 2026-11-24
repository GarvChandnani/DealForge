import { useMemo, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CircleHelp, Download, FileText, Pencil, Plus, Search, Trash2, Users, X } from "lucide-react";
import { clientsApi, dealsApi, mandatesApi, originatorsApi } from "../api/client";
import type { Client, ClientDocument, ClientInteraction, Deal, Mandate, Originator, VerificationCheck } from "../types";

type CrmWorkspaceProps = { title: "Clients" | "Originators" };
type EditableRecord = Client | Originator;

const CLIENT_STATUSES = ["active", "prospect", "inactive"];
const ONBOARDING_STATUSES = ["not_started", "in_progress", "documents_pending", "complete"];
const EMPTY_CLIENTS: Client[] = [];
const EMPTY_ORIGINATORS: Originator[] = [];

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0] ?? "").join("").toUpperCase();
}

function displayError(error: unknown) {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function inputString(form: FormData, key: string) {
  const value = String(form.get(key) ?? "").trim();
  return value || undefined;
}

function inputNumber(form: FormData, key: string) {
  const value = inputString(form, key);
  return value === undefined ? undefined : Number(value);
}

export function CrmWorkspace({ title }: CrmWorkspaceProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [originatorFilter, setOriginatorFilter] = useState("");
  const [editing, setEditing] = useState<EditableRecord | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [selectedOriginator, setSelectedOriginator] = useState<Originator | null>(null);
  const [toast, setToast] = useState("");
  const isClients = title === "Clients";

  const clientsQuery = useQuery({
    queryKey: ["clients"],
    queryFn: async () => (await clientsApi.list({ limit: 200 })).data,
    enabled: isClients,
  });
  const originatorsQuery = useQuery({
    queryKey: ["originators"],
    queryFn: async () => (await originatorsApi.list({ limit: 200 })).data,
  });
  const dealsQuery = useQuery({
    queryKey: ["deals"],
    queryFn: async () => (await dealsApi.list({ limit: 200 })).data,
    enabled: !isClients,
  });
  const mandatesQuery = useQuery({
    queryKey: ["mandates"],
    queryFn: async () => (await mandatesApi.list()).data,
    enabled: !isClients,
  });
  const records = isClients ? clientsQuery.data ?? EMPTY_CLIENTS : originatorsQuery.data ?? EMPTY_ORIGINATORS;
  const originators = originatorsQuery.data ?? EMPTY_ORIGINATORS;

  const filteredRecords = useMemo(() => records.filter((record) => {
    const needle = search.trim().toLowerCase();
    const matchSearch = !needle || (
      isClients
        ? `${(record as Client).name} ${(record as Client).contact_email ?? ""} ${(record as Client).sector ?? ""} ${(record as Client).location ?? ""}`
        : `${(record as Originator).full_name ?? ""} ${(record as Originator).firm_name ?? ""} ${(record as Originator).email ?? ""} ${(record as Originator).sectors ?? ""}`
    ).toLowerCase().includes(needle);
    if (!matchSearch) return false;
    if (isClients) {
      const client = record as Client;
      return (!sectorFilter || (client.sector ?? client.industry) === sectorFilter)
        && (!statusFilter || client.status === statusFilter)
        && (!originatorFilter || client.assigned_originator_id === originatorFilter);
    }
    return !statusFilter || (record as Originator).status === statusFilter;
  }), [isClients, originatorFilter, records, search, sectorFilter, statusFilter]);

  const saveMutation = useMutation({
    mutationFn: async (form: FormData) => {
      if (isClients) {
        const payload: Partial<Client> = {
          name: String(form.get("name") ?? "").trim(),
          industry: inputString(form, "industry"),
          sector: inputString(form, "sector"),
          website: inputString(form, "website"),
          contact_email: inputString(form, "contact_email"),
          phone: inputString(form, "phone"),
          location: inputString(form, "location"),
          turnover: inputNumber(form, "turnover"),
          revenue: inputNumber(form, "revenue"),
          funding_requirement: inputNumber(form, "funding_requirement"),
          currency: String(form.get("currency") ?? "USD"),
          assigned_originator_id: inputString(form, "assigned_originator_id"),
          description: inputString(form, "description"),
          status: String(form.get("status") ?? "active"),
          onboarding_status: String(form.get("onboarding_status") ?? "not_started"),
        };
        return editing
          ? clientsApi.update(editing.id, payload)
          : clientsApi.create(payload);
      }
      const payload: Partial<Originator> = {
        full_name: String(form.get("full_name") ?? "").trim(),
        email: inputString(form, "email"),
        phone: inputString(form, "phone"),
        title: inputString(form, "title"),
        firm_name: inputString(form, "firm_name"),
        sectors: inputString(form, "sectors"),
        biography: inputString(form, "biography"),
        status: String(form.get("status") ?? "active"),
      };
      return editing
        ? originatorsApi.update(editing.id, payload)
        : originatorsApi.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [isClients ? "clients" : "originators"] });
      setShowForm(false);
      setEditing(null);
      setToast(`${title.slice(0, -1)} saved`);
      window.setTimeout(() => setToast(""), 3000);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => isClients ? clientsApi.delete(id) : originatorsApi.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [isClients ? "clients" : "originators"] });
      setToast(`${title.slice(0, -1)} deleted`);
      window.setTimeout(() => setToast(""), 3000);
    },
  });

  function submitRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveMutation.mutate(new FormData(event.currentTarget));
  }

  function removeRecord(record: EditableRecord) {
    const name = isClients
      ? (record as Client).name
      : (record as Originator).full_name ?? (record as Originator).firm_name ?? "this originator";
    if (window.confirm(`Delete ${name}? This action cannot be undone.`)) {
      deleteMutation.mutate(record.id);
    }
  }

  const query = isClients ? clientsQuery : originatorsQuery;
  const sectorOptions = Array.from(new Set((clientsQuery.data ?? [])
    .map((client) => client.sector ?? client.industry)
    .filter((sector): sector is string => Boolean(sector)))).sort();

  return (
    <div className="module-stack">
      <div className="module-stat-row">
        <div className="mini-stat"><span>{isClients ? "Client organizations" : "Originator profiles"}</span><strong>{records.length}</strong></div>
        <div className="mini-stat"><span>{isClients ? "Onboarding in progress" : "Active relationships"}</span><strong>{isClients ? (clientsQuery.data ?? []).filter((client) => client.onboarding_status !== "complete").length : originators.filter((originator) => originator.status === "active").length}</strong></div>
        <div className="mini-stat"><span>{isClients ? "Sectors represented" : "Active mandates"}</span><strong>{isClients ? sectorOptions.length : (mandatesQuery.data ?? []).filter((mandate) => mandate.status === "active").length}</strong></div>
        <div className="mini-stat"><span>Workspace scope</span><strong>Private</strong></div>
      </div>

      <section className="panel module-panel">
        <div className="panel-header crm-header">
          <div><span className="eyebrow">LIVE CRM DATA</span><h2>{isClients ? "Client portfolio & onboarding" : "Originator directory"}</h2></div>
          <div className="module-toolbar">
            <label className="inline-search"><Search size={15} /><input aria-label={`Search ${title}`} placeholder={`Search ${title.toLowerCase()}…`} value={search} onChange={(event) => setSearch(event.target.value)} /></label>
            <button className="button button-primary" onClick={() => { setEditing(null); saveMutation.reset(); setShowForm(true); }} type="button"><Plus size={15} /> Add {title.slice(0, -1)}</button>
          </div>
        </div>

        <div className="crm-filters">
          {isClients && <label className="filter-control"><span>Sector</span><select aria-label="Filter by sector" value={sectorFilter} onChange={(event) => setSectorFilter(event.target.value)}><option value="">All sectors</option>{sectorOptions.map((sector) => <option key={sector}>{sector}</option>)}</select></label>}
          <label className="filter-control"><span>Status</span><select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{(isClients ? CLIENT_STATUSES : ["active", "inactive"]).map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
          {isClients && <label className="filter-control"><span>Originator</span><select aria-label="Filter by originator" value={originatorFilter} onChange={(event) => setOriginatorFilter(event.target.value)}><option value="">All originators</option>{originators.map((originator) => <option key={originator.id} value={originator.id}>{originator.full_name ?? originator.firm_name ?? "Originator"}</option>)}</select></label>}
        </div>
        {deleteMutation.error != null && <div className="form-error crm-mutation-error" role="alert">{displayError(deleteMutation.error)}</div>}

        {query.isLoading ? <div className="crm-loading">Loading {title.toLowerCase()}…</div>
          : query.isError ? <div className="error-banner"><CircleHelp size={17} /><span>{title} could not be loaded.</span><button onClick={() => void query.refetch()} type="button">Retry</button></div>
            : filteredRecords.length === 0 ? <div className="crm-empty"><span className="empty-icon">{isClients ? <Building2 size={18} /> : <Users size={18} />}</span><strong>{records.length ? "No matching records" : `No ${title.toLowerCase()} yet`}</strong><p>{records.length ? "Adjust your search or filters to see records." : `Create a ${title.slice(0, -1).toLowerCase()} profile to get started.`}</p></div>
              : isClients ? <div className="table-scroll"><table className="data-table full-table crm-table"><thead><tr><th>Client</th><th>Sector / location</th><th>Revenue / funding</th><th>Originator</th><th>Onboarding</th><th>Status</th><th>Actions</th></tr></thead><tbody>
                {(filteredRecords as Client[]).map((client) => <tr key={client.id}>
                  <td><button className="crm-record-link" onClick={() => setSelectedClient(client)} type="button"><strong className="table-primary">{client.name}</strong><small>{client.contact_email ?? client.industry ?? "Client profile"}</small></button></td>
                  <td>{client.sector ?? client.industry ?? "—"}<small className="crm-cell-sub">{client.location ?? "Location not provided"}</small></td>
                  <td>{client.revenue == null ? "—" : `${client.currency} ${Number(client.revenue).toLocaleString()}`}<small className="crm-cell-sub">Funding {client.funding_requirement == null ? "—" : `${client.currency} ${Number(client.funding_requirement).toLocaleString()}`}</small></td>
                  <td>{originators.find((item) => item.id === client.assigned_originator_id)?.full_name ?? originators.find((item) => item.id === client.assigned_originator_id)?.firm_name ?? "—"}</td>
                  <td><span className="neutral-pill">{client.onboarding_status.replaceAll("_", " ")}</span></td>
                  <td><span className={`neutral-pill${client.status === "active" ? " pill-green" : ""}`}>{client.status}</span></td>
                  <td><div className="crm-row-actions"><button className="icon-button small-icon" aria-label={`Edit ${client.name}`} onClick={() => { setEditing(client); saveMutation.reset(); setShowForm(true); }} type="button"><Pencil size={14} /></button><button className="icon-button small-icon" aria-label={`Delete ${client.name}`} onClick={() => removeRecord(client)} type="button"><Trash2 size={14} /></button></div></td>
                </tr>)}
              </tbody></table></div>
                : <div className="table-scroll"><table className="data-table full-table crm-table"><thead><tr><th>Originator</th><th>Organization</th><th>Sectors</th><th>Deals sourced</th><th>Mandates</th><th>Status</th><th>Actions</th></tr></thead><tbody>
                  {(filteredRecords as Originator[]).map((originator) => {
                    const relatedDeals = (dealsQuery.data ?? []).filter((deal) => deal.originator_id === originator.id);
                    const relatedMandates = (mandatesQuery.data ?? []).filter((mandate) => mandate.originator_id === originator.id);
                    return <tr key={originator.id}>
                      <td><button className="crm-record-link contact-person" onClick={() => setSelectedOriginator(originator)} type="button"><span className="avatar contact-avatar">{initials(originator.full_name ?? originator.firm_name ?? "O")}</span><span><strong className="table-primary">{originator.full_name ?? "Originator"}</strong><small>{originator.title ?? originator.email ?? "Professional profile"}</small></span></button></td>
                      <td>{originator.firm_name ?? "Independent"}</td><td>{originator.sectors ?? "—"}</td>
                      <td>{relatedDeals.filter((deal) => !["closed_won", "closed_lost"].includes(deal.stage)).length} active · {relatedDeals.filter((deal) => ["closed_won", "closed_lost"].includes(deal.stage)).length} completed</td>
                      <td>{relatedMandates.filter((mandate) => mandate.status === "active").length} active · {relatedMandates.filter((mandate) => ["completed", "closed", "closed_won"].includes(mandate.status)).length} completed</td>
                      <td><span className={`neutral-pill${originator.status === "active" ? " pill-green" : ""}`}>{originator.status}</span></td>
                      <td><div className="crm-row-actions"><button className="icon-button small-icon" aria-label={`Edit ${originator.full_name ?? "originator"}`} onClick={() => { setEditing(originator); saveMutation.reset(); setShowForm(true); }} type="button"><Pencil size={14} /></button><button className="icon-button small-icon" aria-label={`Delete ${originator.full_name ?? "originator"}`} onClick={() => removeRecord(originator)} type="button"><Trash2 size={14} /></button></div></td>
                    </tr>;
                  })}
                </tbody></table></div>}
        {isClients && <div className="footnote-banner">Client data is organization-scoped. TXT/CSV extraction is draft-only; external MCA, DIN, KYC, or AML checks are not configured and no verification is claimed.</div>}
      </section>

      {showForm && <RecordForm title={title} record={editing} originators={originators} pending={saveMutation.isPending} error={saveMutation.error} onSubmit={submitRecord} onClose={() => { setShowForm(false); setEditing(null); saveMutation.reset(); }} />}
      {selectedClient && <ClientDetail client={selectedClient} onClose={() => setSelectedClient(null)} />}
      {selectedOriginator && <OriginatorDetail originator={selectedOriginator} deals={dealsQuery.data ?? []} mandates={mandatesQuery.data ?? []} onClose={() => setSelectedOriginator(null)} />}
      {toast && <div className="toast"><span className="toast-check">✓</span>{toast}<button aria-label="Dismiss" onClick={() => setToast("")} type="button"><X size={15} /></button></div>}
    </div>
  );
}

function OriginatorDetail({ originator, deals, mandates, onClose }: {
  originator: Originator;
  deals: Deal[];
  mandates: Mandate[];
  onClose: () => void;
}) {
  const relatedDeals = deals.filter((deal) => deal.originator_id === originator.id);
  const relatedMandates = mandates.filter((mandate) => mandate.originator_id === originator.id);
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="create-modal crm-modal client-detail" role="dialog" aria-modal="true" aria-labelledby="originator-detail-title">
    <div className="modal-heading"><div><span className="eyebrow">ORIGINATOR PROFILE</span><h2 id="originator-detail-title">{originator.full_name ?? "Originator"}</h2></div><button className="icon-button" aria-label="Close originator details" onClick={onClose} type="button"><X size={18} /></button></div>
    <div className="client-facts"><span>{originator.title ?? "Professional"}</span><span>{originator.firm_name ?? "Independent"}</span><span>{originator.email ?? "Email not provided"}</span><span>{originator.phone ?? "Phone not provided"}</span></div>
    {originator.biography && <p className="extraction-note">{originator.biography}</p>}
    {originator.sectors && <p className="extraction-note">Sector coverage · {originator.sectors}</p>}
    <section className="client-detail-section"><div className="detail-section-title"><Users size={15} /><strong>Associated deals</strong></div>
      {relatedDeals.length ? relatedDeals.map((deal) => <div className="client-document-row" key={deal.id}><span>{deal.name}</span><small>{deal.stage.replaceAll("_", " ")}</small></div>) : <p className="crm-muted">No deals are assigned to this originator.</p>}
    </section>
    <section className="client-detail-section"><div className="detail-section-title"><FileText size={15} /><strong>Mandates</strong></div>
      {relatedMandates.length ? relatedMandates.map((mandate) => <div className="client-document-row" key={mandate.id}><span>{mandate.name}</span><small>{mandate.status}</small></div>) : <p className="crm-muted">No mandates are assigned to this originator.</p>}
    </section>
  </section></div>;
}

function RecordForm({ title, record, originators, pending, error, onSubmit, onClose }: {
  title: "Clients" | "Originators";
  record: EditableRecord | null;
  originators: Originator[];
  pending: boolean;
  error: unknown;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
}) {
  const client = title === "Clients" ? record as Client | null : null;
  const originator = title === "Originators" ? record as Originator | null : null;
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="create-modal crm-modal" role="dialog" aria-modal="true" aria-labelledby="crm-form-title">
    <div className="modal-heading"><div><span className="eyebrow">LIVE CRM RECORD</span><h2 id="crm-form-title">{record ? "Edit" : "Add"} {title.slice(0, -1)}</h2></div><button className="icon-button" aria-label="Close dialog" onClick={onClose} type="button"><X size={18} /></button></div>
    <form className="create-form" onSubmit={onSubmit}>
      {title === "Clients" ? <>
        <label>Company name<input autoFocus maxLength={200} name="name" required defaultValue={client?.name} /></label>
        <div className="form-two"><label>Sector<input maxLength={120} name="sector" defaultValue={client?.sector ?? client?.industry ?? ""} /></label><label>Industry<input maxLength={120} name="industry" defaultValue={client?.industry ?? ""} /></label></div>
        <div className="form-two"><label>Company email<input maxLength={254} name="contact_email" type="email" defaultValue={client?.contact_email ?? ""} /></label><label>Phone<input maxLength={30} name="phone" defaultValue={client?.phone ?? ""} /></label></div>
        <div className="form-two"><label>Location<input maxLength={200} name="location" defaultValue={client?.location ?? ""} /></label><label>Website<input maxLength={500} name="website" type="url" defaultValue={client?.website ?? ""} /></label></div>
        <div className="form-two"><label>Annual turnover<input min="0" name="turnover" type="number" step="0.01" defaultValue={client?.turnover ?? ""} /></label><label>Annual revenue<input min="0" name="revenue" type="number" step="0.01" defaultValue={client?.revenue ?? ""} /></label></div>
        <div className="form-two"><label>Funding requirement<input min="0" name="funding_requirement" type="number" step="0.01" defaultValue={client?.funding_requirement ?? ""} /></label><label>Currency<select name="currency" defaultValue={client?.currency ?? "USD"}><option>USD</option><option>EUR</option><option>GBP</option><option>INR</option></select></label></div>
        <label>Assigned originator<select name="assigned_originator_id" defaultValue={client?.assigned_originator_id ?? ""}><option value="">Unassigned</option>{originators.map((item) => <option key={item.id} value={item.id}>{item.full_name ?? item.firm_name ?? "Originator"}</option>)}</select></label>
        <div className="form-two"><label>Client status<select name="status" defaultValue={client?.status ?? "active"}>{CLIENT_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label><label>Onboarding status<select name="onboarding_status" defaultValue={client?.onboarding_status ?? "not_started"}>{ONBOARDING_STATUSES.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label></div>
        <label>Company notes<textarea name="description" rows={3} defaultValue={client?.description ?? ""} /></label>
      </> : <>
        <label>Full name<input autoFocus maxLength={200} name="full_name" required defaultValue={originator?.full_name ?? ""} /></label>
        <div className="form-two"><label>Work email<input maxLength={254} name="email" type="email" defaultValue={originator?.email ?? ""} /></label><label>Phone<input maxLength={30} name="phone" defaultValue={originator?.phone ?? ""} /></label></div>
        <div className="form-two"><label>Title<input maxLength={120} name="title" defaultValue={originator?.title ?? ""} /></label><label>Firm<input maxLength={200} name="firm_name" defaultValue={originator?.firm_name ?? ""} /></label></div>
        <label>Sector coverage<input maxLength={500} name="sectors" placeholder="Technology, healthcare…" defaultValue={originator?.sectors ?? ""} /></label>
        <label>Professional biography<textarea name="biography" rows={3} defaultValue={originator?.biography ?? ""} /></label>
        <label>Status<select name="status" defaultValue={originator?.status ?? "active"}><option>active</option><option>inactive</option></select></label>
      </>}
      {error != null && <div className="form-error" role="alert">{displayError(error)}</div>}
      <div className="modal-actions"><button className="button button-secondary" onClick={onClose} type="button">Cancel</button><button className="button button-primary" disabled={pending} type="submit">{pending ? "Saving…" : record ? "Save changes" : "Create profile"}</button></div>
    </form>
  </section></div>;
}

function ClientDetail({ client, onClose }: { client: Client; onClose: () => void }) {
  const queryClient = useQueryClient();
  const interactionFormRef = useRef<HTMLFormElement>(null);
  const [documentError, setDocumentError] = useState("");
  const interactionsQuery = useQuery({
    queryKey: ["client-interactions", client.id],
    queryFn: async () => (await clientsApi.interactions(client.id)).data,
  });
  const documentsQuery = useQuery({
    queryKey: ["client-documents", client.id],
    queryFn: async () => (await clientsApi.documents(client.id)).data,
  });
  const checksQuery = useQuery({
    queryKey: ["client-verification-checks", client.id],
    queryFn: async () => (await clientsApi.verificationChecks(client.id)).data,
  });
  const interactionMutation = useMutation({
    mutationFn: (form: FormData) => clientsApi.addInteraction(client.id, {
      interaction_type: String(form.get("interaction_type") ?? "note"),
      summary: String(form.get("summary") ?? "").trim(),
      notes: inputString(form, "notes"),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["client-interactions", client.id] });
      interactionFormRef.current?.reset();
    },
  });
  const documentMutation = useMutation({
    mutationFn: (file: File) => clientsApi.uploadDocument(client.id, file),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["client-documents", client.id] });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
  const checkMutation = useMutation({
    mutationFn: (checkType: string) => clientsApi.runSimulatedCheck(client.id, checkType),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["client-verification-checks", client.id] });
    },
  });
  function addInteraction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    interactionMutation.mutate(new FormData(event.currentTarget));
  }
  async function downloadDocument(record: ClientDocument) {
    try {
      const response = await clientsApi.downloadDocument(client.id, record.id);
      const url = URL.createObjectURL(response.data);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = record.name;
      anchor.click();
      URL.revokeObjectURL(url);
      setDocumentError("");
    } catch (error) {
      setDocumentError(displayError(error));
    }
  }
  const uploadError = documentMutation.error;
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="create-modal crm-modal client-detail" role="dialog" aria-modal="true" aria-labelledby="client-detail-title">
    <div className="modal-heading"><div><span className="eyebrow">CLIENT PROFILE · {client.onboarding_status.replaceAll("_", " ").toUpperCase()}</span><h2 id="client-detail-title">{client.name}</h2></div><button className="icon-button" aria-label="Close client details" onClick={onClose} type="button"><X size={18} /></button></div>
    <div className="client-facts"><span>{client.sector ?? client.industry ?? "Sector not provided"}</span><span>{client.location ?? "Location not provided"}</span><span>{client.contact_email ?? "Email not provided"}</span></div>
    <section className="client-detail-section"><div className="detail-section-title"><FileText size={15} /><strong>Onboarding documents</strong><label className="button button-secondary file-upload-button">Upload<input aria-label="Upload client document" type="file" accept=".pdf,.docx,.txt,.csv,.xlsx" onChange={(event) => { const file = event.currentTarget.files?.[0]; if (file) documentMutation.mutate(file); event.currentTarget.value = ""; }} /></label></div>
      <p className="extraction-note">Uploads are stored in the configured local document directory. Basic draft extraction is available for TXT/CSV files only; review fields manually before saving. PDF/DOCX extraction is not configured.</p>
      {documentsQuery.isLoading ? <p className="crm-muted">Loading documents…</p> : documentsQuery.isError ? <p className="form-error">Documents could not be loaded.</p> : (documentsQuery.data ?? []).map((item: ClientDocument) => <div className="client-document-group" key={item.id}><div className="client-document-row"><FileText size={14} /><span>{item.name}</span><small>{item.size_bytes == null ? "—" : `${Math.ceil(item.size_bytes / 1024)} KB`}</small><button className="icon-button small-icon" aria-label={`Download ${item.name}`} onClick={() => void downloadDocument(item)} type="button"><Download size={14} /></button></div>{item.extracted_fields && Object.keys(item.extracted_fields).length > 0 && <p className="extracted-fields">Draft fields · {Object.entries(item.extracted_fields).map(([field, value]) => `${field.replaceAll("_", " ")}: ${value}`).join(" · ")}</p>}</div>)}
      {uploadError != null && <p className="form-error" role="alert">{displayError(uploadError)}</p>}
      {documentError && <p className="form-error" role="alert">{documentError}</p>}
      {documentMutation.isPending && <p className="crm-muted">Uploading…</p>}
    </section>
    <section className="client-detail-section"><div className="detail-section-title"><CircleHelp size={15} /><strong>Verification-ready checks</strong></div>
      <p className="extraction-note">Demo-only simulation. No MCA, DIN, KYC, or AML registry or external provider is contacted, and these results are not verification.</p>
      <div className="verification-actions">{["mca", "din", "kyc", "aml"].map((checkType) => <button className="button button-secondary" disabled={checkMutation.isPending} key={checkType} onClick={() => checkMutation.mutate(checkType)} type="button">Simulate {checkType.toUpperCase()}</button>)}</div>
      {checksQuery.isLoading ? <p className="crm-muted">Loading check history…</p> : checksQuery.isError ? <p className="form-error">Verification check history could not be loaded.</p> : (checksQuery.data ?? []).map((check: VerificationCheck) => <div className="client-document-row" key={check.id}><CircleHelp size={14} /><span>{check.check_type.toUpperCase()} · {check.status}</span><small>{new Date(check.created_at).toLocaleString()}</small></div>)}
      {checkMutation.error && <p className="form-error" role="alert">{displayError(checkMutation.error)}</p>}
    </section>
    <section className="client-detail-section"><div className="detail-section-title"><Users size={15} /><strong>Interaction history</strong></div>
      {interactionsQuery.isLoading ? <p className="crm-muted">Loading interactions…</p> : interactionsQuery.isError ? <p className="form-error">Interaction history could not be loaded.</p> : (interactionsQuery.data ?? []).length === 0 ? <p className="crm-muted">No interactions have been recorded.</p> : (interactionsQuery.data ?? []).map((interaction: ClientInteraction) => <article className="interaction-item" key={interaction.id}><strong>{interaction.summary}</strong><span>{interaction.interaction_type} · {new Date(interaction.created_at).toLocaleString()}</span>{interaction.notes && <p>{interaction.notes}</p>}</article>)}
      <form className="interaction-form" ref={interactionFormRef} onSubmit={addInteraction}><select name="interaction_type" aria-label="Interaction type"><option value="note">Note</option><option value="meeting">Meeting</option><option value="call">Call</option><option value="email">Email</option></select><input name="summary" aria-label="Interaction summary" placeholder="Add an interaction…" required maxLength={500} /><button className="button button-primary" disabled={interactionMutation.isPending} type="submit">Add</button></form>
      {interactionMutation.error && <p className="form-error" role="alert">{displayError(interactionMutation.error)}</p>}
    </section>
  </section></div>;
}
