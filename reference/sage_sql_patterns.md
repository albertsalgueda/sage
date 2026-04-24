# Sage 200 SQL Patterns Reference

> Extracted from `scriptbbddsage.sql` (22MB, 273,108 lines, 3,395 CREATE TABLE statements).
> Source database: `[Sage]` on SQL Server. Script date: 19/03/2026.

---

## 1. File Structure

Every table definition follows this exact sequence:

```sql
/****** Object:  Table [dbo].[TableName]    Script Date: 19/03/2026 19:26:41 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[TableName](
    -- columns...
 CONSTRAINT [ConstraintName] PRIMARY KEY CLUSTERED
(
    -- PK columns...
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

Default values are defined SEPARATELY via ALTER TABLE, much later in the file (starting around line 128,000):

```sql
ALTER TABLE [dbo].[TableName] ADD  DEFAULT (value) FOR [ColumnName]
```

---

## 2. CREATE TABLE Examples

### 2.1 Simple Lookup Table -- Zonas (Sales Zones)

```sql
CREATE TABLE [dbo].[Zonas](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CodigoZona] [int] NOT NULL,
    [Zona] [varchar](25) NOT NULL,
    [CodigoJefeZona_] [int] NOT NULL,
    [ComisionSobreZona%_] [decimal](28, 10) NOT NULL,
    [IdZona] [uniqueidentifier] NOT NULL,
 CONSTRAINT [Zonas_PK_Zona] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CodigoZona] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

Defaults:
```sql
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT (0) FOR [CodigoEmpresa]
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT (0) FOR [CodigoZona]
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT ('') FOR [Zona]
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT (0) FOR [CodigoJefeZona_]
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT (0) FOR [ComisionSobreZona%_]
ALTER TABLE [dbo].[Zonas] ADD  DEFAULT (newid()) FOR [IdZona]
```

### 2.2 Reference Table -- Almacenes (Warehouses)

```sql
CREATE TABLE [dbo].[Almacenes](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CodigoAlmacen] [varchar](4) NOT NULL,
    [GrupoAlmacen] [varchar](4) NOT NULL,
    [Responsable] [varchar](30) NOT NULL,
    [Almacen] [varchar](25) NOT NULL,
    [Domicilio] [varchar](40) NOT NULL,
    [CodigoPostal] [varchar](8) NOT NULL,
    [CodigoMunicipio] [varchar](7) NOT NULL,
    [Municipio] [varchar](25) NOT NULL,
    [CodigoProvincia] [varchar](5) NOT NULL,
    [Provincia] [varchar](20) NOT NULL,
    [Telefono] [varchar](15) NOT NULL,
    [Fax] [varchar](15) NOT NULL,
    [AgruparMovimientos] [smallint] NOT NULL,
    [IdDelegacion] [varchar](10) NOT NULL,
    [IdAlmacen] [uniqueidentifier] NOT NULL,
 CONSTRAINT [Almacenes_Almacen] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CodigoAlmacen] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

Defaults:
```sql
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT (0) FOR [CodigoEmpresa]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [CodigoAlmacen]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [GrupoAlmacen]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Responsable]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Almacen]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Domicilio]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [CodigoPostal]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [CodigoMunicipio]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Municipio]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [CodigoProvincia]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Provincia]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Telefono]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [Fax]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ((-1)) FOR [AgruparMovimientos]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT ('') FOR [IdDelegacion]
ALTER TABLE [dbo].[Almacenes] ADD  DEFAULT (newid()) FOR [IdAlmacen]
```

### 2.3 Mid-Complexity Table -- Familias (Product Families)

```sql
CREATE TABLE [dbo].[Familias](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CodigoFamilia] [varchar](10) NOT NULL,
    [CodigoSubfamilia] [varchar](10) NOT NULL,
    [Descripcion] [varchar](250) NOT NULL,
    [%Margen] [decimal](28, 10) NOT NULL,
    [%Margen2] [decimal](28, 10) NOT NULL,
    [%Margen3] [decimal](28, 10) NOT NULL,
    [CodigoArancelario] [varchar](12) NOT NULL,
    [Colores_] [smallint] NOT NULL,
    [GrupoTalla_] [smallint] NOT NULL,
    [GrupoIva] [tinyint] NOT NULL,
    [GrupoIvaCompras] [tinyint] NOT NULL,
    [%Descuento] [decimal](28, 10) NOT NULL,
    [%Descuento2] [decimal](28, 10) NOT NULL,
    [%Descuento3] [decimal](28, 10) NOT NULL,
    [%DescuentoCompras] [decimal](28, 10) NOT NULL,
    [%DescuentoCompras2] [decimal](28, 10) NOT NULL,
    [%DescuentoCompras3] [decimal](28, 10) NOT NULL,
    [CodigoSeccion] [varchar](10) NOT NULL,
    [CodigoProyecto] [varchar](10) NOT NULL,
    [CodigoDepartamento] [varchar](10) NOT NULL,
    [TrataNumerosSerieLc] [smallint] NOT NULL,
    [CodigoSerie] [varchar](10) NOT NULL,
    [ImagenTactilSR] [varchar](50) NOT NULL,
    [DescuentoMaxSR] [decimal](28, 10) NOT NULL,
    [PeriodoGarantiaSR] [smallint] NOT NULL,
    [PublicarInternet] [smallint] NOT NULL,
    [IdFamilia] [uniqueidentifier] NOT NULL,
    [PublicarGCRM] [smallint] NOT NULL,
    [%Margen4] [decimal](28, 10) NOT NULL,
    [%Margen5] [decimal](28, 10) NOT NULL,
 CONSTRAINT [Familias_PK_Familia] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CodigoFamilia] ASC,
    [CodigoSubfamilia] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

