#!/usr/bin/env python3
"""
SQL Direct Injection Test for Sage 200.

Creates Sage objects by writing directly to system tables (lsysCampos, lsysDatos, lsysScripts)
and business tables (CF_Equipos, CF_Resultados, CF_Clasificacion) via SQL Server.

This bypasses the Sage IDE for everything except screens (lsysPantallas — binary sysMascara)
and reports (lsysInformes — binary sysMascara).

Usage:
    python sql_injection_test.py --host <IP> [--port 1433] [--user sa] [--password <pw>]
    python sql_injection_test.py --test          # Dry-run: print SQL without executing
    python sql_injection_test.py --verify        # Check if objects exist after injection
    python sql_injection_test.py --cleanup       # Remove injected objects
"""

import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# SQL statements for the certification module (CF_*)
# Reference: sage/reference/solution_dat_extract.md
# ---------------------------------------------------------------------------

# --- 1. CREATE TABLE statements ---

SQL_CREATE_TABLES = """
-- ============================================================
-- CF_Equipos — Football teams
-- ============================================================
CREATE TABLE [dbo].[CF_Equipos](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CF_CodigoEquipo] [smallint] NOT NULL,
    [CF_Nombre] [varchar](30) NOT NULL,
    [CF_JuegaEuropa] [smallint] NOT NULL,
    [CF_Competicion] [smallint] NOT NULL
 CONSTRAINT [CF_Equipos_Principal] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CF_CodigoEquipo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
;

-- ============================================================
-- CF_Resultados — Match results
-- ============================================================
CREATE TABLE [dbo].[CF_Resultados](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CF_Jornada] [smallint] NOT NULL,
    [CF_EquipoLocal] [smallint] NOT NULL,
    [CF_GolesLocal] [smallint] NOT NULL,
    [CF_EquipoVisitante] [smallint] NOT NULL,
    [CF_GolesVisitante] [smallint] NOT NULL,
    [CF_Fecha] [datetime] NOT NULL
 CONSTRAINT [CF_Resultados_Principal] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CF_Jornada] ASC,
    [CF_EquipoLocal] ASC,
    [CF_EquipoVisitante] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
;

-- ============================================================
-- CF_Clasificacion — League standings
-- ============================================================
CREATE TABLE [dbo].[CF_Clasificacion](
    [CodigoEmpresa] [smallint] NOT NULL,
    [CF_Posicion] [smallint] NOT NULL,
    [CF_Equipo] [smallint] NOT NULL,
    [CF_PartidosJugados] [smallint] NOT NULL,
    [CF_PartidosGanados] [smallint] NOT NULL,
    [CF_PartidosEmpatados] [smallint] NOT NULL,
    [CF_PartidosPerdidos] [smallint] NOT NULL,
    [CF_GolesFavor] [smallint] NOT NULL,
    [CF_GolesContra] [smallint] NOT NULL,
    [CF_Puntos] [smallint] NOT NULL,
    [CF_Positivos] [smallint] NOT NULL,
    [CF_DiferenciaGoles] [smallint] NOT NULL
 CONSTRAINT [CF_Clasificacion_Principal] PRIMARY KEY CLUSTERED
(
    [CodigoEmpresa] ASC,
    [CF_Posicion] ASC,
    [CF_Equipo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
;
"""

# --- 2. DEFAULT constraints ---

SQL_DEFAULTS = """
ALTER TABLE [dbo].[CF_Equipos] ADD DEFAULT ((0)) FOR [CodigoEmpresa];
ALTER TABLE [dbo].[CF_Equipos] ADD DEFAULT ((0)) FOR [CF_CodigoEquipo];
ALTER TABLE [dbo].[CF_Equipos] ADD DEFAULT ('') FOR [CF_Nombre];
ALTER TABLE [dbo].[CF_Equipos] ADD DEFAULT ((0)) FOR [CF_JuegaEuropa];
ALTER TABLE [dbo].[CF_Equipos] ADD DEFAULT ((1)) FOR [CF_Competicion];

ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CodigoEmpresa];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CF_Jornada];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CF_EquipoLocal];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CF_GolesLocal];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CF_EquipoVisitante];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT ((0)) FOR [CF_GolesVisitante];
ALTER TABLE [dbo].[CF_Resultados] ADD DEFAULT (getdate()) FOR [CF_Fecha];

ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CodigoEmpresa];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_Posicion];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_Equipo];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_PartidosJugados];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_PartidosGanados];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_PartidosEmpatados];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_PartidosPerdidos];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_GolesFavor];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_GolesContra];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_Puntos];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_Positivos];
ALTER TABLE [dbo].[CF_Clasificacion] ADD DEFAULT ((0)) FOR [CF_DiferenciaGoles];
"""

