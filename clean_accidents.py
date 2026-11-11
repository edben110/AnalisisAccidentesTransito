"""
Limpieza del dataset US Accidents (Kaggle: sobhanmoosavi/us-accidents) con PySpark.

Requisitos: Python 3.10-3.13, Java 17+ y pyspark 4.x.
En Windows el script configura HADOOP_HOME usando tools/hadoop (winutils.exe).

Uso basico:
    py -3.12 clean_accidents.py

Uso avanzado:
    py -3.12 clean_accidents.py --input data/us_accidents/US_Accidents_March23.csv \
                                --out data/us_accidents_clean/US_Accidents_March23_clean.csv \
                                --parts 4 --threads 4 --driver-memory 6g

El script:
  1. Lee el CSV crudo (todo como texto).
  2. Perfila la calidad de los datos en una sola pasada (nulos, duplicados,
     valores imposibles, formatos invalidos).
  3. Aplica las reglas de limpieza.
  4. Escribe un unico CSV limpio + un reporte de calidad (CSV).
"""

from __future__ import annotations

import argparse
import csv
import functools
import operator
import os
import shutil
import sys
import time
from pathlib import Path

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

# --------------------------------------------------------------------------
# Configuracion del dataset
# --------------------------------------------------------------------------

# Columnas numericas: (columna, minimo valido, maximo valido)
NUMERIC_RANGES: dict[str, tuple[float | None, float | None]] = {
    "Start_Lat": (24.0, 50.0),        # bounding box continental de EE. UU.
    "Start_Lng": (-125.0, -66.0),
    "End_Lat": (24.0, 50.0),
    "End_Lng": (-125.0, -66.0),
    "Distance(mi)": (0.0, 100.0),     # > 100 mi en un tramo de accidente es error
    "Temperature(F)": (-60.0, 130.0),
    "Wind_Chill(F)": (-60.0, 130.0),
    "Humidity(%)": (0.0, 100.0),
    "Pressure(in)": (20.0, 33.0),
    "Visibility(mi)": (0.0, 20.0),
    "Wind_Speed(mph)": (0.0, 100.0),
    "Precipitation(in)": (0.0, 10.0),
}

BOOLEAN_COLUMNS = [
    "Amenity", "Bump", "Crossing", "Give_Way", "Junction", "No_Exit",
    "Railway", "Roundabout", "Station", "Stop", "Traffic_Calming",
    "Traffic_Signal", "Turning_Loop",
]

TEXT_COLUMNS = [
    "ID", "Source", "Description", "Street", "City", "County", "State",
    "Zipcode", "Country", "Timezone", "Airport_Code", "Wind_Direction",
    "Weather_Condition", "Sunrise_Sunset", "Civil_Twilight",
    "Nautical_Twilight", "Astronomical_Twilight",
]

TIMESTAMP_COLUMNS = ["Start_Time", "End_Time", "Weather_Timestamp"]

# Valores que en el CSV significan "sin dato".
NULL_TOKENS = {
    "NULL", "N/A", "NA", "NAN", "NONE", "-", "?", "UNKNOWN", "SIN DATO",
}

# Direccion del viento: valor crudo -> abreviatura estandar de 16 rumbos.
WIND_DIRECTIONS = {
    "CALM": "CALM", "VARIABLE": "VAR", "VAR": "VAR",
    "NORTH": "N", "NORTH NORTHEAST": "NNE", "NORTHEAST": "NE",
    "EAST NORTHEAST": "ENE", "EAST": "E", "EAST SOUTHEAST": "ESE",
    "SOUTHEAST": "SE", "SOUTH SOUTHEAST": "SSE", "SOUTH": "S",
    "SOUTH SOUTHWEST": "SSW", "SOUTHWEST": "SW", "WEST SOUTHWEST": "WSW",
    "WEST": "W", "WEST NORTHWEST": "WNW", "NORTHWEST": "NW",
    "NORTH NORTHWEST": "NNW",
}
# El dataset mezcla nombres largos ("South") y abreviaturas ("S"): ambos son validos.
WIND_ALIASES = {**WIND_DIRECTIONS, **{v: v for v in WIND_DIRECTIONS.values()}}