Defaults:
```sql
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [CodigoEmpresa]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ('') FOR [CodigoFamilia]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ('') FOR [CodigoSubfamilia]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ('') FOR [Descripcion]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [%Margen]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [%Margen2]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [%Margen3]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ('') FOR [CodigoArancelario]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [Colores_]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [GrupoTalla_]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [GrupoIva]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [GrupoIvaCompras]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((0)) FOR [%Descuento]
-- ... pattern continues: (0) for numeric, ('') for varchar, (newid()) for GUID
ALTER TABLE [dbo].[Familias] ADD  DEFAULT (newid()) FOR [IdFamilia]
ALTER TABLE [dbo].[Familias] ADD  DEFAULT ((-1)) FOR [PublicarGCRM]
```

### 2.4 Header Table -- CabeceraAlbaranCliente (Customer Delivery Note Header)

This is a large document header table (~260 columns). Key structural excerpt:

```sql
CREATE TABLE [dbo].[CabeceraAlbaranCliente](
    [CodigoEmpresa] [smallint] NOT NULL,
    [IdDelegacion] [varchar](10) NOT NULL,
    [EjercicioAlbaran] [smallint] NOT NULL,
    [SerieAlbaran] [varchar](10) NOT NULL,
    [NumeroAlbaran] [int] NOT NULL,
    [FechaAlbaran] [datetime] NOT NULL,
    [CodigoCliente] [varchar](15) NOT NULL,
    [CodigoCadena_] [varchar](10) NOT NULL,
    [NumeroLineas] [smallint] NOT NULL,
    [SiglaNacion] [varchar](2) NOT NULL,
    [CifDni] [varchar](13) NOT NULL,
    -- ... address fields (RazonSocial, Domicilio, CodigoPostal, Municipio, Provincia, Nacion) ...
    -- ... payment fields (CodigoCondiciones, FormadePago, NumeroPlazos, DiasPrimerPlazo) ...
    -- ... bank fields (CodigoBanco, CodigoAgencia, DC, CCC, IBAN) ...
    -- ... tax fields (CodigoTerritorio, IndicadorIva, IvaIncluido, GrupoIva) ...
    -- ... amount fields: all [decimal](28, 10) NOT NULL ...
    [ImporteBruto] [decimal](28, 10) NOT NULL,
    [ImporteDescuento] [decimal](28, 10) NOT NULL,
    [BaseImponible] [decimal](28, 10) NOT NULL,
    [TotalCuotaIva] [decimal](28, 10) NOT NULL,
    [ImporteFactura] [decimal](28, 10) NOT NULL,
    [ImporteLiquido] [decimal](28, 10) NOT NULL,
    -- ... status flags (StatusFacturado, StatusContabilizado, etc.) ...
    -- ... export fields, divisa, analytics ...
    [FechaCreacion] [datetime] NOT NULL,
    [HoraCreacion] [decimal](28, 19) NOT NULL,
    [MovConta] [uniqueidentifier] NOT NULL,
    [IdAlbaranCli] [uniqueidentifier] NOT NULL,
    [idAlbaranProAF] [uniqueidentifier] NOT NULL,
 CONSTRAINT [CabeceraAlbaranCliente_Albaran] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [EjercicioAlbaran] ASC,
    [SerieAlbaran] ASC,
    [NumeroAlbaran] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
```