# --- 3. Field registration in lsysCampos ---
# sysId format: "TableName.FieldName"
# sysTipoTab: 2=smallint, 12=varchar, 135=datetime
# sysLongitud: field length (0 for fixed-size types)
# sysNulo: 0=NOT NULL
# sysConfigurable: 0
# sysDeUsuario: -1 (user-created)
# sysModificado: 0
# sysCampoLibre: 0

LSYSCAMPOS_FIELDS = [
    # CF_Equipos
    ("CF_Equipos.CodigoEmpresa",  "Codigo Empresa",     2, 0, "((0))", 0, ""),
    ("CF_Equipos.CF_CodigoEquipo","Cod. Equipo",         2, 0, "((0))", 0, "Cod. Equipo"),
    ("CF_Equipos.CF_Nombre",      "Nombre Equipo",      12, 30, "('')", 0, "Nombre Equipo"),
    ("CF_Equipos.CF_JuegaEuropa", "Juega en Europa",     2, 0, "((0))", 0, "Juega en Europa"),
    ("CF_Equipos.CF_Competicion", "Competicion",          2, 0, "((1))", 0, "Competicion"),
    # CF_Resultados
    ("CF_Resultados.CodigoEmpresa",     "Codigo Empresa",     2, 0, "((0))", 0, ""),
    ("CF_Resultados.CF_Jornada",        "Jornada",            2, 0, "((0))", 0, "Jornada"),
    ("CF_Resultados.CF_EquipoLocal",    "Local",              2, 0, "((0))", 0, "Local"),
    ("CF_Resultados.CF_GolesLocal",     "Goles Local",        2, 0, "((0))", 0, "Goles Local"),
    ("CF_Resultados.CF_EquipoVisitante","Visitante",           2, 0, "((0))", 0, "Visitante"),
    ("CF_Resultados.CF_GolesVisitante", "Goles Visitante",     2, 0, "((0))", 0, "Goles Visitante"),
    ("CF_Resultados.CF_Fecha",          "Fecha",             135, 0, "(getdate())", 0, "Fecha"),
    # CF_Clasificacion
    ("CF_Clasificacion.CodigoEmpresa",       "Codigo Empresa",     2, 0, "((0))", 0, ""),
    ("CF_Clasificacion.CF_Posicion",         "Posicion",           2, 0, "((0))", 0, "Posicion"),
    ("CF_Clasificacion.CF_Equipo",           "Equipo",             2, 0, "((0))", 0, "Equipo"),
    ("CF_Clasificacion.CF_PartidosJugados",  "PJ",                 2, 0, "((0))", 0, "PJ"),
    ("CF_Clasificacion.CF_PartidosGanados",  "PG",                 2, 0, "((0))", 0, "PG"),
    ("CF_Clasificacion.CF_PartidosEmpatados","PE",                  2, 0, "((0))", 0, "PE"),
    ("CF_Clasificacion.CF_PartidosPerdidos", "PP",                  2, 0, "((0))", 0, "PP"),
    ("CF_Clasificacion.CF_GolesFavor",       "GF",                  2, 0, "((0))", 0, "GF"),
    ("CF_Clasificacion.CF_GolesContra",      "GC",                  2, 0, "((0))", 0, "GC"),
    ("CF_Clasificacion.CF_Puntos",           "Puntos",              2, 0, "((0))", 0, "Puntos"),
    ("CF_Clasificacion.CF_Positivos",        "P+",                  2, 0, "((0))", 0, "P+"),
    ("CF_Clasificacion.CF_DiferenciaGoles",  "DG",                  2, 0, "((0))", 0, "DG"),
]

def gen_lsyscampos_sql():
    """Generate INSERT statements for lsysCampos."""
    stmts = []
    for sysid, desc, tipotab, longitud, defecto, nulo, rotulo in LSYSCAMPOS_FIELDS:
        sql = (
            f"INSERT INTO [dbo].[lsysCampos] "
            f"([sysId], [sysDescripcion], [sysTipoTab], [sysLongitud], [sysDefecto], "
            f"[sysNulo], [sysRotulo], [sysAplicacion], [sysConfigurable], [sysDeUsuario], "
            f"[sysModificado], [sysCampoLibre]) VALUES ("
            f"'{sysid}', '{desc}', {tipotab}, {longitud}, '{defecto}', "
            f"{nulo}, N'{rotulo}', '', 0, -1, 0, 0);"
        )
        stmts.append(sql)
    return "\n".join(stmts)


