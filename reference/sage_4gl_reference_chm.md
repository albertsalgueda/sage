# Sage 200 4GL Language Reference (from CHM Help Files)

> Compiled from official Sage 200 CHM help documentation (AjudaSageChm.zip).
> Source: LcScript.chm, LcPanta.chm, LcTablas.chm, and related CHM files.

---

## Table of Contents

1. [Language Overview](#1-language-overview)
2. [Data Types and Variables (Dim)](#2-data-types-and-variables)
3. [Operators](#3-operators)
4. [Instructions (Control Flow)](#4-instructions-control-flow)
5. [Record Operations (Queries)](#5-record-operations)
6. [SQL Execution Functions](#6-sql-execution-functions)
7. [Screen Control (FrmControl)](#7-screen-control-frmcontrol)
8. [Report Functions (Listado)](#8-report-functions)
9. [String Functions](#9-string-functions)
10. [Date and Time Functions](#10-date-and-time-functions)
11. [Math Functions](#11-math-functions)
12. [File I/O Functions](#12-file-io-functions)
13. [User Interface Functions](#13-user-interface-functions)
14. [Application Variables](#14-application-variables)
15. [Session/Global Variables (VarAsigna/VarLee)](#15-session-variables)
16. [Screen Events Reference](#16-screen-events-reference)
17. [Report Events Reference](#17-report-events-reference)
18. [Grid/Layout Calculation Events](#18-grid-calculation-events)
19. [Utility Functions](#19-utility-functions)
20. [Complete Code Examples](#20-complete-code-examples)
21. [Obsolete Functions Mapping](#21-obsolete-functions)
22. [Complete Function Index](#22-complete-function-index)

---

## 1. Language Overview

A "calculo" (calculation/script) is a set of instructions, functions, and variables written in Sage's proprietary 4GL language, combined to program specific behaviors in the application. Scripts can be viewed, designed, executed, and deleted from the Administration Console (Consola de Administracion > Personalizacion > Calculos).

The language consists of:
- **Operators** (arithmetic, comparison, concatenation)
- **Instructions** (control flow: Dim, Ifn/Ifa, Whilen/Whilea, Gosub/Goto, Return, End)
- **Functions** (built-in functions for records, SQL, strings, dates, files, UI, etc.)

Scripts are organized into **labels** (etiquetas) which serve as entry points triggered by events from screens or reports.

### Comments
```
' This is a comment (single quote at line start)
```

### Script Structure
```
' Variable declarations
Dim Variable1 As Numero
Dim Variable2 As Cadena

' Main code
...
End

' Subroutines (labels)
MySubroutine:
    ...
Return
```

---

## 2. Data Types and Variables

### Dim Statement

All variables must be declared before use. Undeclared variables cause a compilation error.

#### Basic Types

```
Dim Variable As Numero       ' Numeric (includes dates stored as numbers)
Dim Variable As Cadena       ' String
Dim Variable As Registro     ' Record handle (for query workspaces)
```

#### Field Variables (bound to query fields)

```
Dim Prefix.FieldName As Campo (RegisterVar, FieldName) Numero|Cadena
```

Where:
- `Prefix.FieldName` - variable name to use in script
- `RegisterVar` - previously declared Registro variable
- `FieldName` - field name as defined in the query (Campos column in Query Editor)

#### Application Variables

```
Dim Apli.VarName As Campo (Apli, VarName) Cadena|Numero
```

The keyword `Apli` indicates synchronization with an application variable. Common ones: Empresa, Ejercicio, etc. Available in the VarAplis node of personalization.

#### PARAM Variable (for inter-script parameters)

```
Dim PARAM As Cadena
```

Format: `"ParamName1:=value1, ParamName2:=value2"`
Use `:=` to assign, `,` to separate. See `Calculo` and `ExtraerParam` functions.

#### Variable Naming Rules
- Must start with a letter
- Can use dots to separate words (e.g., `Articulos.Codigo`)

### Examples

```
Dim Numero1 As Numero
Dim Cadena1 As Cadena
Dim PARAM As Cadena
Dim Articulos As Registro
Dim Articulos.Codigo As Campo (Articulos, Codigo) Numero
Dim Apli.Empresa As Campo (Apli, Empresa) Cadena
```

---

## 3. Operators

### Arithmetic Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `+` | Addition | `3 + 3` |
| `-` | Subtraction / Negation | `3 - 1` or `-1` |
| `*` | Multiplication | `3 * 3` |
| `/` | Division | `3 / 3` |

Parentheses set priority: `(5 + 10) * 2 = 30`

### Comparison Operators

| Operator | Description |
|----------|-------------|
| `=` | Equal to |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |
| `<>` | Not equal to |

Result is a logical value: TRUE (`-1`) or FALSE (`0`).

### Concatenation Operator

| Operator | Description | Example |
|----------|-------------|---------|
| `&` | Concatenates strings | `"Casa" & "blanca"` produces `"Casablanca"` |

---

## 4. Instructions (Control Flow)

### Complete Instructions List

| Instruction | Purpose |
|-------------|---------|
| `Dim` | Declare variables |
| `Ifn...Then...Else...Endif` | Numeric conditional |
| `Ifa...Then...Else...Endif` | String conditional |
| `Whilen...Then...Loop` | Numeric loop |
| `Whilea...Then...Loop` | String loop |
| `Gosub...Return` | Call subroutine, return |
| `Goto` | Jump to label |
| `End` | End script execution |
| `Depurar` | Enable debugger |
| `NoDepurar` | Disable debugger |

### Ifn (Numeric Conditional)

```
Ifn Num1 >,<,>=,<=,<>,= Num2 Then
    ' Executes if comparison is true
    ...
Else
    ' Executes if comparison is false (optional)
    ...
Endif
```

### Ifa (String Conditional)

```
Ifa Cad1 >,<,>=,<=,<>,= Cad2 Then
    ' Executes if comparison is true
    ...
Else
    ' Executes if comparison is false (optional)
    ...
Endif
```

### Whilen (Numeric Loop)

```
Whilen Num1 >,<,>=,<=,<>,= Num2 Then
    ' Executes while condition is true
    ...
Loop
```

### Whilea (String Loop)

```
Whilea Cad1 >,<,>=,<=,<>,= Cad2 Then
    ' Executes while condition is true
    ...
Loop
```

### Gosub / Return

```
Gosub MyLabel
...
End

MyLabel:
    ' Subroutine code
    ...
Return
```

Flow jumps to label, executes until `Return`, then continues after the `Gosub`.

### Goto

```
Goto MyLabel
...

MyLabel:
    ' Code continues here (no return)
    ...
```

### Inline Conditionals (IIf variants)

| Function | Compares | Returns |
|----------|----------|---------|
| `IIfnn(Num1 op Num2, Num3, Num4)` | Numbers | Number |
| `IIfaa(Cad1 op Cad2, Cad3, Cad4)` | Strings | String |
| `IIfan(Cad1 op Cad2, Num3, Num4)` | Strings | Number |
| `IIfna(Num1 op Num2, Cad3, Cad4)` | Numbers | String |

Operators for IIf: `>`, `<`, `=` only.

Examples:
```
Num = IIfnn(Onda < 1, 0, 1)
Cad = IIfaa(Sexo = "H", "Hombre", "Mujer")
Num = IIfan(Sexo = "Hombre", 0, 1)
Cad = IIfna(Nota > 4, "Aprobado", "Suspendido")
```

### Logical Functions

**And(Num1, Num2)** - Compares 2 logical values. Returns Num2 if both are true.

```
Num = And(Condition1, Condition2)
```

---

## 5. Record Operations

### AbreConsulta - Open Query Workspace

Opens a workspace in the database. Does NOT execute SQL or open any record -- only loads query info and prepares structures.

```
Reg[-1(Error)] = AbreConsulta("QueryName"[, CursorLocation])
```

| Argument | Description |
|----------|-------------|
| QueryName | Name of the query to open |
| CursorLocation | Optional: `-1` = client cursor, `0` = cursor defined in query |

Returns: `-1` on error, `>0` = register number assigned.

IMPORTANT: Always close queries when done with `CierraRegistro`. Leaving queries open causes memory leaks.

Cannot open action queries (DELETE/UPDATE/INSERT) -- use `EjecutaBorra`, `EjecutaInserta`, `EjecutaModifica` instead.

### Seleccion - Execute Query and Get Records

Actually sends the SQL query to the server and receives results.

```
Num[0,-1] = Seleccion(Reg[, "WhereClause"][, "OrderByClause"][, "HavingClause"])
```

| Argument | Description |
|----------|-------------|
| Reg | Register number from AbreConsulta |
| WhereClause | Optional: additional WHERE condition |
| OrderByClause | Optional: ORDER BY clause |
| HavingClause | Optional: HAVING clause |

Returns: `0` = failure, `-1` = success.

### CierraRegistro - Close Query Workspace

```
[Num[0,-1] =] CierraRegistro(Reg)
```

Returns: `0` = failure, `-1` = success.

### Navigation Functions

| Function | Description |
|----------|-------------|
| `Primero(Reg)` | Move to first record |
| `Siguiente(Reg)` | Move to next record |
| `Anterior(Reg)` | Move to previous record |
| `Ultimo(Reg)` | Move to last record |

All return: `0` = failure/no more records, `-1` = success.

### Record Manipulation

**Nuevo** - Save new record:
```
[Num[0,-1] =] Nuevo(Reg[, Lotes])
```
Lotes (optional, for client-cursor batch-optimistic queries): `-1` = update server (default), `0` = save locally only.

**Graba** - Save modifications:
```
[Num[0,-1] =] Graba(Reg[, Lotes])
```

**Borra** - Delete current record:
```
[Num[0,-1] =] Borra(Reg)
```

**IniciaRegistro** - Initialize fields to defaults (empty string / zero):
```
Num[0,-1] = IniciaRegistro(Reg)
```

**CopiaRegistro** - Copy field values between queries:
```
Num[0,-1] = CopiaRegistro(RegOrigin, RegDestination)
```
Only copies fields defined in both queries that have corresponding script variables.

**RefrescaRegistro** - Refresh data without re-executing query:
```
RefrescaRegistro(Reg[, Affected[1-Current,2-Group,3-All,4-AllChapters]][, Values[1-NoPending,2-All]])
```

**CuentaRegistro** - Get record count:
```
Num = CuentaRegistro(Reg)
```
Returns `-1` if count cannot be determined. Accuracy depends on cursor type (Keyset, Forward only, Static) and location (Client vs Server).

**BuscaConsulta** - Search within existing result set:
```
[Num[0,-1] =] BuscaConsulta(Reg, "Comparison", Mode[0-First,1-Last,2-Next,3-Previous])
```
Searches records already obtained by `Seleccion`, not the database directly.

**EstadoRegistro** - Check record status:
```
Num = EstadoRegistro(Reg)
```
Returns `-1` if record is valid/positioned.

**MarcaRegAsigna / MarcaRegRetorna** - Bookmark management:
```
CadMarca = MarcaRegRetorna(Reg, 0)    ' Save position
Ret = MarcaRegAsigna(Reg, CadMarca)   ' Restore position
```

### MuestraConsulta - Display Query in Screen

Opens a full interactive screen showing query results:
```
Num[0(Cancel),-1(Accept)] = MuestraConsulta(Registro, "WindowTitle", "HelpText",
    "QueryName", Editable[0-View,1-Add/Edit,2-Edit], "ColumnMask"
    [, "WhereClause"][, "OrderByClause"][, "HavingClause"]
    [, NonModal(0,-1)][, Repository(0,-1)])
```

Column mask: string of digits per column: `0`=editable, `1`=not editable, `2`=hidden.

### CadenaSQL - Get SQL String

Returns the SQL statement of a query:
```
Cad = CadenaSQL(Reg)
```

---

## 6. SQL Execution Functions

### EjecutaSQL - Execute Action Query

Executes a pre-defined action query (DELETE/UPDATE/INSERT):
```
Num[0,-1] = EjecutaSQL("QueryName")
```
Cannot modify WHERE clause. Only for action queries.

### EjecutaBorra - Mass Delete

```
Num[RecordsDeleted] = EjecutaBorra("QueryName"[, "WhereClause"])
```
Only for SELECT queries. Returns count of deleted records, `0` on error.

### EjecutaInserta - Insert Record

```
Num[0,-1] = EjecutaInserta("QueryName", "InsertString")
```

Insert string format: `"Field1;Value1;Field2;Value2;...;FieldN;ValueN"`

IMPORTANT formatting rules:
- String values must be in single quotes: `'text value'`
- Double single quotes inside strings: `'Castro ''Quini'', Enrique'`
- Date format: `dd/mm/yyyy` (no quotes)
- Decimal separator: `,` (comma)
- Field separator: `;` (semicolon)

Example:
```
Res = EjecutaInserta("PruebaInserta",
    "DNI;'34788774L';Telefono;937166655;Nombre;'Castro ''Quini'', Enrique';Fecha;23/10/2002;Peso;73,45")
```

### EjecutaModifica - Mass Update

```
Num[RecordsModified] = EjecutaModifica("QueryName", "ModifyString"[, "WhereClause"])
```

Modify string format: `"Field1;Value1;Field2;Value2;...;FieldN;ValueN"` (same rules as EjecutaInserta).

Example:
```
Res = EjecutaModifica("Municipios", "CodigoAutonomia;69", "CodigoMunicipio Like '08%'")
```

### EjecutaOperacion - Execute Operation

```
Num[0,-1] = EjecutaOperacion("OperationName", "Parameters", NumReturn[, "StringReturn"])
```

### ValorASql - Format Value for SQL

Converts a value to SQL-safe format:
```
Cad = ValorASql(Value, Type[0-Numeric,1-String,2-Date])
```

---

## 7. Screen Control (FrmControl)

Controls screen elements (controls, fields, grids, menus) from scripts.

### Syntax

```
[Cad | Num =] FrmControl("ScreenName", "Method", CallType, "Arg0", "Arg1", "Arg2")
```

**CallType values:**
- `1` = Method (execute)
- `2` = Get (read value)
- `4` = Let (set value)

**ScreenName formats:**
- Simple screen: `"ScreenName"`
- Master-Detail: `"MasterDetail.Master"` or `"MasterDetail.Detail"`
- Wizard: `"Wizard.ScreenAlias"`

### Available Methods/Properties

| Method | Purpose |
|--------|---------|
| `CONTROLENABLED` | Enable/disable a control or grid column |
| `FIELDCHANGED` | Check if control value was modified |
| `ALLOWUPDATE` | Enable/disable record modification |
| `ALLOWADDNEW` | Enable/disable record addition |
| `ALLOWDELETE` | Enable/disable record deletion |
| `CAPTION` | Get/set screen title or control label |
| `FIELDVALUE` | Get/set control value |
| `DATACHANGED` | Check if any control value was modified |
| `EXECUTERELATION` | Execute field relation |
| `SETFOCUS` | Set focus to a control |
| `UPDATE` | Save the record |
| `REFRESH` | Refresh current field values |
| `PARAM` | Get screen parameter string |
| `LOCKED` | Enable/disable entire screen |
| `REFRESHGRID` | Refresh a specific grid |
| `CONTROLVISIBLE` | Show/hide a control or grid column |
| `MENUITEMCHECK` | Get/set menu check state |
| `MENUITEMENABLED` | Enable/disable menu item |
| `LOADLAYOUT` | Load a column layout for a screen |
| `REQUIREDVALUE` | Set/get if control is required |
| `SELECTEDROWS` | Get recordset of selected grid rows |
| `RECORDSETGRID` | Get recordset of a grid |
| `MODOMANTENIMIENTO` | Get if maintenance is in Card or List mode |
| `EJECUTAMENU` | Execute a screen menu option |

### FrmControl Usage Examples

**Enable/disable a control:**
```
' Get: is control enabled?
Num = FrmControl("MyScreen", "CONTROLENABLED", 2, "txtField", "", "")
' Returns: 0=disabled, -1=enabled

' Set: disable control
FrmControl("MyScreen", "CONTROLENABLED", 4, "txtField", "0", "")
' Arg1: 0=disable, -1=enable
```

**Get/set field value:**
```
' Get value
Cad = FrmControl("MyScreen", "FIELDVALUE", 2, "txtField", "", "")

' Set value
FrmControl("MyScreen", "FIELDVALUE", 4, "txtField", "NewValue", "")
```

**Allow/disallow updates:**
```
' Disable modifications
FrmControl("MyScreen", "ALLOWUPDATE", 4, "0", "", "")
' For specific grid: Arg1 = grid name
FrmControl("MyScreen", "ALLOWUPDATE", 4, "0", "grdDataForm", "")
```

**Set caption:**
```
FrmControl("MyScreen", "CAPTION", 4, "txtField", "New Label", "")
' For screen title: Arg0 = ""
FrmControl("MyScreen", "CAPTION", 4, "", "New Window Title", "")
```

**Set focus:**
```
FrmControl("MyScreen", "SETFOCUS", 1, "txtField", "", "")
```

**Refresh grid:**
```
FrmControl("MyScreen", "REFRESHGRID", 1, "Grid", "", "")
```

**Show/hide control:**
```
' Hide
FrmControl("MyScreen", "CONTROLVISIBLE", 4, "txtField", "0", "")
' Show
FrmControl("MyScreen", "CONTROLVISIBLE", 4, "txtField", "-1", "")
```

**Required field:**
```
FrmControl("MyScreen", "REQUIREDVALUE", 4, "txtField", "-1", "")
```

**Execute menu:**
```
FrmControl("MyScreen", "EJECUTAMENU", 1, "MenuItemName", "", "")
```

---

## 8. Report Functions

### ListadoEjecuta - Execute Report

```
Num[0,-1] = ListadoEjecuta("ReportMask", "Condition", "Order", "Mode")
```

Mode values: `*` (preview), `A` (printer A), `B` (printer B), `C` (printer C), `S` (file), `P` (PDF).

### ListadoCarga - Load Report

```
Num = ListadoCarga("ReportName", Reg, "Condition")
```

### ListadoDetalle - Print Detail Line

```
Num = ListadoDetalle(Reg)
```

### ListadoDescarga - Unload Report

```
ListadoDescarga()
```

### ListadoAsignaCmp - Assign Report Field

```
ListadoAsignaCmp("FieldName", Value)
```

### ListadoLeeCmp - Read Report Field

```
Value = ListadoLeeCmp("FieldName")
```

### ListadoEdita - Edit Report

```
ListadoEdita("ReportName")
```

### ListadoInfo - Report Info

```
Cad = ListadoInfo("Property")
```

### ListadoIdioma - Report Language

```
ListadoIdioma("LanguageCode")
```

### Report Example

```
Dim Num As Numero
Dim Municipios As Registro

Municipios = AbreConsulta("_joan_Municipios")
Num = Seleccion(Municipios, "CodigoMunicipio Like '08%'", "", "")
Num = ListadoCarga("Ent_LisMunicipios", Municipios, "")

Whilen Num = -1 Then
    Num = ListadoDetalle(Municipios)
    Num = Siguiente(Municipios)
Loop

ListadoDescarga()
End
```

---

## 9. String Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `Mid` | `Mid(Cad, Start, Length)` | Extract substring (1-based) |
| `Left` | `Left(Cad, Length)` | Left portion |
| `Right` | `Right(Cad, Length)` | Right portion |
| `Trim` | `Trim(Cad, Mode)` | Remove spaces. Mode: `"L"`=left, `"R"`=right, `"T"`=both |
| `Len` | `Len(Cad)` | String length |
| `Instr` | `Instr(Start, Cad, Search)` | Find substring position (1-based, 0=not found) |
| `UCase` | `UCase(Cad)` | Convert to uppercase |
| `LCase` | `LCase(Cad)` | Convert to lowercase |
| `Val` | `Val(Cad)` | Convert string to number |
| `Str` | `Str(Num)` | Convert number to string |
| `Format` | `Format(Value, "FormatString")` | Format value. E.g. `Format(Fecha, "dd-mm-yyyy")` |
| `Chr` | `Chr(AsciiCode)` | Character from ASCII code |
| `Asc` | `Asc(Cad)` | ASCII code of first character |
| `String` | `String(Length, "Char")` | Repeat character N times |

### String Examples

```
CadenaInicial = UCase(CadenaInicial)     ' To uppercase
CadenaInicial = LCase(CadenaInicial)     ' To lowercase
NumPos = Instr(1, CadenaInicial, CadenaBuscar)  ' Find position
Cad = Trim(Cad, "T")                    ' Trim both sides
Cad = Right(Cad, 2)                      ' Last 2 chars
Cad = Left(Cad, 2)                       ' First 2 chars
Cad = Mid(Cad, Len(Cad) / 2, 1)         ' Middle char
```

---

## 10. Date and Time Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `Ahora` | `Ahora(Mode)` | Current date/time. Mode: `0`=date+time, `1`=date only, `2`=time only |
| `CalcFecha` | `CalcFecha("Unit", Amount, BaseDate)` | Date arithmetic. Unit: `"d"`=days, `"m"`=months, `"y"`=years |
| `Fan` | `Fan("dd-mm-yyyy")` | Convert string to date number |
| `Naf` | `Naf(DateNum)` | Convert date number to string (dd-mm-yyyy) |
| `Format` | `Format(DateNum, "dd-mm-yyyy")` | Format date with pattern |

### Date Examples

```
' Current date display
MsgBox("Today: " & Naf(Ahora(0)), 0, "Date")

' Add days to date
Fecha = CalcFecha("d", Val(Dias), Ahora(0))

' Compare dates
Ifn Fecha > Fan("31-12-2001") Then
    MsgBox("Year 2002 or later", 0, "Date")
Endif

' Format date
Cad = Format(Fecha, "dd-mm-yyyy")
```

---

## 11. Math Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `Abs` | `Abs(Num)` | Absolute value |
| `Redondea` | `Redondea(Num, Decimals)` | Round to N decimal places |
| `Sqr` | `Sqr(Num)` | Square root |

---

## 12. File I/O Functions

### File Operations

| Function | Syntax | Description |
|----------|--------|-------------|
| `Open` | `Handle = Open("Path", "Mode")` | Open file. Mode: `"Input"`, `"Output"`, `"Binary"` |
| `Close` | `Close(Handle)` | Close file |
| `LineGet` | `Ret = LineGet(Handle, Variable)` | Read line (sequential) |
| `LinePut` | `LinePut(Handle, Data)` | Write line (sequential) |
| `Get` | `Ret = Get(Handle, Position, Variable)` | Read (random access) |
| `Put` | `Put(Handle, Position, Data)` | Write (random access) |
| `Kill` | `Kill("Path")` | Delete file |
| `Name` | `Name("OldPath", "NewPath")` | Rename file |
| `FicheroExiste` | `Num = FicheroExiste("Path")` | Check if file exists (`-1`=yes) |
| `FicheroTemporal` | `Cad = FicheroTemporal()` | Get temporary file path |

### File Dialog Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `FicheroDlgAbre` | `Cad = FicheroDlgAbre("Title", "Filter", "DefaultExt")` | Open file dialog |
| `FicheroDlgSalva` | `Cad = FicheroDlgSalva("Title", "Filter", "DefaultExt")` | Save file dialog |

Filter format: `"Description|*.ext|All files|*.*|"`

### Directory Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `DirectorioCrea` | `Num = DirectorioCrea("Path")` | Create directory |
| `DirectorioExiste` | `Num = DirectorioExiste("Path")` | Check if dir exists (`-1`=yes) |

### Serial Port (COM)

| Function | Syntax | Description |
|----------|--------|-------------|
| `ComAbre` | `Num = ComAbre(Port, "Config", Mode)` | Open COM port |
| `ComCierra` | `ComCierra` | Close COM port |
| `ComLee` | `Cad = ComLee()` | Read from COM |
| `ComGraba` | `ComGraba("Data")` | Write to COM |
| `ComLongitudLee` | `Num = ComLongitudLee()` | Get buffer length |

### File I/O Example

```
' Sequential write
I = Open("C:\MiPrueba.txt", "Output")
J = LinePut(I, String(20, "A"))
J = LinePut(I, String(20, "B"))
J = Close(I)

' Sequential read
I = Open("C:\MiPrueba.txt", "Input")
J = -1
Whilen J = -1 Then
    J = LineGet(I, A)
Loop
J = Close(I)

' Rename and delete
Name("C:\MiPrueba.txt", "C:\MiPrueba2.txt")
Kill("C:\MiPrueba2.txt")
```

---

## 13. User Interface Functions

### MsgBox - Message Dialog

```
Num = MsgBox("Message", ButtonType, "Title")
```

Button types (common):
- `0` = OK only
- `16` = Critical icon
- `36` = Yes/No with question icon
- `64` = Information icon

Return values: `6` = Yes, `7` = No

### Aviso - Warning

```
Aviso("Message")
```

### Input - Input Dialog

```
Cad = Input("Prompt", "Title", "Default")
```

Returns user input string, or empty string if cancelled.

### Mantenimiento - Open Maintenance Screen

```
Mantenimiento("ScreenName"[, "idDatos:=XXX, Where:=XXXXX"][, LoadCalc(0,-1)])
```

| Argument | Description |
|----------|-------------|
| ScreenName | Name of the screen to load |
| Parameters | Optional: `idDatos:=`, `Where:=` |
| LoadCalc | `-1` = load screen's associated calculation, `0` = use current calculation for events |

### Calculo - Call Another Script

```
Num = Calculo("ScriptName", "Parameters")
```

Parameters format: `"Label:=StartLabel, Param1:=Value1, Param2:=Value2"`

Use `ExtraerParam` in the called script to retrieve parameters.

### ExtraerParam - Extract Parameter

```
Cad = ExtraerParam(PARAM, "ParamName")
```

### Procesa - Execute External Process

```
Num = Procesa("ProcessName"[, "Parameters"])
```

### SendKeys - Send Keystrokes

```
SendKeys("Keys")
```

### Shell - Execute External Program

```
Shell("Command", WindowStyle)
```
WindowStyle: `0`=hidden, `1`=normal, `2`=minimized, `3`=maximized.

### PunteroMouse - Change Mouse Cursor

```
PunteroMouse(CursorType)
```
`0` = default, `11` = hourglass

### Status Bar Functions

```
StatusTexto("Text")                    ' Set status text
StatusIniProgreso(Min, Max)            ' Initialize progress bar
StatusProgreso                         ' Increment progress
StatusRestaura                         ' Restore status bar
```

### EnviaCorreo - Send Email

```
Num = EnviaCorreo("To", "CC", "BCC", "Subject", "Body"[, "Attachments"][, "From"])
```

### WizControl - Wizard Control

```
WizControl("WizardName", "Method", CallType, "Arg0", "Arg1", "Arg2")
```

Similar to FrmControl but for wizard screens.

---

## 14. Application Variables

Application variables persist during application execution. Declared with `Apli` keyword:

```
Dim Apli.Empresa As Campo (Apli, Empresa) Cadena
Dim Apli.Ejercicio As Campo (Apli, Ejercicio) Numero
```

### Creating/Deleting Application Variables

```
CreaVarApli("VarName", Type, InitialValue)
```
Type: `1` = String, `2` = Numeric

```
BorraVarApli("Apli.VarName")
```

### Application Variable Example

```
Dim N As Numero
Dim Apli.RS As Campo (Apli, RS) Numero

CreaVarApli("RS", 2, 0)           ' Create numeric var
Apli.RS = Municipios               ' Assign register handle

N = Calculo("Prueba2", "Campos")   ' Call another script
BorraVarApli("Apli.RS")            ' Clean up
```

---

## 15. Session Variables

These persist across the session (not just within a single script):

| Function | Syntax | Description |
|----------|--------|-------------|
| `VarAsignaC` | `VarAsignaC("Name", "Value")` | Assign string variable |
| `VarAsignaN` | `VarAsignaN("Name", Value)` | Assign numeric variable |
| `VarLeeC` | `Cad = VarLeeC("Name")` | Read string variable |
| `VarLeeN` | `Num = VarLeeN("Name")` | Read numeric variable |

---

## 16. Screen Events Reference

When a screen has an associated calculation (set in screen properties, "Calculo asociado"), the screen triggers events that execute labels in the calculation.

### Screen-Level Events

| Event Label | When Triggered |
|-------------|----------------|
| `AntesDe_XXX` | On entering the screen (load) |
| `DespuesDe_XXX` | On leaving the screen (unload) |
| `AlCambiarRegistro_XXX` | When changing to a different record |
| `AntesAgregar_XXX` | Before inserting a new record |
| `DespuesAgregar_XXX` | After inserting a new record |
| `AntesModificar_XXX` | Before modifying a record |
| `DespuesModificar_XXX` | After modifying a record |
| `AntesEliminar_XXX` | Before deleting a record |
| `DespuesEliminar_XXX` | After deleting a record |

Where `XXX` is the screen name.

### Text Box (Control) Events

| Event | When Triggered |
|-------|----------------|
| Al entrar en (OnEnter) | Control gains focus |
| Al salir de (OnExit) | Control loses focus |

These are configured per-control in the screen editor, referencing labels in the associated calculation.

### Grid/Layout Events

Same as screen events but `XXX` is the layout identifier name:

| Event Label | When Triggered |
|-------------|----------------|
| `AlCambiarRegistro_XXX` | When grid row changes |
| `AntesAgregar_XXX` | Before adding grid row |
| `DespuesAgregar_XXX` | After adding grid row |
| `AntesModificar_XXX` | Before modifying grid row |
| `DespuesModificar_XXX` | After modifying grid row |
| `AntesEliminar_XXX` | Before deleting grid row |
| `DespuesEliminar_XXX` | After deleting grid row |

The screen editor allows overriding default label names.

### "Before" Event Return Convention

For `Antes*` (before) events, you can cancel the operation by returning a specific value or using `Aviso` to show an error. The operation proceeds only if the label completes without error.

---

## 17. Report Events Reference

When a report has an associated calculation (in report properties, "Calculo asociado"), these labels are triggered:

| Event Label | When Triggered |
|-------------|----------------|
| `EntradaInforme` | At start, before loading data and showing wizard/output config |
| `SalidaInforme` | At end, after closing temp files and unloading data |
| `LecturaRegistro` | After reading each data record, before printing it |
| `ListadoCabPag` | Page header |
| `ListadoCabRep` | Report header |
| `ListadoCab1` to `ListadoCab9` | Group headers 1-9 |
| `ListadoDet1` to `ListadoDet9` | Detail sections 1-9 |
| `ListadoPie1` to `ListadoPie9` | Group footers 1-9 |
| `ListadoPieRep` | Report footer |
| `ListadoPiePag` | Page footer |

---

## 18. Grid Calculation Events

For grids (rejillas) not tied to a maintenance screen, you can define a calculation associated to the screen. Three levels of events:

### Level 1: Screen level
- Single event on enter/exit of the screen
- Grid workspaces are accessible from this event

### Level 2: Layout level
- `AntesAgregar_XXX`, `DespuesAgregar_XXX`
- `AntesModificar_XXX`, `DespuesModificar_XXX`
- `AntesEliminar_XXX`, `DespuesEliminar_XXX`
- `AlCambiarRegistro_XXX`

### Level 3: Column level
- Al entrar en (OnEnter for column)
- Al salir de (OnExit for column)

### Grid Workspace Access

```
' Main grid workspace
Dim Grid As Registro

' Relation workspace
Dim Grid.RelationQueryName As Registro
```

### Grid Load Example

```
Dim Grid.Provincias As Registro
Dim ret As Numero

xLoad:
    MsgBox("Rs " & Grid.Provincias, 0, "Calcul")
    Ret = Seleccion(Grid.Provincias, "CodigoProvincia = '08'")
    FrmControl("Test_Mask1600", "REFRESHGRID", 1, "Grid", "", "")
End
```

The "Cargar datos al inicio" (Load data at start) checkbox in Layout properties controls whether grid data loads during screen load or manually via script.

---

## 19. Utility Functions

### Null Handling

```
Null(Variable)                  ' Set variable to null
Num = IsNull(Variable)          ' Check if null (-1=yes, 0=no)
```

### Error Handling

```
Err(Mode)                       ' 0=get error code, 1=enable error alerts, 2=disable alerts, 6+=force error
Cad = Error(ErrorCode)          ' Get error description text
```

### INI File Functions

```
Cad = IniLee("Section", "SubSection", "Key", "Default")    ' Read from app config
IniGraba("Section", "SubSection", "Key", "Value")           ' Write to app config
```

### Transaction Control

```
TransAbre       ' Begin transaction
TransAcepta     ' Commit transaction
TransCancela    ' Rollback transaction
```

### GUID Generation

```
Cad = DameNuevoGuid()    ' Generate new GUID
```

### Debug Control

```
Depurar         ' Enable debugger for this script
NoDepurar       ' Disable debugger
```

### Language/Translation

```
Cad = Idioma()                          ' Get current language code
Cad = IdiomaTraduce("Text", "LangCode") ' Translate text
Cad = Traduce("Text")                   ' Translate using current language
```

---

## 20. Complete Code Examples

### Example 1: Query iteration with count and loop

```
Dim Ret As Numero
Dim Municipios As Registro
Dim Muni.CodigoMunicipio As Campo (Municipios, CodigoMunicipio) Cadena
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena

Municipios = AbreConsulta("Municipios")
Ret = Seleccion(Municipios, "CodigoMunicipio Like '08%'")

Ifn Ret = -1 Then
    MsgBox("Count: " & Str(CuentaRegistro(Municipios)), 0, "Municipios")

    Whilen Ret = -1 Then
        MsgBox("Code: " & Muni.CodigoMunicipio & " - Name: " & Muni.Municipio, 0, "Municipio")
        Ret = Siguiente(Municipios)
    Loop
Endif

Ret = CierraRegistro(Municipios)
Ifn Ret = 0 Then
    MsgBox("Error closing query", 0, "Municipio")
Endif

End
```

### Example 2: Copy records between queries with progress bar

```
Dim Num As Numero
Dim Ret As Numero
Dim Municipios As Registro
Dim Muni.CodigoMunicipio As Campo (Municipios, CodigoMunicipio) Cadena
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena
Dim Municipios2 As Registro
Dim Muni2.CodigoAutonomia As Campo (Municipios2, CodigoAutonomia) Numero
Dim Muni2.CodigoMunicipio As Campo (Municipios2, CodigoMunicipio) Cadena
Dim Muni2.Municipio As Campo (Municipios2, Municipio) Cadena

PunteroMouse(11)

Municipios2 = AbreConsulta("Municipios2")
Ret = Seleccion(Municipios2)

Municipios = AbreConsulta("Municipios", -1)
Ret = Seleccion(Municipios, "CodigoMunicipio Like '08%'")

Ifn Ret = -1 Then
    Num = CuentaRegistro(Municipios)
    StatusIniProgreso(1, Num)

    Whilen Ret = -1 Then
        Ret = StatusTexto(Muni.Municipio)
        Ifn Ret = -1 Then
            Ret = IniciaRegistro(Municipios2)
            Ret = CopiaRegistro(Municipios, Municipios2)
            Nuevo(Municipios2)
            Ret = Siguiente(Municipios)
        Endif
    Loop

    StatusRestaura
Endif

Ret = CierraRegistro(Municipios)
Ret = CierraRegistro(Municipios2)
PunteroMouse(0)

End
```

### Example 3: BuscaConsulta search

```
Dim Ret As Numero
Dim Municipios As Registro
Dim Muni.CodigoMunicipio As Campo (Municipios, CodigoMunicipio) Cadena
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena

Municipios = AbreConsulta("Municipios")
Ret = Seleccion(Municipios, "CodigoNacion = 108")

Ifn Ret = -1 Then
    Ret = BuscaConsulta(Municipios, "Municipio Like 'Te%'", 0)
    Ifn Ret = -1 Then
        MsgBox("Found: " & Muni.CodigoMunicipio & " - " & Muni.Municipio, 0, "Municipio")
    Endif

    Ret = BuscaConsulta(Municipios, "Municipio Like 'Sa%'", 3)
    Ifn Ret = -1 Then
        MsgBox("Found: " & Muni.CodigoMunicipio & " - " & Muni.Municipio, 0, "Municipio")
    Endif
Endif

Ret = CierraRegistro(Municipios)
End
```

### Example 4: Graba (save modification)

```
Dim Ret As Numero
Dim Municipios As Registro
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena

Municipios = AbreConsulta("Municipios")
Ret = Seleccion(Municipios, "CodigoMunicipio = '08187'")
Ifn Ret = -1 Then
    Muni.Municipio = "Sabadell"
    Ifn Graba(Municipios) = 0 Then
        MsgBox("Error", 0, "Graba")
    Endif
Endif
CierraRegistro(Municipios)
```

### Example 5: Borra (delete with confirmation)

```
Dim Ret As Numero
Dim Municipios As Registro
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena

Municipios = AbreConsulta("_joan_Municipios")
Ret = Seleccion(Municipios, "CodigoMunicipio = '08021'")
Ifn Ret = -1 Then
    Ret = MsgBox("Delete " & Muni.Municipio & "?", 36, "Municipio")
    Ifn Ret = 6 Then
        Borra(Municipios)
    Endif
Endif
CierraRegistro(Municipios)
```

### Example 6: Date arithmetic

```
Dim Dias As Cadena
Dim Fecha As Numero

MsgBox("Today: " & Naf(Ahora(0)), 0, "Date Calc")

Dias = Input("How many days?", "Date Calc", "1")
Ifa Dias <> "" Then
    Fecha = CalcFecha("d", Val(Dias), Ahora(0))
    MsgBox("In " & Dias & " days: " & Format(Fecha, "dd-mm-yyyy"), 64, "Date Calc")
Endif

Ifn Fecha > Fan("31-12-2001") Then
    MsgBox("Year 2002 or later", 0, "Date Calc")
Endif

End
```

### Example 7: Null handling with Gosub

```
Dim Num As Numero

Null(Num)
Gosub CompruebaNulo
Num = 23
Gosub CompruebaNulo

End

CompruebaNulo:
    Ifn IsNull(Num) = -1 Then
        MsgBox("Variable is null", 64, "Nulls")
    Else
        MsgBox("Value: " & Num, 64, "Nulls")
    Endif
Return
```

### Example 8: Error handling

```
Dim Num As Numero
Dim Cad As Cadena

Err(1)                           ' Enable error alerts
Num = 1
MsgBox("Error is: " & Str(Err(0)), 0, "Error 1")

Cad = Mid("", -1, -5)           ' Causes argument error
Num = Err(0)
MsgBox("Error: " & UCase(Error(Num)), 0, "Problem")

Err(6)                           ' Force error code 6
Num = Err(0)
MsgBox("Forced error: " & Str(Num), 0, "Error")

Err(2)                           ' Disable error alerts
Cad = Mid("", -1, -5)           ' No alert for this error

End
```

### Example 9: Inter-script parameter passing

Script "Prueba1":
```
Dim Num As Numero
Num = Calculo("Prueba2", "Label:=Inicio, Municipio:=Sant Quirze del Valles, Codigo:=08238")
End
```

Script "Prueba2":
```
Dim Num As Numero
Dim PARAM As Cadena
Dim P1 As Cadena
Dim P2 As Cadena

Inicio:
P1 = ExtraerParam(PARAM, "Codigo")
P2 = ExtraerParam(PARAM, "Municipio")
MsgBox("Codigo=" & P1 & " - Municipio=" & P2, 0, "ExtraerParam")
End
```

### Example 10: MuestraConsulta (interactive query screen)

```
Dim Num As Numero
Dim Municipios As Registro
Dim Muni.CodigoMunicipio As Campo (Municipios, CodigoMunicipio) Cadena
Dim Muni.Municipio As Campo (Municipios, Municipio) Cadena

Num = MuestraConsulta(Municipios, "Barcelona Municipalities", "Select a municipality",
    "Municipios", 0, "1122222", "CodigoMunicipio Like '08%'", "Municipio")

Ifn Num = -1 Then
    MsgBox("Code: " & Muni.CodigoMunicipio & " - Name: " & Muni.Municipio, 0, "Municipio")
Endif
Ifn Municipios <> -1 Then
    CierraRegistro(Municipios)
Endif
```

### Example 11: File operations

```
Dim A As Cadena
Dim I As Numero
Dim J As Numero

' Write sequential file
I = Open("C:\MiPrueba.txt", "Output")
J = LinePut(I, String(20, "A"))
J = LinePut(I, String(20, "B"))
J = LinePut(I, String(20, "C"))
J = Close(I)

' Read sequential file
I = Open("C:\MiPrueba.txt", "Input")
J = -1
Whilen J = -1 Then
    J = LineGet(I, A)
Loop
J = Close(I)

' Binary read/write
I = Open("C:\MiPrueba.txt", "Binary")
J = Put(I, 1, String(20, "A"))
J = Put(I, 2, String(20, "B"))
J = Get(I, 1, A)
J = Close(I)

' Rename and delete
Name("C:\MiPrueba.txt", "C:\MiPrueba2.txt")
Kill("C:\MiPrueba2.txt")

End
```

### Example 12: Serial port communication

```
Dim dblpeso As Numero
Dim strPeso As Cadena
Dim intAbiertoBien As Numero
Dim intLongCom As Numero
Dim blnEstable As Numero

blnEstable = 0
intAbiertoBien = ComAbre(1, "9600,n,8,1", 1)

Ifn intAbiertoBien <> -1 Then
    MsgBox("Port error", 64, "COM Port")
    End
Endif

ComGraba("$")

Whilen blnEstable <> 32 Then
    ComGraba("$")
    intLongCom = 0
    Whilen intLongCom < 10 Then
        intLongCom = ComLongitudLee()
    Loop

    strPeso = ComLee()
    ' ... process weight data ...
Loop

ComCierra
MsgBox("Weight: " & dblpeso, 64, "Weight")
End
```

---

## 21. Obsolete Functions

Functions from Win32 that are replaced in CLASS:

| Old (Win32) | New (CLASS) |
|-------------|-------------|
| `AbreTabla` | `AbreConsulta` + `Seleccion` |
| `AdjuntaMail` | `EnviaCorreo` |
| `Busca` | `BuscaConsulta` |
| `Call` | `Procesa` |
| `CambiaEuro` | Removed |
| `CreaCita` / `CreaTarea` | Removed |
| `DatosMail` / `DireccionesMail` / `EnviaMail` / `NuevoMail` / `LoginMail` / `LogoutMail` | `EnviaCorreo` |
| `DialogoBoton` | `Mantenimiento` |
| `DialogoCActivo` / `DialogoCampo` / `DialogoEjecuta` | `FrmControl` |
| `Indice` | Removed |
| `ListadoDatosEnEuros` / `ListadoMonedaPresentacion` / `ListadoNivel` | Removed |
| `MnTCActivo` / `MntFijaCampo` / `MntModificado` / `MntSaltaCampo` | `FrmControl` |

---

## 22. Complete Function Index

### Record/Query Operations
`AbreConsulta`, `Seleccion`, `CierraRegistro`, `Primero`, `Siguiente`, `Anterior`, `Ultimo`, `Nuevo`, `Graba`, `Borra`, `IniciaRegistro`, `CopiaRegistro`, `RefrescaRegistro`, `CuentaRegistro`, `BuscaConsulta`, `EstadoRegistro`, `MarcaRegAsigna`, `MarcaRegRetorna`, `MuestraConsulta`, `CadenaSQL`

### SQL Execution
`EjecutaSQL`, `EjecutaBorra`, `EjecutaInserta`, `EjecutaModifica`, `EjecutaOperacion`, `ValorASql`

### Screen/Form Control
`FrmControl`, `Mantenimiento`, `WizControl`

### Reports
`ListadoEjecuta`, `ListadoCarga`, `ListadoDescarga`, `ListadoDetalle`, `ListadoAsignaCmp`, `ListadoLeeCmp`, `ListadoEdita`, `ListadoInfo`, `ListadoIdioma`

### String Functions
`Mid`, `Left`, `Right`, `Trim`, `Len`, `Instr`, `UCase`, `LCase`, `Val`, `Str`, `Format`, `Chr`, `Asc`, `String`

### Date/Time Functions
`Ahora`, `CalcFecha`, `Fan`, `Naf`

### Math Functions
`Abs`, `Redondea`, `Sqr`

### Logical Functions
`And`, `IIfaa`, `IIfan`, `IIfna`, `IIfnn`, `IsNull`, `Null`

### File I/O
`Open`, `Close`, `Get`, `Put`, `LineGet`, `LinePut`, `Kill`, `Name`, `FicheroExiste`, `FicheroTemporal`, `FicheroDlgAbre`, `FicheroDlgSalva`, `DirectorioCrea`, `DirectorioExiste`

### Serial Port
`ComAbre`, `ComCierra`, `ComLee`, `ComGraba`, `ComLongitudLee`

### User Interface
`MsgBox`, `Aviso`, `Input`, `SendKeys`, `Shell`, `PunteroMouse`, `StatusTexto`, `StatusIniProgreso`, `StatusProgreso`, `StatusRestaura`

### Script/Program Flow
`Calculo`, `ExtraerParam`, `Procesa`, `EnviaCorreo`

### Application Variables
`CreaVarApli`, `BorraVarApli`

### Session Variables
`VarAsignaC`, `VarAsignaN`, `VarLeeC`, `VarLeeN`

### INI Configuration
`IniLee`, `IniGraba`

### Transaction Control
`TransAbre`, `TransAcepta`, `TransCancela`

### Error Handling
`Err`, `Error`

### Language
`Idioma`, `IdiomaTraduce`, `Traduce`

### Miscellaneous
`DameNuevoGuid`, `CambiaDivisa`, `Depurar`, `NoDepurar`, `SeleccionaArbol`, `SeleccionaLimites`, `SeleccionaSeleccion`

---

## Appendix: Key Patterns for AI Code Generation

### Standard Query Pattern (Read)
```
Dim Reg As Registro
Dim Reg.Field As Campo (Reg, Field) Tipo

Reg = AbreConsulta("QueryName")
Ret = Seleccion(Reg[, "WHERE clause"])
Ifn Ret = -1 Then
    Whilen Ret = -1 Then
        ' Process Reg.Field values
        Ret = Siguiente(Reg)
    Loop
Endif
CierraRegistro(Reg)
```

### Standard Insert Pattern
```
Reg = AbreConsulta("QueryName")
Ret = Seleccion(Reg)
IniciaRegistro(Reg)
Reg.Field1 = Value1
Reg.Field2 = Value2
Nuevo(Reg)
CierraRegistro(Reg)
```

### Standard Update Pattern
```
Reg = AbreConsulta("QueryName")
Ret = Seleccion(Reg, "WHERE clause")
Ifn Ret = -1 Then
    Reg.Field = NewValue
    Graba(Reg)
Endif
CierraRegistro(Reg)
```

### Standard Delete Pattern
```
Reg = AbreConsulta("QueryName")
Ret = Seleccion(Reg, "WHERE clause")
Ifn Ret = -1 Then
    Borra(Reg)
Endif
CierraRegistro(Reg)
```

### Mass SQL Operations Pattern
```
' Mass delete
Num = EjecutaBorra("QueryName", "WHERE clause")

' Mass update
Num = EjecutaModifica("QueryName", "Field1;Value1;Field2;Value2", "WHERE clause")

' Insert
Num = EjecutaInserta("QueryName", "Field1;Value1;Field2;Value2")
```

### Screen Event Handler Pattern
```
' Variable declarations
Dim Ret As Numero
Dim Screen As Registro
Dim Screen.Field As Campo (Screen, Field) Tipo

' Screen enter event
AntesDe_ScreenName:
    ' Initialize, load data
Return

' Before save event
AntesModificar_ScreenName:
    ' Validate data
    Ifn Screen.Field = 0 Then
        Aviso("Field is required")
    Endif
Return

' After save event
DespuesModificar_ScreenName:
    ' Post-save logic
Return

' On field change (configured per control)
OnExitFieldName:
    ' React to field value change
    FrmControl("ScreenName", "FIELDVALUE", 4, "otherField", "calculated value", "")
Return
```

### Report Event Handler Pattern
```
Dim Reg As Registro
Dim Reg.Field As Campo (Reg, Field) Tipo

EntradaInforme:
    ' Initialize report
Return

LecturaRegistro:
    ' Process each record before printing
    ' Can modify ListadoAsignaCmp values here
Return

SalidaInforme:
    ' Cleanup after report
Return
```