Note: `TEXTIMAGE_ON [PRIMARY]` is added when the table contains `[text]` columns.

### 2.5 Line-Item Detail Table -- LineasAlbaranCliente (Customer Delivery Note Lines)

```sql
CREATE TABLE [dbo].[LineasAlbaranCliente](
    [CodigoEmpresa] [smallint] NOT NULL,
    [EjercicioAlbaran] [smallint] NOT NULL,
    [SerieAlbaran] [varchar](10) NOT NULL,
    [NumeroAlbaran] [int] NOT NULL,
    [Orden] [smallint] NOT NULL,
    [LineasPosicion] [uniqueidentifier] NOT NULL,
    [LineasPosicionCompuesto] [uniqueidentifier] NOT NULL,
    [LineasPosicionRegalo] [uniqueidentifier] NOT NULL,
    [LineaPedido] [uniqueidentifier] NOT NULL,
    [FechaRegistro] [datetime] NOT NULL,
    [FechaAlbaran] [datetime] NOT NULL,
    [CodigoArticulo] [varchar](20) NOT NULL,
    [CodigoAlmacen] [varchar](4) NOT NULL,
    [DescripcionArticulo] [varchar](50) NOT NULL,
    [CodigoFamilia] [varchar](10) NOT NULL,
    [CodigoSubfamilia] [varchar](10) NOT NULL,
    [CodigoProyecto] [varchar](10) NOT NULL,
    [CodigoSeccion] [varchar](10) NOT NULL,
    [CodigoDepartamento] [varchar](10) NOT NULL,
    [Unidades] [decimal](28, 10) NOT NULL,
    [Precio] [decimal](28, 10) NOT NULL,
    [PrecioCoste] [decimal](28, 10) NOT NULL,
    [%Descuento] [decimal](28, 10) NOT NULL,
    [%Iva] [decimal](28, 10) NOT NULL,
    [ImporteBruto] [decimal](28, 10) NOT NULL,
    [ImporteNeto] [decimal](28, 10) NOT NULL,
    [BaseImponible] [decimal](28, 10) NOT NULL,
    [CuotaIva] [decimal](28, 10) NOT NULL,
    [ImporteLiquido] [decimal](28, 10) NOT NULL,
    -- ... ~170 columns total ...
 CONSTRAINT [LineasAlbaranCliente_Albaran] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [EjercicioAlbaran] ASC,
    [SerieAlbaran] ASC,
    [NumeroAlbaran] ASC,
    [Orden] ASC,
    [LineasPosicion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
```

Note how the line PK extends the header PK (CodigoEmpresa + EjercicioAlbaran + SerieAlbaran + NumeroAlbaran) plus line-specific keys (Orden + LineasPosicion).

---

## 3. PRIMARY KEY Patterns

### 3.1 Constraint Naming Conventions

Three naming styles observed (in order of frequency):

| Style | Example | Pattern |
|-------|---------|---------|
| TableName_PK | `[AccionesClases_PK]` | Short form |
| TableName_PK_EntityName | `[Familias_PK_Familia]`, `[Zonas_PK_Zona]` | With entity suffix |
| TableName_EntityName | `[Actividades_Actividad]`, `[Articulos_Articulo]`, `[Clientes_Cliente]`, `[Almacenes_Almacen]` | Legacy style |
| TableName_DescriptiveName | `[AcumuladoStock_AcumuladoArticulo]`, `[ActividadesEjercicios_Ano]` | Descriptive |

### 3.2 PK Structure

All PKs follow this exact template:

```sql
 CONSTRAINT [ConstraintName] PRIMARY KEY CLUSTERED
(
    [Column1] ASC,
    [Column2] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
```

The WITH clause is ALWAYS identical. Never varies.

### 3.3 CodigoEmpresa as First PK Column

`[CodigoEmpresa]` is the FIRST column of the PK in the vast majority of business tables (~517 out of 3,353 PKs that could be counted this way). This is because Sage 200 is a multi-company system -- every business entity is scoped to a company.

**Typical PK patterns by table type:**