# --- 4. Query definitions in lsysDatos ---
# sysGrupo: 0 (standard)
# sysId: query name
# Key fields: sysCampos (field list), sysTablas (FROM tables), sysClauWhere, sysClauOrder,
#   sysClauJoin, sysClavePrimaria, sysSql

LSYSDATOS_QUERIES = [
    {
        "sysGrupo": 0,
        "sysId": "CF_Equipos",
        "sysDescripcion": "Mantenimiento de Equipos",
        "sysCampos": "CodigoEmpresa,CF_CodigoEquipo,CF_Nombre,CF_JuegaEuropa,CF_Competicion",
        "sysTablas": "CF_Equipos",
        "sysClavePrimaria": "CodigoEmpresa,CF_CodigoEquipo",
        "sysClauOrder": "CF_CodigoEquipo ASC",
        "sysIdTablaPrincipal": "CF_Equipos",
        "sysSql": "",
    },
    {
        "sysGrupo": 0,
        "sysId": "CF_Resultados",
        "sysDescripcion": "Mantenimiento de Resultados",
        "sysCampos": "CodigoEmpresa,CF_Jornada,CF_EquipoLocal,CF_GolesLocal,CF_EquipoVisitante,CF_GolesVisitante,CF_Fecha",
        "sysTablas": "CF_Resultados",
        "sysClavePrimaria": "CodigoEmpresa,CF_Jornada,CF_EquipoLocal,CF_EquipoVisitante",
        "sysClauOrder": "CF_Jornada ASC",
        "sysIdTablaPrincipal": "CF_Resultados",
        "sysSql": "",
    },
    {
        "sysGrupo": 0,
        "sysId": "CF_Clasificacion",
        "sysDescripcion": "Clasificacion de Liga",
        "sysCampos": "CodigoEmpresa,CF_Posicion,CF_Equipo,CF_PartidosJugados,CF_PartidosGanados,CF_PartidosEmpatados,CF_PartidosPerdidos,CF_GolesFavor,CF_GolesContra,CF_Puntos,CF_Positivos,CF_DiferenciaGoles",
        "sysTablas": "CF_Clasificacion",
        "sysClavePrimaria": "CodigoEmpresa,CF_Posicion,CF_Equipo",
        "sysClauOrder": "CF_Posicion ASC",
        "sysIdTablaPrincipal": "CF_Clasificacion",
        "sysSql": "",
    },
    {
        "sysGrupo": 0,
        "sysId": "CF_ClasificacionOrden",
        "sysDescripcion": "Clasificacion ordenada por puntos",
        "sysCampos": "*",
        "sysTablas": "CF_Clasificacion",
        "sysClavePrimaria": "CodigoEmpresa,CF_Posicion,CF_Equipo",
        "sysClauOrder": "CF_Puntos DESC, CF_Positivos DESC, CF_DiferenciaGoles DESC, CF_PartidosJugados DESC, CF_Nombre ASC",
        "sysIdTablaPrincipal": "CF_Clasificacion",
        "sysClauJoin": "LEFT JOIN CF_Equipos ON CF_Equipos.CodigoEmpresa = CF_Clasificacion.CodigoEmpresa AND CF_Equipos.CF_CodigoEquipo = CF_Clasificacion.CF_Equipo",
        "sysSql": "SELECT * FROM CF_Clasificacion LEFT JOIN CF_Equipos ON CF_Equipos.CodigoEmpresa = CF_Clasificacion.CodigoEmpresa AND CF_Equipos.CF_CodigoEquipo = CF_Clasificacion.CF_Equipo ORDER BY CF_Puntos DESC, CF_Positivos DESC, CF_DiferenciaGoles DESC, CF_PartidosJugados DESC, CF_Nombre ASC",
    },
    {
        "sysGrupo": 0,
        "sysId": "CF_ClasificacionLiga_Lis",
        "sysDescripcion": "Listado Clasificacion Liga",
        "sysCampos": "*",
        "sysTablas": "CF_Clasificacion",
        "sysClavePrimaria": "CodigoEmpresa,CF_Posicion,CF_Equipo",
        "sysClauOrder": "CF_Puntos DESC, CF_Positivos DESC, CF_DiferenciaGoles DESC",
        "sysIdTablaPrincipal": "CF_Clasificacion",
        "sysSql": "",
    },
]