# Clave natural para identificar el mismo accidente reportado dos veces:
# mismo instante de inicio y mismas coordenadas exactas.
DEDUPE_KEY = ["Start_Time", "Start_Lat", "Start_Lng"]

# Columnas sin las cuales la fila no sirve para analisis.
CRITICAL_COLUMNS = ["ID", "Start_Time", "Start_Lat", "Start_Lng", "Severity", "State"]

# Duracion maxima creible de un accidente (24 h).
MAX_DURATION_HOURS = 24

COLUMN_ORDER = [
    "ID", "Source", "Severity", "Start_Time", "End_Time", "Start_Lat",
    "Start_Lng", "End_Lat", "End_Lng", "Distance(mi)", "Description",
    "Street", "City", "County", "State", "Zipcode", "Country", "Timezone",
    "Airport_Code", "Weather_Timestamp", "Temperature(F)", "Wind_Chill(F)",
    "Humidity(%)", "Pressure(in)", "Visibility(mi)", "Wind_Direction",
    "Wind_Speed(mph)", "Precipitation(in)", "Weather_Condition", "Amenity",
    "Bump", "Crossing", "Give_Way", "Junction", "No_Exit", "Railway",
    "Roundabout", "Station", "Stop", "Traffic_Calming", "Traffic_Signal",
    "Turning_Loop", "Sunrise_Sunset", "Civil_Twilight", "Nautical_Twilight",
    "Astronomical_Twilight",
]


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------


def configurar_hadoop_windows(raiz: Path) -> None:
    """En Windows, Spark necesita winutils.exe para operar con disco local.

    Se busca en tools/hadoop o en %USERPROFILE%\\.hadoop y se exporta HADOOP_HOME.
    """
    if os.name != "nt" or os.environ.get("HADOOP_HOME"):
        return
    candidatos = [raiz / "tools" / "hadoop", Path.home() / ".hadoop"]
    for candidato in candidatos:
        winutils = candidato / "bin" / "winutils.exe"
        if winutils.exists():
            os.environ["HADOOP_HOME"] = str(candidato)
            os.environ["PATH"] = str(candidato / "bin") + os.pathsep + os.environ.get("PATH", "")
            print(f"HADOOP_HOME configurado en {candidato}")
            return