| Table Type | PK Columns |
|------------|------------|
| Master (Clientes, Articulos) | `CodigoEmpresa + CodigoXxx` |
| Reference (Almacenes, Zonas) | `CodigoEmpresa + CodigoXxx` |
| Hierarchical (Familias) | `CodigoEmpresa + CodigoFamilia + CodigoSubfamilia` |
| Document Header (CabeceraAlbaran) | `CodigoEmpresa + Ejercicio + Serie + Numero` |
| Document Line (LineasAlbaran) | `CodigoEmpresa + Ejercicio + Serie + Numero + Orden + LineasPosicion` |
| Sync tables | `sysGuidRegistro` (single GUID) |
| System tables (lsys*) | `sysXxx` columns (no CodigoEmpresa) |

---

## 4. Recurring Field Patterns

### 4.1 Universal Fields (appear in almost every business table)

| Field | Type | Default | Appears In | Notes |
|-------|------|---------|------------|-------|
| `[CodigoEmpresa]` | `[smallint] NOT NULL` | `(0)` | 3,814 columns (~2,083 tables) | ALWAYS first column, ALWAYS in PK |

### 4.2 Very Common Fields (top 30 by frequency)

| Field | Count | Type | Default |
|-------|-------|------|---------|
| `CodigoEmpresa` | 3,814 | `smallint` | `(0)` |
| `Ejercicio` | 721 | `smallint` | `(0)` |
| `CodigoEmpleado` | 435 | `int` | `(0)` |
| `CodigoUsuario` | 401 | `smallint` | `(0)` |
| `CodigoTerritorio` | 393 | `smallint` | `(0)` |
| `SiglaNacion` | 333 | `varchar(2)` | `('ES')` or `('')` |
| `CodigoArticulo` | 317 | `varchar(20)` | `('')` |
| `FechaAlta` | 314 | `datetime` | `(getdate())` or `NULL` |
| `IdDelegacion` | 254 | `varchar(10)` | `('')` |
| `CodigoProyecto` | 236 | `varchar(10)` | `('')` |
| `CodigoCliente` | 228 | `varchar(15)` | `('')` |
| `CodigoCanal` | 200 | `varchar(10)` | `('')` |
| `CodigoDepartamento` | 179 | `varchar(10)` | `('')` |
| `Dni` | 170 | `varchar(14)` | `('')` |

### 4.3 GUID Identity Fields (Id* pattern)

Most business tables end with a `uniqueidentifier` identity field:

| Table | GUID Field | Default |
|-------|------------|---------|
| Almacenes | `[IdAlmacen]` | `(newid())` |
| Articulos | `[IdArticulo]` | `(newid())` |
| Clientes | `[IdCliente]` | `(newid())` |
| Familias | `[IdFamilia]` | `(newid())` |
| Zonas | `[IdZona]` | `(newid())` |
| CabeceraAlbaranCliente | `[IdAlbaranCli]` | `(newid())` |

Pattern: `Id` + EntityName (singular), always `[uniqueidentifier] NOT NULL`, default `(newid())`.

### 4.4 Analytics Triple

These three fields appear together in many tables:

```sql
[CodigoProyecto] [varchar](10) NOT NULL,   -- DEFAULT ('')
[CodigoSeccion] [varchar](10) NOT NULL,    -- DEFAULT ('')
[CodigoDepartamento] [varchar](10) NOT NULL, -- DEFAULT ('')
```

### 4.5 Address Block

Standard address fields that appear together in master tables (Clientes, CabeceraAlbaran, etc.):

```sql
[CodigoPostal] [varchar](8) NOT NULL,
[CodigoMunicipio] [varchar](7) NOT NULL,
[Municipio] [varchar](25) NOT NULL,
[CodigoProvincia] [varchar](5) NOT NULL,
[Provincia] [varchar](20) NOT NULL,
[CodigoNacion] [smallint] NOT NULL,
[Nacion] [varchar](25) NOT NULL,
```

---

## 5. Data Type Conventions

### 5.1 Type Frequency (across all 3,395 tables)

| SQL Type | Count | Usage |
|----------|-------|-------|
| `varchar(N)` | 24,153 | Strings -- most common type |
| `decimal(28, 10)` | 23,092 | ALL monetary/numeric amounts |
| `smallint` | 16,471 | Codes, flags, booleans, counters |
| `datetime` | 3,838 | All dates (always nullable for optional dates) |
| `tinyint` | 3,693 | Small codes (0-255) |
| `uniqueidentifier` | 3,432 | GUIDs for identity and cross-references |
| `int` | 3,295 | Larger counters, numeric codes |
| `nvarchar(N)` | 655 | Unicode strings (rare, mostly in ad-hoc tables) |
| `text` | 622 | Long text fields (comments, descriptions) |