def gen_lsysdatos_sql():
    """Generate INSERT statements for lsysDatos."""
    stmts = []
    for q in LSYSDATOS_QUERIES:
        join = q.get("sysClauJoin", "")
        sql_val = q.get("sysSql", "")
        sql = (
            f"INSERT INTO [dbo].[lsysDatos] "
            f"([sysId], [sysGrupo], [sysDescripcion], [sysCampos], [sysTablas], "
            f"[sysClavePrimaria], [sysClauOrder], [sysIdTablaPrincipal], [sysSql], "
            f"[sysClauJoin], [sysGrupoDatos], [sysAplicacion], [sysDistintos], "
            f"[sysCamposRep], [sysCamposTip], [sysCamposDir], [sysCamposSiz], "
            f"[sysCamposDup], [sysAlias], [sysClauWhere], [sysMaxRecords], "
            f"[sysCacheSize], [sysCursortype], [sysVentana], [sysTimeOut], "
            f"[sysLocalizacion], [sysCamposFijos], [sysClauGroup], [sysClauHaving], "
            f"[sysConfigurable], [sysDeUsuario], [sysNoParser], [sysNoSecurity], "
            f"[sysLockType], [sysTablesSecurity], [sysQueryType], [sysProcFixFld], "
            f"[sysExplorer], [sysTipoModificacion]) VALUES ("
            f"'{q['sysId']}', {q['sysGrupo']}, '{q['sysDescripcion']}', "
            f"'{q['sysCampos']}', '{q['sysTablas']}', "
            f"'{q['sysClavePrimaria']}', '{q['sysClauOrder']}', "
            f"'{q['sysIdTablaPrincipal']}', '{sql_val}', "
            f"'{join}', '', '', '', "
            f"'', '', '', '', "
            f"'', '', '', 0, "
            f"0, 0, 0, 0, "
            f"0, '', '', '', "
            f"0, -1, 0, 0, "
            f"0, '', 0, 0, "
            f"0, 0);"
        )
        stmts.append(sql)
    return "\n".join(stmts)


# --- 5. Calculation scripts in lsysScripts ---
# sysGrupo: 0
# sysId: script name
# syscalculoFuente: 4GL source code
# syscalculoCompilado: empty (Sage compiles on first run)

SCRIPT_CF_EQUIPOS = r"""Inicio:
    FrmControl("CF_Equipos", "CONTROLENABLED", 4, "txtCF_Competicion", "0","")
    FrmControl("CF_Equipos", "CONTROLENABLED", 4, "grdDataForm.CF_Competicion", "0","")
    FrmControl("CF_Equipos", "FIELDVALUE", 4, "grdDataForm.CF_Competicion", "1","")

AlCambiar:
    Ifn CF_Equipos.CF_JuegaEuropa <> 0 Then
        FrmControl("CF_Equipos", "CONTROLENABLED", 4, "txtCF_Competicion", "-1","")
        FrmControl("CF_Equipos", "CONTROLENABLED", 4, "grdDataForm.CF_Competicion", "-1","")
    Else
        FrmControl("CF_Equipos", "CONTROLENABLED", 4, "txtCF_Competicion", "0","")
        FrmControl("CF_Equipos", "CONTROLENABLED", 4, "grdDataForm.CF_Competicion", "0","")
        FrmControl("CF_Equipos", "FIELDVALUE", 4, "grdDataForm.CF_Competicion", "1","")
        FrmControl("CF_Equipos", "FIELDVALUE", 4, "txtCF_Competicion", "1","")
    Endif

AntesInsertar:
    Ifn CF_Equipos.CF_JuegaEuropa <> 0 Then
        Ifn CF_Equipos.CF_Competicion = 1 Then
            MsgBox("Si el equipo juega en Europa, se tiene que informar competicion", 32, "Competicion")
            Apli.CancelarAccion = "-1"
        Endif
    Endif

DespuesInsertar:
    Ifn CF_Equipos.CF_JuegaEuropa <> 0 Then
        Ifn CF_Equipos.CF_Competicion = 1 Then
            MsgBox("Si el equipo juega en Europa, se tiene que informar competicion", 32, "Competicion")
            Apli.CancelarAccion = "-1"
        Endif
    Endif

AntesModificar:
    Ifn CF_Equipos.CF_JuegaEuropa <> 0 Then
        Ifn CF_Equipos.CF_Competicion = 1 Then
            MsgBox("Si el equipo juega en Europa, se tiene que informar competicion", 32, "Competicion")
            Apli.CancelarAccion = "-1"
        Endif
    Endif

DespuesModificar:
    Ifn CF_Equipos.CF_JuegaEuropa <> 0 Then
        Ifn CF_Equipos.CF_Competicion = 1 Then
            MsgBox("Si el equipo juega en Europa, se tiene que informar competicion", 32, "Competicion")
            Apli.CancelarAccion = "-1"
        Endif
    Endif
"""

