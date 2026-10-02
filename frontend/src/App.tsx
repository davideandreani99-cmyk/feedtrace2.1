import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, Me, TokenResponse, api, hasToken, setToken } from "./api";
import { ENTITIES, EntityDef, FieldDef, IMPORT_ENTITIES } from "./entities";

type Row = Record<string, unknown>;

// ---------------------------------------------------------------- login
function Login({ onLogged }: { onLogged: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needCode, setNeedCode] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, totp_code: code || null }),
      });
      setToken(res.access_token);
      onLogged();
    } catch (err) {
      if (err instanceof ApiError && err.message === "totp_required") {
        setNeedCode(true);
        setError("Inserisci il codice di verifica a 2 passaggi.");
      } else {
        setError(err instanceof Error ? err.message : "Errore");
      }
    }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <h1>FeedTrace</h1>
      <label>
        Email
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {needCode && (
        <label>
          Codice di verifica
          <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" />
        </label>
      )}
      {error && <p className="error">{error}</p>}
      <button type="submit">Accedi</button>
    </form>
  );
}

// ---------------------------------------------------------------- anagrafica generica
function EntityPage({ entity, canWrite }: { entity: EntityDef; canWrite: boolean }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [refs, setRefs] = useState<Record<string, Row[]>>({});
  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setRows(await api<Row[]>(`/${entity.path}`));
      const loaded: Record<string, Row[]> = {};
      for (const f of entity.fields) {
        if (f.kind === "ref" && f.ref && !loaded[f.ref.path]) {
          loaded[f.ref.path] = await api<Row[]>(`/${f.ref.path}?active=true`);
        }
      }
      setRefs(loaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore");
    }
  }, [entity]);

  useEffect(() => {
    setForm({});
    void load();
  }, [load]);

  function cell(f: FieldDef, row: Row): string {
    const value = row[f.name];
    if (value === null || value === undefined) return "";
    if (typeof value === "boolean") return value ? "sì" : "no";
    if (f.kind === "ref" && f.ref) {
      const found = (refs[f.ref.path] ?? []).find((r) => r.id === value);
      return found ? String(found[f.ref.label]) : String(value);
    }
    return String(value);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const body: Record<string, unknown> = {};
    for (const f of entity.fields) {
      const value = form[f.name];
      if (value === undefined || value === "") continue;
      body[f.name] = f.kind === "number" && typeof value === "string" ? value.replace(",", ".") : value;
    }
    try {
      await api(`/${entity.path}`, { method: "POST", body: JSON.stringify(body) });
      setForm({});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore");
    }
  }

  async function deactivate(id: unknown) {
    if (!window.confirm("Disattivare questo elemento? Non viene cancellato.")) return;
    try {
      await api(`/${entity.path}/${String(id)}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore");
    }
  }

  return (
    <section>
      <h2>{entity.title}</h2>
      {error && <p className="error">{error}</p>}
      {canWrite && (
        <form className="card grid" onSubmit={submit}>
          {entity.fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {f.kind === "bool" ? (
                <input
                  type="checkbox"
                  checked={form[f.name] === true}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.checked })}
                />
              ) : f.kind === "select" ? (
                <select
                  value={String(form[f.name] ?? "")}
                  required={f.required}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                >
                  <option value="">{f.required ? "Seleziona…" : "(predefinito)"}</option>
                  {f.options?.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              ) : f.kind === "ref" && f.ref ? (
                <select
                  value={String(form[f.name] ?? "")}
                  required={f.required}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                >
                  <option value="">Seleziona…</option>
                  {(refs[f.ref.path] ?? []).map((r) => (
                    <option key={String(r.id)} value={String(r.id)}>
                      {String(r[f.ref!.label])}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.kind === "date" ? "date" : "text"}
                  inputMode={f.kind === "number" ? "decimal" : undefined}
                  value={String(form[f.name] ?? "")}
                  required={f.required}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                />
              )}
            </label>
          ))}
          <button type="submit">Aggiungi</button>
        </form>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {entity.fields.map((f) => (
                <th key={f.name}>{f.label}</th>
              ))}
              <th>Stato</th>
              {canWrite && <th />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.id)} className={row.active === false ? "inactive" : ""}>
                {entity.fields.map((f) => (
                  <td key={f.name}>{cell(f, row)}</td>
                ))}
                <td>{row.active === false ? "disattivato" : "attivo"}</td>
                {canWrite && (
                  <td>
                    {row.active !== false && (
                      <button className="secondary" onClick={() => void deactivate(row.id)}>
                        Disattiva
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={entity.fields.length + 2}>Nessun elemento.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- ricette (sola lettura)
function RecipesPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Row[]>("/recipes")
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);
  return (
    <section>
      <h2>Ricette</h2>
      <p>Creazione e nuove versioni tramite import o API (editor grafico nelle prossime fasi).</p>
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Codice</th>
              <th>Nome</th>
              <th>Versione</th>
              <th>Valida dal</th>
              <th>Fase</th>
              <th>Righe</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r.id)}>
                <td>{String(r.code)}</td>
                <td>{String(r.name)}</td>
                <td>{String(r.version)}</td>
                <td>{String(r.valid_from)}</td>
                <td>{String(r.phase)}</td>
                <td>{(r.lines as unknown[]).length}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>Nessuna ricetta.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- import
interface ImportResult {
  total: number;
  ok: number;
  applied: boolean;
  errors: { line: number; message: string }[];
}

function ImportPage() {
  const [entity, setEntity] = useState(IMPORT_ENTITIES[0].path);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const current = IMPORT_ENTITIES.find((e) => e.path === entity)!;

  async function run(confirm: boolean) {
    if (!file) return;
    setError("");
    const data = new FormData();
    data.append("file", file);
    try {
      setResult(await api<ImportResult>(`/imports/${entity}?confirm=${confirm}`, {
        method: "POST",
        body: data,
      }));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Errore");
    }
  }

  return (
    <section>
      <h2>Importa da CSV / Excel</h2>
      <div className="card">
        <label>
          Cosa importare
          <select value={entity} onChange={(e) => { setEntity(e.target.value); setResult(null); }}>
            {IMPORT_ENTITIES.map((e) => (
              <option key={e.path} value={e.path}>{e.title}</option>
            ))}
          </select>
        </label>
        <p>Colonne attese: <code>{current.hint}</code> (numeri con la virgola, date gg/mm/aaaa).</p>
        <input type="file" accept=".csv,.xlsx" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); }} />
        <div className="row">
          <button onClick={() => void run(false)} disabled={!file}>Anteprima</button>
          <button onClick={() => void run(true)} disabled={!file || !result || result.errors.length > 0 || result.applied}>
            Conferma import
          </button>
        </div>
        {error && <p className="error">{error}</p>}
        {result && (
          <div>
            <p>
              Righe: {result.total} · valide: {result.ok} · errori: {result.errors.length}
              {result.applied && " · IMPORT APPLICATO"}
            </p>
            <ul>
              {result.errors.map((e) => (
                <li key={e.line}>Riga {e.line}: {e.message}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- registro modifiche
function AuditPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Row[]>("/audit-log?limit=100")
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);
  return (
    <section>
      <h2>Registro modifiche</h2>
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Data (UTC)</th><th>Entità</th><th>Azione</th><th>Dettaglio</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r.id)}>
                <td>{String(r.at).replace("T", " ").slice(0, 19)}</td>
                <td>{String(r.entity)}</td>
                <td>{String(r.action)}</td>
                <td><code>{JSON.stringify(r.after ?? r.before)?.slice(0, 120)}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- shell
export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [page, setPage] = useState("sites");
  const [logged, setLogged] = useState(hasToken());

  const loadMe = useCallback(async () => {
    try {
      setMe(await api<Me>("/auth/me"));
    } catch {
      setToken(null);
      setLogged(false);
      setMe(null);
    }
  }, []);

  useEffect(() => {
    if (logged) void loadMe();
  }, [logged, loadMe]);

  function logout() {
    setToken(null);
    setLogged(false);
    setMe(null);
  }

  async function switchTenant(tenantId: string) {
    const res = await api<TokenResponse>("/auth/switch-tenant", {
      method: "POST",
      body: JSON.stringify({ tenant_id: tenantId }),
    });
    setToken(res.access_token);
    await loadMe();
  }

  if (!logged) return <Login onLogged={() => setLogged(true)} />;
  if (!me) return <p className="center">Caricamento…</p>;

  const canWrite = me.permissions.includes("masterdata:write");
  const entity = ENTITIES.find((e) => e.path === page);

  return (
    <div className="app">
      <header>
        <strong>FeedTrace</strong>
        {me.memberships.length > 1 ? (
          <select value={me.tenant_id} onChange={(e) => void switchTenant(e.target.value)}>
            {me.memberships.map((m) => (
              <option key={m.tenant_id} value={m.tenant_id}>{m.name}</option>
            ))}
          </select>
        ) : (
          <span>{me.memberships[0]?.name}</span>
        )}
        <span className="grow" />
        <span>{me.full_name} ({me.role})</span>
        <button className="secondary" onClick={logout}>Esci</button>
      </header>
      <nav>
        {ENTITIES.map((e) => (
          <button key={e.path} className={page === e.path ? "active" : ""} onClick={() => setPage(e.path)}>
            {e.title}
          </button>
        ))}
        <button className={page === "recipes" ? "active" : ""} onClick={() => setPage("recipes")}>Ricette</button>
        {me.permissions.includes("import:run") && (
          <button className={page === "import" ? "active" : ""} onClick={() => setPage("import")}>Importa</button>
        )}
        {me.permissions.includes("audit:read") && (
          <button className={page === "audit" ? "active" : ""} onClick={() => setPage("audit")}>Registro</button>
        )}
      </nav>
      <main>
        {entity && <EntityPage entity={entity} canWrite={canWrite} />}
        {page === "recipes" && <RecipesPage />}
        {page === "import" && <ImportPage />}
        {page === "audit" && <AuditPage />}
      </main>
    </div>
  );
}
