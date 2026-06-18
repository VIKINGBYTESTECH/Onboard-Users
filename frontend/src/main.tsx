import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BadgeCheck,
  ClipboardCheck,
  FileText,
  KeyRound,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { PublicClientApplication, type AccountInfo } from "@azure/msal-browser";
import "./styles.css";

const explicitApiBase = import.meta.env.VITE_API_BASE_URL || "";
const inferredBackendBase = `${window.location.protocol}//${window.location.hostname}:8010`;
const API_BASES = explicitApiBase ? [explicitApiBase] : ["", inferredBackendBase];
const HELP_URL = explicitApiBase ? `${explicitApiBase}/help/setup` : "/help/setup";

type Employee = {
  full_name: string;
  company: string;
  job_title: string;
  department: string;
  manager: string;
  office_location: string;
  start_date: string;
  employee_type: string;
  needs_pc: "Ja" | "Nei";
  needs_mobile: "Ja" | "Nei";
};

type Approvals = {
  hr_approved: boolean;
  manager_approved: boolean;
  execute: boolean;
};

type Report = {
  summary: string[];
  errors: string[];
  deviations: string[];
  next_steps: string[];
  status: "Fullført" | "Delvis fullført" | "Avventer";
  username: string | null;
  temporary_password: string | null;
  accounts: string[];
  groups: string[];
  licenses: string[];
  teams: string[];
  sharepoint_groups: string[];
  distribution_lists: string[];
  equipment: string[];
  tasks: string[];
  welcome_email: string;
  audit_log: string[];
  graph_configured: boolean;
  graph_executed: boolean;
  raw_graph_results: Record<string, unknown>[];
};

type Config = {
  graph_configured: boolean;
  default_domain: string;
  send_password_by_email: boolean;
  entra_tenant_id: string;
  entra_client_id: string;
  admin_auth_available: boolean;
};

type Options = {
  companies: string[];
  departments: string[];
  office_locations: string[];
  employee_types: string[];
  pc_models: string[];
  mobile_subscriptions: string[];
};

type SetupRuntime = {
  frontend_origin: string;
  entra_tenant_id: string;
  entra_client_id: string;
  entra_client_secret: string;
  entra_default_domain: string;
  entra_usage_location: string;
  onboarding_portal_url: string;
  it_contact_email: string;
  send_password_by_email: boolean;
};

type SetupStatus = {
  enabled: boolean;
  complete: boolean;
  needs_setup: boolean;
  restart_required: boolean;
  options: Options;
};

const emptyEmployee: Employee = {
  full_name: "",
  company: "Example Company AS",
  job_title: "",
  department: "IT",
  manager: "",
  office_location: "Oslo",
  start_date: new Date().toISOString().slice(0, 10),
  employee_type: "Fast",
  needs_pc: "Ja",
  needs_mobile: "Nei",
};

async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const errors: string[] = [];
  for (const base of API_BASES) {
    const url = `${base}${path}`;
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options.headers || {}),
        },
      });
      if (!res.ok) {
        errors.push(`${url}: ${res.status} ${await res.text()}`);
        continue;
      }
      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const text = await res.text();
        errors.push(`${url}: forventet JSON, fikk ${text.slice(0, 120)}`);
        continue;
      }
      return res.json();
    } catch (err) {
      errors.push(`${url}: ${err instanceof Error ? err.message : String(err)}`);
    }
  }
  throw new Error(errors.join("\n"));
}

async function microsoftSignIn(config: Config): Promise<{ account: AccountInfo | null; token: string }> {
  if (!config.entra_client_id || !config.entra_tenant_id) {
    throw new Error("Microsoft-login krever ENTRA_CLIENT_ID og ENTRA_TENANT_ID.");
  }
  const msal = new PublicClientApplication({
    auth: {
      clientId: config.entra_client_id,
      authority: `https://login.microsoftonline.com/${config.entra_tenant_id}`,
      redirectUri: window.location.origin,
    },
    cache: { cacheLocation: "sessionStorage" },
  });
  await msal.initialize();
  const response = await msal.loginPopup({ scopes: ["openid", "profile", "email"] });
  return { account: response.account, token: response.idToken };
}