SCRIPT_CF_RESULTADOS = r"""Inicio:
Return
"""

SCRIPT_CF_CLASIFICACION = r"""Dim CF_Clasificacion As Registro
Dim CF_Resultados As Registro
Dim CF_Equipos As Registro
Dim CF_ClasificacionOrden As Registro
Dim CF_Clasificacion.CodigoEmpresa As Campo(CF_Clasificacion, CodigoEmpresa) Tipo Numero
Dim CF_Clasificacion.CF_Posicion As Campo(CF_Clasificacion, CF_Posicion) Tipo Numero
Dim CF_Clasificacion.CF_Equipo As Campo(CF_Clasificacion, CF_Equipo) Tipo Numero
Dim CF_Clasificacion.CF_PartidosJugados As Campo(CF_Clasificacion, CF_PartidosJugados) Tipo Numero
Dim CF_Clasificacion.CF_PartidosGanados As Campo(CF_Clasificacion, CF_PartidosGanados) Tipo Numero
Dim CF_Clasificacion.CF_PartidosEmpatados As Campo(CF_Clasificacion, CF_PartidosEmpatados) Tipo Numero
Dim CF_Clasificacion.CF_PartidosPerdidos As Campo(CF_Clasificacion, CF_PartidosPerdidos) Tipo Numero
Dim CF_Clasificacion.CF_GolesFavor As Campo(CF_Clasificacion, CF_GolesFavor) Tipo Numero
Dim CF_Clasificacion.CF_GolesContra As Campo(CF_Clasificacion, CF_GolesContra) Tipo Numero
Dim CF_Clasificacion.CF_Puntos As Campo(CF_Clasificacion, CF_Puntos) Tipo Numero
Dim CF_Clasificacion.CF_Positivos As Campo(CF_Clasificacion, CF_Positivos) Tipo Numero
Dim CF_Clasificacion.CF_DiferenciaGoles As Campo(CF_Clasificacion, CF_DiferenciaGoles) Tipo Numero
Dim CF_Equipos.CF_CodigoEquipo As Campo(CF_Equipos, CF_CodigoEquipo) Tipo Numero
Dim CF_Resultados.CF_EquipoLocal As Campo(CF_Resultados, CF_EquipoLocal) Tipo Numero
Dim CF_Resultados.CF_GolesLocal As Campo(CF_Resultados, CF_GolesLocal) Tipo Numero
Dim CF_Resultados.CF_EquipoVisitante As Campo(CF_Resultados, CF_EquipoVisitante) Tipo Numero
Dim CF_Resultados.CF_GolesVisitante As Campo(CF_Resultados, CF_GolesVisitante) Tipo Numero
Dim CF_ClasificacionOrden.CF_Clasificacion.CF_Equipo As Campo(CF_ClasificacionOrden, CF_Clasificacion.CF_Equipo) Tipo Numero
Dim PartidosJugados As Numero
Dim PartidosGanados As Numero
Dim PartidosEmpatados As Numero
Dim PartidosPerdidos As Numero
Dim GolesFavor As Numero
Dim GolesContra As Numero
Dim Puntos As Numero
Dim Positivos As Numero
Dim DiferenciaGoles As Numero
Dim Num As Numero
Dim Res As Numero
Dim Pos As Numero
Dim cadUpdate As Texto

Inicio:
    Ifn CF_Resultados = -1 Then
        CF_Resultados = AbreConsulta("CF_Resultados")
    Endif
    Ifn CF_Clasificacion = -1 Then
        CF_Clasificacion = AbreConsulta("CF_Clasificacion")
    Endif
    Ifn CF_Equipos = -1 Then
        CF_Equipos = AbreConsulta("CF_Equipos")
    Endif
    Ifn CF_ClasificacionOrden = -1 Then
        CF_ClasificacionOrden = AbreConsulta("CF_ClasificacionOrden")
    Endif
    Num = EjecutaBorra("CF_Clasificacion")
    Gosub Proceso
    Gosub OrdenarClasificacion
    Gosub LanzarListado
    Gosub Fin

Fin:
    Ifn CF_ClasificacionOrden <> -1 Then CierraRegistro(CF_ClasificacionOrden) Endif
    Ifn CF_Equipos <> -1 Then CierraRegistro(CF_Equipos) Endif
    Ifn CF_Clasificacion <> -1 Then CierraRegistro(CF_Clasificacion) Endif
    Ifn CF_Resultados <> -1 Then CierraRegistro(CF_Resultados) Endif
    MsgBox("Proceso terminado", 32, "Proceso")
Return

Proceso:
    Gosub InicializaClasificacion
    Num = Seleccion(CF_Equipos, "1=1")
    Num = Primero(CF_Equipos)
    Whilen Num = -1 Then
        PartidosJugados = 0
        PartidosGanados = 0
        PartidosEmpatados = 0
        PartidosPerdidos = 0
        GolesFavor = 0
        GolesContra = 0
        Puntos = 0
        Positivos = 0
        DiferenciaGoles = 0

        ' --- As LOCAL ---
        Num = Seleccion(CF_Resultados, "CF_EquipoLocal = " & CF_Equipos.CF_CodigoEquipo)
        Num = Primero(CF_Resultados)
        Whilen Num = -1 Then
            PartidosJugados = PartidosJugados + 1
            GolesFavor = GolesFavor + CF_Resultados.CF_GolesLocal
            GolesContra = GolesContra + CF_Resultados.CF_GolesVisitante
            Ifn CF_Resultados.CF_GolesLocal > CF_Resultados.CF_GolesVisitante Then
                PartidosGanados = PartidosGanados + 1
                Puntos = Puntos + 3
            Else
                Ifn CF_Resultados.CF_GolesLocal < CF_Resultados.CF_GolesVisitante Then
                    PartidosPerdidos = PartidosPerdidos + 1
                    Positivos = Positivos - 3
                Else
                    PartidosEmpatados = PartidosEmpatados + 1
                    Puntos = Puntos + 1
                    Positivos = Positivos - 1
                Endif
            Endif
            Num = Siguiente(CF_Resultados)
        Loop

        ' --- As VISITOR ---
        Num = Seleccion(CF_Resultados, "CF_EquipoVisitante = " & CF_Equipos.CF_CodigoEquipo)
        Num = Primero(CF_Resultados)
        Whilen Num = -1 Then
            PartidosJugados = PartidosJugados + 1
            GolesFavor = GolesFavor + CF_Resultados.CF_GolesVisitante
            GolesContra = GolesContra + CF_Resultados.CF_GolesLocal
            Ifn CF_Resultados.CF_GolesLocal < CF_Resultados.CF_GolesVisitante Then
                PartidosGanados = PartidosGanados + 1
                Puntos = Puntos + 3
                Positivos = Positivos + 3
            Else
                Ifn CF_Resultados.CF_GolesLocal > CF_Resultados.CF_GolesVisitante Then
                    PartidosPerdidos = PartidosPerdidos + 1
                Else
                    PartidosEmpatados = PartidosEmpatados + 1
                    Puntos = Puntos + 1
                    Positivos = Positivos + 1
                Endif
            Endif
            Num = Siguiente(CF_Resultados)
        Loop

        Positivos = Puntos
        DiferenciaGoles = GolesFavor - GolesContra

        cadUpdate = "UPDATE CF_Clasificacion SET "
        cadUpdate = cadUpdate & "CF_PartidosJugados = " & PartidosJugados
        cadUpdate = cadUpdate & " , CF_PartidosGanados = " & PartidosGanados
        cadUpdate = cadUpdate & " , CF_PartidosEmpatados = " & PartidosEmpatados
        cadUpdate = cadUpdate & " , CF_PartidosPerdidos = " & PartidosPerdidos
        cadUpdate = cadUpdate & " , CF_GolesFavor = " & GolesFavor
        cadUpdate = cadUpdate & " , CF_GolesContra = " & GolesContra
        cadUpdate = cadUpdate & " , CF_Puntos = " & Puntos
        cadUpdate = cadUpdate & " , CF_Positivos = " & Positivos
        cadUpdate = cadUpdate & " , CF_DiferenciaGoles = " & DiferenciaGoles
        cadUpdate = cadUpdate & " WHERE CF_Equipo = " & CF_Equipos.CF_CodigoEquipo
        Res = EjecutaSQL("exec:=" & cadUpdate)
        Num = Siguiente(CF_Equipos)
    Loop
Return

InicializaClasificacion:
    Res = Seleccion(CF_Clasificacion, "1=2")
    Num = Seleccion(CF_Equipos, "1=1")
    Num = Primero(CF_Equipos)
    Whilen Num = -1 Then
        Res = IniciaRegistro(CF_Clasificacion)
        CF_Clasificacion.CF_DiferenciaGoles = 0
        CF_Clasificacion.CF_Equipo = CF_Equipos.CF_CodigoEquipo
        CF_Clasificacion.CF_GolesContra = 0
        CF_Clasificacion.CF_GolesFavor = 0
        CF_Clasificacion.CF_PartidosEmpatados = 0
        CF_Clasificacion.CF_PartidosGanados = 0
        CF_Clasificacion.CF_PartidosJugados = 0
        CF_Clasificacion.CF_PartidosPerdidos = 0
        CF_Clasificacion.CF_Posicion = 0
        CF_Clasificacion.CF_Positivos = 0
        CF_Clasificacion.CF_Puntos = 0
        CF_Clasificacion.CodigoEmpresa = Apli.ApliCodigoEmpresa
        Res = Nuevo(CF_Clasificacion)
        Num = Siguiente(CF_Equipos)
    Loop
Return

OrdenarClasificacion:
    RefrescaRegistro(CF_ClasificacionOrden)
    Num = Seleccion(CF_ClasificacionOrden, "1=1")
    Num = Primero(CF_ClasificacionOrden)
    Pos = 0
    Whilen Num = -1 Then
        Pos = Pos + 1
        cadUpdate = "UPDATE CF_Clasificacion SET "
        cadUpdate = cadUpdate & "CF_Posicion = " & Pos
        cadUpdate = cadUpdate & " WHERE CF_Equipo = " & CF_ClasificacionOrden.CF_Clasificacion.CF_Equipo
        Res = EjecutaSQL("exec:=" & cadUpdate)
        Num = Siguiente(CF_ClasificacionOrden)
    Loop
Return

LanzarListado:
    Res = ListadoEjecuta("CF_ClasificacionOrden_Lis","","","S","","")
Return
"""