### 5.2 Key Type Patterns

| Usage | Sage Type | Notes |
|-------|-----------|-------|
| Boolean/flag | `[smallint] NOT NULL` | 0 = false, -1 or 1 = true |
| Money/amount | `[decimal](28, 10) NOT NULL` | ALWAYS 28,10 precision |
| Percentage | `[decimal](28, 10) NOT NULL` | Field name prefixed with `%` |
| Short code | `[varchar](1-10) NOT NULL` | Variable length |
| Description | `[varchar](25-250) NOT NULL` | Short to medium text |
| Long text | `[text] NULL` | Nullable, triggers `TEXTIMAGE_ON [PRIMARY]` |
| Date required | `[datetime] NOT NULL` | With `DEFAULT (getdate())` |
| Date optional | `[datetime] NULL` | No default needed |
| GUID identity | `[uniqueidentifier] NOT NULL` | With `DEFAULT (newid())` |
| Time of day | `[decimal](28, 19) NOT NULL` | Stored as decimal (e.g., HoraCreacion) |

### 5.3 Default Value Rules

Total default statements: ~67,000. Distribution:

| Default | Count | Applied To |
|---------|-------|------------|
| `(0)` or `((0))` | 42,154 | `smallint`, `tinyint`, `int`, `decimal` |
| `('')` | 21,953 | `varchar` (ALL varchar fields default to empty string) |
| `(newid())` | 1,607 | `uniqueidentifier` |
| `(getdate())` | 1,301 | `datetime` (dates with required current timestamp) |

Note: Both `(0)` and `((0))` are used interchangeably. Same for `('M')` vs `(('M'))`.

Special defaults observed:
- `('ES')` for `SiglaNacion` (default country Spain)
- `('M')` for `TipoArticulo` (default article type)
- `('CLI')` for `CodigoCategoriaCliente_`
- `((-1))` for some boolean flags (e.g., `AgruparMovimientos`, `PublicarGCRM`)
- `((1))` for some defaults (e.g., `FactorConversion_`, `ValoracionStock`)

---

## 6. Naming Conventions

### 6.1 Table Names

| Pattern | Example | Meaning |
|---------|---------|---------|
| PascalCase singular | `Clientes`, `Articulos`, `Almacenes` | Master data (note: Spanish plural) |
| Cabecera + DocumentType | `CabeceraAlbaranCliente`, `CabeceraPedidoProveedor` | Document headers |
| Lineas + DocumentType | `LineasAlbaranCliente`, `LineasPedidoProveedor` | Document line items |
| Entity + Qualifier | `ArticuloCliente`, `ArticuloProveedor` | Cross-reference |
| Acumulado + Entity | `AcumuladosConta`, `AcumuladoStock` | Accumulated/aggregate tables |
| lsys + Name | `lsysAcciones`, `lsysCampos`, `lsysPantallas` | System/metadata tables |
| TableName_Sync | `Clientes_Sync`, `Almacenes_Sync` | Sync tracking (40 tables) |
| TableName_Bak | `Articulos_Bak`, `Clientes_Bak` | Backup tables |
| Lc suffix | `CodigoTipoClienteLc`, `ComercialAsignadoLc` | LogicControl module fields |
| SR suffix | `ImagenTactilSR`, `PrecioPorTramosSR` | Sage Retail module fields |
| _ suffix | `CodigoDefinicion_`, `Colores_`, `Lote_` | Legacy/optional fields |

### 6.2 Column Names

| Pattern | Example | Type |
|---------|---------|------|
| `Codigo` + Entity | `CodigoCliente`, `CodigoArticulo`, `CodigoAlmacen` | Foreign keys / codes |
| `Id` + Entity | `IdCliente`, `IdArticulo`, `IdAlmacen` | GUID identity fields |
| `Descripcion` + qualifier | `DescripcionArticulo`, `Descripcion2Articulo` | Text descriptions |
| `Nombre` + qualifier | `Nombre`, `NombreEnvios` | Names |
| `Importe` + type | `ImporteBruto`, `ImporteNeto`, `ImporteIva` | Money amounts |
| `%` + name | `%Descuento`, `%Comision`, `%Margen` | Percentages |
| `Status` + name | `StatusFacturado`, `StatusContabilizado` | Status flags |
| `Bloqueo` + name | `BloqueoCompra`, `BloqueoAlbaran` | Block/lock flags |
| `Ejercicio` + doc | `EjercicioAlbaran`, `EjercicioPedido` | Fiscal year |
| `Serie` + doc | `SerieAlbaran`, `SeriePedido` | Document series |
| `Numero` + doc | `NumeroAlbaran`, `NumeroPedido` | Document number |
| `Fecha` + event | `FechaAlta`, `FechaAlbaran`, `FechaBaja` | Dates |
| `Copias` + doc | `CopiasAlbaran`, `CopiasFactura` | Print copies |
| `Mascara` + doc | `MascaraAlbaran_`, `MascaraFactura_` | Print templates |

