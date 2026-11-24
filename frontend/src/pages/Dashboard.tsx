import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity, ArrowRight, ArrowUpRight, Bell, BriefcaseBusiness,
  Building2, Check, ChevronDown, ChevronRight, CircleHelp, Command,
  ContactRound, FileCheck2, FileText, FolderOpen, Globe2, Handshake,
  LayoutDashboard, LogOut, Menu, Network, PanelLeftClose, Plus, Search,
  Settings2, ShieldCheck, Sparkles, Target, TrendingUp, Users, Wallet, X, Zap,
} from "lucide-react";
import { authApi, clientsApi, contactsApi, dealsApi, originatorsApi } from "../api/client";
import type { Client, Contact, Deal, DealStage, Originator } from "../types";
import { CrmWorkspace } from "./CrmWorkspace";
import { DealPipeline } from "./DealPipeline";
import { MandateGenerator } from "./MandateGenerator";
import countryToCurrency from "country-to-currency";
import { COUNTRY_CURRENCY_OPTIONS, type CountryCode } from "../utils/currency";

type ModuleKey =
  | "Overview" | "Originators" | "Clients" | "Deal Pipeline" | "Mandate Generator"
  | "Investor Network" | "Capital Matching" | "Data Room" | "Due Diligence"
  | "Compliance" | "Transactions" | "AI Command Center" | "Settings";

const navigation: { name: ModuleKey; icon: typeof LayoutDashboard; group: string }[] = [
  { name: "Overview", icon: LayoutDashboard, group: "Workspace" },
  { name: "Originators", icon: ContactRound, group: "Workspace" },
  { name: "Clients", icon: Building2, group: "Workspace" },
  { name: "Deal Pipeline", icon: BriefcaseBusiness, group: "Workspace" },
  { name: "Mandate Generator", icon: FileText, group: "Origination" },
  { name: "Investor Network", icon: Network, group: "Origination" },
  { name: "Capital Matching", icon: Target, group: "Origination" },
  { name: "Data Room", icon: FolderOpen, group: "Execution" },
  { name: "Due Diligence", icon: FileCheck2, group: "Execution" },
  { name: "Compliance", icon: ShieldCheck, group: "Execution" },
  { name: "Transactions", icon: Wallet, group: "Execution" },
  { name: "AI Command Center", icon: Sparkles, group: "Intelligence" },
  { name: "Settings", icon: Settings2, group: "Intelligence" },
];

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
const EMPTY_DEALS: Deal[] = [];
const EMPTY_CONTACTS: Contact[] = [];
const CURRENT_DATE_LABEL = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" }).format(new Date());

const illustrative = {
  originators: [
    { name: "Northstar Advisory", type: "Boutique advisory", coverage: "Technology · Industrials", mandate: "3 active", initials: "NA", color: "blue" },
    { name: "Meridian Partners", type: "Investment bank", coverage: "Healthcare · Consumer", mandate: "2 active", initials: "MP", color: "violet" },
    { name: "Westbridge Capital", type: "Independent sponsor", coverage: "Business services", mandate: "4 active", initials: "WC", color: "green" },
  ],
  clients: [
    { name: "Aurelia Systems", industry: "Enterprise software", location: "New York, US", status: "Active" },
    { name: "Cedar Peak Health", industry: "Healthcare technology", location: "Boston, US", status: "In diligence" },
    { name: "Lattice Industrial Group", industry: "Advanced manufacturing", location: "Chicago, US", status: "Active" },
  ],
  investors: [
    { name: "Summit Ridge Capital", type: "Private equity", focus: "Software", minimum: 50_000_000, maximum: 250_000_000, fit: "96%", initials: "SR" },
    { name: "Harborstone Partners", type: "Growth equity", focus: "Healthcare", minimum: 25_000_000, maximum: 100_000_000, fit: "91%", initials: "HP" },
    { name: "Alder Creek Holdings", type: "Family office", focus: "Industrials", minimum: 10_000_000, maximum: 75_000_000, fit: "88%", initials: "AC" },
  ],
  mandates: [
    { name: "Project Atlas", client: "Aurelia Systems", amount: 85_000_000, due: "14 days", status: "Investor outreach" },
    { name: "Project Cedar", client: "Cedar Peak Health", amount: 42_000_000, due: "21 days", status: "Preparation" },
    { name: "Project Foundry", client: "Lattice Industrial Group", amount: 120_000_000, due: "31 days", status: "Market review" },
  ],
  activity: [
    { title: "Investor shortlist prepared", detail: "Project Atlas · 12 qualified investors", time: "12 min ago", icon: Sparkles, tone: "blue" },
    { title: "Due diligence room updated", detail: "Cedar Peak Health · 4 documents added", time: "1 hr ago", icon: FileCheck2, tone: "green" },
    { title: "Mandate terms reviewed", detail: "Project Foundry · Northstar Advisory", time: "3 hrs ago", icon: Handshake, tone: "violet" },
  ],
};

interface DashboardProps {
  onLogout: () => void;
}

interface ExchangeRates {
  date: string;
  rates: Record<string, number>;
}

type CurrencyFormatter = (value: number | null | undefined, sourceCurrency?: string) => string;
type AmountConverter = (value: number | null | undefined, sourceCurrency?: string) => number | null;

const DEFAULT_COUNTRY: CountryCode = "IN";
const COUNTRY_STORAGE_KEY = "dealforge_currency_country";

function sumDealValues(deals: Deal[], convertAmount: AmountConverter, weight: (deal: Deal) => number = () => 1): number | null {
  let total = 0;
  for (const deal of deals) {
    if (deal.value == null) continue;
    const converted = convertAmount(deal.value, deal.currency);
    if (converted === null) return null;
    total += converted * weight(deal);
  }
  return total;
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0] ?? "").join("").toUpperCase();
}

function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><BriefcaseBusiness size={19} /></span>
      <strong>{title}</strong>
      <p>{detail}</p>
      {action}
    </div>
  );
}