SCRIPTS = [
    ("CF_Equipos", "Script pantalla CF_Equipos", SCRIPT_CF_EQUIPOS),
    ("CF_Resultados", "Script pantalla CF_Resultados", SCRIPT_CF_RESULTADOS),
    ("CF_Clasificacion", "Calculo Clasificacion Liga", SCRIPT_CF_CLASIFICACION),
]


def gen_lsysscripts_sql():
    """Generate INSERT statements for lsysScripts."""
    stmts = []
    for sysid, desc, source in SCRIPTS:
        safe_source = source.replace("'", "''")
        sql = (
            f"INSERT INTO [dbo].[lsysScripts] "
            f"([sysGrupo], [sysId], [sysDescripcion], [syscalculoFuente], "
            f"[syscalculoCompilado], [sysAplicacion], [sysConfigurable], "
            f"[sysDeUsuario], [sysCalculoRTF]) VALUES ("
            f"0, '{sysid}', '{desc}', '{safe_source}', "
            f"'', '', 0, -1, '');"
        )
        stmts.append(sql)
    return "\n".join(stmts)


# --- 6. Verification queries ---

SQL_VERIFY = """
-- Check tables exist
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('CF_Equipos', 'CF_Resultados', 'CF_Clasificacion')
ORDER BY TABLE_NAME;

-- Check fields registered
SELECT sysId, sysDescripcion, sysTipoTab, sysLongitud
FROM lsysCampos WHERE sysId LIKE 'CF_%'
ORDER BY sysId;

-- Check queries registered
SELECT sysId, sysDescripcion, sysTablas
FROM lsysDatos WHERE sysId LIKE 'CF_%'
ORDER BY sysId;

-- Check scripts registered
SELECT sysId, sysDescripcion, LEN(syscalculoFuente) as script_length
FROM lsysScripts WHERE sysId LIKE 'CF_%'
ORDER BY sysId;
"""

