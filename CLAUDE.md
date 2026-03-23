# Sage200 AI Audit — Computer-Use & Code Generation

## What is this repo
Scripts and experiments to test if AI can automate Sage 200 development workflows. Part of a 3-week feasibility audit for Grupo Solitium.

## Two experiments to run

### Experiment 1: Code Generation (no VM needed)
Test if LLMs can generate valid Sage 200 artifacts from a functional spec:
- SQL: CREATE TABLE, ALTER TABLE, PRIMARY KEY
- 4GL scripts: calculation logic using AbreConsulta, Seleccion, EjecutaSQL, etc.
- Query definitions: SELECT with JOINs, ORDER BY

**How to test:** Use the prompt in `reference/prompt_certificacion.md` as input. Compare output against `reference/solution_dat_extract.md` (the known correct solution).

### Experiment 2: Computer-Use (needs VM running)
Test if an AI agent can drive the Sage 200 GUI to create objects (tables, fields, screens, scripts) via the IDE — because the .dat binary format is NOT reverse-engineerable.

**How to test:** Connect to the Sage VM via VNC/RDP, then use Anthropic or OpenAI computer-use APIs to navigate: `Consola de Administración → Herramientas → Importar Objetos de Repositorio`.

## Sage VM Setup
- **VM file:** `VMSage200.zip` (in `../assets/vm/`, NOT in this repo — too large)
- **Hypervisor:** VMware Player 17.0 (installer also in `../assets/vm/`)
- Once running, enable RDP (port 3389) or install a VNC server
- Connection details go in `.env` (see `.env.example`)

## Sage 200 REST API (Plan B)
- Docs: https://developer.sage.com/200/reference/
- Auth: OAuth 2.0
- Endpoints: Sales, Purchases, Stock, Cash Book, POP, SOP
- **Note:** API covers business operations. It likely does NOT cover the dev layer (creating tables/screens). Verify when access is configured.

## Key Context

### Sage 4GL Language Quick Reference
```
Variables:     Dim X As Registro | Dim X.Field As Campo(Table, Field) Tipo
Control flow:  Ifn...Then...Else...Endif | Whilen...Then...Loop | Gosub/Goto
Records:       AbreConsulta, CierraRegistro, Seleccion, Primero, Siguiente, Nuevo, Graba, Borra
SQL:           EjecutaSQL("exec:=" & sql), EjecutaBorra, EjecutaInserta, EjecutaModifica
Forms:         FrmControl(screen, action, params...) — CONTROLENABLED, FIELDVALUE, REQUIREDVALUE
Events:        Inicio, AlCambiar, AntesInsertar, DespuesInsertar, AntesModificar, DespuesModificar
Functions:     Mid, Left, Right, Trim, Val, Abs, Redondea, Ahora, CalcFecha, MsgBox
Reports:       ListadoEjecuta("ReportName","","","S","","")
```

### SQL Conventions
- All custom tables use a prefix (e.g., `CF_`)
- Every table starts with `CodigoEmpresa smallint NOT NULL DEFAULT ((0))`
- PKs: `ALTER TABLE [T] WITH NOCHECK ADD CONSTRAINT [T_Principal] PRIMARY KEY CLUSTERED (...) ON [PRIMARY]`
- Types: `smallint` (ints, bools), `varchar(N)` (text), `datetime` (dates)
- Booleans: 0=No, non-zero=Yes. Defaults: ints→`((0))`, strings→`('')`, dates→`(getdate())`

### Screen Conventions
- Controls: `lbl` (labels), `txt` (inputs), `grd` (grids). Grid is always `grdDataForm`
- Grid layout: `lyt` + TableName. Relations: `Rel` + prefix
- List of values: `"Option1;Option2;Option3"`

### .dat Format (NOT reverse-engineerable)
Binary/proprietary. Contains SQL, fields, screens, scripts serialized together. Cannot generate programmatically. Must use computer-use to drive Sage UI, or write directly to system SQL tables (risky/unsupported).

## Reference Materials
- `reference/prompt_certificacion.md` — The functional spec (input)
- `reference/solution_dat_extract.md` — Extracted correct solution (expected output)
- `../assets/` — PDF manual (124p), DOCX prompt, ZIP with .dat objects
- Full project context: `../CLAUDE.md`