export function Dashboard({ onLogout }: DashboardProps) {
  const queryClient = useQueryClient();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const currencySearchRef = useRef<HTMLInputElement>(null);
  const [activeModule, setActiveModule] = useState<ModuleKey>("Overview");
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createKind, setCreateKind] = useState<"deal" | "contact">("deal");
  const [toast, setToast] = useState("");
  const [period, setPeriod] = useState("30D");
  const [settings, setSettings] = useState({ notifications: true, weeklyDigest: false, compact: false });
  const [aiRunning, setAiRunning] = useState(false);
  const [investorFilter, setInvestorFilter] = useState("");
  const [countryCode, setCountryCode] = useState<CountryCode>(() => {
    const storedCountry = localStorage.getItem(COUNTRY_STORAGE_KEY);
    return storedCountry && Object.prototype.hasOwnProperty.call(countryToCurrency, storedCountry)
      ? storedCountry as CountryCode
      : DEFAULT_COUNTRY;
  });
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false);
  const [currencySearch, setCurrencySearch] = useState("");

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  const dealsQuery = useQuery({
    queryKey: ["deals"],
    queryFn: async () => (await dealsApi.list({ limit: 100 })).data,
  });
  const contactsQuery = useQuery({
    queryKey: ["contacts"],
    queryFn: async () => (await contactsApi.list({ limit: 100 })).data,
  });
  const clientsQuery = useQuery({
    queryKey: ["clients"],
    queryFn: async () => (await clientsApi.list({ limit: 100 })).data,
  });
  const originatorsQuery = useQuery({
    queryKey: ["originators"],
    queryFn: async () => (await originatorsApi.list({ limit: 100 })).data,
  });
  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: async () => (await authApi.me()).data,
  });
  const ratesQuery = useQuery<ExchangeRates>({
    queryKey: ["exchange-rates", "INR"],
    queryFn: async () => {
      const response = await fetch("https://latest.currency-api.pages.dev/v1/currencies/inr.json");
      if (!response.ok) {
        throw new Error(`Exchange-rate service returned HTTP ${response.status}.`);
      }
      const payload: unknown = await response.json();
      if (
        typeof payload !== "object" ||
        payload === null ||
        !("date" in payload) ||
        typeof payload.date !== "string" ||
        !("inr" in payload) ||
        typeof payload.inr !== "object" ||
        payload.inr === null
      ) {
        throw new Error("Exchange-rate service returned an invalid INR rate table.");
      }
      const rates = payload.inr as Record<string, unknown>;
      if (Object.values(rates).some((rate) => typeof rate !== "number" || !Number.isFinite(rate) || rate <= 0)) {
        throw new Error("Exchange-rate service returned invalid currency rates.");
      }
      return {
        date: payload.date,
        rates: rates as Record<string, number>,
      };
    },
    staleTime: 6 * 60 * 60 * 1000,
    retry: 1,
  });
  const deals = dealsQuery.data ?? EMPTY_DEALS;
  const contacts = contactsQuery.data ?? EMPTY_CONTACTS;
  const targetCurrency = countryToCurrency[countryCode];
  const exchangeRates = ratesQuery.data?.rates;
  const targetCountry = COUNTRY_CURRENCY_OPTIONS.find((option) => option.countryCode === countryCode);
  const convertAmount = useMemo<AmountConverter>(() => (value, sourceCurrency = "USD") => {
    if (value == null || !Number.isFinite(value)) return null;
    if (sourceCurrency.toUpperCase() === targetCurrency) return value;
    if (!exchangeRates) return null;
    const sourceRate = exchangeRates[sourceCurrency.toLowerCase()];
    const targetRate = exchangeRates[targetCurrency.toLowerCase()];
    if (!sourceRate || !targetRate) return null;
    const converted = value / sourceRate * targetRate;
    return Number.isFinite(converted) ? converted : null;
  }, [exchangeRates, targetCurrency]);
  const currencyFormat = useMemo(
    () => new Intl.NumberFormat("en", {
      style: "currency",
      currency: targetCurrency,
      notation: "compact",
      maximumFractionDigits: 1,
    }),
    [targetCurrency],
  );
  const formatMoney = useMemo<CurrencyFormatter>(() => (value, sourceCurrency = targetCurrency) => {
    if (value == null) return ratesQuery.isLoading ? "…" : "—";
    if (!Number.isFinite(value)) return "—";
    const converted = convertAmount(value, sourceCurrency);
    if (converted === null) return ratesQuery.isLoading ? "…" : "—";
    return currencyFormat.format(converted);
  }, [convertAmount, currencyFormat, ratesQuery.isLoading, targetCurrency]);
  const selectedCurrencyRateMissing = Boolean(exchangeRates && !exchangeRates[targetCurrency.toLowerCase()]);
  const filteredCountries = useMemo(() => {
    const needle = currencySearch.trim().toLowerCase();
    const options = COUNTRY_CURRENCY_OPTIONS.filter((option) =>
      `${option.countryName} ${option.countryCode} ${option.currencyCode} ${option.currencyName}`.toLowerCase().includes(needle),
    );
    return options.sort((left, right) => left.countryCode === countryCode ? -1 : right.countryCode === countryCode ? 1 : left.countryName.localeCompare(right.countryName));
  }, [countryCode, currencySearch]);
  const searchResults = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return [];
    return [
      ...deals.filter((deal) => deal.name.toLowerCase().includes(needle)).slice(0, 4)
        .map((deal) => ({ label: deal.name, meta: `${stages.find((stage) => stage.key === deal.stage)?.label ?? deal.stage} · Deal`, module: "Deal Pipeline" as ModuleKey })),
      ...contacts.filter((contact) => `${contact.full_name} ${contact.company ?? ""}`.toLowerCase().includes(needle)).slice(0, 4)
        .map((contact) => ({ label: contact.full_name, meta: `${contact.company ?? contact.contact_type} · Contact`, module: "Clients" as ModuleKey })),
      ...(clientsQuery.data ?? []).filter((client) => `${client.name} ${client.sector ?? ""}`.toLowerCase().includes(needle)).slice(0, 4)
        .map((client) => ({ label: client.name, meta: `${client.sector ?? client.industry ?? "Client"} · Client`, module: "Clients" as ModuleKey })),
      ...(originatorsQuery.data ?? []).filter((originator) => `${originator.full_name ?? ""} ${originator.firm_name ?? ""}`.toLowerCase().includes(needle)).slice(0, 4)
        .map((originator) => ({ label: originator.full_name ?? originator.firm_name ?? "Originator", meta: `${originator.firm_name ?? "Originator"} · Profile`, module: "Originators" as ModuleKey })),
      ...illustrative.investors.filter((investor) => investor.name.toLowerCase().includes(needle)).slice(0, 2)
        .map((investor) => ({ label: investor.name, meta: `${investor.type} · Illustrative`, module: "Investor Network" as ModuleKey })),
    ];
  }, [clientsQuery.data, contacts, deals, originatorsQuery.data, search]);

  const createMutation = useMutation({
    mutationFn: async (payload:
      | { kind: "deal"; values: Partial<Deal>; file?: File }
      | { kind: "contact"; values: Partial<Contact> }) => {
      if (payload.kind === "contact") {
        await contactsApi.create(payload.values);
        return { documentUploadFailed: false };
      }
      const created = await dealsApi.create(payload.values);
      if (payload.file) {
        try {
          await dealsApi.uploadDocument(created.data.id, payload.file);
          return { documentUploadFailed: false };
        } catch {
          return { documentUploadFailed: true };
        }
      }
      return { documentUploadFailed: false };
    },
    onSuccess: async (result, payload) => {
      await queryClient.invalidateQueries({ queryKey: [payload.kind === "deal" ? "deals" : "contacts"] });
      setShowCreate(false);
      setToast(result.documentUploadFailed
        ? "Deal created, but its document could not be uploaded."
        : payload.kind === "deal" ? "Deal created successfully" : "Contact added successfully");
      window.setTimeout(() => setToast(""), 3200);
    },
  });

  function openCreate(kind: "deal" | "contact") {
    setCreateKind(kind);
    setShowCreate(true);
    setActiveModule(kind === "deal" ? "Deal Pipeline" : "Clients");
  }

  function navigate(module: ModuleKey) {
    setActiveModule(module);
    setShowMobileNav(false);
    setShowSearch(false);
    setSearch("");
  }

  function chooseCountry(nextCountry: CountryCode) {
    setCountryCode(nextCountry);
    localStorage.setItem(COUNTRY_STORAGE_KEY, nextCountry);
    setShowCurrencyPicker(false);
    setCurrencySearch("");
  }

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (createKind === "deal") {
      const transactionSize = String(form.get("transaction_size") || "");
      const optionalNumber = (key: string) => {
        const value = String(form.get(key) || "");
        return value ? Number(value) : undefined;
      };
      const file = form.get("document");
      createMutation.mutate({
        kind: "deal",
        values: {
          name: String(form.get("name")),
          company_name: String(form.get("company_name")),
          industry: String(form.get("industry") || "") || undefined,
          sector: String(form.get("sector") || "") || undefined,
          deal_type: String(form.get("deal_type") || "") || undefined,
          stage: String(form.get("stage")) as DealStage,
          transaction_size: transactionSize ? Number(transactionSize) : undefined,
          value: transactionSize ? Number(transactionSize) : undefined,
          revenue: optionalNumber("revenue"),
          ebitda: optionalNumber("ebitda"),
          funding_requirement: optionalNumber("funding_requirement"),
          target_valuation: optionalNumber("target_valuation"),
          probability: optionalNumber("probability"),
          currency: String(form.get("currency")),
          description: String(form.get("description") || "") || undefined,
          originator_id: String(form.get("originator_id") || "") || undefined,
          client_id: String(form.get("client_id") || "") || undefined,
        },
        file: file instanceof File && file.size ? file : undefined,
      });
    } else {
      createMutation.mutate({
        kind: "contact",
        values: {
          first_name: String(form.get("first_name")),
          last_name: String(form.get("last_name")),
          email: String(form.get("email") || "") || undefined,
          company: String(form.get("company") || ""),
          contact_type: String(form.get("contact_type")) as Contact["contact_type"],
        },
      });
    }
  }

  function runAgent() {
    setAiRunning(true);
    window.setTimeout(() => {
      setAiRunning(false);
      setToast("Market scan complete · 3 illustrative opportunities identified");
      window.setTimeout(() => setToast(""), 3500);
    }, 1400);
  }

  const pageTitle = activeModule === "Overview" ? "Good morning" : activeModule;
  const pageSubtitle = activeModule === "Overview"
    ? "Here’s what’s happening across your deal portfolio."
    : moduleDescriptions[activeModule];
  const isIllustrativeModule = !["Overview", "Deal Pipeline", "Clients", "Originators", "Mandate Generator", "Settings"].includes(activeModule);
  const moduleAction = activeModule === "Deal Pipeline" || activeModule === "Overview"
    ? <button className="button button-primary" onClick={() => openCreate("deal")} type="button"><Plus size={16} /> New deal</button>
    : activeModule === "Clients" || activeModule === "Originators" || activeModule === "Mandate Generator"
      ? null
      : activeModule === "AI Command Center"
        ? <button className="button button-primary" onClick={runAgent} type="button"><Sparkles size={16} /> {aiRunning ? "Running scan…" : "Run market scan"}</button>
        : <button className="button button-secondary" onClick={() => setToast("This workspace is ready for your team’s live data.")} type="button"><CircleHelp size={16} /> Learn more</button>;

  return (
    <div className={`app-shell${settings.compact ? " compact-mode" : ""}`}>
      {showMobileNav && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setShowMobileNav(false)} type="button" />}
      <aside className={`sidebar${showMobileNav ? " sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark"><Zap size={18} fill="currentColor" /></div>
          <div className="brand-copy"><strong>dealforge</strong><span>CAPITAL WORKSPACE</span></div>
          <button className="icon-button sidebar-collapse" aria-label="Close navigation" onClick={() => setShowMobileNav(false)} type="button"><PanelLeftClose size={17} /></button>
        </div>
        <button className="workspace-switch" onClick={() => setShowProfile((open) => !open)} type="button">
          <span className="workspace-avatar">{initials(profileQuery.data?.full_name ?? "DF")}</span>
          <span className="workspace-copy"><strong>{profileQuery.data?.full_name ?? "Your workspace"}</strong><small>{profileQuery.data?.role ?? "Organization"} · Deal team</small></span>
          <ChevronDown size={15} />
        </button>
        <nav className="side-nav" aria-label="Main navigation">
          {["Workspace", "Origination", "Execution", "Intelligence"].map((group) => (
            <div className="nav-group" key={group}>
              <span className="nav-label">{group}</span>
              {navigation.filter((item) => item.group === group).map(({ name, icon: Icon }) => (
                <button key={name} className={`nav-item${activeModule === name ? " nav-active" : ""}`} onClick={() => navigate(name)} type="button">
                  <Icon size={17} strokeWidth={1.8} /><span>{name}</span>
                  {name === "AI Command Center" && <span className="nav-status" />}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="plan-card"><span className="plan-icon"><Sparkles size={15} /></span><div><strong>DealForge Intelligence</strong><small>Workspace protected</small></div><ShieldCheck size={15} className="plan-check" /></div>
          <button className="nav-item support-link" onClick={() => setToast("Support is available at support@dealforge.example")} type="button"><CircleHelp size={17} /><span>Help & support</span><ArrowUpRight size={14} /></button>
          <button className="nav-item signout-link" onClick={onLogout} type="button"><LogOut size={17} /><span>Sign out</span></button>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setShowMobileNav(true)} type="button"><Menu size={19} /></button>
          <div className="breadcrumbs"><span>DealForge</span><ChevronRight size={14} /><strong>{activeModule}</strong></div>
          <div className="topbar-right">
            <div className="global-search">
              <Search size={16} />
              <input ref={searchInputRef} aria-label="Search deals, clients, investors" placeholder="Search deals, clients…" value={search} onFocus={() => setShowSearch(true)} onChange={(event) => { setSearch(event.target.value); setShowSearch(true); }} onKeyDown={(event) => { if (event.key === "Escape") setShowSearch(false); }} />
              <kbd><Command size={11} /> K</kbd>
              {showSearch && search.trim() && <div className="popover search-popover">
                <span className="popover-label">SEARCH RESULTS</span>
                {searchResults.length ? searchResults.map((result) => <button className="search-result" key={`${result.module}-${result.label}`} onClick={() => navigate(result.module)} type="button"><Search size={14} /><span><strong>{result.label}</strong><small>{result.meta}</small></span><ArrowUpRight size={14} /></button>) : <p className="popover-empty">No matching deals or contacts.</p>}
              </div>}
            </div>
            <div className="popover-anchor currency-anchor">
              <button
                className={`currency-button${showCurrencyPicker ? " currency-active" : ""}`}
                aria-label={`Display currency ${targetCurrency}, selected for ${targetCountry?.countryName ?? countryCode}`}
                aria-expanded={showCurrencyPicker}
                onClick={() => {
                  setShowCurrencyPicker((open) => !open);
                  setCurrencySearch("");
                  setShowNotifications(false);
                  setShowProfile(false);
                  window.setTimeout(() => currencySearchRef.current?.focus(), 0);
                }}
                type="button"
              >
                <Globe2 size={15} /><strong>{targetCurrency}</strong><ChevronDown size={13} />
              </button>
              {showCurrencyPicker && <div className="popover currency-popover">
                <div className="currency-popover-heading">
                  <span><strong>Display currency</strong><small>Choose a country to convert deal values.</small></span>
                  <button className="icon-button small-icon" aria-label="Close currency selector" onClick={() => setShowCurrencyPicker(false)} type="button"><X size={15} /></button>
                </div>
                <label className="currency-search"><Search size={14} /><input ref={currencySearchRef} aria-label="Search countries and currencies" placeholder="Search countries or currencies…" value={currencySearch} onChange={(event) => setCurrencySearch(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") setShowCurrencyPicker(false); }} /></label>
                <div className="currency-country-list">
                  {filteredCountries.length ? filteredCountries.map((option) => <button className={`currency-country${countryCode === option.countryCode ? " currency-country-selected" : ""}`} key={option.countryCode} onClick={() => chooseCountry(option.countryCode)} type="button"><span className="currency-country-name">{option.countryName}</span><span className="currency-country-code">{option.currencyCode}</span>{countryCode === option.countryCode && <Check size={14} />}</button>) : <p className="popover-empty">No countries match your search.</p>}
                </div>
                <div className="currency-rate-status">
                  {ratesQuery.isLoading ? <><span className="rate-spinner" /> Loading daily exchange rates…</> : ratesQuery.isError ? <><CircleHelp size={13} /><span>Exchange rates unavailable. Values needing conversion are hidden.</span><button onClick={() => void ratesQuery.refetch()} type="button">Retry</button></> : selectedCurrencyRateMissing ? <><CircleHelp size={13} /><span>No daily rate is published for {targetCurrency}; converted values are hidden.</span></> : <><ShieldCheck size={13} /><span>Daily rates · updated {ratesQuery.data?.date}</span></>}
                </div>
              </div>}
            </div>
            <div className="popover-anchor">
              <button className={`icon-button notification-button${showNotifications ? " control-active" : ""}`} aria-label="Notifications" onClick={() => { setShowNotifications((open) => !open); setShowProfile(false); }} type="button"><Bell size={18} /><i /></button>
              {showNotifications && <div className="popover notification-popover"><div className="popover-heading"><strong>Notifications</strong><button onClick={() => setShowNotifications(false)} type="button">Dismiss</button></div><div className="notification-row"><span className="activity-icon blue"><Sparkles size={15} /></span><span><strong>Investor shortlist ready</strong><small>Project Atlas · 12 minutes ago</small></span></div><div className="notification-row"><span className="activity-icon green"><Check size={15} /></span><span><strong>Workspace secured</strong><small>Your organization data is isolated</small></span></div></div>}
            </div>
            <div className="popover-anchor">
              <button className="user-button" onClick={() => { setShowProfile((open) => !open); setShowNotifications(false); }} type="button"><span className="avatar">{initials(profileQuery.data?.full_name ?? "DF")}</span><span className="user-name">{profileQuery.data?.full_name ?? "Deal team"}</span><ChevronDown size={14} /></button>
              {showProfile && <div className="popover profile-popover"><strong>{profileQuery.data?.full_name ?? "DealForge user"}</strong><small>{profileQuery.data?.email ?? "Workspace account"}</small><button onClick={() => { navigate("Settings"); setShowProfile(false); }} type="button"><Settings2 size={15} /> Account settings</button><button onClick={onLogout} type="button"><LogOut size={15} /> Sign out</button></div>}
            </div>
          </div>
        </header>

        <main className="content-area">
          <div className="page-heading">
            <div><div className="date-line"><span className="live-dot" /> LIVE WORKSPACE <span className="date-divider">/</span> {CURRENT_DATE_LABEL}</div><h1>{pageTitle}{activeModule === "Overview" && <span className="heading-period">, {profileQuery.data?.full_name?.split(" ")[0] ?? "team"}</span>}</h1><p>{pageSubtitle}</p></div>
            <div className="page-actions">{activeModule === "Overview" && <span className="secure-badge"><ShieldCheck size={14} /> Private workspace</span>}{moduleAction}</div>
          </div>
          {(ratesQuery.isError || selectedCurrencyRateMissing) && <div className="error-banner currency-error-banner"><CircleHelp size={17} /><span>{ratesQuery.isError ? "Exchange rates are unavailable. Financial values that need conversion are hidden until rates can be loaded." : `No daily exchange rate is published for ${targetCurrency}. Values that need conversion are hidden.`}</span>{ratesQuery.isError && <button onClick={() => void ratesQuery.refetch()} type="button">Retry rates</button>}</div>}
          {isIllustrativeModule && <div className="illustrative-notice"><Activity size={15} /><span><strong>Illustrative workspace view</strong> · Sample records shown for product demonstration; no live module API is connected yet.</span></div>}
          {activeModule === "Overview" && <Overview deals={deals} contacts={contacts} dealsQuery={dealsQuery} contactsQuery={contactsQuery} onCreate={openCreate} onNavigate={navigate} period={period} setPeriod={setPeriod} formatMoney={formatMoney} convertAmount={convertAmount} />}
          {activeModule === "Deal Pipeline" && <DealPipeline
            deals={deals}
            clients={clientsQuery.data ?? []}
            originators={originatorsQuery.data ?? []}
            loading={dealsQuery.isLoading}
            error={dealsQuery.isError}
            onCreate={() => openCreate("deal")}
            onRetry={() => void dealsQuery.refetch()}
            onStageChange={async (deal, stage) => {
              try {
                await dealsApi.update(deal.id, { stage });
                await queryClient.invalidateQueries({ queryKey: ["deals"] });
              } catch {
                setToast("Could not update deal stage. Please retry.");
              }
            }}
            onUpdate={async (dealId, values) => {
              await dealsApi.update(dealId, values);
              await queryClient.invalidateQueries({ queryKey: ["deals"] });
            }}
            onDelete={async (deal) => {
              await dealsApi.delete(deal.id);
              await queryClient.invalidateQueries({ queryKey: ["deals"] });
              setToast("Deal deleted.");
            }}
            formatMoney={formatMoney}
            convertAmount={convertAmount}
          />}
          {(activeModule === "Clients" || activeModule === "Originators") && <CrmWorkspace title={activeModule} />}
          {activeModule === "Mandate Generator" && <MandateGenerator />}
          {activeModule === "Investor Network" && <Investors filter={investorFilter} onFilterChange={setInvestorFilter} onMatch={() => navigate("Capital Matching")} formatMoney={formatMoney} />}
          {activeModule === "Capital Matching" && <Matches onOpenInvestors={() => navigate("Investor Network")} formatMoney={formatMoney} />}
          {activeModule === "Data Room" && <DataRoom onUpload={() => setToast("Document upload will be available when storage is configured.")} />}
          {activeModule === "Due Diligence" && <DueDiligence onOpenRoom={() => navigate("Data Room")} />}
          {activeModule === "Compliance" && <Compliance />}
          {activeModule === "Transactions" && <Transactions formatMoney={formatMoney} />}
          {activeModule === "AI Command Center" && <AICommand running={aiRunning} onRun={runAgent} />}
          {activeModule === "Settings" && <Settings settings={settings} onChange={(key, value) => setSettings((current) => ({ ...current, [key]: value }))} profile={profileQuery.data} />}
        </main>
      </div>

      {showCreate && <CreateModal
        kind={createKind}
        pending={createMutation.isPending}
        error={createMutation.error}
        originators={originatorsQuery.data ?? []}
        clients={clientsQuery.data ?? []}
        onClose={() => { setShowCreate(false); createMutation.reset(); }}
        onSubmit={submitCreate}
      />}
      {toast && <div className="toast"><span className="toast-check"><Check size={15} /></span>{toast}<button aria-label="Dismiss" onClick={() => setToast("")} type="button"><X size={15} /></button></div>}
    </div>
  );
}

function Overview({ deals, contacts, dealsQuery, contactsQuery, onCreate, onNavigate, period, setPeriod, formatMoney, convertAmount }: {
  deals: Deal[]; contacts: Contact[];
  dealsQuery: { isLoading: boolean; isError: boolean; refetch: () => Promise<unknown> };
  contactsQuery: { isLoading: boolean; isError: boolean };
  onCreate: (kind: "deal" | "contact") => void;
  onNavigate: (module: ModuleKey) => void;
  period: string; setPeriod: (period: string) => void;
  formatMoney: CurrencyFormatter;
  convertAmount: AmountConverter;
}) {
  const openDeals = deals.filter((deal) => !["closed_won", "closed_lost"].includes(deal.stage));
  const activeValue = sumDealValues(openDeals, convertAmount);
  const weighted = sumDealValues(openDeals, convertAmount, (deal) => (deal.probability ?? 0) / 100);
  const closedDeals = deals.filter((deal) => deal.stage === "closed_won");
  const wonValue = sumDealValues(closedDeals, convertAmount);
  const loading = dealsQuery.isLoading || contactsQuery.isLoading;
  return (
    <>
      <section className="metric-grid">
        <Metric label="Active pipeline" value={dealsQuery.isError ? "—" : formatMoney(activeValue)} sub={`${openDeals.length} active opportunities`} icon={TrendingUp} trend="Portfolio value" tone="blue" loading={loading} />
        <Metric label="Weighted pipeline" value={dealsQuery.isError ? "—" : formatMoney(weighted)} sub="Probability-adjusted value" icon={Target} trend="Risk-adjusted" tone="violet" loading={dealsQuery.isLoading} />
        <Metric label="Closed won" value={dealsQuery.isError ? "—" : formatMoney(wonValue)} sub={`${closedDeals.length} completed transactions`} icon={Wallet} trend="Lifetime" tone="green" loading={dealsQuery.isLoading} />
        <Metric label="Relationships" value={contactsQuery.isError ? "—" : contacts.length.toString()} sub="Across your organization" icon={Users} trend="CRM contacts" tone="amber" loading={contactsQuery.isLoading} />
      </section>

      {(dealsQuery.isError || contactsQuery.isError) && <div className="error-banner"><CircleHelp size={17} /><span>Some live workspace data could not be loaded.</span><button onClick={() => void dealsQuery.refetch()} type="button">Retry</button></div>}

      <div className="overview-grid">
        <section className="panel pipeline-panel">
          <div className="panel-header"><div><span className="eyebrow">PORTFOLIO HEALTH</span><h2>Deal pipeline</h2></div><div className="panel-controls"><div className="period-tabs">{["7D", "30D", "90D"].map((item) => <button className={period === item ? "period-active" : ""} key={item} onClick={() => setPeriod(item)} type="button">{item}</button>)}</div><button className="icon-button small-icon" aria-label="Open full pipeline" onClick={() => onNavigate("Deal Pipeline")} type="button"><ArrowUpRight size={15} /></button></div></div>
          {dealsQuery.isLoading ? <SkeletonChart /> : dealsQuery.isError ? <EmptyState title="Pipeline unavailable" detail="Check your connection and retry to load live deals." action={<button className="button button-secondary" onClick={() => void dealsQuery.refetch()} type="button">Retry connection</button>} /> : deals.length === 0 ? <EmptyState title="Your pipeline starts here" detail="Create an opportunity to see stage distribution and portfolio value." action={<button className="button button-secondary" onClick={() => onCreate("deal")} type="button"><Plus size={15} /> Create first deal</button>} /> : <PipelineChart deals={deals} formatMoney={formatMoney} convertAmount={convertAmount} />}
          <div className="chart-footnote"><span><span className="legend-dot blue-dot" /> Active deal volume</span><span>{deals.length} total opportunities</span></div>
        </section>

        <section className="panel agent-panel">
          <div className="panel-header"><div><span className="eyebrow">DEALFORGE INTELLIGENCE</span><h2>AI agent activity</h2></div><span className="online-badge"><i /> Operational</span></div>
          <div className="agent-summary"><div className="agent-orbit"><div className="orbit-ring" /><Sparkles size={21} /></div><div><strong>Origination copilot</strong><p>Monitoring pipeline signals and matching opportunities.</p></div></div>
          <div className="agent-tasks">{illustrative.activity.slice(0, 3).map((item) => <div className="agent-task" key={item.title}><span className={`activity-icon ${item.tone}`}><item.icon size={14} /></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className="task-time">{item.time}</span></div>)}</div>
          <button className="text-action" onClick={() => onNavigate("AI Command Center")} type="button">Open command center <ArrowRight size={14} /></button>
        </section>

        <section className="panel recent-panel">
          <div className="panel-header"><div><span className="eyebrow">LATEST OPPORTUNITIES</span><h2>Recent deals</h2></div><button className="text-action" onClick={() => onNavigate("Deal Pipeline")} type="button">View pipeline <ArrowRight size={14} /></button></div>
          {dealsQuery.isLoading ? <SkeletonRows /> : dealsQuery.isError ? <EmptyState title="Couldn’t load deals" detail="Live opportunity data is temporarily unavailable." action={<button className="button button-secondary" onClick={() => void dealsQuery.refetch()} type="button">Try again</button>} /> : deals.length === 0 ? <EmptyState title="No deals yet" detail="Your organization’s opportunities will appear here once added." action={<button className="button button-secondary" onClick={() => onCreate("deal")} type="button"><Plus size={15} /> Add an opportunity</button>} /> : <DealTable deals={deals.slice(0, 5)} formatMoney={formatMoney} />}
        </section>

        <section className="panel mandates-panel">
          <div className="panel-header"><div><span className="eyebrow">ORIGINATION TRACKER</span><h2>Active mandates</h2></div><button className="icon-button small-icon" aria-label="View mandates" onClick={() => onNavigate("Mandate Generator")} type="button"><ArrowUpRight size={15} /></button></div>
          <div className="mandate-list">{illustrative.mandates.map((item, index) => <button className="mandate-row" key={item.name} onClick={() => onNavigate("Mandate Generator")} type="button"><span className={`mandate-number mandate-${index}`}>0{index + 1}</span><span className="mandate-main"><strong>{item.name}</strong><small>{item.client}</small></span><span className="mandate-value"><strong>{formatMoney(item.amount, "USD")}</strong><small>{item.due}</small></span><ChevronRight size={15} /></button>)}</div>
          <p className="panel-footnote">Fictional sample mandates · Open Mandate Generator to create source-grounded drafts</p>
        </section>

        <section className="panel investor-panel">
          <div className="panel-header"><div><span className="eyebrow">NETWORK COVERAGE</span><h2>Investor network</h2></div><button className="text-action" onClick={() => onNavigate("Investor Network")} type="button">Explore network <ArrowRight size={14} /></button></div>
          <div className="investor-strip">{illustrative.investors.map((investor) => <button className="investor-chip" key={investor.name} onClick={() => onNavigate("Investor Network")} type="button"><span className="avatar investor-avatar">{investor.initials}</span><span><strong>{investor.name}</strong><small>{investor.type} · {investor.fit} match fit</small></span><ArrowUpRight size={14} /></button>)}</div>
          <p className="panel-footnote">Illustrative profiles · Investor API not connected</p>
        </section>
      </div>
    </>
  );
}

function Metric({ label, value, sub, icon: Icon, trend, tone, loading }: { label: string; value: string; sub: string; icon: typeof TrendingUp; trend: string; tone: string; loading: boolean }) {
  return <article className="metric-card"><div className="metric-top"><span className={`metric-icon ${tone}`}><Icon size={17} /></span><span className="metric-trend"><ArrowUpRight size={13} /> {trend}</span></div><span className="metric-label">{label}</span>{loading ? <span className="skeleton metric-skeleton" /> : <strong className="metric-value">{value}</strong>}<span className="metric-sub">{sub}</span></article>;
}

function PipelineChart({ deals, formatMoney, convertAmount }: { deals: Deal[]; formatMoney: CurrencyFormatter; convertAmount: AmountConverter }) {
  const active = deals.filter((deal) => !["closed_won", "closed_lost"].includes(deal.stage));
  return <div className="pipeline-visual">
    <div className="funnel-bars">{stages.slice(0, 4).map((stage) => {
      const stageDeals = active.filter((deal) => deal.stage === stage.key);
      const value = sumDealValues(stageDeals, convertAmount);
      const max = Math.max(...stages.slice(0, 4).map((item) => sumDealValues(active.filter((deal) => deal.stage === item.key), convertAmount) ?? 0), 1);
      return <div className="funnel-col" key={stage.key}><strong>{stageDeals.length}</strong><div className="funnel-track"><span className={`funnel-fill ${stage.tone}`} style={{ height: `${Math.max((value ?? 0) / max * 100, stageDeals.length ? 18 : 4)}%` }} /></div><span>{stage.label}</span><small>{formatMoney(value)}</small></div>;
    })}</div>
    <div className="pipeline-chart-total"><span>Weighted active value</span><strong>{formatMoney(sumDealValues(active, convertAmount, (deal) => (deal.probability ?? 0) / 100))}</strong><span className="chart-total-caption">{active.length} active {active.length === 1 ? "deal" : "deals"}</span></div>
  </div>;
}

function DealTable({ deals, formatMoney }: { deals: Deal[]; formatMoney: CurrencyFormatter }) {
  return <div className="table-scroll"><table className="data-table"><thead><tr><th>Opportunity</th><th>Stage</th><th>Probability</th><th className="align-right">Value</th></tr></thead><tbody>{deals.map((deal) => <tr key={deal.id}><td><span className="table-primary">{deal.name}</span><span className="table-secondary">Updated {new Date(deal.updated_at).toLocaleDateString()}</span></td><td><span className={`stage-pill stage-${deal.stage}`}>{stages.find((stage) => stage.key === deal.stage)?.label ?? deal.stage}</span></td><td><div className="probability"><span><i style={{ width: `${deal.probability ?? 0}%` }} /></span>{deal.probability ?? 0}%</div></td><td className="align-right value-cell">{formatMoney(deal.value ?? 0, deal.currency)}</td></tr>)}</tbody></table></div>;
}

function Investors({ filter, onFilterChange, onMatch, formatMoney }: { filter: string; onFilterChange: (value: string) => void; onMatch: () => void; formatMoney: CurrencyFormatter }) {
  const filtered = illustrative.investors.filter((investor) => `${investor.name} ${investor.type} ${investor.focus}`.toLowerCase().includes(filter.toLowerCase()));
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Network profiles" value="1,284" /><MiniStat label="Active relationships" value="246" /><MiniStat label="Sector coverage" value="18 sectors" /><MiniStat label="New this quarter" value="+34" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">ILLUSTRATIVE NETWORK</span><h2>Investor relationships</h2></div><div className="inline-search"><Search size={15} /><input aria-label="Search investors" placeholder="Search network…" value={filter} onChange={(event) => onFilterChange(event.target.value)} /></div></div>{filtered.length ? <div className="investor-cards">{filtered.map((investor) => <article className="investor-card" key={investor.name}><div className="investor-card-top"><span className="avatar investor-avatar">{investor.initials}</span><span className="match-score">{investor.fit} fit</span></div><strong>{investor.name}</strong><span>{investor.type}</span><div className="investor-focus"><span>Investment focus</span><strong>{investor.focus} · {formatMoney(investor.minimum, "USD")}–{formatMoney(investor.maximum, "USD")}</strong></div><button className="button button-secondary button-full" onClick={onMatch} type="button">View opportunities <ArrowRight size={14} /></button></article>)}</div> : <EmptyState title="No investors match" detail="Try a different firm name, strategy, or sector." /> }<div className="footnote-banner">Fictional profiles for interface demonstration · Investor network API is not connected.</div></section></div>;
}

function Matches({ onOpenInvestors, formatMoney }: { onOpenInvestors: () => void; formatMoney: CurrencyFormatter }) {
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Potential matches" value="28" /><MiniStat label="High confidence" value="11" /><MiniStat label="Capital identified" value={formatMoney(412_000_000, "USD")} /><MiniStat label="Sectors covered" value="08" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">ILLUSTRATIVE MATCH INTELLIGENCE</span><h2>Capital match shortlist</h2></div><button className="button button-secondary" onClick={onOpenInvestors} type="button"><Users size={15} /> Investor network</button></div><div className="match-list">{illustrative.investors.map((investor, index) => <div className="match-row" key={investor.name}><span className="match-rank">0{index + 1}</span><div className="match-deal"><strong>{["Project Atlas", "Project Cedar", "Project Foundry"][index]}</strong><small>{["Enterprise software", "Healthcare technology", "Advanced manufacturing"][index]}</small></div><span className="avatar investor-avatar">{investor.initials}</span><div className="match-investor"><strong>{investor.name}</strong><small>{investor.focus} · {formatMoney(investor.minimum, "USD")}–{formatMoney(investor.maximum, "USD")}</small></div><div className="match-fit"><strong>{investor.fit}</strong><small>Fit score</small></div><button className="icon-button small-icon" aria-label={`Review match for ${investor.name}`} onClick={onOpenInvestors} type="button"><ArrowUpRight size={15} /></button></div>)}</div><div className="footnote-banner">Match rankings are fictional examples and are not generated from live investor data.</div></section></div>;
}

function DataRoom({ onUpload }: { onUpload: () => void }) {
  const docs = [{ name: "Information memorandum", project: "Project Atlas", date: "Today", status: "Reviewed", icon: FileText }, { name: "Quality of earnings report", project: "Project Cedar", date: "Yesterday", status: "In review", icon: FileCheck2 }, { name: "Management presentation", project: "Project Foundry", date: "Nov 08", status: "Reviewed", icon: FileText }];
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Active rooms" value="12" /><MiniStat label="Documents" value="386" /><MiniStat label="Pending review" value="07" /><MiniStat label="Access requests" value="03" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">SECURE DOCUMENT WORKSPACE</span><h2>Recent data room activity</h2></div><button className="button button-primary" onClick={onUpload} type="button"><Plus size={15} /> Upload document</button></div><div className="document-list">{docs.map((doc) => <div className="document-row" key={doc.name}><span className="document-icon"><doc.icon size={17} /></span><span className="document-name"><strong>{doc.name}</strong><small>{doc.project} · {doc.date}</small></span><span className="neutral-pill">{doc.status}</span><button className="icon-button small-icon" aria-label={`Open ${doc.name}`} onClick={onUpload} type="button"><ArrowUpRight size={15} /></button></div>)}</div><div className="footnote-banner">Fictional document metadata · File storage integration is not configured.</div></section></div>;
}

function DueDiligence({ onOpenRoom }: { onOpenRoom: () => void }) {
  const checks = [{ name: "Corporate structure", count: "12 / 12", state: "Complete" }, { name: "Financial review", count: "08 / 14", state: "In progress" }, { name: "Legal documentation", count: "06 / 11", state: "In progress" }, { name: "Management references", count: "03 / 08", state: "In progress" }];
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Open workstreams" value="08" /><MiniStat label="Checks complete" value="74%" /><MiniStat label="Items outstanding" value="19" /><MiniStat label="Next review" value="Today" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">ILLUSTRATIVE WORKSTREAM</span><h2>Project Atlas · diligence tracker</h2></div><button className="button button-secondary" onClick={onOpenRoom} type="button"><FileText size={15} /> Open data room</button></div><div className="checklist">{checks.map((check) => <div className="checklist-row" key={check.name}><span className="checklist-mark"><Check size={14} /></span><span><strong>{check.name}</strong><small>{check.state === "Complete" ? "All requested documents received" : "Outstanding items require review"}</small></span><span className="check-count">{check.count}</span><span className={`neutral-pill${check.state === "Complete" ? " pill-green" : ""}`}>{check.state}</span></div>)}</div><div className="footnote-banner">Fictional project and checklist progress for demonstration purposes.</div></section></div>;
}

function Compliance() {
  const checks = [{ name: "Entity verification", scope: "Organization · 2026 annual review", state: "Verified" }, { name: "Sanctions screening", scope: "Investor network · 246 profiles", state: "Monitoring" }, { name: "Data retention policy", scope: "Workspace configuration", state: "Current" }, { name: "Access review", scope: "User permissions · last reviewed Nov 04", state: "Review due" }];
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Control status" value="Healthy" /><MiniStat label="Open reviews" value="02" /><MiniStat label="Policies current" value="11 / 12" /><MiniStat label="Last audit" value="Nov 04" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">WORKSPACE CONTROLS</span><h2>Compliance overview</h2></div><span className="secure-badge"><ShieldCheck size={14} /> Protected</span></div><div className="compliance-list">{checks.map((check) => <div className="compliance-row" key={check.name}><span className="compliance-check"><ShieldCheck size={16} /></span><span><strong>{check.name}</strong><small>{check.scope}</small></span><span className={`neutral-pill${check.state === "Verified" || check.state === "Current" ? " pill-green" : ""}`}>{check.state}</span><ChevronRight size={15} /></div>)}</div><div className="footnote-banner">Illustrative compliance checklist · No legal or regulatory determination is implied.</div></section></div>;
}

function Transactions({ formatMoney }: { formatMoney: CurrencyFormatter }) {
  const rows = [{ name: "Atlas Growth Financing", client: "Aurelia Systems", amount: 85_000_000, status: "Documentation", date: "Nov 18, 2026" }, { name: "Cedar Series C", client: "Cedar Peak Health", amount: 42_000_000, status: "Conditions precedent", date: "Nov 26, 2026" }, { name: "Foundry Acquisition", client: "Lattice Industrial Group", amount: 120_000_000, status: "Preparation", date: "Dec 04, 2026" }];
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="In execution" value="06" /><MiniStat label="Deal value" value={formatMoney(247_000_000, "USD")} /><MiniStat label="Closing this quarter" value="03" /><MiniStat label="Avg. time to close" value="47 days" /></div><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">ILLUSTRATIVE TRANSACTION TRACKER</span><h2>Execution overview</h2></div><button className="button button-secondary" onClick={() => window.print()} type="button"><FileText size={15} /> Export view</button></div><div className="table-scroll"><table className="data-table full-table"><thead><tr><th>Transaction</th><th>Client</th><th>Value</th><th>Stage</th><th>Expected close</th></tr></thead><tbody>{rows.map((row) => <tr key={row.name}><td><strong className="table-primary">{row.name}</strong></td><td>{row.client}</td><td className="value-cell">{formatMoney(row.amount, "USD")}</td><td><span className="neutral-pill">{row.status}</span></td><td>{row.date}</td></tr>)}</tbody></table></div><div className="footnote-banner">Fictional transaction records · No transaction API is currently connected.</div></section></div>;
}

function AICommand({ running, onRun }: { running: boolean; onRun: () => void }) {
  return <div className="module-stack"><div className="module-stat-row"><MiniStat label="Agents online" value="04" /><MiniStat label="Tasks today" value="18" /><MiniStat label="Opportunities surfaced" value="07" /><MiniStat label="System status" value="Operational" /></div><div className="ai-command-grid"><section className="panel ai-command-card"><div className="ai-command-orbit"><div /><Sparkles size={30} /></div><span className="eyebrow">ORIGINATION COPILOT</span><h2>Market intelligence, on demand.</h2><p>Scan deal signals, investor mandates, and sector activity to surface relevant opportunities for your team.</p><button className="button button-primary" onClick={onRun} type="button"><Sparkles size={15} /> {running ? "Scanning market signals…" : "Run market scan"}</button><small>Demo interaction · no external AI provider is configured.</small></section><section className="panel module-panel"><div className="panel-header"><div><span className="eyebrow">RECENT ACTIVITY</span><h2>Agent operations</h2></div><span className="online-badge"><i /> All systems nominal</span></div><div className="agent-tasks large-tasks">{illustrative.activity.map((item) => <div className="agent-task" key={item.title}><span className={`activity-icon ${item.tone}`}><item.icon size={15} /></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className="task-time">{item.time}</span></div>)}</div></section></div></div>;
}

type WorkspaceSettings = { notifications: boolean; weeklyDigest: boolean; compact: boolean };

function Settings({ settings, onChange, profile }: { settings: WorkspaceSettings; onChange: (key: keyof WorkspaceSettings, value: boolean) => void; profile?: { full_name: string; email: string; role: string } }) {
  return <div className="settings-grid"><section className="panel settings-panel"><span className="eyebrow">PERSONAL PROFILE</span><h2>Account details</h2><div className="profile-summary"><span className="avatar profile-avatar">{initials(profile?.full_name ?? "DF")}</span><span><strong>{profile?.full_name ?? "DealForge user"}</strong><small>{profile?.email ?? "Account email"}</small></span><span className="neutral-pill">{profile?.role ?? "member"}</span></div><p className="settings-note">Your account is authenticated and scoped to your organization. Profile editing is available through the secure account API.</p></section><section className="panel settings-panel"><span className="eyebrow">WORKSPACE PREFERENCES</span><h2>Interface & notifications</h2><ToggleRow title="Workspace notifications" detail="Receive updates about deals and investor activity." checked={settings.notifications} onChange={(value) => onChange("notifications", value)} /><ToggleRow title="Weekly digest" detail="Show a weekly summary of workspace activity." checked={settings.weeklyDigest} onChange={(value) => onChange("weeklyDigest", value)} /><ToggleRow title="Compact density" detail="Reduce spacing across lists and data tables." checked={settings.compact} onChange={(value) => onChange("compact", value)} /></section><section className="panel settings-panel security-settings"><span className="eyebrow">SECURITY</span><h2>Organization protection</h2><div className="security-row"><ShieldCheck size={17} /><span><strong>Tenant isolation enabled</strong><small>Your data is scoped to your organization.</small></span><span className="pill-green neutral-pill">Active</span></div><div className="security-row"><Check size={17} /><span><strong>Authenticated session</strong><small>Protected API requests use expiring access tokens.</small></span><span className="pill-green neutral-pill">Secure</span></div></section></div>;
}

function ToggleRow({ title, detail, checked, onChange }: { title: string; detail: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <div className="toggle-row"><span><strong>{title}</strong><small>{detail}</small></span><button className={`toggle${checked ? " toggle-on" : ""}`} aria-pressed={checked} aria-label={`${title}: ${checked ? "on" : "off"}`} onClick={() => onChange(!checked)} type="button"><i /></button></div>;
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return <article className="mini-stat"><span>{label}</span><strong>{value}</strong></article>;
}

function SkeletonChart() {
  return <div className="skeleton-chart">{[48, 73, 56, 88, 63, 94, 70, 82].map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}</div>;
}

function SkeletonRows() {
  return <div className="skeleton-rows">{[0, 1, 2].map((row) => <span key={row} />)}</div>;
}

function CreateModal({ kind, pending, error, originators, clients, onClose, onSubmit }: { kind: "deal" | "contact"; pending: boolean; error: Error | null; originators: Originator[]; clients: Client[]; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="create-modal" role="dialog" aria-modal="true" aria-labelledby="create-title"><div className="modal-heading"><div><span className="eyebrow">LIVE CRM RECORD</span><h2 id="create-title">{kind === "deal" ? "Create opportunity" : "Add a relationship"}</h2></div><button className="icon-button" aria-label="Close dialog" onClick={onClose} type="button"><X size={18} /></button></div><p className="modal-description">{kind === "deal" ? "Add a new opportunity to your organization’s secure pipeline." : "Add a contact to your organization’s relationship network."}</p><form className="create-form" onSubmit={onSubmit}>
    {kind === "deal" ? <>
      <label>Deal title<input autoFocus maxLength={255} minLength={1} name="name" placeholder="e.g. Project Northstar" required /></label>
      <label>Company name<input maxLength={255} name="company_name" placeholder="Company legal or trading name" required /></label>
      <div className="form-two"><label>Industry<input maxLength={120} name="industry" placeholder="e.g. Software" /></label><label>Sector<input maxLength={120} name="sector" placeholder="e.g. Technology" /></label></div>
      <div className="form-two"><label>Deal type<input maxLength={100} name="deal_type" placeholder="Growth financing, acquisition..." /></label><label>Current stage<select name="stage">{stages.map((stage) => <option key={stage.key} value={stage.key}>{stage.label}</option>)}</select></label></div>
      <div className="form-two"><label>Transaction size<input min="0" name="transaction_size" placeholder="0" required step="any" type="number" /></label><label>Currency<select name="currency"><option value="USD">USD · US Dollar</option><option value="EUR">EUR · Euro</option><option value="GBP">GBP · Pound Sterling</option><option value="INR">INR · Indian Rupee</option></select></label></div>
      <div className="form-two"><label>Revenue<input min="0" name="revenue" placeholder="Annual revenue" step="any" type="number" /></label><label>EBITDA<input name="ebitda" placeholder="EBITDA" step="any" type="number" /></label></div>
      <div className="form-two"><label>Funding requirement<input min="0" name="funding_requirement" placeholder="Funding needed" step="any" type="number" /></label><label>Target valuation<input min="0" name="target_valuation" placeholder="Target valuation" step="any" type="number" /></label></div>
      <div className="form-two"><label>Originator assignment<select name="originator_id"><option value="">Unassigned</option>{originators.map((originator) => <option key={originator.id} value={originator.id}>{originator.full_name}</option>)}</select></label><label>Linked client<select name="client_id"><option value="">No linked client</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label></div>
      <div className="form-two"><label>Probability<input max="100" min="0" name="probability" placeholder="0" type="number" /></label><label>Deal document<input accept=".pdf,.docx,.txt,.csv,.xlsx" name="document" type="file" /></label></div>
      <label>Deal description<textarea maxLength={10000} name="description" placeholder="Add context for your team…" rows={3} /></label>
    </> : <>
      <div className="form-two"><label>First name<input autoFocus maxLength={100} name="first_name" placeholder="First name" required /></label><label>Last name<input maxLength={100} name="last_name" placeholder="Last name" required /></label></div>
      <label>Work email<input maxLength={254} name="email" placeholder="name@company.com" type="email" /></label>
      <label>Organization<input maxLength={255} name="company" placeholder="Company or firm" /></label>
      <label>Relationship type<select name="contact_type"><option value="lead">Lead</option><option value="prospect">Prospect</option><option value="customer">Customer</option><option value="partner">Partner</option></select></label>
    </>}
    {error && <div className="form-error" role="alert">{error.message}</div>}
    <div className="modal-actions"><button className="button button-secondary" onClick={onClose} type="button">Cancel</button><button className="button button-primary" disabled={pending} type="submit">{pending ? <span className="button-spinner" /> : <Plus size={15} />}{kind === "deal" ? "Create opportunity" : "Save contact"}</button></div>
  </form></section></div>;
}

const moduleDescriptions: Record<ModuleKey, string> = {
  Overview: "Here’s what’s happening across your deal portfolio.",
  Clients: "Manage client profiles, onboarding, documents, and interactions.",
  Originators: "Manage originator profiles, relationships, and sourced deals.",
  "Deal Pipeline": "Track opportunities from initial qualification through close.",
  "Mandate Generator": "Extract document facts and prepare human-reviewed mandate and teaser drafts.",
  "Investor Network": "Explore investor relationships, mandates, and sector coverage.",
  "Capital Matching": "Surface aligned investors for active opportunities.",
  "Data Room": "Coordinate secure document access across transactions.",
  "Due Diligence": "Track diligence requests, reviews, and outstanding workstreams.",
  Compliance: "Monitor organization controls and compliance workflows.",
  Transactions: "Follow execution milestones from signing through close.",
  "AI Command Center": "Coordinate intelligence workflows across your deal lifecycle.",
  Settings: "Manage your profile, workspace preferences, and security.",
};