def crear_spark(threads: int, driver_memory: str) -> SparkSession:
    """Crea la SparkSession local con un perfil moderado para una PC."""
    return (
        SparkSession.builder
        .master(f"local[{threads}]")
        .appName("US-Accidents-Cleaning")
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", str(max(threads * 8, 16)))
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def leer_csv(spark: SparkSession, ruta: Path, multilinea: bool) -> DataFrame:
    """Lee el CSV crudo manteniendo todas las columnas como string."""
    return (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .option("multiLine", "true" if multilinea else "false")
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .csv(str(ruta))
    )


# --------------------------------------------------------------------------
# Perfil de calidad (una sola pasada sobre los datos crudos)
# --------------------------------------------------------------------------


def _expr_invalido(columna: str, minimo: float | None, maximo: float | None):
    """Expresion que marca un valor numerico fuera de rango o no parseable."""
    col = F.col(f"`{columna}`")
    numero = col.cast("double")
    condiciones = [
        col.isNotNull() & (F.trim(col) != "") & numero.isNull(),  # no parseable
        numero.isNotNull() & numero.isNaN(),
    ]
    if minimo is not None:
        condiciones.append(numero < minimo)
    if maximo is not None:
        condiciones.append(numero > maximo)
    return F.sum(F.when(functools.reduce(operator.or_, condiciones), 1).otherwise(0))


def perfil_calidad(df: DataFrame) -> dict[str, int]:
    """Calcula todas las metricas de calidad en una unica pasada."""
    exprs: list = [F.count(F.lit(1)).alias("total")]
    nombre_expr: list[tuple[str, str]] = [("total", "Filas totales")]

    # --- nulos y vacios por columna -------------------------------------
    for col in COLUMN_ORDER:
        c = F.col(f"`{col}`")
        exprs.append(F.sum(F.when(c.isNull(), 1).otherwise(0)).alias(f"{col}__nulos"))
        exprs.append(F.sum(F.when(c.isNotNull() & (F.trim(c) == ""), 1).otherwise(0)).alias(f"{col}__vacios"))
        nombre_expr.append((f"{col}__nulos", f"Nulos en {col}"))
        nombre_expr.append((f"{col}__vacios", f"Vacios en {col}"))

    # --- duplicados ------------------------------------------------------
    # La clave se compara ya tipada: el CSV mezcla "2017-07-23 04:21:01" y
    # "2017-07-23 04:21:01.000000000" para el mismo instante, y como texto
    # parecerian accidentes distintos.
    exprs.append(F.countDistinct(
        F.to_timestamp(F.col("`Start_Time`")),
        F.col("`Start_Lat`").cast("double"),
        F.col("`Start_Lng`").cast("double"),
    ).alias("claves_distintas"))
    exprs.append(F.countDistinct(F.col("`ID`")).alias("ids_distintos"))
    nombre_expr += [
        ("claves_distintas", "Claves naturales distintas"),
        ("ids_distintos", "IDs distintos"),
    ]

    # --- rangos numericos ------------------------------------------------
    for col, (minimo, maximo) in NUMERIC_RANGES.items():
        exprs.append(_expr_invalido(col, minimo, maximo).alias(f"{col}__invalidos"))
        nombre_expr.append((f"{col}__invalidos", f"Valores fuera de rango en {col}"))

    # --- fechas ----------------------------------------------------------
    inicio = F.to_timestamp(F.col("`Start_Time`"))
    fin = F.to_timestamp(F.col("`End_Time`"))
    marca = F.to_timestamp(F.col("`Weather_Timestamp`"))
    exprs += [
        F.sum(F.when(F.col("`Start_Time`").isNotNull() & inicio.isNull(), 1).otherwise(0)).alias("start__invalidos"),
        F.sum(F.when(F.col("`End_Time`").isNotNull() & fin.isNull(), 1).otherwise(0)).alias("end__invalidos"),
        F.sum(F.when(F.col("`Weather_Timestamp`").isNotNull() & marca.isNull(), 1).otherwise(0)).alias("weather_ts__invalidos"),
        F.sum(F.when(fin < inicio, 1).otherwise(0)).alias("fin_antes_inicio"),
        F.sum(F.when(fin > inicio + F.expr(f"INTERVAL {MAX_DURATION_HOURS} HOURS"), 1).otherwise(0)).alias("duracion_excesiva"),
        F.sum(F.when(F.col("`End_Lat`").isNull() != F.col("`End_Lng`").isNull(), 1).otherwise(0)).alias("fin_coord_parcial"),
    ]
    nombre_expr += [
        ("start__invalidos", "Start_Time no parseable"),
        ("end__invalidos", "End_Time no parseable"),
        ("weather_ts__invalidos", "Weather_Timestamp no parseable"),
        ("fin_antes_inicio", "End_Time anterior a Start_Time"),
        ("duracion_excesiva", f"Duracion mayor a {MAX_DURATION_HOURS} h"),
        ("fin_coord_parcial", "End_Lat/End_Lng con solo una de las dos"),
    ]

    # --- formatos categoricos -------------------------------------------
    exprs += [
        F.sum(F.when(~F.col("`Zipcode`").rlike(r"^\d{5}(-\d{4})?$"), 1).otherwise(0)).alias("zip__invalidos"),
        F.sum(F.when(~F.col("`State`").rlike(r"^[A-Z]{2}$"), 1).otherwise(0)).alias("state__invalidos"),
        F.sum(F.when(~F.upper(F.trim(F.col("`Severity`"))).isin("1", "2", "3", "4"), 1).otherwise(0)).alias("severity__invalidos"),
        F.sum(F.when(~F.col("`Country`").eqNullSafe(F.lit("US")), 1).otherwise(0)).alias("country__invalidos"),
        F.sum(F.when(~F.upper(F.trim(F.col("`Wind_Direction`"))).isin(list(WIND_ALIASES)), 1).otherwise(0)).alias("wind__invalidos"),
    ]
    nombre_expr += [
        ("zip__invalidos", "Zipcode con formato invalido"),
        ("state__invalidos", "State distinto de 2 letras mayusculas"),
        ("severity__invalidos", "Severity fuera de 1-4"),
        ("country__invalidos", "Country distinto de US"),
        ("wind__invalidos", "Wind_Direction fuera del catalogo"),
    ]

    # Valores categoricos escritos de varias formas.
    for variante in ["CALM", "VARIABLE", "SOUTH", "WEST", "NORTH", "EAST"]:
        clave = f"variante_{variante.lower()}"
        exprs.append(F.sum(F.when(F.upper(F.trim(F.col("`Wind_Direction`"))) == variante, 1).otherwise(0)).alias(clave))
        nombre_expr.append((clave, f"Wind_Direction escrito como '{variante}'"))

    fila = df.select(*exprs).collect()[0].asDict()
    total = fila["total"]
    fila["duplicados_clave"] = total - fila["claves_distintas"]
    fila["duplicados_id"] = total - fila["ids_distintos"]
    nombre_expr += [
        ("duplicados_clave", "Filas duplicadas por clave natural"),
        ("duplicados_id", "IDs duplicados"),
    ]
    fila["_nombres"] = nombre_expr
    return fila


# --------------------------------------------------------------------------
# Limpieza
# --------------------------------------------------------------------------


def limpiar_texto(df: DataFrame) -> DataFrame:
    """Recorta espacios y convierte placeholders ('NULL', 'N/A', ...) en nulos."""
    for col in TEXT_COLUMNS:
        c = f"`{col}`"
        limpio = F.trim(F.col(c))
        df = df.withColumn(
            col,
            F.when(F.upper(limpio).isin(list(NULL_TOKENS)), F.lit(None)).otherwise(limpio),
        )
    return df


def normalizar_categoricas(df: DataFrame) -> DataFrame:
    """Estandariza estado, zip, pais, direccion del viento y severidad."""
    df = df.withColumn(
        "State",
        F.when(F.upper(F.trim(F.col("State"))).rlike("^[A-Z]{2}$"),
               F.upper(F.trim(F.col("State")))),
    )
    # Zipcode: conserva los primeros 5 digitos (ZIP+4 -> ZIP5); invalido -> nulo.
    df = df.withColumn(
        "Zipcode",
        F.when(F.trim(F.col("Zipcode")).rlike(r"^\d{5}(-\d{4})?$"),
               F.substring(F.trim(F.col("Zipcode")), 1, 5)),
    )
    df = df.withColumn("Country", F.lit("US"))

    direccion = F.upper(F.trim(F.col("Wind_Direction")))
    mapeo = F.create_map(*[F.lit(x) for par in WIND_ALIASES.items() for x in par])
    df = df.withColumn(
        "Wind_Direction",
        F.when(direccion.isNull(), F.lit(None)).otherwise(mapeo[direccion]),
    )

    severidad = F.trim(F.col("Severity"))
    df = df.withColumn(
        "Severity",
        F.when(severidad.rlike("^[1-4]$"), severidad.cast("int")),
    )
    return df


def normalizar_tipos(df: DataFrame) -> DataFrame:
    """Convierte fechas, numericos y booleanos a sus tipos reales."""
    for col in TIMESTAMP_COLUMNS:
        df = df.withColumn(col, F.to_timestamp(F.col(f"`{col}`")))

    for col in NUMERIC_RANGES:
        df = df.withColumn(col, F.col(f"`{col}`").cast("double"))

    for col in BOOLEAN_COLUMNS:
        df = df.withColumn(
            col,
            F.when(F.upper(F.trim(F.col(f"`{col}`"))) == "TRUE", F.lit(True))
             .when(F.upper(F.trim(F.col(f"`{col}`"))) == "FALSE", F.lit(False)),
        )
    return df


def anular_fuera_de_rango(df: DataFrame) -> DataFrame:
    """Sustituye por nulo los valores fisicamente imposibles."""
    for col, (minimo, maximo) in NUMERIC_RANGES.items():
        numero = F.col(f"`{col}`")
        condiciones = [numero.isNull()]
        if minimo is not None:
            condiciones.append(numero < minimo)
        if maximo is not None:
            condiciones.append(numero > maximo)
        df = df.withColumn(
            col,
            F.when(functools.reduce(operator.or_, condiciones), F.lit(None)).otherwise(numero),
        )
    return df


def corregir_duraciones(df: DataFrame) -> DataFrame:
    """Anula el fin (hora y coordenadas) cuando la duracion es inverosimil."""
    duracion_ok = (
        F.col("End_Time").isNotNull()
        & (F.col("End_Time") >= F.col("Start_Time"))
        & (F.col("End_Time") <= F.col("Start_Time") + F.expr(f"INTERVAL {MAX_DURATION_HOURS} HOURS"))
    )
    return (
        df.withColumn("End_Time", F.when(duracion_ok, F.col("End_Time")))
          .withColumn("End_Lat", F.when(duracion_ok, F.col("End_Lat")))
          .withColumn("End_Lng", F.when(duracion_ok, F.col("End_Lng")))
    )


def eliminar_duplicados(df: DataFrame) -> DataFrame:
    """Deja una sola fila por accidente repetido.

    Se conserva el reporte con el End_Time mas temprano (el original) y, en caso
    de empate, el ID menor. Asi el resultado es reproducible entre ejecuciones.
    """
    ventana = Window.partitionBy(*DEDUPE_KEY).orderBy(
        F.col("End_Time").asc_nulls_last(), F.col("ID").asc()
    )
    return (
        df.withColumn("_orden", F.row_number().over(ventana))
          .filter(F.col("_orden") == 1)
          .drop("_orden")
    )


def formatear_salida(df: DataFrame) -> DataFrame:
    """Devuelve fechas y booleanos al formato de texto del CSV original."""
    for col in TIMESTAMP_COLUMNS:
        df = df.withColumn(col, F.date_format(F.col(f"`{col}`"), "yyyy-MM-dd HH:mm:ss"))
    for col in BOOLEAN_COLUMNS:
        df = df.withColumn(
            col,
            F.when(F.col(f"`{col}`") == F.lit(True), F.lit("True"))
             .when(F.col(f"`{col}`") == F.lit(False), F.lit("False")),
        )
    return df.select(*[F.col(f"`{c}`") for c in COLUMN_ORDER])


def limpiar(df: DataFrame, deduplicar: bool = True) -> DataFrame:
    df = limpiar_texto(df)
    df = normalizar_categoricas(df)
    df = normalizar_tipos(df)

    df = anular_fuera_de_rango(df)

    # Filas sin datos criticos (incluidas coordenadas que acaban de anularse por
    # estar fuera de rango): no se pueden usar ni recuperar.
    df = df.filter(
        functools.reduce(operator.and_, [F.col(f"`{c}`").isNotNull() for c in CRITICAL_COLUMNS])
    )

    df = corregir_duraciones(df)
    if deduplicar:
        df = eliminar_duplicados(df)

    return formatear_salida(df)


# --------------------------------------------------------------------------
# Escritura
# --------------------------------------------------------------------------


def escribir_csv_unico(
    df: DataFrame,
    destino: Path,
    partes: int,
    temporal: Path,
) -> None:
    """Escribe el DataFrame como CSV y fusiona los part-* en un solo archivo."""
    if temporal.exists():
        shutil.rmtree(temporal)
    temporal.mkdir(parents=True, exist_ok=True)

    (df.coalesce(partes)
       .write
       .mode("overwrite")
       .option("header", "true")
       .option("quote", '"')
       .option("escape", '"')
       .option("nullValue", "")
       .option("emptyValue", "")
       .option("encoding", "UTF-8")
       .csv(str(temporal)))

    destino.parent.mkdir(parents=True, exist_ok=True)
    partes_csv = sorted(p for p in temporal.glob("part-*.csv"))
    if not partes_csv:
        raise RuntimeError(f"No se generaron archivos CSV en {temporal}")

    with destino.open("wb") as salida:
        for i, parte in enumerate(partes_csv):
            with parte.open("rb") as origen:
                if i > 0:  # salta el encabezado de las partes siguientes
                    origen.readline()
                shutil.copyfileobj(origen, salida, length=8 * 1024 * 1024)

    shutil.rmtree(temporal, ignore_errors=True)


def escribir_reporte(ruta: Path, filas: list[tuple[str, object]]) -> None:
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metrica", "valor"])
        writer.writerows(filas)


# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------


def main() -> int:
    raiz = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Limpieza de US Accidents con PySpark")
    parser.add_argument("--input", type=Path,
                        default=raiz / "data" / "us_accidents" / "US_Accidents_March23.csv")
    parser.add_argument("--out", type=Path,
                        default=raiz / "data" / "us_accidents_clean" / "US_Accidents_March23_clean.csv")
    parser.add_argument("--report", type=Path,
                        default=raiz / "data" / "us_accidents_clean" / "reporte_calidad.csv")
    parser.add_argument("--threads", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--driver-memory", default="4g",
                        help="Memoria del proceso driver de Spark, por ejemplo 6g.")
    parser.add_argument("--parts", type=int, default=4)
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="No eliminar registros repetidos del mismo accidente.")
    parser.add_argument("--multiline", action="store_true",
                        help="Usar si el CSV tiene saltos de linea dentro de campos entre comillas.")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: no existe el archivo de entrada: {args.input}")
        return 1

    inicio = time.time()
    configurar_hadoop_windows(raiz)
    spark = crear_spark(args.threads, args.driver_memory)
    spark.sparkContext.setLogLevel("ERROR")

    try:
        print("=" * 70)
        print("LIMPIEZA DE US ACCIDENTS CON PYSPARK")
        print("=" * 70)
        print(f"Entrada : {args.input}")
        print(f"Salida  : {args.out}")

        crudo = leer_csv(spark, args.input, args.multiline).persist(StorageLevel.DISK_ONLY)
        print("\n[1/4] Perfilando calidad de los datos crudos...")
        perfil = perfil_calidad(crudo)

        print(f"\nFilas crudas: {perfil['total']:,}")
        print(f"IDs duplicados: {perfil['duplicados_id']:,}")
        print(f"Duplicados por clave natural: {perfil['duplicados_clave']:,}")
        print(f"End_Lat/End_Lng nulos: {perfil['End_Lat__nulos']:,}")
        for col in ["Zipcode", "Timezone", "Weather_Condition", "Wind_Direction"]:
            print(f"Nulos en {col}: {perfil[f'{col}__nulos']:,}")

        print("\n[2/4] Aplicando reglas de limpieza...")
        limpio = limpiar(crudo, deduplicar=not args.keep_duplicates).persist(StorageLevel.DISK_ONLY)
        total_limpio = limpio.count()
        print(f"Filas limpias: {total_limpio:,} "
              f"(eliminadas {perfil['total'] - total_limpio:,})")

        print(f"\n[3/4] Escribiendo CSV limpio en {args.out} ...")
        escribir_csv_unico(limpio, args.out, args.parts,
                           args.out.parent / "_tmp_spark_csv")

        print(f"\n[4/4] Escribiendo reporte de calidad en {args.report} ...")
        filas_reporte: list[tuple[str, object]] = [("filas_crudas", perfil["total"]),
                                                   ("filas_limpias", total_limpio),
                                                   ("filas_eliminadas", perfil["total"] - total_limpio)]
        for clave, nombre in perfil["_nombres"]:
            filas_reporte.append((nombre, perfil[clave]))
        escribir_reporte(args.report, filas_reporte)

        print("\n" + "=" * 70)
        print(f"LISTO en {time.time() - inicio:.1f} s")
        print(f"CSV limpio : {args.out}")
        print(f"Reporte    : {args.report}")
        print("=" * 70)
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