### 6.3 Capitalization

- **PascalCase** everywhere: `CodigoEmpresa`, `ImporteBruto`, `DescripcionArticulo`
- **No underscores** in standard names (underscores only in trailing `_` for legacy/optional)
- **Spanish language** throughout: Empresa, Cliente, Articulo, Albaran, Pedido, Factura
- **Abbreviations**: Iva, Dto (descuento), Prov (provincia), Mun (municipio)

---

## 7. Sync Table Pattern

Every major business table has a companion `_Sync` table (40 total). They all follow this exact structure:

```sql
CREATE TABLE [dbo].[TableName_Sync](
    [sysGuidRegistro] [uniqueidentifier] NOT NULL,
    [sysTipoAccionRegistro] [varchar](1) NOT NULL,
    [sysFechaRegistro] [datetime] NOT NULL,
    [sysTick] [int] NOT NULL,
    [sysAppId] [int] NOT NULL,
    [sysModifiedDate] [datetime] NOT NULL,
    [sysLinkId] [uniqueidentifier] NULL,
    [sysHostName] [varchar](50) NOT NULL,
    [CodigoEmpresa] [smallint] NOT NULL,
 CONSTRAINT [PK_TableName_Sync] PRIMARY KEY CLUSTERED
(
    [sysGuidRegistro] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

PK naming for Sync tables: `PK_TableName_Sync` (note: `PK_` prefix, different from business tables).

---

## 8. System Tables (lsys*) vs Business Tables

System tables use `sys` prefixed columns instead of `Codigo` prefixed columns:

```sql
CREATE TABLE [dbo].[lsysAcciones](
    [sysTipoAccion] [tinyint] NOT NULL,
    [sysAccion] [varchar](40) NOT NULL,
    [sysNombre] [varchar](30) NOT NULL,
    [sysSeguridad] [smallint] NOT NULL,
    [sysConfigurable] [tinyint] NOT NULL,
 CONSTRAINT [lsysAcciones_PK_lsysAcciones] PRIMARY KEY CLUSTERED
(
    [sysTipoAccion] ASC,
    [sysAccion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
```

Key differences:
- No `CodigoEmpresa` -- system tables are company-independent
- PK naming: `lsysTableName_PK_lsysTableName`
- Column prefix: `sys` instead of `Codigo`

---

## 9. Summary Rules for AI Code Generation

When generating SQL for Sage 200 custom tables:

1. **Schema**: Always `[dbo]`
2. **First column**: `[CodigoEmpresa] [smallint] NOT NULL` with `DEFAULT (0)`
3. **Primary key**: Always starts with `[CodigoEmpresa] ASC`
4. **All columns NOT NULL** (except `datetime` optional dates and `text` fields)
5. **Every varchar field**: `DEFAULT ('')`
6. **Every numeric field**: `DEFAULT (0)`
7. **Every GUID field**: `DEFAULT (newid())`
8. **Every required date**: `DEFAULT (getdate())`
9. **Money/amounts**: Always `[decimal](28, 10) NOT NULL`
10. **Booleans**: `[smallint] NOT NULL` with `DEFAULT (0)`
11. **Include an Id field**: `[IdTableName] [uniqueidentifier] NOT NULL` with `DEFAULT (newid())`
12. **PK WITH clause**: Always the same boilerplate (PAD_INDEX=OFF, etc.)
13. **Defaults are separate**: `ALTER TABLE ... ADD DEFAULT` statements, not inline
14. **PK naming**: `[TableName_PK]` or `[TableName_PK_EntityName]` or `[TableName_EntityName]`
15. **Document headers**: PK = CodigoEmpresa + Ejercicio + Serie + Numero
16. **Document lines**: PK = header PK + Orden + LineasPosicion