# --- 7. Cleanup ---

SQL_CLEANUP = """
-- Remove scripts
DELETE FROM lsysScripts WHERE sysId IN ('CF_Equipos', 'CF_Resultados', 'CF_Clasificacion');

-- Remove queries
DELETE FROM lsysDatos WHERE sysId LIKE 'CF_%';

-- Remove field registrations
DELETE FROM lsysCampos WHERE sysId LIKE 'CF_%';

-- Drop tables
DROP TABLE IF EXISTS [dbo].[CF_Clasificacion];
DROP TABLE IF EXISTS [dbo].[CF_Resultados];
DROP TABLE IF EXISTS [dbo].[CF_Equipos];
"""


def get_all_sql():
    """Return all SQL statements in execution order."""
    sections = [
        ("-- === 1. CREATE TABLES ===", SQL_CREATE_TABLES),
        ("-- === 2. DEFAULT CONSTRAINTS ===", SQL_DEFAULTS),
        ("-- === 3. REGISTER FIELDS (lsysCampos) ===", gen_lsyscampos_sql()),
        ("-- === 4. REGISTER QUERIES (lsysDatos) ===", gen_lsysdatos_sql()),
        ("-- === 5. REGISTER SCRIPTS (lsysScripts) ===", gen_lsysscripts_sql()),
    ]
    return "\n\n".join(f"{header}\n{sql}" for header, sql in sections)