function App() {
  const [employee, setEmployee] = useState<Employee>(emptyEmployee);
  const [approvals, setApprovals] = useState<Approvals>({
    hr_approved: false,
    manager_approved: false,
    execute: false,
  });
  const [config, setConfig] = useState<Config | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<"onboarding" | "admin">("onboarding");
  const [authAccount, setAuthAccount] = useState<AccountInfo | null>(null);
  const [authToken, setAuthToken] = useState("");

  useEffect(() => {
    api<SetupStatus>("/api/setup/status").then((status) => {
      setSetupStatus(status);
      setOptions(status.options);
      applyOptions(status.options);
    }).catch((err) => setError(String(err)));
    api<Config>("/api/config").then(setConfig).catch((err) => setError(String(err)));
  }, []);

  const authRequired = Boolean(config?.admin_auth_available && !setupStatus?.needs_setup);

  useEffect(() => {
    if (!config || setupStatus?.needs_setup) return;
    if (authRequired && !authToken) return;
    api<Options>("/api/options", {}, authToken || undefined).then((data) => {
      setOptions(data);
      applyOptions(data);
    }).catch((err) => setError(String(err)));
  }, [authRequired, authToken, config, setupStatus?.needs_setup]);

  function applyOptions(data: Options) {
    setEmployee((current) => ({
      ...current,
      company: data.companies.includes(current.company) ? current.company : data.companies[0] || current.company,
      department: data.departments.includes(current.department) ? current.department : data.departments[0] || current.department,
      office_location: data.office_locations.includes(current.office_location)
        ? current.office_location
        : data.office_locations[0] || current.office_location,
      employee_type: data.employee_types.includes(current.employee_type) ? current.employee_type : data.employee_types[0] || current.employee_type,
    }));
  }

  const canRun = useMemo(
    () => approvals.hr_approved && approvals.manager_approved && approvals.execute,
    [approvals],
  );

  function patchEmployee<K extends keyof Employee>(key: K, value: Employee[K]) {
    setEmployee((current) => ({ ...current, [key]: value }));
  }

  async function submit(mode: "preview" | "run") {
    setBusy(true);
    setError("");
    try {
      const data = await api<Report>(`/api/onboarding/${mode}`, {
        method: "POST",
        body: JSON.stringify({ employee, approvals }),
      }, authToken || undefined);
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="title-block">
          <div className="mark">
            <UserPlus size={22} />
          </div>
          <div>
            <h1>IT Onboarding</h1>
            <p>HR-input, godkjenning, Entra-provisjonering og rapport</p>
          </div>
        </div>
        <div className="top-actions">
          <button className="secondary admin-button" onClick={() => setView(view === "admin" ? "onboarding" : "admin")}>
            <ShieldCheck size={17} />
            {view === "admin" ? "ONBOARDING" : "ADMIN"}
          </button>
          <div className={`connection ${config?.graph_configured ? "online" : "offline"}`}>
            <ShieldCheck size={17} />
            <span>{config?.graph_configured ? "Entra konfigurert" : "Planmodus"}</span>
          </div>
        </div>
      </header>

      {setupStatus?.needs_setup ? (
        <SetupWizard initialOptions={setupStatus.options} onSaved={(status) => setSetupStatus(status)} />
      ) : authRequired && !authToken && config ? (
        <LoginGate
          config={config}
          onAuthenticated={({ account, token }) => {
            setAuthAccount(account);
            setAuthToken(token);
          }}
        />
      ) : (
      <>
        {view === "admin" ? (
          <AdminPage
            config={config}
            authAccount={authAccount}
            authToken={authToken}
            onAuthenticated={({ account, token }) => {
              setAuthAccount(account);
              setAuthToken(token);
            }}
            onOptionsSaved={(saved) => setOptions(saved)}
            onSetupReopened={(status) => setSetupStatus(status)}
          />
        ) : (
      <section className="layout">
        <section className="panel form-panel">
          <div className="panel-heading">
            <h2>Ny ansatt</h2>
            <span>{config?.default_domain ?? "example.com"}</span>
          </div>

          <div className="form-grid">
            <Field label="Fullt navn">
              <input value={employee.full_name} onChange={(e) => patchEmployee("full_name", e.target.value)} />
            </Field>
            <Field label="Firma">
              <select value={employee.company} onChange={(e) => patchEmployee("company", e.target.value)}>
                {(options?.companies ?? [employee.company]).map((company) => (
                  <option key={company}>{company}</option>
                ))}
              </select>
            </Field>
            <Field label="Stilling">
              <input value={employee.job_title} onChange={(e) => patchEmployee("job_title", e.target.value)} />
            </Field>
            <Field label="Avdeling">
              <select value={employee.department} onChange={(e) => patchEmployee("department", e.target.value)}>
                {(options?.departments ?? [employee.department]).map((department) => (
                  <option key={department}>{department}</option>
                ))}
              </select>
            </Field>
            <Field label="Leder">
              <input value={employee.manager} onChange={(e) => patchEmployee("manager", e.target.value)} />
            </Field>
            <Field label="Kontorsted">
              <select value={employee.office_location} onChange={(e) => patchEmployee("office_location", e.target.value)}>
                {(options?.office_locations ?? [employee.office_location]).map((office) => (
                  <option key={office}>{office}</option>
                ))}
              </select>
            </Field>
            <Field label="Startdato">
              <input type="date" value={employee.start_date} onChange={(e) => patchEmployee("start_date", e.target.value)} />
            </Field>
            <Field label="Ansatttype">
              <select value={employee.employee_type} onChange={(e) => patchEmployee("employee_type", e.target.value)}>
                {(options?.employee_types ?? [employee.employee_type]).map((type) => (
                  <option key={type}>{type}</option>
                ))}
              </select>
            </Field>
            <Field label="Behov for PC">
              <Segmented
                value={employee.needs_pc}
                onChange={(value) => patchEmployee("needs_pc", value)}
              />
            </Field>
            <Field label="Behov for mobil">
              <Segmented
                value={employee.needs_mobile}
                onChange={(value) => patchEmployee("needs_mobile", value)}
              />
            </Field>
          </div>

          <div className="approval-box">
            <label>
              <input
                type="checkbox"
                checked={approvals.hr_approved}
                onChange={(e) => setApprovals((current) => ({ ...current, hr_approved: e.target.checked }))}
              />
              HR har godkjent opprettelse
            </label>
            <label>
              <input
                type="checkbox"
                checked={approvals.manager_approved}
                onChange={(e) => setApprovals((current) => ({ ...current, manager_approved: e.target.checked }))}
              />
              Nærmeste leder har godkjent
            </label>
            <label>
              <input
                type="checkbox"
                checked={approvals.execute}
                onChange={(e) => setApprovals((current) => ({ ...current, execute: e.target.checked }))}
              />
              Utfør irreversible Entra-handlinger
            </label>
          </div>

          <div className="actions">
            <button className="secondary" onClick={() => submit("preview")} disabled={busy}>
              {busy ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
              Forhåndsvis
            </button>
            <button className="primary" onClick={() => submit("run")} disabled={busy || !canRun}>
              {busy ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
              Kjør onboarding
            </button>
          </div>
          {error && <div className="error">{error}</div>}
        </section>

        <ReportPanel report={report} />
      </section>
        )}
      </>
      )}
    </main>
  );
}

function SetupWizard({ initialOptions, onSaved }: { initialOptions: Options; onSaved: (status: SetupStatus) => void }) {
  const [step, setStep] = useState(1);
  const [runtime, setRuntime] = useState<SetupRuntime>({
    frontend_origin: window.location.origin,
    entra_tenant_id: "",
    entra_client_id: "",
    entra_client_secret: "",
    entra_default_domain: "example.com",
    entra_usage_location: "NO",
    onboarding_portal_url: "https://onboarding.example.com",
    it_contact_email: "it@example.com",
    send_password_by_email: false,
  });
  const [options, setOptions] = useState<Options>(initialOptions);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function patchRuntime<K extends keyof SetupRuntime>(key: K, value: SetupRuntime[K]) {
    setRuntime((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const status = await api<SetupStatus>("/api/setup/save", {
        method: "POST",
        body: JSON.stringify({ runtime, options }),
      });
      onSaved(status);
      setMessage("Setup er lagret. Restart backend for at nye miljøverdier skal lastes.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="setup-shell">
      <section className="panel setup-panel">
        <div className="setup-header">
          <div>
            <h2>Førstegangsoppsett</h2>
            <p>Konfigurer lokal runtime, Entra-kobling og standardvalg</p>
          </div>
          <div className="setup-steps">
            {[1, 2, 3].map((item) => (
              <button key={item} className={step === item ? "active" : ""} onClick={() => setStep(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>

        {step === 1 && (
          <div className="form-grid">
            <Field label="Frontend origin">
              <input value={runtime.frontend_origin} onChange={(e) => patchRuntime("frontend_origin", e.target.value)} />
            </Field>
            <Field label="Standard domene">
              <input value={runtime.entra_default_domain} onChange={(e) => patchRuntime("entra_default_domain", e.target.value)} />
            </Field>
            <Field label="Usage location">
              <input value={runtime.entra_usage_location} onChange={(e) => patchRuntime("entra_usage_location", e.target.value)} />
            </Field>
            <Field label="IT kontakt">
              <input value={runtime.it_contact_email} onChange={(e) => patchRuntime("it_contact_email", e.target.value)} />
            </Field>
            <Field label="Onboardingportal">
              <input value={runtime.onboarding_portal_url} onChange={(e) => patchRuntime("onboarding_portal_url", e.target.value)} />
            </Field>
            <label className="check-row">
              <input
                type="checkbox"
                checked={runtime.send_password_by_email}
                onChange={(e) => patchRuntime("send_password_by_email", e.target.checked)}
              />
              Tillat midlertidig passord i e-post
            </label>
          </div>
        )}

        {step === 2 && (
          <>
            <div className="setup-help-row">
              <div>
                <h3>Entra-oppsett</h3>
                <p>Trenger du App Registration, redirect URI, client secret eller Graph permissions?</p>
              </div>
              <a className="secondary help-link" href={HELP_URL} target="_blank" rel="noreferrer">
                <FileText size={17} />
                Hjelp til Entra
              </a>
            </div>
            <div className="form-grid">
              <Field label="Entra tenant ID">
                <input value={runtime.entra_tenant_id} onChange={(e) => patchRuntime("entra_tenant_id", e.target.value)} />
              </Field>
              <Field label="Entra client ID">
                <input value={runtime.entra_client_id} onChange={(e) => patchRuntime("entra_client_id", e.target.value)} />
              </Field>
              <Field label="Entra client secret">
                <input
                  type="password"
                  value={runtime.entra_client_secret}
                  onChange={(e) => patchRuntime("entra_client_secret", e.target.value)}
                />
              </Field>
              <div className="setup-note">
                La client secret stå tom for preview/admin-login uten Graph-provisjonering.
              </div>
            </div>
          </>
        )}

        {step === 3 && (
          <div className="admin-grid">
            <ListEditor label="Firmaer" values={options.companies} onChange={(companies) => setOptions({ ...options, companies })} />
            <ListEditor label="Avdelinger" values={options.departments} onChange={(departments) => setOptions({ ...options, departments })} />
            <ListEditor label="Kontorsteder" values={options.office_locations} onChange={(office_locations) => setOptions({ ...options, office_locations })} />
            <ListEditor label="Ansatttyper" values={options.employee_types} onChange={(employee_types) => setOptions({ ...options, employee_types })} />
            <ListEditor label="PC-modeller" values={options.pc_models} onChange={(pc_models) => setOptions({ ...options, pc_models })} />
            <ListEditor label="Mobilabonnement" values={options.mobile_subscriptions} onChange={(mobile_subscriptions) => setOptions({ ...options, mobile_subscriptions })} />
          </div>
        )}

        <div className="actions">
          <button className="secondary" onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1}>
            Tilbake
          </button>
          {step < 3 ? (
            <button className="primary" onClick={() => setStep(step + 1)}>
              Neste
            </button>
          ) : (
            <button className="primary" onClick={save} disabled={saving}>
              {saving ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
              Lagre setup
            </button>
          )}
        </div>
        {message && <div className="success">{message}</div>}
        {error && <div className="error">{error}</div>}
      </section>
    </section>
  );
}

function LoginGate({
  config,
  onAuthenticated,
}: {
  config: Config;
  onAuthenticated: (auth: { account: AccountInfo | null; token: string }) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn() {
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await microsoftSignIn(config));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="admin-layout">
      <section className="panel login-panel">
        <div className="mark">
          <ShieldCheck size={22} />
        </div>
        <h2>Microsoft-pålogging kreves</h2>
        <p>Appen er koblet til Entra. Logg inn med en bruker som har rollen User Administrator eller Global Administrator.</p>
        <button className="primary" onClick={signIn} disabled={busy}>
          {busy ? <Loader2 className="spin" size={17} /> : <ShieldCheck size={17} />}
          Logg inn med Microsoft
        </button>
        {error && <div className="error">{error}</div>}
      </section>
    </section>
  );
}

function AdminPage({
  config,
  authAccount,
  authToken,
  onAuthenticated,
  onOptionsSaved,
  onSetupReopened,
}: {
  config: Config | null;
  authAccount: AccountInfo | null;
  authToken: string;
  onAuthenticated: (auth: { account: AccountInfo | null; token: string }) => void;
  onOptionsSaved: (options: Options) => void;
  onSetupReopened: (status: SetupStatus) => void;
}) {
  const [options, setOptions] = useState<Options | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const authReady = Boolean(config?.admin_auth_available);

  useEffect(() => {
    if (!authReady || !authToken) return;
    api<Options>("/api/admin/options", {}, authToken)
      .then(setOptions)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [authReady, authToken]);

  async function signIn() {
    setError("");
    if (!config) {
      setError("Admin-login krever backend-konfigurasjon.");
      return;
    }
    try {
      onAuthenticated(await microsoftSignIn(config));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function save() {
    if (!options) return;
    setError("");
    setMessage("");
    const saved = await api<Options>(
      "/api/admin/options",
      { method: "PUT", body: JSON.stringify(options) },
      authToken,
    );
    setOptions(saved);
    onOptionsSaved(saved);
    setMessage("Valgene er lagret.");
  }

  async function reopenSetup() {
    setError("");
    setMessage("");
    try {
      const status = await api<SetupStatus>("/api/setup/reopen", { method: "POST" });
      onSetupReopened(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section className="admin-layout">
      <section className="panel admin-panel">
        <div className="panel-heading">
          <div>
            <h2>Admin</h2>
            <p>Rediger valgene som vises i HR-skjemaet</p>
          </div>
          <button className="primary" onClick={signIn} disabled={!authReady}>
            <ShieldCheck size={17} />
            {authAccount ? authAccount.name || "Innlogget" : "Logg inn med Microsoft"}
          </button>
        </div>
        {!authReady && (
          <div className="warning admin-warning">
            <span>Sett `ENTRA_TENANT_ID` og `ENTRA_CLIENT_ID` i backend for å aktivere admin-login.</span>
            <button className="secondary" onClick={reopenSetup}>
              <RefreshCw size={17} />
              Åpne setup wizard
            </button>
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {message && <div className="success">{message}</div>}
        {options ? (
          <>
            <div className="admin-grid">
              <ListEditor label="Firmaer" values={options.companies} onChange={(companies) => setOptions({ ...options, companies })} />
              <ListEditor label="Avdelinger" values={options.departments} onChange={(departments) => setOptions({ ...options, departments })} />
              <ListEditor label="Kontorsteder" values={options.office_locations} onChange={(office_locations) => setOptions({ ...options, office_locations })} />
              <ListEditor label="Ansatttyper" values={options.employee_types} onChange={(employee_types) => setOptions({ ...options, employee_types })} />
              <ListEditor label="PC-modeller" values={options.pc_models} onChange={(pc_models) => setOptions({ ...options, pc_models })} />
              <ListEditor label="Mobilabonnement" values={options.mobile_subscriptions} onChange={(mobile_subscriptions) => setOptions({ ...options, mobile_subscriptions })} />
            </div>
            <div className="actions">
              <button className="primary" onClick={save}>
                <ClipboardCheck size={17} />
                Lagre valg
              </button>
            </div>
          </>
        ) : (
          <div className="empty-admin">
            Admininnhold lastes etter Microsoft-login. Brukeren må ha rollen User Administrator i Entra.
          </div>
        )}
      </section>
    </section>
  );
}

function ListEditor({ label, values, onChange }: { label: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <label className="list-editor">
      <span>{label}</span>
      <textarea
        value={values.join("\n")}
        onChange={(event) => onChange(event.target.value.split("\n"))}
      />
    </label>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function Segmented({ value, onChange }: { value: "Ja" | "Nei"; onChange: (value: "Ja" | "Nei") => void }) {
  return (
    <div className="segmented">
      {(["Ja", "Nei"] as const).map((option) => (
        <button
          type="button"
          key={option}
          className={value === option ? "active" : ""}
          onClick={() => onChange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function ReportPanel({ report }: { report: Report | null }) {
  if (!report) {
    return (
      <section className="panel report-panel empty-state">
        <FileText size={34} />
        <h2>Rapporten vises her</h2>
        <p>Fyll ut HR-data og kjør forhåndsvisning for å se brukernavn, grupper, lisenser, oppgaver og velkomstmail.</p>
      </section>
    );
  }

  return (
    <section className="panel report-panel">
      <div className="report-header">
        <div>
          <h2>Onboardingrapport</h2>
          <p>{report.username ?? "Ingen bruker foreslått"}</p>
        </div>
        <span className={`status ${statusClass(report.status)}`}>{report.status}</span>
      </div>

      <div className="summary-grid">
        <Metric icon={<KeyRound size={18} />} label="Brukernavn" value={report.username ?? "-"} />
        <Metric icon={<BadgeCheck size={18} />} label="Graph" value={report.graph_executed ? "Utført" : "Ikke utført"} />
        <Metric icon={<ClipboardCheck size={18} />} label="Oppgaver" value={String(report.tasks.length)} />
      </div>

      <Section title="Sammendrag" items={report.summary} />
      <Section title="Feil" items={report.errors} tone="error" />
      <Section title="Avvik" items={report.deviations} tone="warn" />
      <Section title="Neste steg" items={report.next_steps} />

      <div className="columns">
        <Section title="Grupper" items={report.groups} compact />
        <Section title="Lisenser" items={report.licenses} compact />
      </div>
      <div className="columns">
        <Section title="Teams" items={report.teams} compact />
        <Section title="Utstyr" items={report.equipment} compact />
      </div>

      <section className="mail">
        <h3>Velkomstmail</h3>
        <textarea readOnly value={report.welcome_email} />
      </section>

      <details className="audit">
        <summary>Audit logg</summary>
        <ul>
          {report.audit_log.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Section({
  title,
  items,
  tone,
  compact,
}: {
  title: string;
  items: string[];
  tone?: "error" | "warn";
  compact?: boolean;
}) {
  if (!items.length) return null;
  return (
    <section className={`report-section ${tone ?? ""} ${compact ? "compact" : ""}`}>
      <h3>{tone === "warn" ? <AlertTriangle size={16} /> : null}{title}</h3>
      <ul>
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function statusClass(status: Report["status"]) {
  if (status === "Fullført") return "done";
  if (status === "Delvis fullført") return "partial";
  return "waiting";
}

createRoot(document.getElementById("root")!).render(<App />);
