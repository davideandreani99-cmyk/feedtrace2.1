export type FieldKind = "text" | "number" | "bool" | "select" | "ref" | "date";

export interface FieldDef {
  name: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  options?: string[]; // per "select"
  ref?: { path: string; label: string }; // per "ref": elenco da cui scegliere
  inTable?: boolean; // default true
}

export interface EntityDef {
  path: string;
  title: string;
  fields: FieldDef[];
}

const SITE_REF = { path: "sites", label: "name" };

export const ENTITIES: EntityDef[] = [
  {
    path: "sites",
    title: "Siti",
    fields: [
      { name: "name", label: "Nome", kind: "text", required: true },
      { name: "asl_code", label: "Codice ASL", kind: "text", required: true },
      { name: "province", label: "Provincia", kind: "text" },
      { name: "dop_circuit", label: "Circuito DOP", kind: "bool" },
    ],
  },
  {
    path: "suppliers",
    title: "Fornitori",
    fields: [
      { name: "name", label: "Ragione sociale", kind: "text", required: true },
      { name: "vat_number", label: "P.IVA", kind: "text" },
      { name: "reg_183_number", label: "N. reg. 183/2005", kind: "text" },
      { name: "medicated_supplier", label: "Mangimi medicati", kind: "bool" },
    ],
  },
  {
    path: "raw-materials",
    title: "Materie prime",
    fields: [
      { name: "code", label: "Codice", kind: "text", required: true },
      { name: "name", label: "Nome", kind: "text", required: true },
      {
        name: "type",
        label: "Tipo",
        kind: "select",
        required: true,
        options: [
          "CEREALE",
          "SOTTOPRODOTTO",
          "PROTEICO",
          "PREMISCELA",
          "INTEGRATORE",
          "ADDITIVO",
          "LIQUIDO",
          "ACQUA",
          "MANGIME_FINITO",
          "PREMISCELA_MEDICATA",
          "MANGIME_MEDICATO",
        ],
      },
      { name: "unit", label: "Unità", kind: "select", options: ["kg", "l"] },
      { name: "density_kg_l", label: "Densità kg/l", kind: "number" },
      { name: "dry_matter_pct", label: "% s.s.", kind: "number" },
      { name: "requires_analysis", label: "Richiede analisi", kind: "bool" },
    ],
  },
  {
    path: "containers",
    title: "Contenitori",
    fields: [
      { name: "site_id", label: "Sito", kind: "ref", required: true, ref: SITE_REF },
      { name: "code", label: "Codice", kind: "text", required: true },
      {
        name: "type",
        label: "Tipo",
        kind: "select",
        required: true,
        options: ["SILO", "TRAMOGGIA", "CISTERNA", "VASCA_BRODA", "BIG_BAG", "MAGAZZINO"],
      },
      { name: "capacity", label: "Capacità", kind: "number" },
      {
        name: "consumption_policy",
        label: "Politica di consumo",
        kind: "select",
        options: ["FIFO", "PROPORZIONALE", "TUTTI_PRESENTI"],
      },
    ],
  },
  {
    path: "plants",
    title: "Impianti",
    fields: [
      { name: "site_id", label: "Sito", kind: "ref", required: true, ref: SITE_REF },
      { name: "code", label: "Codice", kind: "text", required: true },
      { name: "name", label: "Nome", kind: "text", required: true },
      {
        name: "type",
        label: "Tipo",
        kind: "select",
        required: true,
        options: ["MISCELATORE_BATCH", "BRODA", "CARRO"],
      },
      {
        name: "lot_rule",
        label: "Regola lotto",
        kind: "select",
        options: ["PER_CICLO", "GIORNALIERO_PER_RICETTA"],
      },
      { name: "processing_cost_eur_t", label: "Costo lavorazione €/t", kind: "number" },
      { name: "medicated_authorized", label: "Autorizzato medicati", kind: "bool" },
    ],
  },
  {
    path: "destination-lots",
    title: "Lotti destinazione",
    fields: [
      { name: "site_id", label: "Sito", kind: "ref", required: true, ref: SITE_REF },
      { name: "internal_code", label: "Codice interno", kind: "text", required: true },
      { name: "external_code", label: "Codice Pig'UP", kind: "text" },
      {
        name: "phase",
        label: "Fase",
        kind: "select",
        options: ["SVEZZAMENTO", "MAGRONAGGIO", "INGRASSO", "SCROFE", "ALTRO"],
      },
      { name: "head_count", label: "N. capi", kind: "number" },
      { name: "dop", label: "DOP", kind: "bool" },
    ],
  },
  {
    path: "locations",
    title: "Luoghi",
    fields: [
      { name: "site_id", label: "Sito", kind: "ref", required: true, ref: SITE_REF },
      { name: "name", label: "Nome (sala, box, valvola)", kind: "text", required: true },
      { name: "kind", label: "Tipo", kind: "text" },
    ],
  },
];

export const IMPORT_ENTITIES: { path: string; title: string; hint: string }[] = [
  { path: "suppliers", title: "Fornitori", hint: "name;vat_number;reg_183_number;medicated_supplier" },
  { path: "raw-materials", title: "Materie prime", hint: "code;name;type;unit;density_kg_l;dry_matter_pct" },
  { path: "containers", title: "Contenitori", hint: "site_code;code;type;capacity;consumption_policy" },
  { path: "destination-lots", title: "Lotti destinazione", hint: "site_code;internal_code;external_code;phase;head_count" },
  { path: "recipes", title: "Ricette", hint: "recipe_code;recipe_name;plant_type;phase;material_code;kg_per_t" },
];