def execute_via_ssh(host, sql_statements, db="Sage", user="sa", password=""):
    """Execute SQL via SSH + sqlcmd on the remote host."""
    import subprocess

    ssh_key = Path.home() / ".ssh" / "google_compute_engine"

    # Write SQL to temp file and upload
    tmp_sql = Path("/tmp/sage_injection.sql")
    tmp_sql.write_text(sql_statements)

    # Upload SQL file
    scp_cmd = [
        "scp", "-i", str(ssh_key), "-o", "StrictHostKeyChecking=no",
        str(tmp_sql), f"albert@{host}:C:/sage_injection.sql"
    ]
    print(f"  Uploading SQL file to {host}...")
    r = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  SCP error: {r.stderr}")
        return False

    # Execute via sqlcmd
    # Note: sqlcmd path may vary; common locations on SQL Server installations
    sqlcmd = (
        f'sqlcmd -S localhost -d {db} -U {user} -P "{password}" '
        f'-i C:\\sage_injection.sql -o C:\\sage_injection_result.txt'
    )
    ssh_cmd = [
        "ssh", "-i", str(ssh_key), "-o", "StrictHostKeyChecking=no",
        f"albert@{host}", sqlcmd
    ]
    print(f"  Executing SQL via sqlcmd...")
    r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=120)
    print(f"  stdout: {r.stdout[:500]}")
    if r.stderr:
        print(f"  stderr: {r.stderr[:500]}")

    # Download results
    scp_cmd = [
        "scp", "-i", str(ssh_key), "-o", "StrictHostKeyChecking=no",
        f"albert@{host}:C:/sage_injection_result.txt", "/tmp/sage_injection_result.txt"
    ]
    r = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        result = Path("/tmp/sage_injection_result.txt").read_text()
        print(f"\n  === SQL Results ===\n{result[:2000]}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Sage 200 SQL Direct Injection Test")
    parser.add_argument("--host", help="SQL Server host IP")
    parser.add_argument("--port", type=int, default=1433)
    parser.add_argument("--user", default="sa")
    parser.add_argument("--password", default="")
    parser.add_argument("--db", default="Sage")
    parser.add_argument("--test", action="store_true", help="Dry-run: print SQL")
    parser.add_argument("--verify", action="store_true", help="Run verification queries")
    parser.add_argument("--cleanup", action="store_true", help="Remove injected objects")
    parser.add_argument("--output", help="Save SQL to file instead of executing")
    args = parser.parse_args()

    if args.test or args.output:
        sql = get_all_sql()
        if args.output:
            Path(args.output).write_text(sql)
            print(f"SQL saved to {args.output}")
        else:
            print(sql)
        return

    if args.verify:
        if not args.host:
            print("ERROR: --host required for verify")
            sys.exit(1)
        execute_via_ssh(args.host, SQL_VERIFY, args.db, args.user, args.password)
        return

    if args.cleanup:
        if not args.host:
            print("ERROR: --host required for cleanup")
            sys.exit(1)
        print("=== CLEANUP: Removing CF_* objects ===")
        execute_via_ssh(args.host, SQL_CLEANUP, args.db, args.user, args.password)
        return

    # Full injection
    if not args.host:
        print("ERROR: --host required (or use --test for dry-run)")
        sys.exit(1)

    print("=== Sage 200 SQL Direct Injection ===")
    print(f"Host: {args.host}:{args.port}")
    print(f"Database: {args.db}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    sql = get_all_sql()
    print(f"Total SQL: {len(sql)} chars, {sql.count(';')} statements")
    execute_via_ssh(args.host, sql, args.db, args.user, args.password)

    print("\n=== Verifying ===")
    execute_via_ssh(args.host, SQL_VERIFY, args.db, args.user, args.password)

    print("\nDone! Check Sage IDE to see if objects appear in the tree.")


if __name__ == "__main__":
    main()
