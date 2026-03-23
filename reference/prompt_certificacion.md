  --
  --

Se requiere desarrollar un módulo en Sage 200 para la **gestión de
equipos, resultados y cálculo de clasificación de liga**, incluyendo
mantenimiento de datos e informe final.

Los objetos generados deben llevar el prefijo cf\_

Mantenimiento de Equipos y Resultados

Se deberá crear una tabla de Equipos y su correspondiente mantenimiento
que deberá funcionar en modo ficha y en modo grid de la misma manera.

Los campos en **[CodigoEmpresa y CodigoEquipo]{.underline}** forman la
clave principal.

  Campo                             Rótulo                     Tipo dato
  --------------------------------- -------------------------- -------------------------
  **[CodigoEmpresa]{.underline}**   No aparecerá en pantalla   Repositorio
  **[CódigoEquipo]{.underline}**    Cod. Equipo                Entero
  Nombre                            Nombre Equipo              Texto 30
  JuegaEuropa                       Juega en Europa            Si/No (Defecto No)
  Competicion                       Competición                Entero Lista de Valores
                                                               1.- Vacio (defecto)
                                                               2.- Europa League
                                                               3.- Champios League

Reglas de Negocio:

Si juega en europa está a No, el campo competición deberá estar
inhabilitado. Si el campo está a Sí, deberá informarse obligatoriamente
Europa League o Champions League en el campo competición.

Mantenimiento de Resultados:

Se deberá crear una tabla llamada Resultados y su correspondiente
pantalla para registrar los diferentes partidos de cada jornada.

Los campos en Codigoempresa, Jornada, EquipoLocal y EquipoVisitante
forman la clave principal.

  Campo                               Rótulo                     Tipo dato
  ----------------------------------- -------------------------- ------------------------------------
  **[CodigoEmpresa]{.underline}**     No aparecerá en pantalla   Repositorio
  **[Jornada]{.underline}**           Jornada                    Entero
  **Equipo Local**                    Local                      Entero (referencia tablas equipos)
  [GolesLocal]{.underline}            Goles Local                Entero
  **[EquipoVisitante]{.underline}**   Visitante                  Entero (referencia tablas equipos)
  GolesVisitante                      Goles Visitante            Entero
  Fecha                               Fecha                      Fecha

En la pantalla asociada en los campos EquipoLocal y EquipoVisitante se
deberá mostrar un desplegable para poder seleccionar los equipos
existentes en la tabla de Equipos, mostrando a su lado como no editable
el nombre de cada uno de ellos (campo no editable). Además, los campos
GolesLocal y GolesVisitante tendrá el valor por defecto 0. El campo
Jornada podrá contener los valores de 1 a 38. El campo fecha tendrá por
defecto el valor del día de introducción de datos.

Este mantenimiento será editable tanto en modo ficha como en modo grid,
que tendrá las mismas particularidades que la ficha.

2: Cálculo Clasificación

Necesitamos tener una tabla donde se calcule la clasificación actual de
la liga en un momento dado. Para ello crearemos una nueva tabla llamada
***[Clasificacion]{.underline}***. Los campos en negrita corresponden a
la clave principal.

  Campo                             Rótulo                     Tipo dato
  --------------------------------- -------------------------- -------------
  **[CodigoEmpresa]{.underline}**   No aparecerá en pantalla   Repositorio
  **[Posicion]{.underline}**        Posición                   Entero
  **Equipo**                        Equipo                     Entero
  PartidosJugados                   PJ                         Entero
  PartidosGanados                   PG                         Entero
  PartidosEmpatados                 PE                         Entero
  PartidosPerdidos                  PP                         Entero
  GolesFavor                        GF                         Entero
  GolesContra                       GC                         Entero
  Puntos                            Puntos                     Entero
  Positivos                         P+                         Entero
  DiferenciaGoles                   DG                         Entero

Para cada equipo se completarán los campos de la tabla según:

PJ: Numero de partidos jugados por este equipo

PG: Numero de partidos ganados por este equipo

PE: Número de partidos empatados por este equipo

PP: Número de partidos perdidos por este equipo

GF: Suma de los goles conseguidos por este equipo

GC: Suma de los goles que le han marcado a este equipo

Puntos: Por cada partido ganado (+3), por cada partido empatado (+1),
por cada partido perdido (0)

Positivos: Suma de: por cada partido ganado como visitante (+3), por
cada partido empatado como visitante (+1), por cada partido perdido como
visitante (0), por cada partido ganado como local (0), por cada partido
empatado como local (-1), por cada partido perdido como local (-3)

DiferenciaGoles: Diferencia entre los goles marcados y goles recibidos
por este equipo.

La posición 1 corresponderá al equipo que más puntos tenga, mientras que
la 20 será el equipo que menos puntos haya conseguido. En caso de empate
entre más de un equipo, la posición se determinará por este criterio:

1.- Mayor número de puntos

2.- Mayor número de positivos

3.- Diferencia de goles más grande

4.- Menos partidos jugados

5.- orden alfabético del equipo

3: Informe de Clasificación

Crearemos un nuevo informe que se ejecutará desde el cálculo de
clasificación una vez haya finalizado y que mostrará la información de
éste con el siguiente diseño:

![cid:image001.jpg\@01D43F7B.4731CB80](media/image1.jpeg){width="5.241666666666666in"
height="7.416666666666667in"}
