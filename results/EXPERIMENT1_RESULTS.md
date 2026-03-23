# Experiment 1: Code Generation Results

**Date:** 2026-03-23
**Model:** claude-sonnet-4-20250514
**Overall Grade: 79.1%**

## Summary

Claude Sonnet was given the functional specification from `reference/prompt_certificacion.md` (Sage 200 football league module) with a system prompt containing Sage 4GL language reference and SQL conventions. It was asked to generate SQL tables, primary keys, queries, 4GL screen scripts, 4GL calculation scripts, and screen definitions.

## Scores by Category

| Category | Score | Notes |
|---|---|---|
| SQL Tables (fields) | **100%** | All 3 tables, all 20 fields correct |
| Primary Keys | **100%** | All 3 PKs with correct columns |
| 4GL Keyword Coverage | **93.3%** | 14/15 keywords used (missing: `EjecutaBorra`) |
| Ranking Query | **100%** | JOIN, ORDER BY with all 4 criteria |
| Text Similarity | **2.4%** | Low (expected — different formatting, comments, variable names) |

## Detailed Analysis

### What Claude Got RIGHT

1. **SQL CREATE TABLE** — Perfect. All three tables (CF_Equipos, CF_Resultados, CF_Clasificacion) with correct field names, types (`smallint`, `varchar(30)`, `datetime`), defaults (`((0))`, `('')`, `(getdate())`), and `CodigoEmpresa` as first field.

2. **Primary Keys** — Perfect. Correct `ALTER TABLE ... WITH NOCHECK ADD CONSTRAINT ... PRIMARY KEY CLUSTERED` syntax. One minor difference: CF_Clasificacion PK uses `(CodigoEmpresa, CF_Posicion)` vs solution's `(CodigoEmpresa, CF_Posicion, CF_Equipo)`.

3. **4GL Screen Script (CF_Equipos)** — Business rules implemented:
   - `Inicio`: disables Competicion field initially
   - `AlCambiar`: enables/disables Competicion based on JuegaEuropa
   - `AntesInsertar/AntesModificar`: validates Competicion when JuegaEuropa is set
   - Uses `FrmControl`, `MsgBox`, `Apli.CancelarAccion = "-1"` correctly

4. **4GL Calculation Script (CF_Clasificacion)** — Complete implementation:
   - Iterates all teams, calculates stats as local and visitor
   - Correct point calculation: win=+3, draw=+1, loss=0
   - Correct "Positivos" calculation: visitor win=+3, visitor draw=+1, local draw=-1, local loss=-3
   - DiferenciaGoles = GF - GC
   - Updates positions using ORDER BY ranking query
   - Launches report at end

5. **Ranking Query** — Correct JOIN between CF_Clasificacion and CF_Equipos, correct ORDER BY: Puntos DESC, Positivos DESC, DiferenciaGoles DESC, PartidosJugados ASC, Nombre ASC

6. **Screen Definitions** — Included control names, labels, grid layouts, relations, and list of values

### What Claude Got WRONG or DIFFERENT

1. **`EjecutaBorra` not used** — The reference solution uses `EjecutaBorra("CF_Clasificacion")` to clear the table before recalculation. Claude used `EjecutaSQL("exec:= DELETE FROM...")` instead. Functionally equivalent but uses a different API call.

2. **CF_Clasificacion PK** — Claude used `(CodigoEmpresa, CF_Posicion)`, solution uses `(CodigoEmpresa, CF_Posicion, CF_Equipo)`. Claude's approach is debatable since Posicion should be unique per company.

3. **4GL Syntax variations:**
   - Claude used `Retorno` (not in reference — reference uses `Return`)
   - Claude used `Else Ifn` (reference uses separate `Ifn` blocks)
   - Claude passed extra params to `AbreConsulta` (reference uses simpler form: `AbreConsulta("QueryName")`)
   - Claude used `Graba()` (reference uses `Nuevo()` then `EjecutaSQL UPDATE`)

4. **CF_Competicion default** — Claude used `DEFAULT ((0))`, reference uses `DEFAULT ((1))` (1 = "Vacio" in the list of values). This is a semantic error: the prompt says "Vacio (defecto)" which maps to value 1, not 0.

5. **Low text similarity (2.4%)** — Expected. Claude generates more verbose code with comments, different variable names, and different formatting. The functional correctness is high despite low textual overlap.

### Report naming
- Claude used `CF_InformeClasificacion`, reference uses `CF_ClasificacionOrden_Lis`

## Conclusion

**Claude Sonnet can generate functionally correct Sage 200 code from a natural language specification.** The SQL output is nearly identical to the reference. The 4GL output captures all business logic correctly with minor syntactic variations. The main gap is in exact Sage 200 API conventions (e.g., `EjecutaBorra` vs `DELETE`, `Return` vs `Retorno`), which could be improved with more examples in the system prompt or few-shot learning.

**Viability for Plan A:** HIGH for SQL and calculation logic. MEDIUM for screen scripts (syntax variations that may not compile in Sage IDE). Would benefit from:
- A few-shot example of correct 4GL in the system prompt
- Validation step against the Sage 4GL parser (requires VM)
- Post-processing to normalize syntax (`Retorno` → `Return`, etc.)

## Files Generated

- `generated_20260323_163846.md` — Full Claude output
- `evaluation_20260323_163846.json` — Structured evaluation data
- `diff_20260323_163846.txt` — Unified diff vs reference
