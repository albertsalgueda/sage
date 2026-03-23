# Extracted Solution from Cert_JaviCoboHAvanzada.dat

Reference solution for the certification prompt. Extracted via `strings` from the binary .dat file.

## Manifest

```
Tables:      CF_Clasificacion, CF_Equipos, CF_Resultados
Fields:      20 total
Queries:     CF_Clasificacion, CF_ClasificacionLiga_Lis, CF_ClasificacionOrden, CF_Equipos, CF_Resultados
Screens:     CF_Equipos, CF_Resultados
Calculations: CF_Clasificacion, CF_Equipos, CF_Resultados
Reports:     CF_ClasificacionOrden_Lis
Operations:  OP_CF_Clasificacion, OP_CF_Equipos, OP_CF_Resultados
User menu:   Clasificación, Resultados, Equipos
```

## SQL — CREATE TABLE

```sql
CREATE TABLE dbo.[CF_Clasificacion] (
  [CodigoEmpresa] smallint NOT NULL DEFAULT ((0)),
  [CF_Posicion] smallint NOT NULL DEFAULT ((0)),
  [CF_Equipo] smallint NOT NULL DEFAULT ((0)),
  [CF_PartidosJugados] smallint NOT NULL DEFAULT ((0)),
  [CF_PartidosGanados] smallint NOT NULL DEFAULT ((0)),
  [CF_PartidosEmpatados] smallint NOT NULL DEFAULT ((0)),
  [CF_PartidosPerdidos] smallint NOT NULL DEFAULT ((0)),
  [CF_GolesFavor] smallint NOT NULL DEFAULT ((0)),
  [CF_GolesContra] smallint NOT NULL DEFAULT ((0)),
  [CF_Puntos] smallint NOT NULL DEFAULT ((0)),
  [CF_Positivos] smallint NOT NULL DEFAULT ((0)),
  [CF_DiferenciaGoles] smallint NOT NULL DEFAULT ((0))
)

CREATE TABLE dbo.[CF_Equipos] (
  [CodigoEmpresa] smallint NOT NULL DEFAULT ((0)),
  [CF_CodigoEquipo] smallint NOT NULL DEFAULT ((0)),
  [CF_Nombre] varchar(30) NOT NULL DEFAULT (''),
  [CF_JuegaEuropa] smallint NOT NULL DEFAULT ((0)),
  [CF_Competicion] smallint NOT NULL DEFAULT ((1))
)

CREATE TABLE dbo.[CF_Resultados] (
  [CodigoEmpresa] smallint NOT NULL DEFAULT ((0)),
  [CF_Jornada] smallint NOT NULL DEFAULT ((0)),
  [CF_EquipoLocal] smallint NOT NULL DEFAULT ((0)),
  [CF_GolesLocal] smallint NOT NULL DEFAULT ((0)),
  [CF_EquipoVisitante] smallint NOT NULL DEFAULT ((0)),
  [CF_GolesVisitante] smallint NOT NULL DEFAULT ((0)),
  [CF_Fecha] datetime NOT NULL DEFAULT (getdate())
)
```

## SQL — PRIMARY KEYS

```sql
ALTER TABLE [CF_Clasificacion] WITH NOCHECK ADD CONSTRAINT [CF_Clasificacion_Principal]
  PRIMARY KEY CLUSTERED ([CodigoEmpresa],[CF_Posicion],[CF_Equipo]) ON [PRIMARY]

ALTER TABLE [CF_Equipos] WITH NOCHECK ADD CONSTRAINT [CF_Equipos_Principal]
  PRIMARY KEY CLUSTERED ([CodigoEmpresa],[CF_CodigoEquipo]) ON [PRIMARY]

ALTER TABLE [CF_Resultados] WITH NOCHECK ADD CONSTRAINT [CF_Resultados_Principal]
  PRIMARY KEY CLUSTERED ([CodigoEmpresa],[CF_Jornada],[CF_EquipoLocal],[CF_EquipoVisitante]) ON [PRIMARY]
```

## Query — CF_ClasificacionOrden (ranking query)

```sql
SELECT * FROM CF_Clasificacion
LEFT JOIN CF_Equipos ON
  CF_Equipos.CodigoEmpresa = CF_Clasificacion.CodigoEmpresa
  AND CF_Equipos.CF_CodigoEquipo = CF_Clasificacion.CF_Equipo
ORDER BY
  CF_Puntos DESC,
  CF_Positivos DESC,
  CF_DiferenciaGoles DESC,
  CF_PartidosJugados DESC,
  CF_Nombre ASC
```

## Screen — CF_Equipos

```
Title: Mantenimiento de CF_Equipos
Controls: lblCF_CodigoEquipo, lblCF_Nombre, lblCF_JuegaEuropa, lblCF_Competicion,
          txtCF_CodigoEquipo, txtCF_Nombre, txtCF_JuegaEuropa, txtCF_Competicion,
          grdDataForm
Data source: CF_Equipos
Grid layout: lytCF_Equipos (CF_CodigoEquipo, CF_Nombre, CF_JuegaEuropa, CF_Competicion)
Labels: "Cod. Equipo", "Nombre Equipo", "Juega en Europa", "Competición"
List of values (Competicion): "Vacio;Europa League;Champions League"
Events: Inicio, AlCambiar, AntesInsertar, DespuesInsertar, AntesModificar, DespuesModificar
```

## Screen — CF_Resultados

```
Title: Mantenimiento de CF_Resultados
Controls: lblCF_Jornada, lblCF_Fecha, Frame (Local), Frame2 (Visitante),
          txtCF_Jornada, txtCF_Fecha, txtCF_EquipoLocal, txtCF_GolesLocal, txtLocal,
          txtCF_EquipoVisitante, txtCF_GolesVisitante, txtVisitante, grdDataForm
Relations: RelCF_EquiposL (CF_CodigoEquipo={txtCF_EquipoLocal}),
           RelCF_EquiposV (CF_CodigoEquipo={txtCF_EquipoVisitante})
Defaults: CF_Fecha=NOW, CF_GolesLocal=0, CF_GolesVisitante=0
Grid: lytCF_Resultados (Jornada, EquipoLocal, NombreL, EquipoVisitante, NombreV, GolesLocal, GolesVisitante, Fecha)
```

## 4GL — CF_Equipos Screen Script

```vb
Inicio:
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
            MsgBox("Si el equipo juega en Europa, se tiene que informar competición", 32, "Competición")
            Apli.CancelarAccion = "-1"
        Endif
    Endif
' (Same validation repeated in DespuesInsertar, AntesModificar, DespuesModificar)
```

## 4GL — CF_Clasificacion Calculation Script (full)

```vb
Dim CF_Clasificacion As Registro
Dim CF_Resultados As Registro
Dim CF_Equipos As Registro
Dim CF_ClasificacionOrden As Registro
' ... (Dim declarations for all fields) ...
Dim PartidosJugados As Numero
Dim PartidosGanados As Numero
Dim PartidosEmpatados As Numero
Dim PartidosPerdidos As Numero
Dim GolesFavor As Numero
Dim GolesContra As Numero
Dim Puntos As Numero
Dim Positivos As Numero
Dim DiferenciaGoles As Numero

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
    Gosub inicializaClasificacion
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
```
